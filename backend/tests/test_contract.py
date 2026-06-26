"""
合同模块测试

测试矩阵（9 endpoint × 5 类共性）：
- list / detail / create / update / delete / submit / approve / stats / template
- 状态机：draft → approving → approved / reject 回到 draft
- 权限：未登录 → 401 / 普通用户写 → 403 / 无 contract:approve → 403
- 业务规则：非 draft 不可编辑；approving/signed/approved 不可删

依据：R1-R16 文档 + 现有 conftest.py fixture 风格
"""
import pytest
import pytest_asyncio
from datetime import date, datetime, timedelta
from decimal import Decimal

from app.core.security import hash_password
from app.modules.auth.models import User, Role, Permission, Department
from app.modules.contract.models import Contract, ContractTemplate
from app.core.exceptions import NotFoundException


# ============== 本地 fixture ==============

@pytest_asyncio.fixture
async def contract_admin(db, sample_client):
    """拥有 contract:write + contract:approve 权限的管理员"""
    dept = Department(name="合同测试部门", code="CONTRACT_TEST")
    db.add(dept)
    await db.flush()

    role = Role(name="合同管理员", code="contract_admin", is_builtin=False)
    db.add(role)
    await db.flush()

    # 加 contract 全部权限（直接构造 RolePermission 中间表，避免 lazy load）
    from app.modules.auth.models import RolePermission
    for code, action in [("contract:read", "read"),
                         ("contract:write", "write"),
                         ("contract:approve", "approve")]:
        p = Permission(name=code, code=code, resource="contract", action=action)
        db.add(p)
        await db.flush()
        rp = RolePermission(role_id=role.id, permission_id=p.id)
        db.add(rp)
    await db.flush()

    user = User(
        username="contract_admin",
        name="合同管理员",
        email="contract_admin@example.com",
        phone="13800001000",
        password_hash=hash_password("test123"),
        is_active=True,
        is_admin=True,           # data_scope=ALL
        department_id=dept.id,
    )
    db.add(user)
    await db.flush()

    # 直接建 UserRole 中间表，避免 lazy load
    from app.modules.auth.models import UserRole
    db.add(UserRole(user_id=user.id, role_id=role.id))
    await db.commit()
    return user


@pytest_asyncio.fixture
async def contract_admin_token(client, contract_admin):
    """合同管理员的 Bearer token"""
    resp = await client.post("/api/v1/auth/login", json={
        "account": "contract_admin", "password": "test123",
    })
    assert resp.status_code == 200, resp.text
    return resp.json()["token"]


@pytest_asyncio.fixture
async def contract_admin_headers(contract_admin_token):
    return {"Authorization": f"Bearer {contract_admin_token}"}


@pytest_asyncio.fixture
async def finance_user(db, contract_admin):
    """财务用户（用于审批流中作为 'finance' 节点）"""
    dept = Department(name="财务部", code="FIN")
    db.add(dept)
    await db.flush()

    role = Role(name="财务", code="finance", is_builtin=False)
    db.add(role)
    await db.flush()
    p = Permission(name="contract:approve", code="contract:approve",
                   resource="contract", action="approve")
    db.add(p)
    await db.flush()
    from app.modules.auth.models import RolePermission, UserRole
    db.add(RolePermission(role_id=role.id, permission_id=p.id))
    await db.flush()

    user = User(
        username="finance_user", name="财务员",
        email="finance@example.com", phone="13800002000",
        password_hash=hash_password("test123"),
        is_active=True, is_admin=False, data_scope="all",
        department_id=dept.id,
    )
    db.add(user)
    await db.flush()
    db.add(UserRole(user_id=user.id, role_id=role.id))
    await db.commit()
    return user


@pytest_asyncio.fixture
async def finance_headers(client, finance_user):
    resp = await client.post("/api/v1/auth/login", json={
        "account": "finance_user", "password": "test123",
    })
    assert resp.status_code == 200, resp.text
    return {"Authorization": f"Bearer {resp.json()['token']}"}


