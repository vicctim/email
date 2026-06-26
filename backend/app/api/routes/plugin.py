import io
import logging
import zipfile
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, require_admin
from app.api.schemas import ApprovalRequest
from app.database.models import PublishQueue, PublishStatus, WordPressSite
from app.services.audit import add_audit_log
from app.workers.tasks import send_whatsapp_notification


logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/plugin", tags=["plugin"])

# O diretório do plugin é montado em /plugin no container (ver docker-compose)
PLUGIN_DIR = Path("/plugin/email-extractor")
PLUGIN_FILENAME = "email-extractor.zip"


def _build_zip() -> io.BytesIO:
    """Compacta o diretório do plugin em memória e retorna um BytesIO."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for file_path in PLUGIN_DIR.rglob("*"):
            if file_path.is_file():
                arcname = file_path.relative_to(PLUGIN_DIR.parent)
                zf.write(file_path, arcname)
    buf.seek(0)
    return buf


@router.get("/download", summary="Download do plugin WordPress como .zip", dependencies=[Depends(require_admin)])
async def download_plugin():
    """Retorna o plugin WordPress compactado como arquivo .zip para download."""
    buf = _build_zip()
    headers = {
        "Content-Disposition": f'attachment; filename="{PLUGIN_FILENAME}"',
        "Cache-Control": "no-cache",
    }
    return StreamingResponse(
        buf,
        media_type="application/zip",
        headers=headers,
    )


@router.get("/info", summary="Informações do plugin WordPress")
async def plugin_info():
    """Retorna metadados do plugin (versão, nome, etc.) para exibir no painel."""
    version = "desconhecido"
    plugin_main = PLUGIN_DIR / "email-extractor.php"
    if plugin_main.exists():
        content = plugin_main.read_text()
        for line in content.splitlines():
            if line.startswith("define('EMAILEXT_VERSION'"):
                parts = line.split("'")
                if len(parts) >= 4:
                    version = parts[3]
                break

    return {
        "name": "Email Extractor Bridge",
        "version": version,
        "filename": PLUGIN_FILENAME,
        "description": "Recebe posts automaticamente do sistema Email Extractor com suporte a aprovação manual.",
    }


@router.post("/approve", summary="Webhook de aprovação manual do post")
async def approve_post(payload: ApprovalRequest, session: AsyncSession = Depends(get_db)):
    """Recebido do plugin WordPress quando o cliente aprova um post manualmente."""
    # Busca o item de fila pelo post_id e approval_token
    stmt = (
        select(PublishQueue)
        .where(
            PublishQueue.approval_token == payload.approval_token,
            PublishQueue.post_id == payload.post_id,
            PublishQueue.status == PublishStatus.published,
        )
    )
    queue_item = await session.scalar(stmt)

    site = await session.get(WordPressSite, payload.site_id)

    if queue_item is None:
        if site:
            add_audit_log(
                session,
                event="approval_failed",
                message=f"Tentativa de aprovação inválida para post {payload.post_id} no site {site.name}: token não encontrado ou post já aprovado",
                payload=payload.model_dump(),
            )
            await session.commit()
        return {"ok": False, "message": "Token de aprovação inválido ou post já aprovado"}

    if queue_item.approved_at:
        return {"ok": False, "message": "Post já aprovado anteriormente"}

    # Só registramos no nosso banco (o plugin já mudou o status no WordPress)
    queue_item.approved_at = datetime.now(timezone.utc)

    add_audit_log(
        session,
        event="post_approved",
        message=f"Post {payload.post_id} aprovado manualmente no site {site.name if site else '?'}",
        payload={"post_id": payload.post_id, "site_id": payload.site_id, "queue_id": queue_item.id},
    )
    await session.commit()

    # Notifica WhatsApp que o post foi aprovado
    try:
        send_whatsapp_notification.apply_async(
            kwargs={
                "kind": "approved",
                "title": queue_item.email_subject or queue_item.parsed_title or f"Post #{payload.post_id}",
                "url": queue_item.post_url,
            },
            queue="notify",
        )
    except Exception:
        logger.exception("Falha ao enviar notificação de aprovação")

    return {"ok": True, "message": "Post aprovado com sucesso"}
