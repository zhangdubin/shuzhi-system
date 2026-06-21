"""
数据库连接 + 会话管理
- R11A：注册 SQLAlchemy event listener，记录 DB 慢查询
"""
import logging
import time
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy import event

from app.config import settings

logger = logging.getLogger(__name__)

SLOW_QUERY_THRESHOLD_MS = 200  # 200ms


class Base(DeclarativeBase):
    """所有 ORM 模型的基类"""
    pass


engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,
    pool_size=settings.DB_POOL_SIZE,
    max_overflow=settings.DB_MAX_OVERFLOW,
    pool_recycle=settings.DB_POOL_RECYCLE,
    # 关闭 pool_pre_ping：asyncpg + SQLAlchemy 2.0.27 + greenlet 组合下
    # pool_pre_ping=True 会在同步上下文 await，触发 MissingGreenlet。
    # 业务侧已经用 await get_db() 隔离，不需要预 ping。
    pool_pre_ping=False,
)

AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)


# ============================================================
# R11A：DB 慢查询监控（SQLAlchemy core event listener）
# 监听 before/after cursor execute，记录超过 200ms 的 SQL
# ============================================================
@event.listens_for(engine.sync_engine, "before_cursor_execute")
def _before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
    """记录查询开始时间"""
    conn.info.setdefault('_query_start', {})[id(cursor)] = time.perf_counter()


@event.listens_for(engine.sync_engine, "after_cursor_execute")
def _after_cursor_execute(conn, cursor, statement, parameters, context, executemany):
    """查询完成时计算耗时，超过 200ms 记 prometheus + log warning"""
    starts = conn.info.get('_query_start', {})
    start = starts.pop(id(cursor), None)
    if start is None:
        return
    elapsed_ms = (time.perf_counter() - start) * 1000

    # 解析 SQL 类型 + 表名
    stmt_stripped = statement.strip().split()
    operation = stmt_stripped[0].upper() if stmt_stripped else 'UNKNOWN'
    if operation not in ('SELECT', 'INSERT', 'UPDATE', 'DELETE'):
        return
    # 简单提取表名（FROM/JOIN/INTO/UPDATE 后第一个 token）
    table = 'unknown'
    upper = statement.upper()
    for kw in ('FROM', 'JOIN', 'INTO', 'UPDATE'):
        idx = upper.find(f' {kw} ')
        if idx > 0:
            after = statement[idx + len(kw) + 2:].strip()
            # 取第一个 token，去掉 schema 前缀
            table = after.split()[0].split('.')[-1].rstrip(',;(').strip('"').lower()
            break

    # 记 prometheus
    try:
        from app.core.metrics import db_query_duration_seconds, db_slow_queries_total
        db_query_duration_seconds.labels(table=table, operation=operation).observe(elapsed_ms / 1000)
        if elapsed_ms > SLOW_QUERY_THRESHOLD_MS:
            db_slow_queries_total.labels(table=table, operation=operation).inc()
            logger.warning(
                f"[SLOW SQL] {elapsed_ms:.1f}ms · {operation} {table} · "
                f"stmt={statement[:200]}{'...' if len(statement) > 200 else ''}"
            )
    except Exception:
        pass  # 监控失败不影响业务


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI 依赖：获取数据库会话"""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
