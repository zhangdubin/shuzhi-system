"""UDPE 上下文数据类。

设计文档：plans/udpe-design/design.md §六 6.2
"""
from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass
class BindContext:
    """数据绑定阶段的运行时上下文。

    携带当前用户、调用来源等元信息，供 Resolver / VariableProvider 决定如何取数。
    """
    operator_id: Optional[int] = None
    operator_name: Optional[str] = None
    source_module: Optional[str] = None
    source_id: Optional[str] = None
    extra: dict = field(default_factory=dict)


@dataclass
class RenderContext:
    """渲染阶段的运行时上下文。

    包含 RenderMode（html/pdf）、输出文件名、是否加水印等。
    """
    render_mode: str = "pdf"           # "html" | "pdf"
    copies: int = 1
    watermark: Optional[str] = None
    filename: Optional[str] = None
    options: dict = field(default_factory=dict)
    bind_ctx: Optional[BindContext] = None


@dataclass
class PrintRequest:
    """业务方传入的打印请求（service 层解包后的强类型）。"""
    template_code: str
    data: dict
    options: dict = field(default_factory=dict)


@dataclass
class PrintResult:
    """渲染完成后的产物。"""
    content: bytes
    filename: str
    mime_type: str
    log_id: int
    template_id: int
    renderer_name: str
    elapsed_ms: int
