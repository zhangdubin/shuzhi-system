"""WeasyPrint PDF 渲染器 (M4 阶段 5).

用 CSS 驱动 PDF 生成，比 reportlab 支持更丰富的排版。
内部复用 HTMLRenderer 生成 HTML，再用 WeasyPrint 转 PDF。

用法:
    renderer = WeasyPrintRenderer()
    pdf_bytes = await renderer.render(template, data, ctx)
"""
import logging
from typing import Any

from app.core.print.context import RenderContext

logger = logging.getLogger(__name__)


class WeasyPrintRenderer:
    """WeasyPrint PDF 渲染器 — CSS → PDF。"""

    name = "weasyprint"
    mime_type = "application/pdf"

    async def render(self, template: dict, data: dict, ctx: RenderContext) -> bytes:
        """渲染模板为 PDF (WeasyPrint)。"""
        from .html_renderer import HtmlRenderer

        # 1. 复用 HTML 渲染器生成 body HTML
        html_renderer = HtmlRenderer()
        body_html_bytes = await html_renderer.render(template, data, ctx)
        body_html = body_html_bytes.decode("utf-8") if isinstance(body_html_bytes, bytes) else str(body_html_bytes)

        # 2. 获取纸张配置
        paper = template.get("paper", {})
        paper_size = paper.get("size", "A4")
        orientation = paper.get("orientation", "portrait")
        margin = paper.get("marginMm", {})
        margin_top = margin.get("top", 18)
        margin_right = margin.get("right", 18)
        margin_bottom = margin.get("bottom", 18)
        margin_left = margin.get("left", 18)

        # 3. 组装完整 HTML (含 CSS @page 规则)
        full_html = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
@page {{
    size: {paper_size} {orientation};
    margin: {margin_top}mm {margin_right}mm {margin_bottom}mm {margin_left}mm;
}}
body {{
    font-family: "PingFang SC", "Microsoft YaHei", "Noto Sans CJK SC", "STSong-Light", sans-serif;
    font-size: 12px;
    color: #1F2937;
    line-height: 1.5;
    margin: 0;
    padding: 0;
}}
table {{
    border-collapse: collapse;
    width: 100%;
}}
td, th {{
    padding: 6px 8px;
}}
.title {{
    font-size: 20px;
    font-weight: bold;
    text-align: center;
    color: #0F172A;
    margin: 8px 0;
}}
.text {{
    font-size: 12px;
    color: #1F2937;
    margin: 4px 0;
}}
.spacer {{
    /* height set inline */
}}
.line hr {{
    border: none;
    border-top: 1px solid #E5E7EB;
    margin: 4px 0;
}}
</style>
</head>
<body>
{body_html}
</body>
</html>"""

        # 4. WeasyPrint 转 PDF
        try:
            import weasyprint
            doc = weasyprint.HTML(string=full_html)
            pdf_bytes = doc.write_pdf()
            return pdf_bytes
        except ImportError:
            logger.warning("[UDPE] WeasyPrint 未安装，回退到 reportlab")
            from .pdf_renderer import PdfRenderer
            fallback = PdfRenderer()
            return await fallback.render(template, data, ctx)
        except Exception as e:
            logger.error(f"[UDPE] WeasyPrint 渲染失败: {e}，回退到 reportlab")
            from .pdf_renderer import PdfRenderer
            fallback = PdfRenderer()
            return await fallback.render(template, data, ctx)