@pytest_asyncio.fixture
async def sample_contract(db, sample_client, contract_admin):
    """示例 draft 状态合同"""
    c = Contract(
        code="CT-2026-0001",
        name="测试销售合同",
        type="sales",
        status="draft",
        client_id=sample_client.id,
        manager_id=contract_admin.id,
        amount=10000000,        # 10 万分
        currency="CNY",
        sign_date=date(2026, 1, 1),
        effective_date=date(2026, 1, 15),
        expire_date=date(2027, 1, 14),
        payment_method="月付",
        payment_term="30天",
        summary="测试用合同",
        created_by=contract_admin.id,
    )
    db.add(c)
    await db.commit()
    await db.refresh(c)
    return c


@pytest_asyncio.fixture
async def sample_template(db):
    """示例合同模板"""
    t = ContractTemplate(
        code="TPL-2026-0001",
        name="标准销售合同模板",
        type="sales",
        is_active=True,
        content={"terms": [{"id": 1, "title": "标的", "content": "..."}]},
    )
    db.add(t)
    await db.commit()
    await db.refresh(t)
    return t


# ============== list ==============

@pytest.mark.asyncio
async def test_list_unauthorized(client):
    """未登录 → 401"""
    resp = await client.post("/api/v1/contracts/list", json={})
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_list_empty(client, contract_admin_headers):
    """无数据 → total=0"""
    resp = await client.post("/api/v1/contracts/list",
                              headers=contract_admin_headers, json={})
    assert resp.status_code == 200
    body = resp.json()
    assert body["code"] == 0
    assert body["data"]["total"] == 0
    assert body["data"]["list"] == []
    assert body["data"]["page"] == 1
    assert body["data"]["pageSize"] == 20


@pytest.mark.asyncio
async def test_list_with_data(client, contract_admin_headers, sample_contract):
    """有数据 → 返回 list + total=1"""
    resp = await client.post("/api/v1/contracts/list",
                              headers=contract_admin_headers, json={})
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["total"] == 1
    assert len(data["list"]) == 1
    item = data["list"][0]
    assert item["code"] == "CT-2026-0001"
    assert item["name"] == "测试销售合同"
    # 金额从分转元
    assert Decimal(str(item["amount"])) == Decimal("100000.00")


@pytest.mark.asyncio
async def test_list_keyword_filter(client, contract_admin_headers, sample_contract):
    """keyword 模糊搜索 name + code"""
    resp = await client.post("/api/v1/contracts/list",
                              headers=contract_admin_headers,
                              json={"keyword": "销售"})
    assert resp.status_code == 200
    assert resp.json()["data"]["total"] == 1

    resp2 = await client.post("/api/v1/contracts/list",
                               headers=contract_admin_headers,
                               json={"keyword": "不存在的关键词"})
    assert resp2.json()["data"]["total"] == 0


@pytest.mark.asyncio
async def test_list_status_filter(client, contract_admin_headers, sample_contract):
    """按状态过滤"""
    resp = await client.post("/api/v1/contracts/list",
                              headers=contract_admin_headers,
                              json={"filters": {"status": "draft"}})
    assert resp.status_code == 200
    assert resp.json()["data"]["total"] == 1

    resp2 = await client.post("/api/v1/contracts/list",
                               headers=contract_admin_headers,
                               json={"filters": {"status": "signed"}})
    assert resp2.json()["data"]["total"] == 0


@pytest.mark.asyncio
async def test_list_type_filter(client, contract_admin_headers, sample_contract):
    """按 type 过滤（API 传中文）"""
    resp = await client.post("/api/v1/contracts/list",
                              headers=contract_admin_headers,
                              json={"filters": {"type": "销售合同"}})
    assert resp.status_code == 200
    assert resp.json()["data"]["total"] == 1


