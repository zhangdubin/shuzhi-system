"""UDPE HtmlRenderer：模板 → HTML 字符串。

设计文档：plans/udpe-design/design.md §六 6.3

V1：直接复用 PdfRenderer 的组件渲染逻辑，但输出 HTML 字符串。
复用 _resolve_value / _apply_filters / _bind_text，不重新造轮子。
"""
import logging
from typing import Any

logger = logging.getLogger(__name__)


def _generate_qr_svg(data: str, size: int = 120) -> str:
    """生成 QR Code 的 PNG data URI."""
    try:
        import qrcode
        import io, base64
        qr = qrcode.QRCode(version=None, error_correction=qrcode.constants.ERROR_CORRECT_M, box_size=4, border=1)
        qr.add_data(data)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        b64 = base64.b64encode(buf.getvalue()).decode()
        return f'<img src="data:image/png;base64,{b64}" style="width:{size}px;height:{size}px;" />'
    except Exception as e:
        return f'<span style="color:#DC2626;">[QR Error: {e}]</span>'


def _generate_barcode_html(code_text: str, bar_height: int = 50) -> str:
    """生成 Code128 条码的 PNG data URI."""
    try:
        import barcode
        from barcode.writer import ImageWriter
        import io, base64
        # python-barcode Code128 生成
        code128 = barcode.get("code128", code_text, writer=ImageWriter())
        buf = io.BytesIO()
        code128.write(buf, options={"module_width": 0.3, "module_height": bar_height * 0.3, "font_size": 10, "text_distance": 2, "quiet_zone": 2})
        buf.seek(0)
        b64 = base64.b64encode(buf.getvalue()).decode()
        return f'<img src="data:image/png;base64,{b64}" style="height:{bar_height}px;" />'
    except Exception as e:
        return f'<span style="color:#DC2626;">[Barcode Error: {e}]</span>'


def _esc(v: Any) -> str:
    """HTML 转义。"""
    if v is None:
        return ""
    s = str(v)
    return (s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            .replace('"', "&quot;").replace("'", "&#39;"))


