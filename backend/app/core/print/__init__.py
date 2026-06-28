"""UDPE 核心抽象层（与 core/database 同级）。

设计文档：plans/udpe-design/design.md

公开 API：
- Renderer / DataResolver / VariableProvider（Protocols）
- RendererRegistry / ResolverRegistry / ProviderRegistry（注册中心）
- BindContext / RenderContext / PrintRequest / PrintResult（数据类）
- UDPE 异常族
"""
from app.core.print.context import (
    BindContext,
    PrintRequest,
    PrintResult,
    RenderContext,
)
from app.core.print.exceptions import (
    PrintDataResolveError,
    PrintPermissionDeniedError,
    PrintRenderError,
    PrintTemplateInactiveError,
    PrintTemplateNotFoundError,
    RendererNotFoundError,
    ResolverNotFoundError,
)
from app.core.print.protocols import (
    DataResolver,
    Renderer,
    VariableProvider,
)
from app.core.print.registry import (
    ProviderRegistry,
    RendererRegistry,
    ResolverRegistry,
)

__all__ = [
    # Protocols
    "Renderer", "DataResolver", "VariableProvider",
    # Registries
    "RendererRegistry", "ResolverRegistry", "ProviderRegistry",
    # Contexts
    "BindContext", "RenderContext", "PrintRequest", "PrintResult",
    # Exceptions
    "PrintTemplateNotFoundError", "PrintTemplateInactiveError",
    "PrintRenderError", "PrintDataResolveError", "PrintPermissionDeniedError",
    "RendererNotFoundError", "ResolverNotFoundError",
]