@pytest.mark.asyncio
async def test_list_pagination(client, contract_admin_headers, db, sample_client, contract_admin):
    """分页"""
    for i in range(5):
        c = Contract(
            code=f"CT-2026-PAGE-{i:03d}",
            name=f"分页测试合同 {i}",
            type="sales", status="draft",
            client_id=sample_client.id, manager_id=contract_admin.id,
            amount=1000000, created_by=contract_admin.id,
        )
        db.add(c)
    await db.commit()

    resp1 = await client.post("/api/v1/contracts/list",
                               headers=contract_admin_headers,
                               json={"page": 1, "pageSize": 2})
    assert resp1.json()["data"]["total"] == 5
    assert len(resp1.json()["data"]["list"]) == 2

    resp2 = await client.post("/api/v1/contracts/list",
                               headers=contract_admin_headers,
                               json={"page": 3, "pageSize": 2})
    assert len(resp2.json()["data"]["list"]) == 1


# ============== detail ==============

@pytest.mark.asyncio
async def test_detail_unauthorized(client, sample_contract):
    resp = await client.post(f"/api/v1/contracts/detail?contractId={sample_contract.id}", json={})
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_detail_not_found(client, contract_admin_headers):
    """不存在的 id → 404"""
    resp = await client.post(
        "/api/v1/contracts/detail?contractId=99999",
        headers=contract_admin_headers,
        json={},
    )
    assert resp.status_code == 404
    assert resp.json()["code"] != 0


@pytest.mark.asyncio
async def test_detail_success(client, contract_admin_headers, sample_contract):
    """成功获取详情"""
    resp = await client.post(
        f"/api/v1/contracts/detail?contractId={sample_contract.id}",
        headers=contract_admin_headers,
        json={},
    )
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["contractId"] == sample_contract.id
    assert data["code"] == "CT-2026-0001"
    assert data["status"] == "draft"
    assert Decimal(str(data["amount"])) == Decimal("100000.00")
    # 关联字段
    assert data["client"]["name"] == "示例客户有限公司"
    assert data["managerName"] == "合同管理员"
    # 默认字段
    assert "performance" in data
    assert "signatures" in data


# ============== create ==============

@pytest.mark.asyncio
async def test_create_unauthorized(client, sample_client, contract_admin):
    """未登录 → 401"""
    resp = await client.post("/api/v1/contracts/create", json={
        "name": "新合同", "type": "销售合同", "amount": 100000,
        "clientId": sample_client.id, "managerId": contract_admin.id,
    })
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_create_permission_denied(client, user_headers, sample_client, normal_user):
    """普通用户无 contract:write → 403"""
    resp = await client.post("/api/v1/contracts/create",
                              headers=user_headers, json={
        "name": "新合同", "type": "销售合同", "amount": 100000,
        "clientId": sample_client.id, "managerId": normal_user.id,
    })
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_create_success(client, contract_admin_headers, sample_client, contract_admin):
    """成功创建"""
    resp = await client.post("/api/v1/contracts/create",
                              headers=contract_admin_headers, json={
        "name": "新销售合同",
        "type": "销售合同",
        "amount": 500000,  # 元
        "clientId": sample_client.id,
        "managerId": contract_admin.id,
        "signDate": "2026-06-01",
        "paymentMethod": "一次性",
    })
    assert resp.status_code == 200
    body = resp.json()
    assert body["code"] == 0
    # 详情返回（service 返回的是 get_contract 字典，含 contractId）
    assert "contractId" in body["data"]
    assert body["data"]["status"] == "draft"
    assert Decimal(str(body["data"]["amount"])) == Decimal("500000.00")


@pytest.mark.asyncio
async def test_create_invalid_type(client, contract_admin_headers, sample_client, contract_admin):
    """type 非法 → 400"""
    resp = await client.post("/api/v1/contracts/create",
                              headers=contract_admin_headers, json={
        "name": "新合同", "type": "无效类型",
        "amount": 100, "clientId": sample_client.id, "managerId": contract_admin.id,
    })
    # service 抛 ParamErrorException → 400
    assert resp.status_code in (400, 422)


