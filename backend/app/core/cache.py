"""
Redis 缓存层
- 用法: @cache(key_prefix="dashboard:summary", ttl=300)
- 自动 key 生成: {prefix}:{user_id}:{args_hash}
- 后端写操作时主动 invalidate(prefix)
"""
import hashlib
import json
import logging
from functools import wraps
from typing import Any, Callable, Optional

from app.core.sse import get_redis  # 用同一连接池

logger = logging.getLogger(__name__)

DEFAULT_TTL = 300  # 5 分钟


def _hash_args(*args, **kwargs) -> str:
    """根据 args/kwargs 生成 key 后缀"""
    raw = repr(args) + repr(sorted(kwargs.items()))
    return hashlib.md5(raw.encode()).hexdigest()[:12]


def _make_key(prefix: str, *args, **kwargs) -> str:
    return f"cache:{prefix}:{_hash_args(*args, **kwargs)}"


async def get(key: str) -> Optional[Any]:
    """取缓存"""
    try:
        r = await get_redis()
        raw = await r.get(key)
        if raw:
            return json.loads(raw)
    except Exception as e:
        logger.warning(f"[cache] get {key} 失败: {e}")
    return None


async def set_(key: str, value: Any, ttl: int = DEFAULT_TTL) -> None:
    """设缓存（set_ 避免与 builtin set 冲突）"""
    try:
        r = await get_redis()
        await r.set(key, json.dumps(value, ensure_ascii=False, default=str), ex=ttl)
    except Exception as e:
        logger.warning(f"[cache] set {key} 失败: {e}")


async def delete_pattern(pattern: str) -> int:
    """按模式删除（用于失效整组缓存）"""
    try:
        r = await get_redis()
        deleted = 0
        async for k in r.scan_iter(match=pattern):
            await r.delete(k)
            deleted += 1
        return deleted
    except Exception as e:
        logger.warning(f"[cache] delete_pattern {pattern} 失败: {e}")
        return 0


def _filter_args(args: tuple, kwargs: dict) -> tuple:
    """
    过滤掉非业务参数（db session / AsyncSession / CurrentUser 等）
    R11A 修复：之前 db session 进 args hash 导致 cache key 每次都不同
    """
    def _is_skipable(v):
        # 跳过 db session / ORM 对象
        cls_name = type(v).__name__
        return cls_name in ('AsyncSession', 'Session', 'CurrentUser', 'User', 'Department', 'Role')

    filtered_args = tuple(a for a in args if not _is_skipable(a))
    filtered_kwargs = {k: v for k, v in kwargs.items() if not _is_skipable(v)}
    return filtered_args, filtered_kwargs


def cache(key_prefix: str, ttl: int = DEFAULT_TTL):
    """
    装饰器：缓存函数结果
    用法:
        @cache("dashboard:summary", ttl=300)
        async def summary(db, user):
            ...
    R11A：自动跳过 db session 等 ORM 对象，避免 key 污染
    """
    def decorator(fn: Callable):
        @wraps(fn)
        async def wrapper(*args, **kwargs):
            f_args, f_kwargs = _filter_args(args, kwargs)
            key = _make_key(key_prefix, *f_args, **f_kwargs)
            cached = await get(key)
            if cached is not None:
                logger.debug(f"[cache] HIT {key}")
                # R7.2: 缓存命中埋点（如果是 AI 类型，单独计数）
                if key_prefix.startswith("ai:"):
                    try:
                        from app.core.metrics import business_ai_total
                        ai_type = key_prefix.split(":", 1)[1]  # ask / risk_scan
                        business_ai_total.labels(type=ai_type, cache="hit").inc()
                    except Exception:
                        pass
                return cached
            result = await fn(*args, **kwargs)
            # 只缓存可序列化的结果
            try:
                await set_(key, result, ttl=ttl)
                logger.debug(f"[cache] MISS → SET {key} (ttl={ttl}s)")
                if key_prefix.startswith("ai:"):
                    try:
                        from app.core.metrics import business_ai_total
                        ai_type = key_prefix.split(":", 1)[1]
                        business_ai_total.labels(type=ai_type, cache="miss").inc()
                    except Exception:
                        pass
            except Exception:
                pass
            return result
        return wrapper
    return decorator


async def invalidate(prefix: str) -> int:
    """失效某 prefix 下所有缓存"""
    return await delete_pattern(f"cache:{prefix}:*")
