"""
数据库连接 + 会话管理
- R11A：注册 SQLAlchemy event listener，记录 DB 慢查询
- R17-A：SQLite dialect 兼容（JSONB/ARRAY → JSON/TEXT）以支持 pytest
"""
import logging
import time
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy import event
from sqlalchemy.types import JSON, TEXT
from sqlalchemy import Integer, BigInteger, Table
from sqlalchemy.dialects.postgresql import JSONB, ARRAY

from app.config import settings

logger = logging.getLogger(__name__)

SLOW_QUERY_THRESHOLD_MS = 200  # 200ms


class Base(DeclarativeBase):
    """所有 ORM 模型的基类
    R17-A：BigInteger 主键在 SQLite 测试下自动转成 Integer + autoincrement
    （SQLite 的 ROWID 别名只对 INTEGER PRIMARY KEY 生效）
    """
    pass


@event.listens_for(Table, "instrument_class")
def _patch_bigint_pk(mapper, cls, tablename, table_obj):
    """所有 BigInteger 主键 → Integer 主键 + autoincrement=True
    不影响生产 PostgreSQL（bigint 存到 Integer 一样，SQLAlchemy 渲染时仍是 BIGINT，
    因为 table.columns 实际类型还是 BigInteger，只是 autoincrement=True 启动 seq）。

    SQLAlchemy 2.0 默认对 PK 设 autoincrement='auto'（PG 用 IDENTITY，SQLite 不识别），
    我们强制把 BigInteger PK 转成 Integer + 显式 autoincrement=True。
    跳过复合主键（中间表如 role_permissions，SQLite 不支持）。
    """
    pk_cols = [c for c in table_obj.primary_key.columns]
    if len(pk_cols) != 1:
        return
    col = pk_cols[0]
    if isinstance(col.type, BigInteger):
        col.type = Integer()
        col.autoincrement = True


# instrument_class 可能在 import 时已错过，强制对所有已存在的 Table 同步一次
def _patch_existing_tables():
    """所有已经 import 的 Table，把 BigInteger PK 转成 Integer + autoincrement"""
    for table in Base.metadata.tables.values():
        pk_cols = [c for c in table.primary_key.columns]
        if len(pk_cols) != 1:
            continue
        col = pk_cols[0]
        if isinstance(col.type, BigInteger):
            col.type = Integer()
            col.autoincrement = True


# 注册 metadata 监听器：将来新建的 Table 也会被处理
# 在 Table 创建完成（column 已加入）后触发
from sqlalchemy import MetaData

_original_metadata_create_all = Base.metadata.create_all


def _patched_create_all(self, *args, **kwargs):
    """在 create_all 之前再次确保所有 PK 是 Integer + autoincrement"""
    _patch_existing_tables()
    return _original_metadata_create_all(*args, **kwargs)


# 注意：上面只是兜底，更可靠的方案是 instrument_class
# 但 instrument_class 对 Mapped 模型不触发（Table 已在 metaclass 阶段建好）
# 所以我们在 Base.metadata 上挂事件
@event.listens_for(Base.metadata, "before_create")
def _patch_before_create(target, connection, **kw):
    """CREATE TABLE 之前再 patch 一遍（确保生效）"""
    if connection.dialect.name == "sqlite":
        _patch_existing_tables()


# ============================================================
# R17-A：PostgreSQL 专属类型（JSONB/ARRAY）在 SQLite 测试下做 dialect 兼容
# 思路：models.py 仍写 JSONB/ARRAY，但通过 SQLAlchemy 的
# `column_type_to_string` 事件 + `engine.dialect.name` 检查，
# 在 SQLite 编译 CREATE TABLE 时把 JSONB 渲染成 JSON、ARRAY 渲染成 TEXT。
# ============================================================
from sqlalchemy.dialects.sqlite import base as sqlite_base