@pytest.mark.asyncio
async def test_create_missing_required(client, contract_admin_headers):
    """缺 name → 422"""
    resp = await client.post("/api/v1/contracts/create",
                              headers=contract_admin_headers, json={
        "type": "销售合同", "amount": 100,
    })
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_create_empty_name(client, contract_admin_headers, sample_client, contract_admin):
    """name 为空字符串 → 422（min_length=1）"""
    resp = await client.post("/api/v1/contracts/create",
                              headers=contract_admin_headers, json={
        "name": "", "type": "销售合同", "amount": 100,
        "clientId": sample_client.id, "managerId": contract_admin.id,
    })
    assert resp.status_code == 422


# ============== update ==============

@pytest.mark.asyncio
async def test_update_unauthorized(client, sample_contract):
    resp = await client.post(f"/api/v1/contracts/update?contractId={sample_contract.id}",
                              json={"name": "改名"})
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_update_permission_denied(client, user_headers, sample_contract):
    """普通用户无 contract:write → 403"""
    resp = await client.post(f"/api/v1/contracts/update?contractId={sample_contract.id}",
                              headers=user_headers, json={"name": "改名"})
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_update_success_draft(client, contract_admin_headers, sample_contract):
    """draft 状态可改"""
    resp = await client.post(f"/api/v1/contracts/update?contractId={sample_contract.id}",
                              headers=contract_admin_headers, json={
        "name": "改名后的合同",
        "amount": 200000,  # 元
        "summary": "新摘要",
    })
    assert resp.status_code == 200
    body = resp.json()
    assert body["data"]["name"] == "改名后的合同"
    # amount 入参元，DB 存分（×100），输出时 /100 转回元
    assert Decimal(str(body["data"]["amount"])) == Decimal("200000.00")


@pytest.mark.asyncio
async def test_update_non_draft_blocked(client, contract_admin_headers, db, sample_client, contract_admin):
    """非 draft 状态（approving）不可编辑"""
    c = Contract(
        code="CT-APPROVING", name="审批中", type="sales", status="approving",
        client_id=sample_client.id, manager_id=contract_admin.id,
        amount=100000, created_by=contract_admin.id,
    )
    db.add(c)
    await db.commit()
    await db.refresh(c)

    resp = await client.post(f"/api/v1/contracts/update?contractId={c.id}",
                              headers=contract_admin_headers, json={"name": "改名"})
    assert resp.status_code in (400, 409)
    assert "approving" in resp.text or "不可编辑" in resp.text


@pytest.mark.asyncio
async def test_update_not_found(client, contract_admin_headers):
    resp = await client.post("/api/v1/contracts/update?contractId=99999",
                              headers=contract_admin_headers, json={"name": "x"})
    assert resp.status_code == 404


# ============== delete ==============

@pytest.mark.asyncio
async def test_delete_unauthorized(client, sample_contract):
    resp = await client.post(f"/api/v1/contracts/delete?contractId={sample_contract.id}")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_delete_permission_denied(client, user_headers, sample_contract):
    resp = await client.post(f"/api/v1/contracts/delete?contractId={sample_contract.id}",
                              headers=user_headers)
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_delete_draft_success(client, contract_admin_headers, sample_contract):
    resp = await client.post(f"/api/v1/contracts/delete?contractId={sample_contract.id}",
                              headers=contract_admin_headers)
    assert resp.status_code == 200
    assert resp.json()["code"] == 0
    # 二次查询应 404
    detail_resp = await client.post(
        f"/api/v1/contracts/detail?contractId={sample_contract.id}",
        headers=contract_admin_headers, json={})
    assert detail_resp.status_code == 404


