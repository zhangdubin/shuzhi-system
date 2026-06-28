"""UDPE 三个核心 Protocol：Renderer / DataResolver / VariableProvider。

设计文档：plans/udpe-design/design.md §六 6.2

业务模块通过实现这些 Protocol 并 register 到 registry，
UDPE 引擎就能在运行时动态发现并调用。
"""
from typing import Any, Protocol, runtime_checkable

from app.core.print.context import BindContext, RenderContext


@runtime_checkable
class Renderer(Protocol):
    """模板 → 输出字节流。

    name: 注册名（'pdf' | 'html'）
    mime_type: 输出 MIME（'application/pdf' | 'text/html'）
    """
    name: str
    mime_type: str

    async def render(
        self,
        template: dict,        # 模板 schema（包含 body / vars / paper 等）
        data: dict,            # 业务数据（已合并 VariableProvider + Resolver 结果）
        ctx: RenderContext,
    ) -> bytes: ...


@runtime_checkable
class DataResolver(Protocol):
    """业务单据 ID → 业务数据 dict。

    doc_type: 'contract' | 'reimbursement' | 'expense' | 'invoice' | ...

    实现者负责：从 DB 读、按 identifier（id 或 code）查、组装成 dict。
    """
    doc_type: str

    async def resolve(self, identifier: Any, ctx: BindContext) -> dict: ...


@runtime_checkable
class VariableProvider(Protocol):
    """系统变量提供方（如：当前用户、企业名、IP、时间）。

    name: 注册名（'system' | 'company' | 'env'）
    """
    name: str

    async def provide(self, ctx: BindContext) -> dict: ...
