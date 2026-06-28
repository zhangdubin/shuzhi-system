"""UDPE PdfRenderer：模板 → PDF 字节流。

设计文档：plans/udpe-design/design.md §六 6.3

V1 支持组件：text / title / table / grid / image / line / pagebreak
中文字体：reportlab 内置 STSong-Light（CID 字体，无需字体文件）
"""
import io
import logging
from typing import Any, Optional

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, A3, A5
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.cidfonts import UnicodeCIDFont
from reportlab.platypus import (
    Image, PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle,
)

logger = logging.getLogger(__name__)

# 注册中文字体（重复注册幂等）
try:
    pdfmetrics.registerFont(UnicodeCIDFont("STSong-Light"))
except Exception:
    pass

# 纸型映射
PAPER_SIZES = {
    "A4": A4, "A3": A3, "A5": A5,
}


def _safe(v: Any, default: str = "—") -> str:
    """空值兜底为中文破折号。"""
    if v is None or v == "":
        return default
    return str(v)


def _money(amount: Any, unit: str = "yuan") -> str:
    """过滤器: money。

    amount 单位：元（已乘 100 存为分时，传 Decimal/int；M1 直接传元）。
    """
    try:
        v = float(amount or 0)
        return f"¥ {v:,.2f}"
    except (TypeError, ValueError):
        return "¥ 0.00"