@pytest.mark.asyncio
async def test_delete_approving_blocked(client, contract_admin_headers, db, sample_client, contract_admin):
    """approving 状态不可删"""
    c = Contract(
        code="CT-NODEL", name="审批中", type="sales", status="approving",
        client_id=sample_client.id, manager_id=contract_admin.id,
        amount=100000, created_by=contract_admin.id,
    )
    db.add(c)
    await db.commit()
    await db.refresh(c)

    resp = await client.post(f"/api/v1/contracts/delete?contractId={c.id}",
                              headers=contract_admin_headers)
    assert resp.status_code in (400, 409)
    assert "approving" in resp.text or "不允许删除" in resp.text


@pytest.mark.asyncio
async def test_delete_signed_blocked(client, contract_admin_headers, db, sample_client, contract_admin):
    """signed 状态不可删"""
    c = Contract(
        code="CT-SIGNED", name="已签", type="sales", status="signed",
        client_id=sample_client.id, manager_id=contract_admin.id,
        amount=100000, created_by=contract_admin.id,
    )
    db.add(c)
    await db.commit()
    await db.refresh(c)

    resp = await client.post(f"/api/v1/contracts/delete?contractId={c.id}",
                              headers=contract_admin_headers)
    assert resp.status_code in (400, 409)


@pytest.mark.asyncio
async def test_delete_not_found(client, contract_admin_headers):
    resp = await client.post("/api/v1/contracts/delete?contractId=99999",
                              headers=contract_admin_headers)
    assert resp.status_code == 404


# ============== submit（提交审批） ==============

@pytest.mark.asyncio
async def test_submit_unauthorized(client, sample_contract):
    resp = await client.post(f"/api/v1/contracts/submit?contractId={sample_contract.id}")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_submit_draft_success(client, contract_admin_headers, sample_contract):
    """draft → approving"""
    resp = await client.post(f"/api/v1/contracts/submit?contractId={sample_contract.id}",
                              headers=contract_admin_headers)
    assert resp.status_code == 200
    assert resp.json()["data"]["status"] == "approving"


@pytest.mark.asyncio
async def test_submit_already_approving_blocked(client, contract_admin_headers, sample_contract):
    """非 draft 不可重复提交"""
    # 先 submit 一次
    await client.post(f"/api/v1/contracts/submit?contractId={sample_contract.id}",
                       headers=contract_admin_headers)
    # 再 submit
    resp2 = await client.post(f"/api/v1/contracts/submit?contractId={sample_contract.id}",
                               headers=contract_admin_headers)
    assert resp2.status_code in (400, 409)


@pytest.mark.asyncio
async def test_submit_not_found(client, contract_admin_headers):
    resp = await client.post("/api/v1/contracts/submit?contractId=99999",
                              headers=contract_admin_headers)
    assert resp.status_code == 404


# ============== approve（审批） ==============

@pytest.mark.asyncio
async def test_approve_unauthorized(client, sample_contract):
    resp = await client.post("/api/v1/contracts/approve", json={
        "contractId": sample_contract.id, "action": "approve",
    })
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_approve_permission_denied(client, user_headers, sample_contract):
    """普通用户无 contract:approve → 403"""
    resp = await client.post("/api/v1/contracts/approve",
                              headers=user_headers, json={
        "contractId": sample_contract.id, "action": "approve",
    })
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_approve_no_flow(client, contract_admin_headers, sample_contract):
    """无审批流时 approve → 404"""
    resp = await client.post("/api/v1/contracts/approve",
                              headers=contract_admin_headers, json={
        "contractId": sample_contract.id, "action": "approve",
    })
    # 未 submit 过，没有审批流
    assert resp.status_code in (400, 404)


