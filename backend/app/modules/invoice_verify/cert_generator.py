# -*- coding: utf-8 -*-
"""
发票查验凭证 PDF 生成器
- 单页 A4 竖版
- 内容：抬头（数智化管理系统·查验凭证）、发票号/代码/金额/日期/销售方/购买方/结果、查验编号/时间/来源、二维码（可扫描回查）、国税局章 mock
- 中文字体：reportlab 内置 STSong-Light
"""
import io
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Optional

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.cidfonts import UnicodeCIDFont
from reportlab.pdfgen import canvas
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.invoice_ocr.models import Invoice, InvoiceVerifyRecord

# 注册中文字体（reportlab 内置 CID 字体，无需字体文件）
pdfmetrics.registerFont(UnicodeCIDFont("STSong-Light"))

CERT_DIR = Path(__file__).resolve().parent.parent.parent / "certificates"  # 与 main.py CERT_DIR 同路径
CERT_DIR.mkdir(parents=True, exist_ok=True)


# 中文 PDF 缺字形（一些生僻字）替换为相近字
def _cn(s: Optional[str]) -> str:
    if s is None:
        return "—"
    s = str(s)
    return s if s else "—"


def _amount_yuan(amount_fen: Optional[int]) -> str:
    if not amount_fen:
        return "¥ 0.00"
    return f"¥ {Decimal(amount_fen) / 100:,.2f}"


def _gen_qr_png(data: str) -> Optional[bytes]:
    """生成二维码 PNG bytes；失败返回 None"""
    try:
        import qrcode
        from qrcode.image.pil import PilImage
        qr = qrcode.QRCode(version=2, box_size=4, border=1)
        qr.add_data(data)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        return buf.getvalue()
    except Exception:
        return None


# 数字金额转中文大写（复用 ocr_client._cn_capital，保证一致性）
def _amount_to_cn(amount_yuan: float) -> str:
    from app.integrations.ocr_client import _cn_capital
    return _cn_capital(amount_yuan)