def _chinese_money(amount: Any) -> str:
    """过滤器: chinese_money。阿拉伯数字 → 中文大写金额。

    实现要点：整数部分按"亿/万/仟/佰/拾/元"分段，小数部分按"角/分"补齐。
    覆盖 0 / 0.01 / 0.99 / 1 / 100 / 10000 / 1500000 / 1.23 / 1234567.89 等。
    """
    try:
        v = float(amount or 0)
    except (TypeError, ValueError):
        return "零元整"
    if v < 0:
        return "负" + _chinese_money(-v)
    if v == 0:
        return "零元整"

    digits = "零壹贰叁肆伍陆柒捌玖"
    int_part = int(v)
    dec_part = int(round((v - int_part) * 100))  # 分

    def _section(n: int) -> str:
        """0..9999 段的中文大写（不含'元'）。"""
        if n == 0:
            return "零"
        units = ["仟", "佰", "拾", ""]
        s = ""
        last_zero = False
        for i, u in enumerate(units):
            d = (n // (10 ** (3 - i))) % 10
            if d == 0:
                if not last_zero and s and s[-1] != "零":
                    s += "零"
                last_zero = True
            else:
                s += digits[d] + u
                last_zero = False
        return s.rstrip("零") or "零"

    # 整数部分
    yi = int_part // 100000000
    wan = (int_part // 10000) % 10000
    rest = int_part % 10000

    parts = []
    if yi:
        parts.append(_section(yi) + "亿")
    if wan:
        wan_str = _section(wan) + "万"
        # 补零：1亿0001万 → 1亿零1万
        if parts and wan < 1000:
            wan_str = "零" + wan_str.lstrip("零")
        parts.append(wan_str)
    elif yi and rest:
        parts.append("零")
    if rest:
        rest_str = _section(rest)
        if parts and rest < 1000 and int_part > 10000:
            rest_str = "零" + rest_str.lstrip("零")
        parts.append(rest_str + "元")
    elif not parts:
        parts.append("零元")
    else:
        # 整数部分有值但无"元"尾巴（rest=0 且 wan>0 或 yi>0 的情况），需要补"元"
        if not parts[-1].endswith("元"):
            parts[-1] = parts[-1] + "元"

    # 小数部分
    if dec_part == 0:
        parts.append("整")
    else:
        jiao = dec_part // 10
        fen = dec_part % 10
        if jiao:
            parts.append(digits[jiao] + "角")
        if fen:
            if jiao == 0:
                parts.append("零")
            parts.append(digits[fen] + "分")
    return "".join(parts)



def _format_date(d: Any, fmt: str = "%Y-%m-%d") -> str:
    """过滤器: date / datetime。"""
    if not d:
        return ""
    from datetime import datetime, date
    if isinstance(d, (datetime, date)):
        return d.strftime(fmt)
    return str(d)


# 过滤器注册表
FILTERS = {
    "money": _money,
    "chinese_money": _chinese_money,
    "date": _format_date,
    "datetime": lambda v: _format_date(v, "%Y-%m-%d %H:%M"),
    "upper": lambda v: str(v or "").upper(),
    "lower": lambda v: str(v or "").lower(),
    "default": lambda v, default="": default if v is None or v == "" else v,
}


def _apply_filter(value: Any, filter_name: str) -> Any:
    """应用一个过滤器（不支持参数化，M1 简化）。"""
    fn = FILTERS.get(filter_name)
    if fn is None:
        return value
    try:
        return fn(value)
    except Exception:
        return value


def _resolve_value(data: dict, path: str) -> Any:
    """JSONPath 解析：a.b.c 取值。"""
    if not path:
        return None
    cur = data
    for part in path.split("."):
        if isinstance(cur, dict):
            cur = cur.get(part)
        elif isinstance(cur, list):
            try:
                idx = int(part)
                cur = cur[idx]
            except (ValueError, IndexError):
                return None
        else:
            return None
        if cur is None:
            return None
    return cur


def _apply_filters(value: Any, filter_str: str) -> Any:
    """解析并应用过滤器链: "money | upper"。"""
    if not filter_str:
        return value
    for f in filter_str.split("|"):
        f = f.strip()
        if f:
            value = _apply_filter(value, f)
    return value


def _bind_text(template: str, data: dict) -> str:
    """文本模板插值：把 {{ path | filter1 | filter2 }} 替换成实际值。

    template 例如："{{ invoice.code | upper }} | {{ invoice.title }}"
    """
    import re
    if not template or "{{" not in template:
        return template or ""

    def replacer(m):
        inner = m.group(1).strip()
        # 切分路径与过滤器
        parts = [p.strip() for p in inner.split("|")]
        path = parts[0]
        filters = parts[1:]
        v = _resolve_value(data, path)
        for f in filters:
            v = _apply_filter(v, f)
        if v is None:
            return ""
        return str(v)

    return re.sub(r"\{\{\s*([^}]+?)\s*\}\}", replacer, template)


def _get_paper(template: dict) -> tuple[Any, str]:
    """根据模板 paper / orientation 算出 pagesize + orientation。

    兼容两种 schema：
    - 老式：template.paper = "A4" 字符串
    - 新式（design §三）：template.paper = {size, orientation, marginMm} dict
      此时 orientation / marginMm 来自 paper dict，模板顶层 orientation 仅作 fallback
    """
    paper_field = template.get("paper")
    if isinstance(paper_field, dict):
        paper_name = (paper_field.get("size") or "A4").upper()
        orientation = (paper_field.get("orientation") or "portrait").lower()
    else:
        paper_name = (paper_field or "A4").upper()
        orientation = (template.get("orientation") or "portrait").lower()
    pagesize = PAPER_SIZES.get(paper_name, A4)
    if orientation == "landscape":
        pagesize = (pagesize[1], pagesize[0])
    return pagesize, orientation


def _get_margin_mm(template: dict) -> dict:
    """提取 marginMm（兼容 paper dict 嵌 margin 或模板顶层 marginMm）。"""
    paper_field = template.get("paper")
    if isinstance(paper_field, dict) and isinstance(paper_field.get("marginMm"), dict):
        return paper_field["marginMm"]
    return template.get("marginMm") or {"top": 18, "right": 18, "bottom": 18, "left": 18}


def _make_style(font_size: int = 10, color: str = "#1F2937", bold: bool = False) -> ParagraphStyle:
    return ParagraphStyle(
        f"UDPE-{font_size}-{color}-{bold}",
        fontName="STSong-Light",
        fontSize=font_size,
        textColor=colors.HexColor(color) if color else colors.black,
        leading=font_size * 1.4,
    )


def _build_component(comp: dict, data: dict, styles_cache: dict) -> list:
    """根据组件类型生成 reportlab flowables。"""
    ctype = comp.get("type", "").lower()
    out = []

    if ctype == "text":
        text = comp.get("text", "")
        # 如果有 bind 字段，data 路径优先；否则用 text 模板
        if "bind" in comp:
            text = str(_resolve_value(data, comp["bind"]) or "")
        else:
            text = _bind_text(text, data)
        size = int(comp.get("fontSize") or 10)
        color = comp.get("color", "#1F2937")
        align = comp.get("align", "left")
        style = ParagraphStyle(
            "t", parent=styles_cache["base"],
            fontSize=size, alignment={"left": 0, "center": 1, "right": 2}.get(align, 0),
            textColor=colors.HexColor(color),
        )
        out.append(Paragraph(text or "&nbsp;", style))

    elif ctype == "title":
        text = comp.get("text", "")
        if "bind" in comp:
            text = str(_resolve_value(data, comp["bind"]) or "")
        else:
            text = _bind_text(text, data)
        size = int(comp.get("fontSize") or 18)
        align = comp.get("align", "center")
        style = ParagraphStyle(
            "title", parent=styles_cache["base"],
            fontSize=size, alignment=1, spaceAfter=12,
            textColor=colors.HexColor(comp.get("color", "#0F172A")),
        )
        out.append(Paragraph(f"<b>{text}</b>", style))

    elif ctype == "line":
        # 简化为一条 Spacer + 灰色横线（reportlab 的 Table 1x1 模拟）
        from reportlab.platypus import HRFlowable
        out.append(HRFlowable(
            width="100%", thickness=1,
            color=colors.HexColor(comp.get("color", "#E5E7EB")),
            spaceBefore=4, spaceAfter=4,
        ))

    elif ctype == "spacer":
        h = int(comp.get("height") or 6)
        out.append(Spacer(1, h * mm))

    elif ctype == "table":
        bind_path = comp.get("bind", "")
        rows_data = _resolve_value(data, bind_path) or []
        if not isinstance(rows_data, list):
            rows_data = []
        columns = comp.get("columns", [])
        if not columns:
            return out

        # 表头
        header = [c.get("label", c.get("key", "")) for c in columns]
        # 数据行：每行对应一个 dict
        body = []
        for item in rows_data:
            row = []
            for c in columns:
                key = c.get("key", "")
                val = _resolve_value(item, key) if isinstance(item, dict) else None
                ctype_col = c.get("type", "string")
                if ctype_col == "money" and val is not None:
                    val = _money(val)
                row.append(_safe(val))
            body.append(row)

        tbl_data = [header] + body
        col_widths = [c.get("width", 30) * mm for c in columns]
        # 总宽度 = sum(col_widths)，不足 A4 宽时按比例放大
        available_w = A4[0] - 36 * mm  # 18mm margin each side
        total_w = sum(col_widths)
        if total_w < available_w:
            scale = available_w / total_w
            col_widths = [w * scale for w in col_widths]

        tbl = Table(tbl_data, colWidths=col_widths, repeatRows=1)
        tbl.setStyle(TableStyle([
            ("FONTNAME", (0, 0), (-1, -1), "STSong-Light"),
            ("FONTSIZE", (0, 0), (-1, -1), 9),
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#4F6BFF")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTWEIGHT", (0, 0), (-1, 0), "bold"),
            ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#E5E7EB")),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("LEFTPADDING", (0, 0), (-1, -1), 5),
            ("RIGHTPADDING", (0, 0), (-1, -1), 5),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F9FAFB")]),
        ]))
        out.append(tbl)

    elif ctype == "grid":
        """Excel 风格网格: 单元格边框 + colspan 合并.

        Schema 与 HTML renderer 一致.
        """
        col_count = int(comp.get("colCount") or 5)
        has_border = comp.get("border", True)
        border_color_hex = comp.get("borderColor", "#000000")
        border_w = float(comp.get("borderWidth", 0.5))
        border_color = colors.HexColor(border_color_hex) if has_border else None
        # 列宽: 可指定 colWidths (mm list), 否则等分
        avail_w = A4[0] - 36 * mm
        col_w_input = comp.get("colWidthsMm")
        if col_w_input and isinstance(col_w_input, list):
            col_widths = [float(w) * mm for w in col_w_input]
        else:
            col_widths = [avail_w / col_count] * col_count

        # 构建 cell 数据 + span 信息
        cell_paragraphs = []  # list of (text_paragraph, span, font_size, color, bold, align, h-align, bg)
        row_heights = []  # list of float (mm)
        rows_data = comp.get("rows", [])

        for row in rows_data:
            h = float(row.get("height") or 14)
            row_heights.append(h * mm)
            cells = row.get("cells", [])
            for c in cells:
                span = int(c.get("span", 1))
                fs = int(c.get("fontSize") or 12)
                color = c.get("color", "#000000")
                bold = "bold" if c.get("bold") else "normal"
                align = c.get("align", "left")
                bg = c.get("background")
                # 嵌套组件: 如果 cell 有 children, 拼接渲染
                children = c.get("children")
                if children and isinstance(children, list):
                    parts = []
                    for child in children:
                        ct = child.get("type", "text")
                        if ct in ("text", "title"):
                            ctxt = _bind_text(child.get("text", ""), data)
                            cfs = int(child.get("fontSize") or 12)
                            ccolor = child.get("color", "#1F2937")
                            cweight = "bold" if child.get("bold") or ct == "title" else ""
                            styled_txt = ctxt
                            if cweight:
                                styled_txt = f'<b>{styled_txt}</b>'
                            parts.append(
                                f'<font size="{cfs}" color="{ccolor}">{styled_txt}</font>'
                            )
                        elif ct == "spacer":
                            parts.append(" ")
                        elif ct == "line":
                            parts.append("─" * 20)
                        else:
                            parts.append(_bind_text(child.get("text", ct), data))
                    txt = "<br/>".join(parts)
                else:
                    if "bind" in c:
                        txt = str(_resolve_value(data, c["bind"]) or "")
                    else:
                        txt = _bind_text(c.get("text", ""), data)
                # 用 Paragraph 支持中文字体
                style = ParagraphStyle(
                    "gcell",
                    fontName="STSong-Light",
                    fontSize=fs,
                    textColor=colors.HexColor(color),
                    leading=fs * 1.3,
                    alignment={"left": 0, "center": 1, "right": 2}.get(align, 0),
                )
                if not (children and isinstance(children, list)):
                    content_html = f'<b>{txt}</b>' if bold == "bold" else txt
                else:
                    content_html = txt
                para = Paragraph(content_html or "&nbsp;", style)
                cell_paragraphs.append({"p": para, "span": span, "bg": bg})

        # 拍平为 table data (list of list)
        n_rows = len(rows_data)
        if n_rows == 0:
            return out
        # 算每行的总 span, 用于补齐
        n_cols = col_count
        table_data = [[None] * n_cols for _ in range(n_rows)]
        # 跟踪已被 span 占用的列
        occupied = [[False] * n_cols for _ in range(n_rows)]

        idx = 0
        for ri, row in enumerate(rows_data):
            cells = row.get("cells", [])
            ci = 0
            for c in cells:
                # 找下一个空列
                while ci < n_cols and occupied[ri][ci]:
                    ci += 1
                if ci >= n_cols:
                    break
                span = int(c.get("span", 1))
                cell = cell_paragraphs[idx]
                idx += 1
                # 填入起始 cell
                table_data[ri][ci] = cell["p"]
                # 标记 span 占用
                for k in range(1, span):
                    if ci + k < n_cols:
                        table_data[ri][ci + k] = ""  # 占位
                        occupied[ri][ci + k] = True
                ci += 1
            # 补齐 None
            for cj in range(n_cols):
                if table_data[ri][cj] is None:
                    table_data[ri][cj] = ""

        tbl = Table(
            table_data,
            colWidths=col_widths,
            rowHeights=row_heights,
        )
        style_cmds = [
            ("FONTNAME", (0, 0), (-1, -1), "STSong-Light"),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("LEFTPADDING", (0, 0), (-1, -1), 6),
            ("RIGHTPADDING", (0, 0), (-1, -1), 6),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ]
        if has_border:
            style_cmds.append(("GRID", (0, 0), (-1, -1), border_w, border_color))
            style_cmds.append(("BOX", (0, 0), (-1, -1), border_w, border_color))
        tbl.setStyle(TableStyle(style_cmds))

        # 应用 colspan SPAN
        span_idx = 0
        for ri, row in enumerate(rows_data):
            cells = row.get("cells", [])
            ci = 0
            for c in cells:
                while ci < n_cols and occupied[ri][ci]:
                    ci += 1
                if ci >= n_cols:
                    break
                span = int(c.get("span", 1))
                if span > 1:
                    style_cmds.append(("SPAN", (ci, ri), (ci + span - 1, ri)))
                # 背景色
                bg = cell_paragraphs[span_idx].get("bg")
                if bg:
                    style_cmds.append(("BACKGROUND", (ci, ri), (ci + span - 1, ri), colors.HexColor(bg)))
                ci += 1
                span_idx += 1
        # 二次 setStyle 应用 SPAN / BACKGROUND
        tbl.setStyle(TableStyle(style_cmds))
        out.append(tbl)

    elif ctype == "pagebreak":
        out.append(PageBreak())

    elif ctype == "image":
        url = comp.get("bind") or comp.get("url", "")
        if isinstance(url, str) and url:
            try:
                w = int(comp.get("width", 50)) * mm
                h = int(comp.get("height", 20)) * mm
                out.append(Image(url, width=w, height=h))
            except Exception as e:
                logger.warning(f"[UDPE] image 加载失败: {e}")

    return out


class PdfRenderer:
    """UDPE PdfRenderer：模板 + 数据 → PDF 字节流。

    设计文档：plans/udpe-design/design.md §六 6.3
    """

    name = "pdf"
    mime_type = "application/pdf"

    async def render(self, template: dict, data: dict, ctx) -> bytes:
        pagesize, _ = _get_paper(template)
        margin = _get_margin_mm(template)
        buf = io.BytesIO()
        doc = SimpleDocTemplate(
            buf, pagesize=pagesize,
            leftMargin=margin.get("left", 18) * mm,
            rightMargin=margin.get("right", 18) * mm,
            topMargin=margin.get("top", 18) * mm,
            bottomMargin=margin.get("bottom", 18) * mm,
            title=(template.get("meta") or {}).get("title", "打印"),
        )

        # 基础样式
        base_style = ParagraphStyle(
            "base", fontName="STSong-Light", fontSize=10, leading=14,
        )
        styles_cache = {"base": base_style}

        # 构建 story
        story = []
        body = template.get("body", [])
        for comp in body:
            story.extend(_build_component(comp, data, styles_cache))

        # 水印（V1 简化版：用 Paragraph 放最后覆盖在背景上）
        if ctx and ctx.watermark:
            wm_style = ParagraphStyle(
                "wm", fontName="STSong-Light", fontSize=48,
                textColor=colors.HexColor("#000000"),
                alignment=1,
            )
            # 加 1 个空段 + 水印
            from reportlab.platypus.flowables import Flowable

        doc.build(story)
        return buf.getvalue()
