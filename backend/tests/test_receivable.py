"""
回款模块测试

测试矩阵（8 endpoint × 5 类共性）：
- list / detail / create / update / delete / remind / receive / stats
- 权限：未登录 → 401 / 普通用户写 → 403 / 无 receivable:write → 403
- 业务：到账、催收、状态机

依据：R1-R16 文档 + 现有 conftest.py fixture 风格
"""
import pytest
import pytest_asyncio
from datetime import date, datetime, timedelta
from decimal import Decimal

from app.core.security import hash_password
from app.modules.auth.models import User, Role, Permission, Department
from app.modules.receivable.models import Receivable


# ============== 本地 fixture ==============

@pytest_asyncio.fixture
async def receivable_admin(db, sample_client):
    """拥有 receivable:write 权限的管理员"""
    dept = Department(name="回款测试部门", code="RECEIVABLE_TEST")
    db.add(dept)
    await db.flush()

    role = Role(name="回款管理员", code="receivable_admin", is_builtin=False)
    db.add(role)
    await db.flush()

    from app.modules.auth.models import RolePermission, UserRole
    for code, action in [("receivable:read", "read"),
                         ("receivable:write", "write")]:
        p = Permission(name=code, code=code, resource="receivable", action=action)
        db.add(p)
        await db.flush()
        db.add(RolePermission(role_id=role.id, permission_id=p.id))
    await db.flush()

    user = User(
        username="receivable_admin",
        name="回款管理员",
        email="receivable_admin@example.com",
        phone="13800004000",
        password_hash=hash_password("test123"),
        is_active=True,
        is_admin=True,
        department_id=dept.id,
    )
    db.add(user)
    await db.flush()
    db.add(UserRole(user_id=user.id, role_id=role.id))
    await db.commit()
    return user


@pytest_asyncio.fixture
async def receivable_admin_token(client, receivable_admin):
    resp = await client.post("/api/v1/auth/login", json={
        "account": "receivable_admin", "password": "test123",
    })
    assert resp.status_code == 200, resp.text
    return resp.json()["token"]


@pytest_asyncio.fixture
async def receivable_admin_headers(receivable_admin_token):
    return {"Authorization": f"Bearer {receivable_admin_token}"}


@pytest_asyncio.fixture
async def sample_receivable(db, sample_client, receivable_admin):
    """示例待收款项"""
    r = Receivable(
        code="RV-2026-0001",
        type="合同尾款",
        plan_amount=10000000,  # 10 万（分）
        received_amount=0,
        status="pending",
        plan_date=date(2026, 2, 1),
        client_id=sample_client.id,
        manager_id=receivable_admin.id,
    )
    db.add(r)
    await db.commit()
    await db.refresh(r)
    return r


# ============== list ==============

@pytest.mark.asyncio
async def test_list_unauthorized(client):
    resp = await client.post("/api/v1/receivables/list", json={})
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_list_empty(client, receivable_admin_headers):
    resp = await client.post(
        "/api/v1/receivables/list", json={}, headers=receivable_admin_headers,
    )
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["total"] == 0


@pytest.mark.asyncio
async def test_list_with_data(client, receivable_admin_headers, sample_receivable):
    resp = await client.post(
        "/api/v1/receivables/list", json={}, headers=receivable_admin_headers,
    )
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["total"] == 1
    assert data["list"][0]["code"] == "RV-2026-0001"
    assert Decimal(str(data["list"][0]["planAmount"])) == Decimal("100000.00")


