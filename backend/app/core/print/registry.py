"""UDPE 注册中心。

设计文档：plans/udpe-design/design.md §六 6.2

三个独立的注册中心，存放 Renderer / DataResolver / VariableProvider。
线程安全（asyncio 单线程，无需锁）。
"""
import logging
from typing import Any, Optional

from app.core.print.exceptions import (
    RendererNotFoundError,
    ResolverNotFoundError,
)
from app.core.print.protocols import (
    DataResolver,
    Renderer,
    VariableProvider,
)

logger = logging.getLogger(__name__)


class RendererRegistry:
    """全局 Renderer 注册中心。key = renderer.name"""
    _registry: dict[str, Renderer] = {}

    @classmethod
    def register(cls, renderer: Renderer) -> None:
        if renderer.name in cls._registry:
            logger.warning(f"[UDPE] Renderer '{renderer.name}' 已存在，将被覆盖")
        cls._registry[renderer.name] = renderer
        logger.info(f"[UDPE] Renderer 已注册: {renderer.name} (mime={renderer.mime_type})")

    @classmethod
    def get(cls, name: str) -> Renderer:
        if name not in cls._registry:
            raise RendererNotFoundError(f"Renderer '{name}' 未注册（已注册: {list(cls._registry.keys())}）")
        return cls._registry[name]

    @classmethod
    def all(cls) -> dict[str, Renderer]:
        return dict(cls._registry)

    @classmethod
    def clear(cls) -> None:
        cls._registry.clear()


class ResolverRegistry:
    """全局 DataResolver 注册中心。key = resolver.doc_type"""
    _registry: dict[str, DataResolver] = {}

    @classmethod
    def register(cls, resolver: DataResolver) -> None:
        if resolver.doc_type in cls._registry:
            logger.warning(f"[UDPE] Resolver '{resolver.doc_type}' 已存在，将被覆盖")
        cls._registry[resolver.doc_type] = resolver
        logger.info(f"[UDPE] Resolver 已注册: {resolver.doc_type}")

    @classmethod
    def get(cls, doc_type: str) -> Optional[DataResolver]:
        """找不到返回 None（不抛异常），由调用方决定如何降级。"""
        return cls._registry.get(doc_type)

    @classmethod
    def must_get(cls, doc_type: str) -> DataResolver:
        if doc_type not in cls._registry:
            raise ResolverNotFoundError(f"Resolver '{doc_type}' 未注册")
        return cls._registry[doc_type]

    @classmethod
    def all(cls) -> dict[str, DataResolver]:
        return dict(cls._registry)

    @classmethod
    def clear(cls) -> None:
        cls._registry.clear()


class ProviderRegistry:
    """全局 VariableProvider 注册中心。key = provider.name"""
    _registry: dict[str, VariableProvider] = {}

    @classmethod
    def register(cls, provider: VariableProvider) -> None:
        if provider.name in cls._registry:
            logger.warning(f"[UDPE] Provider '{provider.name}' 已存在，将被覆盖")
        cls._registry[provider.name] = provider
        logger.info(f"[UDPE] Provider 已注册: {provider.name}")

    @classmethod
    def get(cls, name: str) -> Optional[VariableProvider]:
        return cls._registry.get(name)

    @classmethod
    def all(cls) -> dict[str, VariableProvider]:
        return dict(cls._registry)

    @classmethod
    def clear(cls) -> None:
        cls._registry.clear()
