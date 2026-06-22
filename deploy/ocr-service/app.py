"""
PaddleOCR 微服务（端口 8001）
- POST /recognize   调真 PaddleOCR 识别图片 + 字段抽取
- GET  /health      健康检查
- GET  /version     模型版本

协议（与后端 ocr_client._real_recognize 对齐）：
  请求：{file_url, file_id, fields, language, options}
  响应：{code, fields, items, confidence, model, version, elapsedMs}
"""
import logging
import os
import time
from pathlib import Path
from typing import Optional

import httpx
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn

# 引入同目录的 engine 和 postprocess
from engine import get_engine, recognize_image, warmup
from postprocess import extract_invoice_fields

logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("paddleocr")

app = FastAPI(
    title="PaddleOCR Service",
    description="增值税发票识别（PaddleOCR v4 + 正则字段抽取）",
    version="1.0.0",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================
# 模型
# ============================================================
class RecognizeReq(BaseModel):
    file_url: str
    file_id: str = ""
    fields: list[str] = []
    language: str = "zh-CN"
    options: dict = {}


# ============================================================
# 端点
# ============================================================
@app.on_event("startup")
def _startup():
    """启动时预热模型（避免首请求慢）"""
    logger.info("[PaddleOCR] 服务启动中，预热模型...")
    t0 = time.time()
    if warmup():
        logger.info(f"[PaddleOCR] 预热完成，耗时 {time.time() - t0:.1f}s")
    else:
        logger.warning("[PaddleOCR] 预热失败，将在首次请求时重试")


@app.get("/health")
async def health():
    """健康检查（Docker / 业务侧用）"""
    from engine import is_ready
    return {
        "status": "ok" if is_ready() else "loading",
        "service": "paddleocr",
        "version": "1.0.0",
        "model": "ch_PP-OCRv4",
    }


@app.get("/version")
async def version():
    return {
        "service": "paddleocr",
        "version": "1.0.0",
        "model": "ch_PP-OCRv4",
        "engine": "PaddleOCR 2.7.0.3",
    }


@app.get("/debug/recognize")
async def debug_recognize(file_url: str):
    """调试用：返回 PaddleOCR 原始识别结果（带位置）"""
    from engine import recognize_image
    local_path = await _download_or_locate(file_url)
    result = recognize_image(local_path)
    rows = []
    for page in result:
        for poly, text, conf in page:
            cy = sum(p[1] for p in poly) / 4
            cx = sum(p[0] for p in poly) / 4
            rows.append({
                "y": round(cy, 1),
                "x": round(cx, 1),
                "conf": round(conf, 3),
                "text": text,
            })
    rows.sort(key=lambda r: (r["y"], r["x"]))
    return {"rows": rows, "count": len(rows)}


@app.post("/recognize")
async def recognize(req: RecognizeReq):
    """
    识别一张发票图片
    支持的 file_url：
      - http(s)://... 远程 URL（下载）
      - file://... 或 /abs/path 本地路径
      - 相对路径：相对于 OCR_UPLOAD_DIR（默认 /app/uploads）
    """
    t0 = time.time()
    try:
        # 1. 准备本地图片路径
        local_path = await _download_or_locate(req.file_url)
        logger.info(f"[recognize] file_id={req.file_id} file_url={req.file_url} -> {local_path}")

        # 2. PaddleOCR 识别
        ocr_result = recognize_image(local_path)
        if not ocr_result:
            return _fail(req, "未识别到文本", elapsed_ms=int((time.time() - t0) * 1000))

        # 取第一页的所有行
        all_items = ocr_result[0] if ocr_result else []
        if not all_items:
            return _fail(req, "未识别到文本行", elapsed_ms=int((time.time() - t0) * 1000))

        logger.info(f"[recognize] 识别到 {len(all_items)} 行")

        # 3. 字段抽取（在此之前先保留原始 OCR 行，供 postprocess 走分支使用）
        raw_rows = [
            {"y": round(sum(p[1] for p in poly) / 4, 1),
             "x": round(sum(p[0] for p in poly) / 4, 1),
             "conf": round(conf, 3),
             "text": text}
            for poly, text, conf in all_items
        ]
        # 检测标题/关键字，推断票种类型
        full_text_lower = " ".join(t for _, t, _ in all_items).lower()
        hint = ""
        if "航空运输电子客票行程单" in full_text_lower or "航空运输" in full_text_lower or "民航发展基金" in full_text_lower or "燃油附加费" in full_text_lower or "航班号" in full_text_lower:
            hint = "flight_ticket"
        elif "铁路电子客票" in full_text_lower or "车次" in full_text_lower or "二等座" in full_text_lower:
            hint = "train_ticket"
        elif "增值税" in full_text_lower or "价税合计" in full_text_lower or "税率" in full_text_lower:
            hint = "vat_invoice"

        fields = extract_invoice_fields(all_items)

        # 4. 计算综合置信度
        overall_conf = sum(c for _, _, c in all_items) / max(1, len(all_items))

        elapsed_ms = int((time.time() - t0) * 1000)
        logger.info(f"[recognize] 完成: conf={overall_conf:.3f} hint={hint} fields={list(fields.keys())} elapsed={elapsed_ms}ms")

        return {
            "code": 0,
            "message": "ok",
            "fileId": req.file_id,
            "fileUrl": req.file_url,
            "rawText": raw_rows,
            "invoiceTypeHint": hint,
            "fields": fields,
            "items": fields.get("items", {}).get("value", []) if isinstance(fields.get("items"), dict) else fields.get("items", []),
            "confidence": round(overall_conf, 3),
            "model": "paddleocr-v4",
            "version": "1.0.0",
            "elapsedMs": elapsed_ms,
        }
    except HTTPException:
        raise
    except FileNotFoundError as e:
        return _fail(req, f"图片未找到: {e}", elapsed_ms=int((time.time() - t0) * 1000))
    except Exception as e:
        logger.exception(f"[recognize] 异常: {e}")
        return _fail(req, f"识别异常: {str(e)[:200]}", elapsed_ms=int((time.time() - t0) * 1000))


async def _download_or_locate(file_url: str) -> str:
    """把 file_url 转成本地可访问的图片路径"""
    if not file_url:
        raise FileNotFoundError("file_url 为空")

    # http(s) 远程下载
    if file_url.startswith("http://") or file_url.startswith("https://"):
        # 替换 host：环境变量 BACKEND_URL 替换成容器内的 backend 地址
        # 例：file_url = "http://localhost:8000/static/uploads/xxx.png"
        #     BACKEND_URL = "http://shuzhi-backend:8000"
        #     → "http://shuzhi-backend:8000/static/uploads/xxx.png"
        backend_url = os.getenv("BACKEND_URL", "").rstrip("/")
        if backend_url and "localhost" in file_url and "/static/uploads" in file_url:
            # 把 localhost[:port] 替换成 backend_url（兼容带/不带端口的 URL）
            import re
            file_url = re.sub(r"http://localhost(:\d+)?", backend_url, file_url)
            logger.info(f"[recognize] 替换 file_url -> {file_url}")
        async with httpx.AsyncClient(timeout=30) as client:
            r = await client.get(file_url)
            r.raise_for_status()
            tmp = Path(f"/tmp/ocr_{int(time.time()*1000)}")
            tmp.write_bytes(r.content)
            return str(tmp)

    # file:// 本地
    if file_url.startswith("file://"):
        return file_url[7:]

    # 相对路径 → OCR_UPLOAD_DIR 下找
    if not file_url.startswith("/"):
        upload_dir = Path(os.getenv("OCR_UPLOAD_DIR", "/app/uploads"))
        local = upload_dir / file_url
        if local.exists():
            return str(local)
        # 也试 uploads/<file_url>
        local2 = Path("/app/uploads") / file_url.lstrip("/")
        if local2.exists():
            return str(local2)

    # 绝对路径
    p = Path(file_url)
    if p.exists():
        return str(p)

    raise FileNotFoundError(file_url)


def _fail(req: RecognizeReq, message: str, elapsed_ms: int = 0) -> dict:
    return {
        "code": 5001,
        "message": message,
        "fileId": req.file_id,
        "fileUrl": req.file_url,
        "confidence": 0,
        "elapsedMs": elapsed_ms,
    }


if __name__ == "__main__":
    uvicorn.run(
        "app:app",
        host="0.0.0.0",
        port=int(os.getenv("PORT", "8001")),
        workers=1,  # PaddleOCR 模型共享内存，单 worker
        log_level=os.getenv("LOG_LEVEL", "info").lower(),
    )
