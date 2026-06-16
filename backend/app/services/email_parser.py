import hashlib
import re
from dataclasses import dataclass
from difflib import SequenceMatcher
from email import policy
from email.message import EmailMessage
from email.parser import BytesParser
from html import unescape
from urllib.parse import urljoin

import bleach
from bs4 import BeautifulSoup
from bs4.element import NavigableString, Tag


FOOTER_PATTERNS = (
    "todos os direitos reservados",
    "unsubscribe",
    "descadastre",
    "não deseja mais receber",
    "nao deseja mais receber",
    "visualizar este email",
    "view this email",
)

SUBJECT_PREFIX_RE = re.compile(r"^\s*((re|fw|fwd|enc|tr)\s*:\s*)+", re.IGNORECASE)
STYLE_SIZE_RE = re.compile(r"(?:width|height)\s*:\s*(\d+)px", re.IGNORECASE)
TRACKING_URL_PATTERNS = (
    "/open/",
    "/track/",
    "/pixel",
    "beacon",
    "addcampaignemailcountopen",
    "trk.",
    "click.mlsend",
)
SAFE_TAGS = {
    "p",
    "h1",
    "h2",
    "h3",
    "h4",
    "h5",
    "h6",
    "a",
    "strong",
    "em",
    "ul",
    "ol",
    "li",
    "blockquote",
    "img",
    "br",
}
SAFE_ATTRIBUTES = {
    "a": ["href", "title", "target", "rel"],
    "img": ["src", "alt", "title", "width", "height"],
}
SAFE_PROTOCOLS = {"http", "https", "mailto"}


@dataclass(frozen=True)
class ParsedEmail:
    title: str
    excerpt: str | None
    content_html: str
    featured_image_url: str | None
    gallery_image_urls: list[str]
    content_hash: str

    def as_dict(self) -> dict[str, object]:
        return {
            "title": self.title,
            "excerpt": self.excerpt,
            "content_html": self.content_html,
            "featured_image_url": self.featured_image_url,
            "gallery_image_urls": self.gallery_image_urls,
            "content_hash": self.content_hash,
        }


