"""
文件存储抽象层
- local:  本地文件系统（默认）
- minio:  S3 兼容对象存储（MinIO/OSS/COS/S3 都用同一套 API）
切换 backend 只需改 STORAGE_BACKEND + MinIO 凭证，业务代码零改动。
"""
import os
import secrets
import string
from datetime import datetime
from io import BytesIO
from pathlib import Path
from typing import Optional

from app.config import settings


# ============================================================
# 文件 ID 生成器：F-2026-XXXXXX
# ============================================================
def _gen_file_id() -> str:
    alphabet = string.ascii_uppercase + string.digits
    suffix = "".join(secrets.choice(alphabet) for _ in range(6))
    return f"F-{datetime.now().year}-{suffix}"


def _safe_ext(filename: str) -> str:
    _, ext = os.path.splitext(filename)
    ext = ext.lstrip(".").lower()
    return "".join(c for c in ext if c.isalnum())[:16] or "bin"


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


# ============================================================
# 本地存储（fallback）
# ============================================================
UPLOAD_ROOT = Path(__file__).resolve().parent.parent.parent / "uploads"


def _save_local(filename: str, content: bytes) -> dict:
    file_id = _gen_file_id()
    ext = _safe_ext(filename)
    now = datetime.now()
    rel_dir = Path(f"{now.year:04d}/{now.month:02d}/{now.day:02d}")
    abs_dir = UPLOAD_ROOT / rel_dir
    abs_dir.mkdir(parents=True, exist_ok=True)
    save_name = f"{file_id}.{ext}" if ext else file_id
    abs_path = abs_dir / save_name
    abs_path.write_bytes(content)
    rel_path = str(rel_dir / save_name)
    base = settings.PUBLIC_BASE_URL.rstrip("/")
    url = f"{base}/static/uploads/{rel_path}"
    return {
        "fileId": file_id,
        "name": filename,
        "size": len(content),
        "url": url,
        "mimeType": _guess_mime(ext),
        "ext": ext,
        "storage": "local",
    }


# ============================================================
# MinIO / S3 兼容对象存储
# ============================================================
_MINIO_CLIENT: Optional[object] = None


def _get_minio_client():
    """懒加载 MinIO 客户端（避免启动时无 MinIO 报错）"""
    global _MINIO_CLIENT
    if _MINIO_CLIENT is not None:
        return _MINIO_CLIENT
    try:
        from minio import Minio
        from minio.error import S3Error
        endpoint = settings.MINIO_ENDPOINT
        client = Minio(
            endpoint,
            access_key=settings.MINIO_ACCESS_KEY,
            secret_key=settings.MINIO_SECRET_KEY,
            secure=settings.MINIO_SECURE,
            region=settings.MINIO_REGION,
        )
        # 确保 bucket 存在
        bucket = settings.MINIO_BUCKET
        if not client.bucket_exists(bucket):
            client.make_bucket(bucket, location=settings.MINIO_REGION)
        _MINIO_CLIENT = client
        return client
    except Exception as e:
        raise RuntimeError(f"MinIO 客户端初始化失败：{e}")


def _save_minio(filename: str, content: bytes) -> dict:
    file_id = _gen_file_id()
    ext = _safe_ext(filename)
    now = datetime.now()
    # key 形如 2026/06/20/F-2026-XXXXXX.pdf
    key = f"{now.year:04d}/{now.month:02d}/{now.day:02d}/{file_id}.{ext}" if ext else f"{now.year:04d}/{now.month:02d}/{now.day:02d}/{file_id}"
    client = _get_minio_client()
    data = BytesIO(content)
    client.put_object(
        bucket_name=settings.MINIO_BUCKET,
        object_name=key,
        data=data,
        length=len(content),
        content_type=_guess_mime(ext),
    )
    # URL 拼接：minio_public_url > endpoint > 容器内/外 host
    public = settings.MINIO_PUBLIC_URL.strip() if settings.MINIO_PUBLIC_URL else ""
    if public:
        base = public.rstrip("/")
    else:
        # 容器内 = minio:9000；前端访问 = localhost:9000
        endpoint = settings.MINIO_ENDPOINT
        if "minio:" in endpoint:
            endpoint = endpoint.replace("minio:", "localhost:")
        base = f"http://{endpoint}"
    url = f"{base}/{settings.MINIO_BUCKET}/{key}"
    return {
        "fileId": file_id,
        "name": filename,
        "size": len(content),
        "url": url,
        "mimeType": _guess_mime(ext),
        "ext": ext,
        "storage": "minio",
    }


# ============================================================
# 统一入口：根据 STORAGE_BACKEND 选 backend
# ============================================================
async def save_file(filename: str, content: bytes) -> dict:
    """
    保存文件（自动选 backend）
    返回 {fileId, name, size, url, mimeType, ext}
    """
    backend = (settings.STORAGE_BACKEND or "local").lower()
    if backend == "minio":
        return _save_minio(filename, content)
    return _save_local(filename, content)


def get_abs_path(rel_url: str) -> Path:
    """从 url 推断本地绝对路径（用于服务静态文件）"""
    marker = "/static/uploads/"
    if marker in rel_url:
        rel = rel_url.split(marker, 1)[1]
        return UPLOAD_ROOT / rel
    return UPLOAD_ROOT


# ============================================================
# 健康检查（system_settings test-connection 用）
# ============================================================
async def health_check() -> dict:
    """检查存储 backend 是否可用"""
    backend = (settings.STORAGE_BACKEND or "local").lower()
    if backend == "minio":
        try:
            client = _get_minio_client()
            # stat bucket 验证连通性（不列举对象，避免 SDK 版本差异）
            from minio.commonconfig import ENABLED
            _ = client.bucket_exists(settings.MINIO_BUCKET)
            return {
                "status": "reachable",
                "backend": "minio",
                "endpoint": settings.MINIO_ENDPOINT,
                "bucket": settings.MINIO_BUCKET,
                "secure": settings.MINIO_SECURE,
                "region": settings.MINIO_REGION,
            }
        except Exception as e:
            return {"status": "down", "backend": "minio", "error": str(e)}
    # local：检查目录可写
    try:
        UPLOAD_ROOT.mkdir(parents=True, exist_ok=True)
        test = UPLOAD_ROOT / ".healthcheck"
        test.write_text("ok")
        test.unlink()
        return {"status": "reachable", "backend": "local", "uploadRoot": str(UPLOAD_ROOT)}
    except Exception as e:
        return {"status": "down", "backend": "local", "error": str(e)}
