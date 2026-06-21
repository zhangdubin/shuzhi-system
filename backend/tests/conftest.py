"""
测试公用 fixtures

提供：
- db: 内存 SQLite + 自动建表
- client: AsyncClient（用测试数据库）
- auth_token: 已登录的 token
- admin_user / normal_user: 种子用户
- sample_project: 一个示例项目
"""
import asyncio
import os
from typing import AsyncGenerator

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

# ============== 测试环境变量（必须在 import app 之前设置） ==============

os.environ["ENV"] = "testing"
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///:memory:"
os.environ["REDIS_URL"] = "redis://localhost:6379/15"  # 用独立的 db
os.environ["JWT_SECRET_KEY"] = "test-secret-key-not-for-production"
os.environ["LOG_LEVEL"] = "ERROR"  # 减少测试输出

# ============== 数据库（用 SQLite 内存，无需启动 PostgreSQL） ==============

from app.core.database import Base, get_db  # noqa: E402
from app.config import settings  # noqa: E402


@pytest_asyncio.fixture(scope="function")
async def engine():
    """每个测试函数一个新引擎（隔离）"""
    eng = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        echo=False,
        future=True,
    )

    # 启用 SQLite 外键
    @event.listens_for(eng.sync_engine, "connect")
    def _fk_on_connect(dbapi_connection, _):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    async with eng.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield eng
    await eng.dispose()


@pytest_asyncio.fixture(scope="function")
async def session_factory(engine) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


@pytest_asyncio.fixture(scope="function")
async def db(session_factory) -> AsyncGenerator[AsyncSession, None]:
    """每个测试一个 session"""
    async with session_factory() as session:
        yield session


# ============== FastAPI 客户端 ==============

from app.main import app  # noqa: E402


@pytest_asyncio.fixture(scope="function")
async def client(session_factory) -> AsyncGenerator[AsyncClient, None]:
    """FastAPI 测试客户端，注入测试数据库"""

    async def _get_db():
        async with session_factory() as session:
            yield session

    app.dependency_overrides[get_db] = _get_db

    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()


# ============== 种子数据 ==============

from app.modules.auth.models import (  # noqa: E402
    User, Role, Permission, Department, Dictionary
)
from app.modules.project.models import Project, Client  # noqa: E402
from app.core.security import hash_password  # noqa: E402
from datetime import date  # noqa: E402


@pytest_asyncio.fixture
async def admin_user(db) -> User:
    """管理员账号 admin / admin123"""
    # 部门
    dept = Department(name="总经办", code="GM")
    db.add(dept)
    await db.flush()

    # 角色 + 权限
    admin_role = Role(name="超级管理员", code="admin", is_builtin=True)
    db.add(admin_role)
    await db.flush()

    perm = Permission(name="项目写入", code="project:write", resource="project", action="write")
    db.add(perm)
    await db.flush()

    admin_role.permissions.append(perm)
    await db.flush()

    # 用户
    user = User(
        username="admin",
        name="管理员",
        email="admin@example.com",
        phone="13800000001",
        password_hash=hash_password("admin123"),
        is_active=True,
        is_admin=True,
        department_id=dept.id,
    )
    db.add(user)
    await db.flush()
    user.roles.append(admin_role)
    await db.commit()
    await db.refresh(user)
    return user


@pytest_asyncio.fixture
async def normal_user(db) -> User:
    """普通员工 zhangsan / user123（无 project:write 权限）"""
    dept = Department(name="业务部", code="SALES")
    db.add(dept)
    await db.flush()

    user_role = Role(name="业务专员", code="sales", is_builtin=False)
    db.add(user_role)
    await db.flush()

    user = User(
        username="zhangsan",
        name="张三",
        email="zhangsan@example.com",
        phone="13800000002",
        password_hash=hash_password("user123"),
        is_active=True,
        is_admin=False,
        department_id=dept.id,
    )
    db.add(user)
    await db.flush()
    user.roles.append(user_role)
    await db.commit()
    await db.refresh(user)
    return user


@pytest_asyncio.fixture
async def auth_token(client, admin_user) -> str:
    """已登录的 token（admin）"""
    resp = await client.post("/api/v1/auth/login", json={
        "account": "admin",
        "password": "admin123",
    })
    assert resp.status_code == 200, resp.text
    return resp.json()["token"]


@pytest_asyncio.fixture
async def user_token(client, normal_user) -> str:
    """普通用户 token"""
    resp = await client.post("/api/v1/auth/login", json={
        "account": "zhangsan",
        "password": "user123",
    })
    assert resp.status_code == 200, resp.text
    return resp.json()["token"]


@pytest_asyncio.fixture
async def auth_headers(auth_token) -> dict:
    return {"Authorization": f"Bearer {auth_token}"}


@pytest_asyncio.fixture
async def sample_client(db) -> Client:
    """示例客户"""
    c = Client(
        name="示例客户有限公司",
        short_name="示例客户",
        industry="制造业",
        contact_person="李四",
        contact_phone="13900000001",
    )
    db.add(c)
    await db.commit()
    await db.refresh(c)
    return c


@pytest_asyncio.fixture
async def sample_project(db, admin_user, sample_client) -> Project:
    """示例项目"""
    p = Project(
        code="PRJ-2026-0001",
        name="示例项目",
        type="系统集成",
        status="active",
        client_id=sample_client.id,
        manager_id=admin_user.id,
        start_date=date(2026, 1, 1),
        end_date=date(2026, 12, 31),
        contract_amount=100000000,  # 100 万（分）
        budget=80000000,            # 80 万
        spent=10000000,             # 10 万
        progress=25,
        description="用于测试的示例项目",
    )
    db.add(p)
    await db.commit()
    await db.refresh(p)
    return p
