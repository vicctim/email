import httpx

from app.config import get_settings


class WhatsAppNotifier:
    def __init__(self, timeout: float = 15.0) -> None:
        self.settings = get_settings()
        self.timeout = timeout

    async def send_message(self, text: str, number: str | None = None) -> bool:
        if not self.settings.evolution_api_url or not self.settings.evolution_api_key:
            return False

        target = number or self.settings.whatsapp_notify_number
        if not target:
            return False

        url = (
            str(self.settings.evolution_api_url).rstrip("/")
            + f"/message/sendText/{self.settings.evolution_instance}"
        )
        headers = {"apikey": self.settings.evolution_api_key}
        payload = {"number": target, "text": text}

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(url, json=payload, headers=headers)
                response.raise_for_status()
        except Exception:
            return False
        return True

    async def send_success(self, *, title: str, site: str, url: str | None) -> bool:
        return await self.send_message(f"✅ Post publicado: {title} → {site} — {url or ''}".strip())

    @staticmethod
    def _append_query_param(url: str, param: str, value: str) -> str:
        """Adiciona query param a uma URL, detectando se já existe ? na URL."""
        separator = "&" if "?" in url else "?"
        return f"{url}{separator}{param}={value}"

    async def send_approval_pending(self, *, title: str, site: str, url: str | None, token: str) -> bool:
        """Notifica que um post foi criado como rascunho e aguarda aprovação manual."""
        approval_url = self._append_query_param(url, "emailext_approve", token) if url else ""
        return await self.send_message(
            f"📝 Post aguardando aprovação: {title} → {site}\n"
            f"{approval_url}\n"
            "Clique no link acima para visualizar e aprovar o post."
        )

    async def send_approved(self, *, title: str, url: str | None) -> bool:
        """Notifica que um post foi aprovado e publicado."""
        msg = f"✅ Post aprovado e publicado: {title} — {url or ''}".strip()
        return await self.send_message(msg)

    async def send_error(self, *, title: str, error: str) -> bool:
        return await self.send_message(f"❌ Falha ao publicar: {title} — {error}")

