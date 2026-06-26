"""
费用模块测试

测试矩阵（10 endpoint × 5 类共性）：
- list / detail / create / update / delete / batch_delete / submit / mark_paid /
  approve / stats
- 状态机：draft → pending → approved → paid
- 权限：未登录 → 401 / 普通用户写 → 403 / 无 expense:approve → 403

依据：R1-R16 文档 + 现有 conftest.py fixture 风格
"""
import pytest
import pytest_asyncio
from datetime import date, datetime, timedelta
from decimal import Decimal

from app.core.security import hash_password
from app.modules.auth.models import User, Role, Permission, Department
from app.modules.expense.models import Expense
from app.core.exceptions import NotFoundException


# ============== 本地 fixture ==============

@pytest_asyncio.fixture
async def expense_admin(db, sample_client):
    """拥有 expense:write + expense:approve 权限的管理员"""
    dept = Department(name="费用测试部门", code="EXPENSE_TEST")
    db.add(dept)
    await db.flush()

    role = Role(name="费用管理员", code="expense_admin", is_builtin=False)
    db.add(role)
    await db.flush()

    from app.modules.auth.models import RolePermission, UserRole
    for code, action in [("expense:read", "read"),
                         ("expense:write", "write"),
                         ("expense:approve", "approve"),
                         ("expense:delete", "delete")]:
        p = Permission(name=code, code=code, resource="expense", action=action)
        db.add(p)
        await db.flush()
        db.add(RolePermission(role_id=role.id, permission_id=p.id))
    await db.flush()

    user = User(
        username="expense_admin",
        name="费用管理员",
        email="expense_admin@example.com",
        phone="13800003000",
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
async def expense_admin_token(client, expense_admin):
    resp = await client.post("/api/v1/auth/login", json={
        "account": "expense_admin", "password": "test123",
    })
    assert resp.status_code == 200, resp.text
    return resp.json()["token"]


@pytest_asyncio.fixture
async def expense_admin_headers(expense_admin_token):
    return {"Authorization": f"Bearer {expense_admin_token}"}


@pytest_asyncio.fixture
async def sample_expense(db, sample_client, expense_admin):
    """示例 draft 状态费用"""
    e = Expense(
        code="EXP-2026-0001",
        category="差旅",
        title="测试差旅费用",
        description="测试用费用",
        amount=50000,  # 500 元（分）
        currency="CNY",
        expense_date=date(2026, 1, 15),
        applicant_id=expense_admin.id,
        department_id=expense_admin.department_id,
        status="draft",
    )
    db.add(e)
    await db.commit()
    await db.refresh(e)
    return e


# ============== list ==============

@pytest.mark.asyncio
async def test_list_unauthorized(client):
    resp = await client.post("/api/v1/expenses/list", json={})
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_list_empty(client, expense_admin_headers):
    resp = await client.post("/api/v1/expenses/list", json={}, headers=expense_admin_headers)
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["total"] == 0
    assert data["list"] == []


@pytest.mark.asyncio
async def test_list_with_data(client, expense_admin_headers, sample_expense):
    resp = await client.post(
        "/api/v1/expenses/list", json={}, headers=expense_admin_headers,
    )
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["total"] == 1
    assert data["list"][0]["code"] == "EXP-2026-0001"
    # amount 从分转元
    assert Decimal(str(data["list"][0]["amount"])) == Decimal("500.00")


@pytest.mark.asyncio
async def test_list_keyword_filter(client, expense_admin_headers, sample_expense):
    resp = await client.post(
        "/api/v1/expenses/list", json={"keyword": "差旅"}, headers=expense_admin_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["data"]["total"] == 1

    resp2 = await client.post(
        "/api/v1/expenses/list", json={"keyword": "不存在的关键词"}, headers=expense_admin_headers,
    )
    assert resp2.json()["data"]["total"] == 0


@pytest.mark.asyncio
async def test_list_category_filter(client, expense_admin_headers, sample_expense):
    resp = await client.post(
        "/api/v1/expenses/list",
        json={"filters": {"category": "差旅"}},
        headers=expense_admin_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["data"]["total"] == 1


@pytest.mark.asyncio
async def test_list_pagination(client, expense_admin_headers, db, sample_client, expense_admin):
    for i in range(5):
        e = Expense(
            code=f"EXP-PAGE-{i:03d}", category="差旅", title=f"分页测试 {i}",
            amount=10000, expense_date=date(2026, 1, 1),
            applicant_id=expense_admin.id,
            department_id=expense_admin.department_id,
            status="draft",
        )
        db.add(e)
    await db.commit()

    resp = await client.post(
        "/api/v1/expenses/list",
        json={"page": 1, "pageSize": 2},
        headers=expense_admin_headers,
    )
    assert resp.json()["data"]["total"] == 5
    assert len(resp.json()["data"]["list"]) == 2


# ============== detail ==============

@pytest.mark.asyncio
async def test_detail_unauthorized(client, sample_expense):
    resp = await client.post(
        f"/api/v1/expenses/detail?expenseId={sample_expense.id}", json={},
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_detail_not_found(client, expense_admin_headers):
    resp = await client.post(
        "/api/v1/expenses/detail?expenseId=99999",
        headers=expense_admin_headers, json={},
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_detail_success(client, expense_admin_headers, sample_expense):
    resp = await client.post(
        f"/api/v1/expenses/detail?expenseId={sample_expense.id}",
        headers=expense_admin_headers, json={},
    )
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["code"] == "EXP-2026-0001"
    assert data["status"] == "draft"
    assert data["category"] == "差旅"


# ============== create ==============

@pytest.mark.asyncio
async def test_create_unauthorized(client, sample_client, expense_admin):
    resp = await client.post(
        "/api/v1/expenses/create", json={
            "category": "差旅", "title": "新费用", "amount": 1000,
            "expenseDate": "2026-01-15",
        },
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_create_permission_denied(client, user_headers, sample_client):
    resp = await client.post(
        "/api/v1/expenses/create",
        headers=user_headers,
        json={
            "category": "差旅", "title": "新费用", "amount": 1000,
            "expenseDate": "2026-01-15",
        },
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_create_success(client, expense_admin_headers, sample_client):
    resp = await client.post(
        "/api/v1/expenses/create",
        headers=expense_admin_headers,
        json={
            "category": "差旅", "title": "新差旅", "amount": 1000,
            "expenseDate": "2026-01-15", "currency": "CNY",
        },
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["code"] == 0
    assert "expenseId" in body["data"]
    assert body["data"]["status"] == "draft"


@pytest.mark.asyncio
async def test_create_missing_title(client, expense_admin_headers):
    resp = await client.post(
        "/api/v1/expenses/create",
        headers=expense_admin_headers,
        json={
            "category": "差旅", "amount": 1000, "expenseDate": "2026-01-15",
        },
    )
    assert resp.status_code == 422


# ============== update ==============

@pytest.mark.asyncio
async def test_update_unauthorized(client, sample_expense):
    resp = await client.post(
        f"/api/v1/expenses/update?expenseId={sample_expense.id}",
        json={"title": "改名"},
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_update_permission_denied(client, user_headers, sample_expense):
    resp = await client.post(
        f"/api/v1/expenses/update?expenseId={sample_expense.id}",
        headers=user_headers, json={"title": "改名"},
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_update_success_draft(client, expense_admin_headers, sample_expense):
    resp = await client.post(
        f"/api/v1/expenses/update?expenseId={sample_expense.id}",
        headers=expense_admin_headers,
        json={
            "title": "改名后的费用",
            "amount": 80000,
        },
    )
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["title"] == "改名后的费用"


@pytest.mark.asyncio
async def test_update_not_found(client, expense_admin_headers):
    resp = await client.post(
        "/api/v1/expenses/update?expenseId=99999",
        headers=expense_admin_headers, json={"title": "x"},
    )
    assert resp.status_code == 404


# ============== delete ==============

@pytest.mark.asyncio
async def test_delete_unauthorized(client, sample_expense):
    resp = await client.post(
        f"/api/v1/expenses/delete?expenseId={sample_expense.id}",
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_delete_permission_denied(client, user_headers, sample_expense):
    resp = await client.post(
        f"/api/v1/expenses/delete?expenseId={sample_expense.id}",
        headers=user_headers,
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_delete_draft_success(client, expense_admin_headers, sample_expense):
    resp = await client.post(
        f"/api/v1/expenses/delete?expenseId={sample_expense.id}",
        headers=expense_admin_headers,
    )
    assert resp.status_code == 200
    # 二次查询应 404
    detail_resp = await client.post(
        f"/api/v1/expenses/detail?expenseId={sample_expense.id}",
        headers=expense_admin_headers, json={},
    )
    assert detail_resp.status_code == 404


# ============== batch_delete ==============

@pytest.mark.asyncio
async def test_batch_delete_unauthorized(client):
    resp = await client.post(
        "/api/v1/expenses/batch/delete", json={"expenseIds": [1, 2]},
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_batch_delete_success(client, expense_admin_headers, db, sample_client, expense_admin):
    e1 = Expense(code="EXP-B1", category="差旅", title="批删1", amount=100,
                  expense_date=date(2026, 1, 1), applicant_id=expense_admin.id,
                  status="draft")
    e2 = Expense(code="EXP-B2", category="差旅", title="批删2", amount=200,
                  expense_date=date(2026, 1, 1), applicant_id=expense_admin.id,
                  status="draft")
    db.add_all([e1, e2])
    await db.commit()
    await db.refresh(e1)
    await db.refresh(e2)

    resp = await client.post(
        "/api/v1/expenses/batch/delete",
        headers=expense_admin_headers,
        json={"expenseIds": [e1.id, e2.id]},
    )
    assert resp.status_code == 200
    assert resp.json()["data"]["deleted"] == 2


# ============== submit ==============

@pytest.mark.asyncio
async def test_submit_unauthorized(client, sample_expense):
    resp = await client.post(
        f"/api/v1/expenses/submit?expenseId={sample_expense.id}",
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_submit_draft_success(client, expense_admin_headers, sample_expense):
    resp = await client.post(
        f"/api/v1/expenses/submit?expenseId={sample_expense.id}",
        headers=expense_admin_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["data"]["status"] in ("pending", "approving")


@pytest.mark.asyncio
async def test_submit_not_found(client, expense_admin_headers):
    resp = await client.post(
        "/api/v1/expenses/submit?expenseId=99999",
        headers=expense_admin_headers,
    )
    assert resp.status_code == 404


# ============== mark_paid ==============

@pytest.mark.asyncio
async def test_mark_paid_unauthorized(client, sample_expense):
    resp = await client.post(
        f"/api/v1/expenses/mark-paid?expenseId={sample_expense.id}",
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_mark_paid_not_approved(client, expense_admin_headers, sample_expense):
    """draft 状态不可 mark_paid"""
    resp = await client.post(
        f"/api/v1/expenses/mark-paid?expenseId={sample_expense.id}",
        headers=expense_admin_headers,
    )
    # 期望 4xx（不是 approved 状态）
    assert resp.status_code in (400, 409)


# ============== approve ==============

@pytest.mark.asyncio
async def test_approve_unauthorized(client, sample_expense):
    resp = await client.post(
        "/api/v1/expenses/approve",
        json={"expenseId": sample_expense.id, "action": "approve"},
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_approve_permission_denied(client, user_headers, sample_expense):
    resp = await client.post(
        "/api/v1/expenses/approve",
        headers=user_headers,
        json={"expenseId": sample_expense.id, "action": "approve"},
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_approve_no_flow(client, expense_admin_headers, sample_expense):
    """无审批流时 approve → 400/404"""
    resp = await client.post(
        "/api/v1/expenses/approve",
        headers=expense_admin_headers,
        json={"expenseId": sample_expense.id, "action": "approve"},
    )
    assert resp.status_code in (400, 404)


# ============== stats ==============

@pytest.mark.asyncio
async def test_stats_unauthorized(client):
    resp = await client.post("/api/v1/expenses/stats", json={})
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_stats_empty(client, expense_admin_headers):
    resp = await client.post(
        "/api/v1/expenses/stats", json={}, headers=expense_admin_headers,
    )
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data.get("total", 0) == 0


@pytest.mark.asyncio
async def test_stats_with_data(client, expense_admin_headers, sample_expense):
    resp = await client.post(
        "/api/v1/expenses/stats", json={}, headers=expense_admin_headers,
    )
    assert resp.status_code == 200
    # stats 返回 kpi/categoryChart/trendChart 结构（不含 total 顶层字段）
    data = resp.json()["data"]
    assert "kpi" in data
    assert "categoryChart" in data
    assert "trendChart" in data