def _to_html_comp(comp: dict, data: dict) -> str:
    """把单个组件渲染成 HTML 字符串。"""
    from app.modules.print_runtime.renderers.pdf_renderer import (
        _resolve_value, _apply_filters, _bind_text, _safe, _money, _format_date,
    )

    ctype = comp.get("type", "").lower()
    if ctype == "text":
        text = comp.get("text", "")
        if "bind" in comp:
            v = _resolve_value(data, comp["bind"])
            text = _safe(v)
        else:
            text = _bind_text(text, data)
        size = int(comp.get("fontSize") or 10)
        color = comp.get("color", "#1F2937")
        align = comp.get("align", "left")
        return (
            f'<div style="font-size:{size}px;color:{color};text-align:{align};'
            f'padding:2px 0;">{_esc(text) or "&nbsp;"}</div>'
        )

    if ctype == "title":
        text = comp.get("text", "")
        if "bind" in comp:
            text = _safe(_resolve_value(data, comp["bind"]))
        else:
            text = _bind_text(text, data)
        size = int(comp.get("fontSize") or 18)
        align = comp.get("align", "center")
        return (
            f'<h1 style="font-size:{size}px;text-align:{align};'
            f'margin:8px 0;color:{comp.get("color", "#0F172A")};">{_esc(text)}</h1>'
        )

    if ctype == "line":
        color = comp.get("color", "#E5E7EB")
        return f'<hr style="border:none;border-top:1px solid {color};margin:4px 0;" />'

    if ctype == "spacer":
        h = int(comp.get("height") or 6)
        return f'<div style="height:{h}mm;"></div>'

    if ctype == "table":
        bind_path = comp.get("bind", "")
        rows_data = _resolve_value(data, bind_path) or []
        if not isinstance(rows_data, list):
            rows_data = []
        columns = comp.get("columns", [])
        if not columns:
            return ""
        header = "".join(
            f'<th style="background:#4F6BFF;color:white;padding:6px 8px;'
            f'text-align:left;font-size:11px;">{_esc(c.get("label", c.get("key", "")))}</th>'
            for c in columns
        )
        body_html = []
        for idx, item in enumerate(rows_data):
            bg = "#F9FAFB" if idx % 2 == 1 else "#FFFFFF"
            cells = []
            for c in columns:
                key = c.get("key", "")
                val = _resolve_value(item, key) if isinstance(item, dict) else None
                ctype_col = c.get("type", "string")
                if ctype_col == "money" and val is not None:
                    val = _money(val)
                cells.append(
                    f'<td style="padding:5px 8px;border:1px solid #E5E7EB;'
                    f'font-size:10.5px;">{_esc(_safe(val))}</td>'
                )
            body_html.append(f'<tr style="background:{bg};">{"".join(cells)}</tr>')
        return (
            '<table style="width:100%;border-collapse:collapse;margin:8px 0;">'
            f'<thead><tr>{header}</tr></thead>'
            f'<tbody>{"".join(body_html)}</tbody></table>'
        )

    if ctype == "grid":
        """Excel 风格网格: 单元格边框 + colspan 合并.

        Schema 示例:
        {
            "type": "grid",
            "border": true,
            "colCount": 5,
            "rows": [
                {"height": 14, "cells": [
                    {"text": "费 用 报 销 单", "span": 5, "bold": true, "align": "center", "fontSize": 20}
                ]},
                ...
            ]
        }
        """
        border_color = comp.get("borderColor", "#000000")
        border_w = comp.get("borderWidth", 1)
        has_border = comp.get("border", True)
        border_style = (
            f"border:{border_w}px solid {border_color};"
            if has_border else "border:none;"
        )
        rows_html = []
        for row in comp.get("rows", []):
            h = row.get("height")
            height_style = f"height:{h}mm;" if h else "height:14mm;"
            cells = row.get("cells", [])
            cells_html = []
            for c in cells:
                span = int(c.get("span", 1))
                if "bind" in c:
                    txt = _safe(_resolve_value(data, c["bind"]))
                else:
                    txt = _bind_text(c.get("text", ""), data)
                align = c.get("align", "left")
                valign = c.get("valign", "middle")
                fs = int(c.get("fontSize") or 12)
                color = c.get("color", "#000000")
                weight = "bold" if c.get("bold") else "normal"
                pad = c.get("padding", "6px 8px")
                style = (
                    f"{border_style}"
                    f"text-align:{align};"
                    f"vertical-align:{valign};"
                    f"font-size:{fs}px;"
                    f"color:{color};"
                    f"font-weight:{weight};"
                    f"padding:{pad};"
                )
                if c.get("background"):
                    style += f"background:{c['background']};"
                if c.get("width"):
                    style += f"width:{c['width']};"
                # 嵌套组件: 如果 cell 有 children, 递归渲染
                children = c.get("children")
                if children and isinstance(children, list):
                    inner_parts = []
                    for child in children:
                        child_type = child.get("type", "text")
                        if child_type == "title":
                            cfs = int(child.get("fontSize") or 16)
                            calign = child.get("align", "center")
                            ccolor = child.get("color", "#0F172A")
                            ctxt = _bind_text(child.get("text", ""), data)
                            inner_parts.append(
                                f'<div style="font-size:{cfs}px;text-align:{calign};'
                                f'color:{ccolor};font-weight:bold;margin:4px 0;">{_esc(ctxt)}</div>'
                            )
                        elif child_type == "spacer":
                            ch = child.get("height", 6)
                            inner_parts.append(f'<div style="height:{ch}mm;"></div>')
                        elif child_type == "line":
                            cc = child.get("color", "#E5E7EB")
                            inner_parts.append(f'<hr style="border:none;border-top:1px solid {cc};margin:4px 0;">')
                        elif child_type == "text":
                            cfs = int(child.get("fontSize") or 12)
                            calign = child.get("align", "left")
                            ccolor = child.get("color", "#1F2937")
                            cweight = "bold" if child.get("bold") else "normal"
                            ctxt = _bind_text(child.get("text", ""), data)
                            inner_parts.append(
                                f'<div style="font-size:{cfs}px;text-align:{calign};'
                                f'color:{ccolor};font-weight:{cweight};margin:2px 0;">{_esc(ctxt)}</div>'
                            )
                        else:
                            ctxt = _bind_text(child.get("text", str(child_type)), data)
                            inner_parts.append(f'<div style="font-size:12px;margin:2px 0;">{_esc(ctxt)}</div>')
                    cell_content = "".join(inner_parts)
                else:
                    cell_content = _esc(txt) or "&nbsp;"
                cells_html.append(
                    f'<td colspan="{span}" style="{style}">{cell_content}</td>'
                )
            rows_html.append(
                f'<tr style="{height_style}">{"".join(cells_html)}</tr>'
            )
        return (
            f'<table style="width:100%;border-collapse:collapse;'
            f'margin:0;table-layout:fixed;">'
            f'{"".join(rows_html)}</table>'
        )

    if ctype == "pagebreak":
        return '<div style="page-break-after:always;"></div>'

    if ctype == "qrcode":
        qr_data = _bind_text(comp.get("data", comp.get("text", "")), data)
        qr_size = int(comp.get("size", 120))
        label = comp.get("label", "")
        label_html = f'<div style="text-align:center;font-size:11px;color:#4B5563;margin-top:4px;">{_esc(label)}</div>' if label else ""
        return (
            f'<div style="text-align:center;margin:8px 0;">'
            f'{_generate_qr_svg(qr_data, qr_size)}'
            f'{label_html}'
            f'</div>'
        )

    if ctype == "barcode":
        bar_data = _bind_text(comp.get("data", comp.get("text", "")), data)
        bar_height = int(comp.get("height", 50))
        label = comp.get("label", "")
        label_html = f'<div style="text-align:center;font-size:11px;color:#4B5563;margin-top:4px;">{_esc(label)}</div>' if label else ""
        return (
            f'<div style="text-align:center;margin:8px 0;">'
            f'{_generate_barcode_html(bar_data, bar_height)}'
            f'{label_html}'
            f'</div>'
        )

    return ""  # 未支持类型


class HtmlRenderer:
    """UDPE HtmlRenderer：模板 + 数据 → HTML 字符串（用于浏览器预览）。"""

    name = "html"
    mime_type = "text/html; charset=utf-8"

    async def render(self, template: dict, data: dict, ctx) -> bytes:
        body = template.get("body", [])
        parts = [_to_html_comp(c, data) for c in body]

        meta = template.get("meta") or {}
        title = meta.get("title", "打印预览")
        html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<title>{_esc(title)}</title>
<style>
  body {{
    font-family: -apple-system, "Helvetica Neue", "PingFang SC", "Microsoft YaHei", "STSong-Light", serif;
    padding: 12mm;
    color: #1F2937;
    background: #FFFFFF;
    max-width: 800px;
    margin: 0 auto;
  }}
  @page {{ size: A4; margin: 12mm; }}
  table {{ page-break-inside: avoid; }}
  tr {{ page-break-inside: avoid; }}
</style>
</head>
<body>
{''.join(parts)}
</body>
</html>"""
        return html.encode("utf-8")
