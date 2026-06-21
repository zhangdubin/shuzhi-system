"""
OCR 引擎封装（R19.1：换用 rapidocr-onnxruntime）
- 之前用 paddleocr + paddlepaddle 2.6.2，在 arm64 (M1/M2/M3) 上 import 就段错误
- rapidocr 基于 ONNX Runtime，纯 CPU 推理，跨平台稳定
- 模型与 PaddleOCR 兼容（同一套预训练模型）
- API 形态与原 paddleocr 引擎一致：返回 [ (poly, text, conf) ] 列表
- 启动慢：首次 import 约 2-5s（模型从 ~/.rapidocr 下载/缓存）
"""
import logging
import os
import time
from typing import List, Tuple

logger = logging.getLogger(__name__)

# 引擎全局单例（FastAPI 进程内只加载一次）
_ENGINE = None
_ENGINE_LOCK = False


def get_engine():
    """懒加载 rapidocr 引擎（单例）"""
    global _ENGINE, _ENGINE_LOCK
    if _ENGINE is not None:
        return _ENGINE
    if _ENGINE_LOCK:
        return None
    _ENGINE_LOCK = True
    try:
        from rapidocr_onnxruntime import RapidOCR
        logger.info("[RapidOCR] 首次加载 ONNX 模型（PP-OCRv4 中文），路径 ~/.rapidocr ...")
        t0 = time.time()
        _ENGINE = RapidOCR(
            # use_angle_cls=False：不识别方向（发票都是正向的）
        )
        # 立即预热（首次推理会触发模型 lazy load）
        # 注意：rapidocr 模型下载路径在 ~/.rapidocr，首次会下载 ~10MB 模型
        logger.info(f"[RapidOCR] 模型加载完成，耗时 {time.time() - t0:.1f}s")
        return _ENGINE
    except Exception as e:
        logger.error(f"[RapidOCR] 模型加载失败: {e}")
        _ENGINE_LOCK = False
        raise
    finally:
        _ENGINE_LOCK = False


def is_ready() -> bool:
    """检查引擎是否就绪（健康检查用）"""
    return _ENGINE is not None


def warmup():
    """启动时预热（可选）"""
    try:
        get_engine()
        return True
    except Exception as e:
        logger.warning(f"[RapidOCR] 预热失败: {e}")
        return False


def recognize_image(image_path: str) -> List[List[Tuple[List[List[int]], str, float]]]:
    """
    识别一张图片
    返回：[ [ (poly, text, conf), ... ] ]  （单张图一页）
    与 paddleocr 旧格式完全一致，app.py / postprocess.py 无需改动
    """
    engine = get_engine()
    # rapidocr 返回 (result, elapse)
    # result 格式：[[box, text, conf], ...] 或 None
    result, _elapse = engine(image_path)
    return _normalize_rapidocr_output(result)


def _normalize_rapidocr_output(result):
    """rapidocr 输出 → 统一格式 [ (poly, text, conf) ]"""
    if not result:
        return []
    page_items = []
    for item in result:
        # rapidocr 元素： [box, text, conf]
        if isinstance(item, (list, tuple)) and len(item) >= 3:
            box, text, conf = item[0], item[1], item[2]
            # box 是 [[x1,y1],[x2,y2],[x3,y3],[x4,y4]] 或 ndarray
            if hasattr(box, "tolist"):
                box = box.tolist()
            page_items.append((box, str(text), float(conf)))
    return [page_items]
