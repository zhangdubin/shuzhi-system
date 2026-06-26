"""
图片/文档转码器（R18.1）
- 在 OCR 之前把不支持的格式（PDF/HEIC/WEBP/...）转成标准 JPEG
- 支持格式：
  - PDF 多页：转第一页为 JPEG（OCR 业务只取一张主发票）
  - HEIC/HEIF：pillow-heif 解码 → JPEG
  - WEBP/GIF/BMP/TIFF：Pillow 直接转 JPEG
  - JPEG/PNG：跳过（已是标准）
- 失败时抛 OCRFailedException（让上层走标准失败路径）
- 关键：把转码结果重新存到 storage，返回新 url（OCR 端拿新 url 拉图）
"""
import asyncio
import io
from pathlib import Path
from typing import Tuple

import httpx

from app.core.exceptions import OCRFailedException


# 探测魔数（不依赖文件名扩展名，更稳）
_PDF_MAGIC = b"%PDF"
_HEIC_MAGIC = (b"ftypheic", b"ftypheix", b"ftypheim", b"ftypheis", b"ftypmif1")
_HEIF_MAGIC = (b"ftypheic", b"ftypmif1", b"ftypmsf1")
_WEBP_MAGIC = b"RIFF"
_JPEG_MAGIC = (b"\xff\xd8\xff",)
_PNG_MAGIC = (b"\x89PNG\r\n\x1a\n",)


def _detect_format(head: bytes) -> str:
    """根据文件头 16 字节判断格式（返回 'pdf'/'heic'/'webp'/'jpeg'/'png'/'unknown'）"""
    if head.startswith(_PDF_MAGIC):
        return "pdf"
    for m in _JPEG_MAGIC:
        if head.startswith(m):
            return "jpeg"
    if head.startswith(_PNG_MAGIC):
        return "png"
    for m in _HEIC_MAGIC:
        if m in head[:32]:
            return "heic"
    for m in _HEIF_MAGIC:
        if m in head[:32]:
            return "heif"
    if head.startswith(_WEBP_MAGIC) and head[8:12] == b"WEBP":
        return "webp"
    return "unknown"


def _to_internal_url(url: str) -> str:
    """公网 URL → 后端容器内可达的内部 URL（minio:9000 / shuzhi-backend:8000）"""
    if not url:
        return url
    from app.config import settings
    import re
    if settings.STORAGE_BACKEND == "minio":
        public = settings.MINIO_PUBLIC_URL or ""
        m = re.match(r"https?://[^:/]+(?::(\d+))?", public)
        if m:
            port = m.group(1) or "9000"
            url = re.sub(rf"http://localhost:{port}", f"http://minio:{port}", url)
            url = re.sub(rf"https://localhost:{port}", f"https://minio:{port}", url)
    url = re.sub(r"http://localhost:8000/static/uploads", "http://shuzhi-backend:8000/static/uploads", url)
    return url


async def _download(url: str, timeout: float = 30.0) -> bytes:
    """下载远端文件到内存"""
    # 容器内重写：localhost:9000 (公网 MinIO) → minio:9000 (容器内网络)
    url = _to_internal_url(url)
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            r = await client.get(url)
            r.raise_for_status()
            return r.content
    except (httpx.TimeoutException, httpx.HTTPError) as e:
        raise OCRFailedException(f"下载文件失败: {e}") from e


def _convert_pdf_to_jpeg(data: bytes) -> bytes:
    """PDF → 第一页 JPEG（用 PyMuPDF，不依赖 poppler）"""
    try:
        import fitz  # PyMuPDF
    except ImportError:
        raise OCRFailedException("PDF 转码需要 PyMuPDF，请 pip install pymupdf")
    try:
        doc = fitz.open(stream=data, filetype="pdf")
        if len(doc) == 0:
            raise OCRFailedException("PDF 没有可识别页面")
        page = doc.load_page(0)
        # 2x 缩放提高 OCR 精度（PaddleOCR 推荐 300dpi）
        mat = fitz.Matrix(2, 2)
        pix = page.get_pixmap(matrix=mat, alpha=False)
        # pix.tobytes("jpeg") 直接给 JPEG 字节
        return pix.tobytes("jpeg", jpg_quality=92)
    except OCRFailedException:
        raise
    except Exception as e:
        raise OCRFailedException(f"PDF 转码失败: {e}") from e
    finally:
        try:
            doc.close()
        except Exception:
            pass


def _convert_pil_to_jpeg(data: bytes, source_fmt: str) -> bytes:
    """HEIC/WEBP/GIF/BMP/TIFF → JPEG"""
    try:
        from PIL import Image
    except ImportError:
        raise OCRFailedException("图片转码需要 Pillow")
    # HEIC 需要 pillow-heif 注册
    if source_fmt in ("heic", "heif"):
        try:
            import pillow_heif
            pillow_heif.register_heif_opener()
        except ImportError:
            raise OCRFailedException(
                "HEIC/HEIF 解码需要 pillow-heif + libheif 系统库，"
                "请安装 libheif-dev 后 pip install pillow-heif"
            )
    try:
        img = Image.open(io.BytesIO(data))
        # 统一转 RGB（HEIC 可能是 RGBA / 带 alpha）
        if img.mode in ("RGBA", "LA", "P"):
            bg = Image.new("RGB", img.size, (255, 255, 255))
            if img.mode == "P":
                img = img.convert("RGBA")
            bg.paste(img, mask=img.split()[-1] if img.mode in ("RGBA", "LA") else None)
            img = bg
        elif img.mode != "RGB":
            img = img.convert("RGB")
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=92, optimize=True)
        return buf.getvalue()
    except OCRFailedException:
        raise
    except Exception as e:
        raise OCRFailedException(f"{source_fmt.upper()} 转码失败: {e}") from e


async def normalize_to_jpeg(
    file_url: str,
    file_id: str,
    save_callback,
) -> Tuple[str, str, int]:
    """
    把任意支持的格式归一化到 JPEG
    返回 (new_url, new_filename, new_size)
    - 已是 JPEG/PNG：返回原 url（不重新存，节省 IO）
    - 其他格式：转码后调 save_callback(filename, jpeg_bytes) 存到 storage
    """
    data = await _download(file_url)
    head = data[:32]
    fmt = _detect_format(head)

    # 已是标准格式 → 不动
    if fmt in ("jpeg", "png"):
        return file_url, f"{file_id}.{fmt}", len(data)

    # 需要转码
    if fmt == "pdf":
        jpeg_bytes = await asyncio.to_thread(_convert_pdf_to_jpeg, data)
        new_name = f"{file_id}.pdf-page1.jpg"
    elif fmt in ("heic", "heif", "webp"):
        jpeg_bytes = await asyncio.to_thread(_convert_pil_to_jpeg, data, fmt)
        new_name = f"{file_id}.{fmt}.jpg"
    else:
        # 未知格式 → 试一次用 PIL 打开（兜底）
        try:
            jpeg_bytes = await asyncio.to_thread(_convert_pil_to_jpeg, data, fmt)
            new_name = f"{file_id}.{fmt or 'img'}.jpg"
        except OCRFailedException as e:
            raise OCRFailedException(
                f"不支持的文件格式（检测到 {fmt or '未知'}），请上传 JPEG/PNG/PDF/HEIC/WEBP"
            ) from e

    info = await save_callback(new_name, jpeg_bytes)
    return info["url"], new_name, len(jpeg_bytes)
