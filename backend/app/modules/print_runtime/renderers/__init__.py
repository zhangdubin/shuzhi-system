"""UDPE 渲染器集合。

设计文档：plans/udpe-design/design.md §六 6.3

V1 提供两种：
- PdfRenderer  —— 服务端真 PDF（reportlab）
- HtmlRenderer —— 浏览器预览（Jinja2 等价纯 Python）
"""
from app.modules.print_runtime.renderers.html_renderer import HtmlRenderer
from app.modules.print_runtime.renderers.pdf_renderer import PdfRenderer

__all__ = ["HtmlRenderer", "PdfRenderer"]
