import io
import zipfile
from pathlib import Path

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse

from app.api.deps import require_admin

router = APIRouter(prefix="/api/plugin", tags=["plugin"], dependencies=[Depends(require_admin)])

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


@router.get("/download", summary="Download do plugin WordPress como .zip")
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
