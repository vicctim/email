import mimetypes
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
from urllib.parse import urlparse

import httpx
from PIL import Image

from app.config import get_settings


SUPPORTED_IMAGE_FORMATS = {
    "JPEG": "image/jpeg",
    "PNG": "image/png",
    "WEBP": "image/webp",
}


@dataclass(frozen=True)
class DownloadedImage:
    filename: str
    content_type: str
    content: bytes


class ImageHandler:
    def __init__(
        self,
        timeout: float = 30.0,
        *,
        max_width: int | None = None,
        convert_to_webp: bool | None = None,
        webp_quality: int | None = None,
    ) -> None:
        settings = get_settings()
        self.timeout = timeout
        self.max_width = max_width if max_width is not None else settings.image_max_width
        self.convert_to_webp = (
            convert_to_webp if convert_to_webp is not None else settings.image_convert_to_webp
        )
        self.webp_quality = webp_quality if webp_quality is not None else settings.image_webp_quality

    async def download_image(self, url: str) -> DownloadedImage:
        if not url.startswith(("http://", "https://")):
            raise ValueError(f"URL de imagem inválida: {url}")

        async with httpx.AsyncClient(timeout=self.timeout, follow_redirects=True) as client:
            response = await client.get(url)
            response.raise_for_status()

        content = response.content
        content_type = self._validate_image(content, response.headers.get("content-type"))
        content, content_type = self._process_image(content, content_type)
        filename = self._filename_from_url(url, content_type)
        return DownloadedImage(filename=filename, content_type=content_type, content=content)

    async def upload_to_wordpress(
        self,
        *,
        site_url: str,
        username: str,
        app_password: str,
        image_url: str,
    ) -> int:
        image = await self.download_image(image_url)
        media_url = site_url.rstrip("/") + "/wp-json/wp/v2/media"
        headers = {
            "Content-Disposition": f'attachment; filename="{image.filename}"',
            "Content-Type": image.content_type,
        }

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(
                media_url,
                content=image.content,
                headers=headers,
                auth=(username, app_password),
            )
            response.raise_for_status()

        payload = response.json()
        media_id = payload.get("id")
        if not isinstance(media_id, int):
            raise ValueError("WordPress não retornou media_id válido")
        return media_id

    @staticmethod
    def _validate_image(content: bytes, content_type_header: str | None) -> str:
        try:
            image = Image.open(BytesIO(content))
            image.verify()
        except Exception as exc:
            raise ValueError("Arquivo baixado não é uma imagem válida") from exc

        format_name = (image.format or "").upper()
        if format_name not in SUPPORTED_IMAGE_FORMATS:
            raise ValueError(f"Formato de imagem não suportado: {format_name or 'desconhecido'}")

        detected = SUPPORTED_IMAGE_FORMATS[format_name]
        if content_type_header:
            content_type = content_type_header.split(";")[0].strip().lower()
            if content_type in SUPPORTED_IMAGE_FORMATS.values():
                return content_type
        return detected

    def _process_image(self, content: bytes, content_type: str) -> tuple[bytes, str]:
        with Image.open(BytesIO(content)) as image:
            image.load()
            resized = False
            if self.max_width and image.width > self.max_width:
                ratio = self.max_width / image.width
                height = max(1, int(image.height * ratio))
                image = image.resize((self.max_width, height), Image.Resampling.LANCZOS)
                resized = True

            if self.convert_to_webp:
                output = BytesIO()
                if image.mode not in {"RGB", "RGBA"}:
                    image = image.convert("RGBA" if "A" in image.getbands() else "RGB")
                image.save(output, format="WEBP", quality=self.webp_quality, method=6)
                return output.getvalue(), "image/webp"

            if not resized:
                return content, content_type

            output = BytesIO()
            format_name = {
                "image/jpeg": "JPEG",
                "image/png": "PNG",
                "image/webp": "WEBP",
            }[content_type]
            save_kwargs: dict[str, object] = {"optimize": True}
            if format_name == "JPEG":
                if image.mode != "RGB":
                    image = image.convert("RGB")
                save_kwargs["quality"] = 88
            elif format_name == "WEBP":
                save_kwargs["quality"] = self.webp_quality
                save_kwargs["method"] = 6
            image.save(output, format=format_name, **save_kwargs)
            return output.getvalue(), content_type

    @staticmethod
    def _filename_from_url(url: str, content_type: str) -> str:
        path = Path(urlparse(url).path)
        name = path.name or "email-image"
        suffix = path.suffix.lower()
        expected_suffix = mimetypes.guess_extension(content_type) or ".jpg"
        if suffix not in {".jpg", ".jpeg", ".png", ".webp"}:
            name += expected_suffix
        return name