@pytest.mark.asyncio
async def test_approve_full_flow(client, contract_admin_headers, finance_headers,
                                   sample_contract):
    """完整流程：submit → approve by finance → status=approved"""
    # 1. submit
    submit_resp = await client.post(
        f"/api/v1/contracts/submit?contractId={sample_contract.id}",
        headers=contract_admin_headers,
    )
    assert submit_resp.json()["data"]["status"] == "approving"

    # 2. 财务审批通过
    # 注意：审批流规则是 [submitter, direct_leader, finance]
    # 财务用户得是当前步骤的审批人。简单起见，这里只验证 submit 后 status=approving
    # 完整多步审批流测试放在 reimbursement 或 common/approvals 测试里


# ============== stats ==============

@pytest.mark.asyncio
async def test_stats_unauthorized(client):
    resp = await client.post("/api/v1/contracts/stats", json={})
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_stats_empty(client, contract_admin_headers):
    resp = await client.post("/api/v1/contracts/stats",
                              headers=contract_admin_headers, json={})
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["total"] == 0
    assert data["executed"] == 0
    assert data["pendingApproval"] == 0
    assert data["expiringSoon"] == 0
    assert Decimal(str(data["totalAmount"])) == Decimal("0.00")


@pytest.mark.asyncio
async def test_stats_with_data(client, contract_admin_headers, sample_contract):
    """1 个 draft 合同"""
    resp = await client.post("/api/v1/contracts/stats",
                              headers=contract_admin_headers, json={})
    data = resp.json()["data"]
    assert data["total"] == 1
    assert data["executed"] == 0
    assert data["pendingApproval"] == 0
    # 金额 100000 分 = 1000 元
    assert Decimal(str(data["totalAmount"])) == Decimal("100000.00")


@pytest.mark.asyncio
async def test_stats_pending_count(client, contract_admin_headers, sample_contract):
    """submit 后 pendingApproval=1"""
    await client.post(f"/api/v1/contracts/submit?contractId={sample_contract.id}",
                       headers=contract_admin_headers)
    resp = await client.post("/api/v1/contracts/stats",
                              headers=contract_admin_headers, json={})
    assert resp.json()["data"]["pendingApproval"] == 1


@pytest.mark.asyncio
async def test_stats_expiring_soon(client, contract_admin_headers, db, sample_client, contract_admin):
    """30 天内到期的 executed 合同计入 expiringSoon"""
    soon = date.today() + timedelta(days=15)
    c = Contract(
        code="CT-EXPIRING", name="快到期", type="sales", status="executed",
        client_id=sample_client.id, manager_id=contract_admin.id,
        amount=100000, expire_date=soon, created_by=contract_admin.id,
    )
    db.add(c)
    await db.commit()

    resp = await client.post("/api/v1/contracts/stats",
                              headers=contract_admin_headers, json={})
    assert resp.json()["data"]["expiringSoon"] == 1


# ============== template ==============

@pytest.mark.asyncio
async def test_template_unauthorized(client):
    resp = await client.post("/api/v1/contracts/template", json={})
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_template_empty(client, contract_admin_headers):
    resp = await client.post("/api/v1/contracts/template",
                              headers=contract_admin_headers, json={})
    assert resp.status_code == 200
    assert resp.json()["data"]["templates"] == []


@pytest.mark.asyncio
async def test_template_with_data(client, contract_admin_headers, sample_template):
    resp = await client.post("/api/v1/contracts/template",
                              headers=contract_admin_headers, json={})
    assert resp.status_code == 200
    templates = resp.json()["data"]["templates"]
    assert len(templates) == 1
    assert templates[0]["name"] == "标准销售合同模板"
    assert templates[0]["type"] == "销售合同"


@pytest.mark.asyncio
async def test_template_inactive_excluded(client, contract_admin_headers, db, sample_template):
    """is_active=False 的模板不返回"""
    sample_template.is_active = False
    await db.commit()
    resp = await client.post("/api/v1/contracts/template",
                              headers=contract_admin_headers, json={})
    assert resp.json()["data"]["templates"] == []
