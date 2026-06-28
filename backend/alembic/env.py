"""
Alembic 环境配置（支持 async SQLAlchemy）
"""
import asyncio
from logging.config import fileConfig

from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

from alembic import context

# 导入 settings
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.config import settings
from app.core.database import Base
# 导入所有模型（让 Base.metadata 知道）
from app.modules.auth.models import *  # noqa
from app.modules.project.models import *  # noqa
# 阶段 A 新增模块
from app.modules.contract.models import *  # noqa
from app.modules.expense.models import *  # noqa
from app.modules.receivable.models import *  # noqa
from app.modules.invoice_template.models import *  # noqa
from app.modules.invoice_ocr.models import *  # noqa
from app.modules.invoice_verify.models import *  # noqa
from app.modules.common.models import *  # noqa
# AI 平台（Phase 1）
from app.modules.ai.models import *  # noqa
from app.modules.print_runtime.models import *  # noqa

config = context.config

# 用 settings 覆盖
config.set_main_option("sqlalchemy.url", settings.DATABASE_URL)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """离线模式（生成 SQL 脚本）"""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url, target_metadata=target_metadata,
        literal_binds=True, dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online() -> None:
    """在线模式（连接数据库跑迁移）"""
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())
