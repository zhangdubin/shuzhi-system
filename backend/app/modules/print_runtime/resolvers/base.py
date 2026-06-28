"""UDPE Resolver 基类（注入 db session 到 ctx）。

设计文档：plans/udpe-design/design.md §六 6.4

UDPE 引擎在调用 resolver.resolve() 之前，会把 db session 塞到 ctx.extra["db"] 里。
所有 Resolver 继承 BaseResolver 后直接用 self.db。
"""
from typing import Any

from app.core.print import BindContext, DataResolver


class BaseResolver(DataResolver):
    """Resolver 基类：自动从 ctx.extra 取 db。"""

    async def resolve(self, identifier: Any, ctx: BindContext) -> dict:
        # 把 db 缓存到 ctx 上，方便子类调用 service 时用
        if "db" not in ctx.extra:
            raise RuntimeError(f"{self.__class__.__name__}: ctx.extra['db'] 未注入（service 层应注入）")
        return await self._resolve(identifier, ctx)

    async def _resolve(self, identifier: Any, ctx: BindContext) -> dict:
        raise NotImplementedError