class EmailParser:
    allowed_blocks = {"p", "h1", "h2", "h3", "h4", "h5", "h6", "ul", "ol", "blockquote"}
    allowed_inline = {"a", "strong", "b", "em", "i", "br", "span", "li", "img"}
    table_text_tags = {"td", "div"}  # fallback para emails tipo newsletter

    def parse_message(
        self,
        raw_email: bytes,
        *,
        remove_signature: bool = True,
        remove_footer: bool = True,
        convert_bold_to_h3: bool = True,
        extract_gallery: bool = True,
    ) -> ParsedEmail:
        message = BytesParser(policy=policy.default).parsebytes(raw_email)
        subject = str(message.get("subject", "") or "")
        kwargs = dict(
            subject=subject,
            remove_signature=remove_signature,
            remove_footer=remove_footer,
            convert_bold_to_h3=convert_bold_to_h3,
            extract_gallery=extract_gallery,
        )
        parsed = self.parse_html(self.extract_html(message), **kwargs)
        # Fallback: HTML sem conteúdo textual (ex: email image-only) — tenta text/plain
        if not parsed.content_html.strip():
            plain_html = self._plain_text_to_html(message)
            if plain_html:
                parsed = self.parse_html(plain_html, **kwargs)
        return parsed

    def parse_html(
        self,
        html: str,
        *,
        subject: str,
        base_url: str | None = None,
        remove_signature: bool = True,
        remove_footer: bool = True,
        convert_bold_to_h3: bool = True,
        extract_gallery: bool = True,
    ) -> ParsedEmail:
        soup = BeautifulSoup(html or "", "lxml")
        container = soup.body or soup

        for tag in container.find_all(["script", "style", "meta", "link"]):
            tag.decompose()

        if remove_signature or remove_footer:
            self._remove_footer_blocks(container)

        title = self.clean_subject(subject)
        heading = container.find(["h1", "h2"])
        if not title and heading:
            title = heading.get_text(" ", strip=True)
        title = title or "Sem título"

        self._remove_duplicate_title_block(container, title)
        self._convert_lead_emphasis_to_blockquote(container)

        excerpt_tag = container.find("blockquote")
        excerpt = excerpt_tag.get_text(" ", strip=True) if excerpt_tag else None

        image_urls = self._image_urls(container, base_url)
        featured_image_url = self._featured_image_url(container, image_urls)
        gallery_image_urls = (
            self._trailing_gallery_urls(container, featured_image_url, base_url)
            if extract_gallery
            else []
        )

        content_html = self._content_html(
            container,
            convert_bold_to_h3=convert_bold_to_h3,
            excluded_images={url for url in [featured_image_url, *gallery_image_urls] if url},
        )

        # Fallback: email com layout em tabela (newsletters) — extrai de td/div
        if not content_html.strip():
            content_html = self._table_fallback_html(container)

        content_html = self.sanitize_html(content_html)
        content_hash = hashlib.sha256(f"{title}\n{content_html}".encode("utf-8")).hexdigest()

        return ParsedEmail(
            title=title,
            excerpt=excerpt,
            content_html=content_html,
            featured_image_url=featured_image_url,
            gallery_image_urls=gallery_image_urls,
            content_hash=content_hash,
        )

    def normalize_content_html(self, html: str, *, title: str | None = None) -> str:
        soup = BeautifulSoup(html or "", "lxml")
        container = soup.body or soup
        if title:
            self._remove_duplicate_title_block(container, title)
        self._convert_lead_emphasis_to_blockquote(container)
        content_html = self._content_html(
            container,
            convert_bold_to_h3=True,
            excluded_images=set(),
        )
        return self.sanitize_html(content_html)

    @staticmethod
    def clean_subject(subject: str) -> str:
        decoded = unescape(subject or "").strip()
        return SUBJECT_PREFIX_RE.sub("", decoded).strip()

    @staticmethod
    def sanitize_html(html: str) -> str:
        return bleach.clean(
            html or "",
            tags=SAFE_TAGS,
            attributes=SAFE_ATTRIBUTES,
            protocols=SAFE_PROTOCOLS,
            strip=True,
            strip_comments=True,
        )

    @staticmethod
    def extract_html(message: EmailMessage) -> str:
        html_part = message.get_body(preferencelist=("html",))
        if html_part:
            payload = html_part.get_content()
            return payload if isinstance(payload, str) else payload.decode(errors="replace")
        return EmailParser._plain_text_to_html(message)

    @staticmethod
    def _plain_text_to_html(message: EmailMessage) -> str:
        plain_part = message.get_body(preferencelist=("plain",))
        if not plain_part:
            return ""
        text = plain_part.get_content()
        if not isinstance(text, str):
            text = text.decode(errors="replace")
        paragraphs = [f"<p>{line.strip()}</p>" for line in text.splitlines() if line.strip()]
        return "\n".join(paragraphs)

    @staticmethod
    def _is_tracking_pixel(image: Tag) -> bool:
        url = (EmailParser._img_src(image) or "").lower()
        if any(p in url for p in TRACKING_URL_PATTERNS):
            return True
        for attr in ("width", "height"):
            raw = str(image.get(attr, "") or "")
            match = re.search(r"\d+", raw)
            if match and int(match.group()) <= 2:
                return True
        return False

    def _remove_footer_blocks(self, container: Tag) -> None:
        for tag in list(container.find_all(["p", "div", "span", "td", "table", "footer"])):
            text = tag.get_text(" ", strip=True).lower()
            if not text:
                continue
            # Só remove blocos que são claramente footer/assinatura
            # e que não têm conteúdo substancial (>120 chars é provavel conteúdo real)
            is_short = len(text) <= 120
            has_footer_pattern = any(pattern in text for pattern in FOOTER_PATTERNS) or "©" in tag.get_text(" ", strip=True)
            if has_footer_pattern and is_short:
                tag.decompose()
                continue
            if tag.name == "table" and self._looks_like_signature_table(tag):
                tag.decompose()

    def _remove_duplicate_title_block(self, container: Tag, title: str) -> None:
        normalized_title = self._normalize_text(title)
        if not normalized_title:
            return

        for tag in container.find_all(["h1", "h2", "h3", "h4", "h5", "h6", "p", "div", "td"], recursive=True):
            if not isinstance(tag, Tag):
                continue
            if tag.name in {"div", "td"} and tag.find(["h1", "h2", "h3", "h4", "h5", "h6", "p", "div", "td"], recursive=False):
                continue

            text = tag.get_text(" ", strip=True)
            if not text:
                continue
            if self._is_duplicate_title_text(text, title):
                tag.decompose()
                return

    def _convert_lead_emphasis_to_blockquote(self, container: Tag) -> None:
        for tag in container.find_all(["p", "div", "em", "i"], recursive=True):
            if not isinstance(tag, Tag):
                continue
            if tag.name in {"em", "i"} and isinstance(tag.parent, Tag) and tag.parent.name in {"p", "div"}:
                continue
            if tag.name == "div" and tag.find(["p", "div", "blockquote"], recursive=False):
                continue
            if not tag.get_text(" ", strip=True):
                continue
            if not self._is_isolated_emphasis_block(tag):
                return

            emphasis = tag if tag.name in {"em", "i"} else tag.find(["em", "i"])
            if not emphasis:
                return
            html = emphasis.decode_contents().strip()
            if not html:
                return
            blockquote = BeautifulSoup(f"<blockquote>{html}</blockquote>", "lxml").blockquote
            if blockquote:
                tag.replace_with(blockquote)
            return

    @staticmethod
    def _is_isolated_emphasis_block(tag: Tag) -> bool:
        if tag.name in {"em", "i"}:
            return bool(tag.get_text(" ", strip=True))
        children = [child for child in tag.contents if not (isinstance(child, NavigableString) and not child.strip())]
        if len(children) != 1 or not isinstance(children[0], Tag):
            return False
        return children[0].name in {"em", "i"} and bool(children[0].get_text(" ", strip=True))

    @staticmethod
    def _normalize_text(value: str) -> str:
        return re.sub(r"\s+", " ", unescape(value or "").strip()).casefold()

    @classmethod
    def _is_duplicate_title_text(cls, text: str, title: str) -> bool:
        normalized_text = cls._normalize_text(text)
        normalized_title = cls._normalize_text(title)
        if not normalized_text or not normalized_title:
            return False
        if normalized_text == normalized_title:
            return True
        similarity = SequenceMatcher(None, normalized_text, normalized_title).ratio()
        return similarity >= 0.86

    @staticmethod
    def _looks_like_signature_table(tag: Tag) -> bool:
        text = tag.get_text(" ", strip=True).lower()
        if not text:
            return False
        signature_terms = ("telefone", "whatsapp", "assessoria", "imprensa", "cargo", "email", "@")
        image_count = len(tag.find_all("img"))
        return image_count <= 3 and sum(term in text for term in signature_terms) >= 2

    def _image_urls(self, container: Tag, base_url: str | None = None) -> list[str]:
        urls: list[str] = []
        for image in container.find_all("img"):
            if self._is_tracking_pixel(image):
                continue
            url = self._img_src(image, base_url)
            if url and url not in urls:
                urls.append(url)
        return urls

    def _featured_image_url(self, container: Tag, image_urls: list[str]) -> str | None:
        for image in container.find_all("img"):
            if self._is_tracking_pixel(image):
                continue
            url = self._img_src(image)
            if url and self._is_large_image(image):
                return url
        return image_urls[0] if image_urls else None

    def _trailing_gallery_urls(
        self,
        container: Tag,
        featured_image_url: str | None,
        base_url: str | None,
    ) -> list[str]:
        stream: list[tuple[str, str | None]] = []
        for node in container.descendants:
            if isinstance(node, Tag) and node.name == "img":
                if self._is_tracking_pixel(node):
                    continue
                stream.append(("img", self._img_src(node, base_url)))
            elif isinstance(node, NavigableString):
                text = str(node).strip()
                if text:
                    stream.append(("text", text))

        gallery: list[str] = []
        for kind, value in reversed(stream):
            if kind == "img" and value and value != featured_image_url:
                gallery.insert(0, value)
                continue
            if kind == "text" and value and gallery:
                break
        return self._dedupe(gallery)

    def _content_html(
        self,
        container: Tag,
        *,
        convert_bold_to_h3: bool,
        excluded_images: set[str],
    ) -> str:
        blocks: list[str] = []
        for tag in container.find_all(list(self.allowed_blocks), recursive=True):
            if self._has_block_ancestor(tag):
                continue
            html = self._clean_block(tag, convert_bold_to_h3, excluded_images)
            if html:
                blocks.append(html)
        return "\n".join(blocks)

    def _table_fallback_html(self, container: Tag) -> str:
        """Fallback para emails com layout em tabela: extrai parágrafos de td/div."""
        seen_texts: set[str] = set()
        blocks: list[str] = []
        for tag in container.find_all(["td", "div", "p"], recursive=True):
            # Pula se tem filhos que já são containers (evita duplicar)
            children_blocks = tag.find_all(["td", "div", "p"], recursive=False)
            if children_blocks:
                continue
            text = tag.get_text(" ", strip=True)
            if not text or len(text) < 20 or text in seen_texts:
                continue
            # Ignora rodapé / footer patterns
            if any(p in text.lower() for p in FOOTER_PATTERNS) or "©" in text:
                continue
            seen_texts.add(text)
            # Wraps como parágrafo simples
            safe = text.replace("<", "&lt;").replace(">", "&gt;")
            blocks.append(f"<p>{safe}</p>")
        return "\n".join(blocks)

    def _clean_block(self, tag: Tag, convert_bold_to_h3: bool, excluded_images: set[str]) -> str:
        clone = BeautifulSoup(str(tag), "lxml").find(tag.name)
        if clone is None:
            return ""

        for image in list(clone.find_all("img")):
            url = self._img_src(image)
            if not url or url in excluded_images:
                image.decompose()

        if convert_bold_to_h3 and clone.name == "p" and self._is_isolated_bold_paragraph(clone):
            bold = clone.find(["strong", "b"])
            text = bold.decode_contents().strip() if bold else clone.get_text(" ", strip=True)
            return f"<h3>{text}</h3>" if text else ""

        for child in list(clone.find_all(True)):
            if child.name not in self.allowed_blocks | self.allowed_inline:
                child.unwrap()
                continue
            if child.name == "a":
                href = child.get("href")
                child.attrs = {"href": href} if href else {}
                if href and href.startswith("http"):
                    child.attrs.update({"target": "_blank", "rel": "noopener noreferrer"})
            elif child.name == "img":
                src = self._img_src(child)
                attrs = {"src": src} if src else {}
                for attr in ("alt", "title", "width", "height"):
                    value = child.get(attr)
                    if value:
                        attrs[attr] = str(value)
                child.attrs = attrs
            else:
                child.attrs = {}

        text = clone.get_text(" ", strip=True)
        if not text and not clone.find("img"):
            return ""
        return str(clone)

    @staticmethod
    def _is_isolated_bold_paragraph(tag: Tag) -> bool:
        children = [child for child in tag.contents if not (isinstance(child, NavigableString) and not child.strip())]
        if len(children) != 1 or not isinstance(children[0], Tag):
            return False
        child = children[0]
        return child.name in {"strong", "b"} and bool(child.get_text(" ", strip=True))

    @staticmethod
    def _has_block_ancestor(tag: Tag) -> bool:
        parent = tag.parent
        while isinstance(parent, Tag):
            if parent.name in {"ul", "ol", "blockquote"}:
                return True
            parent = parent.parent
        return False

    @staticmethod
    def _is_large_image(image: Tag) -> bool:
        dimensions = []
        for attr in ("width", "height"):
            raw = str(image.get(attr, "") or "")
            match = re.search(r"\d+", raw)
            if match:
                dimensions.append(int(match.group()))
        style = str(image.get("style", "") or "")
        dimensions.extend(int(match.group(1)) for match in STYLE_SIZE_RE.finditer(style))
        return any(value > 200 for value in dimensions) if dimensions else True

    @staticmethod
    def _img_src(image: Tag, base_url: str | None = None) -> str | None:
        for attr in ("src", "data-src", "data-original"):
            value = image.get(attr)
            if value:
                url = str(value).strip()
                if url.startswith("cid:"):
                    return None
                return urljoin(base_url, url) if base_url else url
        return None

    @staticmethod
    def _dedupe(values: list[str]) -> list[str]:
        seen: set[str] = set()
        result: list[str] = []
        for value in values:
            if value not in seen:
                seen.add(value)
                result.append(value)
        return result
