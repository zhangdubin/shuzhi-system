"""UDPE PDF 数字签名模块 (M4 阶段 8).

用 cryptography + PyMuPDF 对 PDF 添加可见签名标记。
V1: 在 PDF 最后一页添加签名信息文字（轻量实现，无需复杂 CMS 库）。
V2: 可升级为 PKCS#7 CMS 签名（需 pyHanko 正确配置）。

用法:
    signed_pdf = sign_pdf(pdf_bytes, reason="UDPE 自动签名")
"""
import io
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


def sign_pdf(pdf_bytes: bytes, reason: str = "UDPE 自动签名", location: str = "数智化管理系统") -> bytes:
    """对 PDF 添加签名标记（最后一页底部签名信息框）。

    Args:
        pdf_bytes: 原始 PDF 字节流
        reason: 签名原因
        location: 签名地点

    Returns:
        添加签名标记后的 PDF 字节流
    """
    try:
        import fitz  # PyMuPDF
        doc = fitz.open("pdf", pdf_bytes)

        # 签名信息
        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        signer_name = "UDPE Print Engine"
        sig_text = (
            f"数字签名: {signer_name}\n"
            f"时间: {ts}\n"
            f"原因: {reason}\n"
            f"地点: {location}"
        )

        # 在最后一页底部添加签名框
        last_page = doc[-1]
        page_rect = last_page.rect
        # 签名框位置: 右下角, 180x60 的区域
        sig_w, sig_h = 180, 60
        sig_x = page_rect.width - sig_w - 20
        sig_y = page_rect.height - sig_h - 20
        sig_rect = fitz.Rect(sig_x, sig_y, sig_x + sig_w, sig_y + sig_h)

        # 画边框
        shape = last_page.new_shape()
        shape.draw_rect(sig_rect)
        shape.finish(color=(0.3, 0.4, 1.0), fill=(0.97, 0.98, 1.0), width=0.5)
        shape.commit()

        # 写签名文字
        last_page.insert_textbox(
            fitz.Rect(sig_x + 6, sig_y + 4, sig_x + sig_w - 6, sig_y + sig_h - 4),
            sig_text,
            fontsize=7,
            fontname="helv",
            color=(0.1, 0.1, 0.4),
        )

        signed_bytes = doc.tobytes()
        doc.close()
        logger.info(f"[UDPE] PDF 已签名标记 ({len(pdf_bytes)} → {len(signed_bytes)} bytes)")
        return signed_bytes
    except Exception as e:
        logger.warning(f"[UDPE] PDF 签名失败（返回原始 PDF）: {e}")
        return pdf_bytes


def is_signing_available() -> bool:
    """检查签名功能是否可用。"""
    try:
        import fitz
        return True
    except ImportError:
        return False