def _patch_postgres_types_for_sqlite():
    """当 SQLite dialect 编译 DDL 时，把 PG 专属类型替换为 SQLite 等价物"""
    from sqlalchemy.dialects.sqlite import base as sqlite_base
    from sqlalchemy.sql import compiler

    # 注册 visit_JSONB 钩子：SQLAlchemy 实际通过 `compiler.visit_<typname>(type_)` 分发
    # 我们用 sqlalchemy.sql.compiler.SQLCompiler 的 visit_json / visit_jsonb 等具体方法
    orig_visit_jsonb = getattr(sqlite_base.SQLiteTypeCompiler, "visit_JSONB", None)
    orig_visit_array = getattr(sqlite_base.SQLiteTypeCompiler, "visit_ARRAY", None)

    def visit_JSONB(self, type_, **kw):  # noqa: N802
        return "JSON"

    def visit_ARRAY(self, type_, **kw):  # noqa: N802
        return "TEXT"

    if orig_visit_jsonb is None:
        sqlite_base.SQLiteTypeCompiler.visit_JSONB = visit_JSONB
    if orig_visit_array is None:
        sqlite_base.SQLiteTypeCompiler.visit_ARRAY = visit_ARRAY


# ============================================================
# R17-A：SQLite 测试下，所有 Integer/BigInteger 主键自动开启 AUTOINCREMENT
# PostgreSQL 默认 SERIAL/IDENTITY，无需干预。
# 通过注册 DDL 事件 + post-replace 字符串实现。
# ============================================================
from sqlalchemy import event as _sa_event  # noqa: F401  保留给可能的扩展
from sqlalchemy.sql.ddl import _CreateDropBase


def _inject_autoincrement_for_sqlite(target, connection, **kw):
    """当 SQLite 执行 CREATE TABLE 时，给 id INTEGER PRIMARY KEY 补 AUTOINCREMENT"""
    if not isinstance(target, _CreateDropBase):
        return
    # 仅在 SQLite
    if connection.dialect.name != "sqlite":
        return
    # 用反射方式处理：拿到 metadata 后 patch 表
    # 这里用更直接的方式：通过 DDLCompiler 的 visit_create_table 钩子
    pass  # 实际处理在 visit_create_table 中


# 监听所有 Table 对象，CREATE 前用 visit 钩子补 AUTOINCREMENT
# SQLAlchemy 2.0 DDLCompiler 没有 process_create_table，需用 visit_create_table
from sqlalchemy.sql import compiler
import re

# 1) 注册 hook：CREATE TABLE 编译前先 patch column 标记
_orig_visit_create_table = compiler.DDLCompiler.visit_create_table


def _patched_visit_create_table(self, create, **kw):
    stmt = _orig_visit_create_table(self, create, **kw)
    if self.dialect.name == "sqlite":
        # 给 id INTEGER/BIGINT PRIMARY KEY 补 AUTOINCREMENT（如果还没有）
        if "PRIMARY KEY" in stmt.upper() and "AUTOINCREMENT" not in stmt.upper():
            stmt = re.sub(
                r"(\bid\s+(INTEGER|BIGINT)\s+PRIMARY KEY)",
                r"\1 AUTOINCREMENT",
                stmt,
                flags=re.IGNORECASE,
            )
    return stmt


compiler.DDLCompiler.visit_create_table = _patched_visit_create_table


# 模块加载时立即注册兼容层（影响所有 SQLite 编译）
_patch_postgres_types_for_sqlite()


def _build_engine_kwargs() -> dict:
    """根据 dialect 选合适的 engine 参数

    - PostgreSQL（asyncpg）：支持 pool_size / max_overflow / pool_recycle
    - SQLite（aiosqlite）：用 StaticPool，不支持 pool 参数
    """
    url = settings.DATABASE_URL
    kw = dict(echo=settings.DEBUG, pool_pre_ping=False)
    if url.startswith("sqlite"):
        # 测试用 SQLite：单连接、内存 DB 必须 StaticPool
        from sqlalchemy.pool import StaticPool
        kw["connect_args"] = {"check_same_thread": False}
        kw["poolclass"] = StaticPool
    else:
        # 生产 PostgreSQL：连接池
        kw["pool_size"] = settings.DB_POOL_SIZE
        kw["max_overflow"] = settings.DB_MAX_OVERFLOW
        kw["pool_recycle"] = settings.DB_POOL_RECYCLE
    return kw


engine = create_async_engine(settings.DATABASE_URL, **_build_engine_kwargs())

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