async def generate_certificate_pdf(rec: InvoiceVerifyRecord, inv: Optional[Invoice]) -> Path:
    pdf_path = CERT_DIR / f"{rec.code}.pdf"

    # 准备数据
    invoice_no = _cn(rec.invoice_no)
    invoice_code = _cn(rec.invoice_code)
    amount_fen = rec.total_amount or 0
    amount_yuan = Decimal(amount_fen) / 100
    amount_str = f"¥ {amount_yuan:,.2f}"
    amount_cn = _amount_to_cn(float(amount_yuan))
    issue_date = rec.issue_date.isoformat() if rec.issue_date else "—"
    seller_name = _cn(inv.seller_name if inv else None)
    buyer_name = _cn(inv.buyer_name if inv else None)
    seller_tax_no = _cn(inv.seller_tax_no if inv else None)
    verified_at = rec.verified_at.strftime("%Y-%m-%d %H:%M:%S") if rec.verified_at else "—"
    elapsed_s = (rec.elapsed_ms or 0) / 1000

    result_map = {
        "pass": ("通过-发票真实有效", colors.HexColor("#10B981")),
        "risk": ("有风险-信息存疑", colors.HexColor("#F59E0B")),
        "repeat": ("重复-已被报销", colors.HexColor("#EF4444")),
        "not_found": ("未查到-请核查", colors.HexColor("#9CA3AF")),
    }
    result_label, result_color = result_map.get(rec.result, ("异常", colors.HexColor("#6B7280")))
    source = rec.source or "国家税务总局全国增值税发票查验平台"

    # ===== 画 PDF =====
    c = canvas.Canvas(str(pdf_path), pagesize=A4)
    width, height = A4

    # 1) 顶部标题
    c.setFillColor(colors.HexColor("#4F6BFF"))
    c.setFont("STSong-Light", 22)
    c.drawString(20 * mm, height - 25 * mm, "发票查验凭证")

    c.setFillColor(colors.HexColor("#6B7280"))
    c.setFont("STSong-Light", 10)
    c.drawString(20 * mm, height - 32 * mm, "数智化管理系统 · Invoice Verification Certificate")
    c.drawString(20 * mm, height - 37 * mm, f"凭证编号：{rec.code}")
    c.drawString(width - 70 * mm, height - 25 * mm, f"查验时间：{verified_at}")
    c.drawString(width - 70 * mm, height - 32 * mm, f"耗时：{elapsed_s:.1f}s")

    # 2) 分割线
    c.setStrokeColor(colors.HexColor("#E5E7EB"))
    c.setLineWidth(0.5)
    c.line(20 * mm, height - 42 * mm, width - 20 * mm, height - 42 * mm)

    # 3) 查验结果大字
    c.setFillColor(result_color)
    c.setFont("STSong-Light", 28)
    prefix = "√ " if rec.result == "pass" else "× "
    c.drawString(20 * mm, height - 58 * mm, prefix + result_label)

    # 4) 关键信息表
    y = height - 72 * mm
    rows = [
        ("发票号码", invoice_no, "开票日期", issue_date),
        ("发票代码", invoice_code, "价税合计", amount_str),
        ("大写金额", amount_cn, "查验来源", source),
        ("销售方", seller_name, "纳税人识别号", seller_tax_no),
        ("购买方", buyer_name, "查验次数", "1 次"),
    ]
    c.setFont("STSong-Light", 10)
    row_h = 12 * mm
    for i, (l1, v1, l2, v2) in enumerate(rows):
        yy = y - i * row_h
        # 标签底色
        c.setFillColor(colors.HexColor("#F3F4F6"))
        c.rect(20 * mm, yy - 9 * mm, 28 * mm, 8 * mm, fill=1, stroke=0)
        c.rect(width / 2 + 0 * mm, yy - 9 * mm, 28 * mm, 8 * mm, fill=1, stroke=0)
        # 标签文字
        c.setFillColor(colors.HexColor("#374151"))
        c.setFont("STSong-Light", 10)
        c.drawString(22 * mm, yy - 6 * mm, l1)
        c.drawString(width / 2 + 2 * mm, yy - 6 * mm, l2)
        # 值
        c.setFillColor(colors.HexColor("#111827"))
        c.setFont("STSong-Light", 11)
        c.drawString(50 * mm, yy - 6 * mm, str(v1)[:40])
        c.drawString(width / 2 + 30 * mm, yy - 6 * mm, str(v2)[:40])

    # 5) 风险说明
    if rec.risk_reason:
        c.setFillColor(colors.HexColor("#FEF3C7"))
        c.rect(20 * mm, y - 5 * 12 * mm - 8 * mm, width - 40 * mm, 14 * mm, fill=1, stroke=0)
        c.setFillColor(colors.HexColor("#92400E"))
        c.setFont("STSong-Light", 10)
        c.drawString(22 * mm, y - 5 * 12 * mm - 4 * mm, "风险说明：")
        c.setFont("STSong-Light", 10)
        c.drawString(40 * mm, y - 5 * 12 * mm - 4 * mm, str(rec.risk_reason)[:60])

    # 6) 二维码 + 国税章
    qr_y = 60 * mm
    qr_data = f"https://inv-verify.shuzhi.local/{rec.code}?invoiceNo={rec.invoice_no or ''}&amount={amount_yuan}&date={issue_date}"
    qr_bytes = _gen_qr_png(qr_data)
    if qr_bytes:
        from reportlab.lib.utils import ImageReader
        img = ImageReader(io.BytesIO(qr_bytes))
        c.drawImage(img, 22 * mm, qr_y, width=30 * mm, height=30 * mm, mask="auto")
        c.setFillColor(colors.HexColor("#6B7280"))
        c.setFont("STSong-Light", 8)
        c.drawString(22 * mm, qr_y - 4 * mm, "扫码回查")

    # 国税局章（圆形 mock）
    c.setStrokeColor(colors.HexColor("#DC2626"))
    c.setLineWidth(1.5)
    seal_x = width - 60 * mm
    seal_y = qr_y + 15 * mm
    c.circle(seal_x, seal_y, 13 * mm, stroke=1, fill=0)
    c.setFillColor(colors.HexColor("#DC2626"))
    c.setFont("STSong-Light", 9)
    # ★ 文字
    c.drawCentredString(seal_x, seal_y + 3 * mm, "发")
    c.setFont("STSong-Light", 8)
    c.drawCentredString(seal_x, seal_y - 1 * mm, "国家税务总局")
    c.drawCentredString(seal_x, seal_y - 5 * mm, "发票查验专用章")
    c.setFont("STSong-Light", 6)
    c.drawCentredString(seal_x, seal_y - 9 * mm, "(电子凭证)")

    # 7) 底部说明
    c.setFillColor(colors.HexColor("#9CA3AF"))
    c.setFont("STSong-Light", 8)
    c.drawString(20 * mm, 25 * mm, "本凭证由数智化管理系统依据国家税务总局发票查验平台接口数据生成。")
    c.drawString(20 * mm, 21 * mm, "查验数据仅用于发票真伪及重复报销判定，请勿用于其他商业用途。")
    c.drawString(20 * mm, 17 * mm, f"生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} · 凭证一次性有效，限企业内部使用。")

    c.showPage()
    c.save()
    return pdf_path
