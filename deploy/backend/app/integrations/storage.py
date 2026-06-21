"""
文件存储抽象层（本地存储实现）
未来切到 OSS/S3 时，只改这个文件，业务代码不动。
"""
import os
import secrets
import string
from datetime import datetime
from pathlib import Path

from app.config import settings


# 文件 ID 生成器：F-2026-XXXXXX
def _gen_file_id() -> str:
    alphabet = string.ascii_uppercase + string.digits
    suffix = "".join(secrets.choice(alphabet) for _ in range(6))
    return f"F-{datetime.now().year}-{suffix}"


# 上传根目录（绝对路径）
UPLOAD_ROOT = Path(__file__).resolve().parent.parent.parent / "uploads"


def _safe_ext(filename: str) -> str:
    """提取安全的扩展名（最多 16 字符，仅允许字母数字）"""
    _, ext = os.path.splitext(filename)
    ext = ext.lstrip(".").lower()
    return "".join(c for c in ext if c.isalnum())[:16] or "bin"


async def save_file(filename: str, content: bytes) -> dict:
    """
    保存文件到本地
    返回 {fileId, name, size, url, mimeType, ext}
    """
    file_id = _gen_file_id()
    ext = _safe_ext(filename)
    now = datetime.now()
    rel_dir = Path(f"{now.year:04d}/{now.month:02d}/{now.day:02d}")
    abs_dir = UPLOAD_ROOT / rel_dir
    abs_dir.mkdir(parents=True, exist_ok=True)

    save_name = f"{file_id}.{ext}" if ext else file_id
    abs_path = abs_dir / save_name
    abs_path.write_bytes(content)

    # 相对路径（用于静态文件挂载）
    rel_path = str(rel_dir / save_name)
    # 公网 URL（开发环境直接给 localhost:8000 静态路径）
    base = settings.PUBLIC_BASE_URL.rstrip("/") if hasattr(settings, "PUBLIC_BASE_URL") and settings.PUBLIC_BASE_URL else "http://localhost"
    url = f"{base}/static/uploads/{rel_path}"

    return {
        "fileId": file_id,
        "name": filename,
        "size": len(content),
        "url": url,
        "mimeType": _guess_mime(ext),
        "ext": ext,
    }


def _guess_mime(ext: str) -> str:
    common = {
        "pdf": "application/pdf",
        "png": "image/png",
        "jpg": "image/jpeg",
        "jpeg": "image/jpeg",
        "webp": "image/webp",
        "ofd": "application/ofd",
        "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "txt": "text/plain",
    }
    return common.get(ext, "application/octet-stream")


def get_abs_path(rel_url: str) -> Path:
    """从 url 推断本地绝对路径（用于服务静态文件）"""
    # url 形如 http://localhost:8000/static/uploads/2026/06/13/F-2026-XXXXXX.pdf
    marker = "/static/uploads/"
    if marker in rel_url:
        rel = rel_url.split(marker, 1)[1]
        return UPLOAD_ROOT / rel
    return UPLOAD_ROOT