@pytest.mark.asyncio
async def test_list_keyword_filter(client, receivable_admin_headers, sample_receivable):
    resp = await client.post(
        "/api/v1/receivables/list",
        json={"keyword": "RV-2026-0001"},
        headers=receivable_admin_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["data"]["total"] == 1


@pytest.mark.asyncio
async def test_list_keyword_miss(client, receivable_admin_headers, sample_receivable):
    resp = await client.post(
        "/api/v1/receivables/list",
        json={"keyword": "不存在的关键词"},
        headers=receivable_admin_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["data"]["total"] == 0


@pytest.mark.asyncio
async def test_list_status_filter(client, receivable_admin_headers, sample_receivable):
    resp = await client.post(
        "/api/v1/receivables/list",
        json={"filters": {"status": "pending"}},
        headers=receivable_admin_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["data"]["total"] == 1


@pytest.mark.asyncio
async def test_list_pagination(client, receivable_admin_headers, db, sample_client, receivable_admin):
    for i in range(5):
        r = Receivable(
            code=f"RV-PAGE-{i:03d}", type="合同尾款",
            plan_amount=10000, received_amount=0, status="pending",
            plan_date=date(2026, 2, 1), client_id=sample_client.id,
            manager_id=receivable_admin.id,
        )
        db.add(r)
    await db.commit()

    resp = await client.post(
        "/api/v1/receivables/list",
        json={"page": 1, "pageSize": 2},
        headers=receivable_admin_headers,
    )
    assert resp.json()["data"]["total"] == 5
    assert len(resp.json()["data"]["list"]) == 2


# ============== detail ==============

@pytest.mark.asyncio
async def test_detail_unauthorized(client, sample_receivable):
    resp = await client.post(
        f"/api/v1/receivables/detail?receivableId={sample_receivable.id}",
        json={},
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_detail_not_found(client, receivable_admin_headers):
    resp = await client.post(
        "/api/v1/receivables/detail?receivableId=99999",
        headers=receivable_admin_headers, json={},
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_detail_success(client, receivable_admin_headers, sample_receivable):
    resp = await client.post(
        f"/api/v1/receivables/detail?receivableId={sample_receivable.id}",
        headers=receivable_admin_headers, json={},
    )
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["code"] == "RV-2026-0001"
    assert data["status"] == "pending"


# ============== create ==============

@pytest.mark.asyncio
async def test_create_unauthorized(client, sample_client):
    resp = await client.post(
        "/api/v1/receivables/create", json={
            "type": "合同尾款", "planAmount": 100000, "planDate": "2026-02-01",
            "clientId": sample_client.id,
        },
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_create_permission_denied(client, user_headers, sample_client):
    resp = await client.post(
        "/api/v1/receivables/create",
        headers=user_headers,
        json={
            "type": "合同尾款", "planAmount": 100000, "planDate": "2026-02-01",
            "clientId": sample_client.id,
        },
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_create_success(client, receivable_admin_headers, sample_client):
    resp = await client.post(
        "/api/v1/receivables/create",
        headers=receivable_admin_headers,
        json={
            "type": "合同尾款", "planAmount": 50000000,
            "planDate": "2026-02-01", "clientId": sample_client.id,
        },
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["code"] == 0
    assert "receivableId" in body["data"]


# ============== update ==============

@pytest.mark.asyncio
async def test_update_unauthorized(client, sample_receivable):
    resp = await client.post(
        f"/api/v1/receivables/update?receivableId={sample_receivable.id}",
        json={"type": "进度款"},
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_update_success(client, receivable_admin_headers, sample_receivable):
    resp = await client.post(
        f"/api/v1/receivables/update?receivableId={sample_receivable.id}",
        headers=receivable_admin_headers,
        json={"type": "进度款", "planAmount": 8000000},
    )
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["type"] == "进度款"


@pytest.mark.asyncio
async def test_update_not_found(client, receivable_admin_headers):
    resp = await client.post(
        "/api/v1/receivables/update?receivableId=99999",
        headers=receivable_admin_headers, json={"type": "x"},
    )
    assert resp.status_code == 404


# ============== delete ==============

@pytest.mark.asyncio
async def test_delete_unauthorized(client, sample_receivable):
    resp = await client.post(
        f"/api/v1/receivables/delete?receivableId={sample_receivable.id}",
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_delete_success(client, receivable_admin_headers, sample_receivable):
    resp = await client.post(
        f"/api/v1/receivables/delete?receivableId={sample_receivable.id}",
        headers=receivable_admin_headers,
    )
    assert resp.status_code == 200
    # 二次查询应 404
    detail = await client.post(
        f"/api/v1/receivables/detail?receivableId={sample_receivable.id}",
        headers=receivable_admin_headers, json={},
    )
    assert detail.status_code == 404


# ============== remind（催收） ==============

@pytest.mark.asyncio
async def test_remind_unauthorized(client, sample_receivable):
    resp = await client.post(
        "/api/v1/receivables/remind",
        json={"receivableId": sample_receivable.id, "remark": "请尽快付款"},
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_remind_success(client, receivable_admin_headers, sample_receivable):
    resp = await client.post(
        "/api/v1/receivables/remind",
        headers=receivable_admin_headers,
        json={"receivableId": sample_receivable.id, "type": "phone", "content": "请尽快付款"},
    )
    assert resp.status_code == 200
    assert resp.json()["code"] == 0


# ============== receive（到账） ==============

@pytest.mark.asyncio
async def test_receive_unauthorized(client, sample_receivable):
    resp = await client.post(
        "/api/v1/receivables/receive",
        json={"receivableId": sample_receivable.id, "receivedAmount": 100000, "receivedDate": "2026-02-15"},
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_receive_success(client, receivable_admin_headers, sample_receivable):
    resp = await client.post(
        "/api/v1/receivables/receive",
        headers=receivable_admin_headers,
        json={"receivableId": sample_receivable.id, "receivedAmount": 5000000, "receivedDate": "2026-02-15"},
    )
    assert resp.status_code == 200
    assert resp.json()["code"] == 0


# ============== stats ==============

@pytest.mark.asyncio
async def test_stats_unauthorized(client):
    resp = await client.post("/api/v1/receivables/stats", json={})
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_stats_empty(client, receivable_admin_headers):
    resp = await client.post(
        "/api/v1/receivables/stats", json={}, headers=receivable_admin_headers,
    )
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_stats_with_data(client, receivable_admin_headers, sample_receivable):
    resp = await client.post(
        "/api/v1/receivables/stats", json={}, headers=receivable_admin_headers,
    )
    assert resp.status_code == 200
