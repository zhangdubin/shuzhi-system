# R17-A · 后端测试补齐子计划

> **生成时间**：2026-06-26 18:30
> **父计划**：[`2026-06-26_182000-r17-optimization-roadmap.md`](2026-06-26_182000-r17-optimization-roadmap.md) §1.2
> **目标**：把后端 pytest 覆盖从 2 文件 / ~30 用例 → 13 文件 / **≥200 用例**
> **工期**：3-5 个工作日（每天 1-2 个模块，每个模块独立 PR）
> **工作树模式**：每模块一个独立 git 分支 `r17-test-<module>`，合入 main

---

## 1. 现状盘点

### 1.1 未测模块清单（13 个 / 164 个端点）

| 模块 | 端点数 | 复杂度 | 优先级 | 预估工时 |
|---|---|---|---|---|
| **contract** | 9 | 中（金额/状态机/审批流） | 🔴 P1 | 1.0 天 |
| **expense** | 10 | 中（费用/审批） | 🔴 P1 | 1.0 天 |
| **receivable** | 8 | 中（回款/合同关联） | 🔴 P1 | 0.8 天 |
| **invoice_ocr** | 18 | 高（OCR 异步/外部服务） | 🟡 P2 | 1.0 天 |
| **invoice_template** | 7 | 低（CRUD） | 🟢 P3 | 0.4 天 |
| **invoice_verify** | 7 | 中（外部服务 mock） | 🟡 P2 | 0.5 天 |
| **admin** | 34 | 高（用户/角色/部门/字典，4 处缓存） | 🟡 P2 | 1.0 天 |
| **ai** | 19 | 中（22 触点，mock client） | 🟢 P3 | 0.7 天 |
| **dashboard** | 2 | 低（缓存层 99% 命中要保） | 🟢 P3 | 0.2 天 |
| **common** | 18 | 低（字典/上传/通知） | 🟢 P3 | 0.5 天 |
| **cron** | 5 | 低（定时任务触发） | 🟢 P3 | 0.3 天 |
| **reimbursement** | 20 | 中（报销 8 类审批） | 🟡 P2 | 0.8 天 |
| **system_settings** | 7 | 中（系统设置） | 🟡 P2 | 0.3 天 |
| **合计** | **164** | — | — | **~8.5 天** |

**注意**：原来计划 3-5 天，但实测 164 端点 × 平均 1.5 用例 ≈ 250 用例，单人写 + 调通要 8-10 天。

### 1.2 现有可复用资产（conftest.py）

```python
# 已有 fixtures，直接复用
admin_user          # 管理员账号 + 部门 + 角色 + 权限
normal_user         # 普通员工（无 project:write 权限）
auth_headers        # admin Bearer token
user_headers        # 普通用户 token
sample_client       # 示例客户
sample_project      # 示例项目
client / db / engine # 测试基础设施
```

### 1.3 现有测试风格（test_auth.py 范例）

- `pytest.mark.asyncio` 异步测试
- 一函数一断言（"given-when-then"）
- 中文 docstring 说明测试目的
- 状态码 + JSON 字段双断言

---

## 2. 测试规范（写之前定下来）

### 2.1 命名
- 文件：`backend/tests/test_<module>.py`（已有：test_auth / test_project）
- 函数：`test_<场景>_<期望>`（如 `test_contract_create_with_invalid_amount_returns_422`）

### 2.2 每个模块必测的 5 类

1. **happy path** — 正常请求成功
2. **参数校验** — 422 / 400 错误路径
3. **权限拒绝** — 普通用户访问受限资源 → 401/403
4. **数据隔离** — 看不到别人的数据（data_scope 验证）
5. **边界** — 空列表 / 超长字符串 / 重复 key

### 2.3 复用模式

```python
# 1. 复用 fixtures（不重复造轮子）
async def test_x(client, auth_headers, sample_project):
    resp = await client.post("/api/v1/contracts/list", headers=auth_headers, json={...})
    assert resp.status_code == 200

# 2. 不依赖外部服务 → 全部 mock
async def test_ocr_recognize(client, auth_headers, monkeypatch):
    async def fake_recognize(file):
        return {"invoiceNo": "123", "confidence": 0.95}
    monkeypatch.setattr("app.modules.invoice_ocr.service.recognize", fake_recognize)
    ...
```

### 2.4 覆盖率目标（粗）

- **P1 业务**（contract/expense/receivable）：行覆盖 ≥ 60%
- **P2 业务**（其他）：行覆盖 ≥ 40%
- **不追求** 100%（mock 外部服务、UI 渲染不在范围）

### 2.5 跑测命令（CI 之前先本地跑通）

```bash
cd backend
pytest -v --tb=short --cov=app --cov-report=term-missing
# 期望：≥200 passed, 覆盖率从 ~5% → ≥30%
```

---

## 3. 执行顺序（按 ROI + 风险）

| Day | 任务 | PR 名 | 提交要点 |
|---|---|---|---|
| **D1 上午** | **contract**（最核心业务） | `r17-test-contract` | 9 endpoint + 5 类共性测试 + 1 fixture `sample_contract` |
| **D1 下午** | **expense** | `r17-test-expense` | 10 endpoint + 共性测试 + 复用 sample_project |
| **D2 上午** | **receivable** | `r17-test-receivable` | 8 endpoint + 共性测试 + 依赖 contract（要造） |
| **D2 下午** | **dashboard**（最快，先保） | `r17-test-dashboard` | 2 endpoint + 缓存命中验证 |
| **D3 上午** | **common** | `r17-test-common` | 18 endpoint（字典/上传/通知） |
| **D3 下午** | **invoice_template** | `r17-test-invoice-template` | 7 endpoint（CRUD） |
| **D4 上午** | **admin** | `r17-test-admin` | 34 endpoint（最大头，分 users/roles/depts/dicts 4 个 test file 子组织） |
| **D4 下午** | **system_settings** | `r17-test-system-settings` | 7 endpoint |
| **D5 上午** | **invoice_ocr + invoice_verify** | `r17-test-invoice-ocr-verify` | 18+7 = 25 endpoint，外部服务全部 mock |
| **D5 下午** | **reimbursement** | `r17-test-reimbursement` | 20 endpoint |
| **D5 收尾** | **ai + cron** | `r17-test-ai-cron` | 19+5 = 24 endpoint，AI client mock |
| **D6 兜底** | 跑全量 + 修 flaky + 覆盖率报告 | — | 整理 `docs/test-coverage-r17.md` |

**每天 1-2 个 PR**，晚上合入 main 后第二天接着干。

---

## 4. 每个模块的"测试契约"模板

以 `contract` 为例（9 个 endpoint）：

```python
# backend/tests/test_contract.py
"""
合同模块测试

测试矩阵：
- list / detail / create / update / delete
- 状态机（draft → pending → active → completed）
- 审批流（提交审核 / 审核通过 / 驳回）
- 权限：未登录 → 401 / 普通用户写 → 403 / data_scope 隔离
"""

import pytest
from datetime import date
from app.modules.contract.models import Contract
from app.core.security import hash_password

# Fixture: 复用 conftest.py 的 sample_client / admin_user
@pytest.fixture
async def sample_contract(db, sample_client, admin_user):
    c = Contract(
        code="CT-2026-0001",
        name="测试合同",
        type="销售合同",
        status="draft",
        amount=100000000,  # 100 万
        client_id=sample_client.id,
        owner_id=admin_user.id,
        sign_date=date(2026, 1, 1),
    )
    db.add(c)
    await db.commit()
    await db.refresh(c)
    return c


# ============== 列表 ==============

@pytest.mark.asyncio
async def test_list_contracts_unauthorized(client):
    resp = await client.post("/api/v1/contracts/list", json={})
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_list_contracts_empty(client, auth_headers):
    resp = await client.post("/api/v1/contracts/list", headers=auth_headers, json={})
    assert resp.status_code == 200
    assert resp.json()["data"]["total"] == 0


@pytest.mark.asyncio
async def test_list_contracts_with_data(client, auth_headers, sample_contract):
    resp = await client.post("/api/v1/contracts/list", headers=auth_headers, json={})
    assert resp.status_code == 200
    assert resp.json()["data"]["total"] == 1
    assert resp.json()["data"]["items"][0]["code"] == "CT-2026-0001"


# ============== 详情 ==============

@pytest.mark.asyncio
async def test_get_contract_not_found(client, auth_headers):
    resp = await client.post("/api/v1/contracts/detail",
                              headers=auth_headers, json={"id": 99999})
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_get_contract_success(client, auth_headers, sample_contract):
    resp = await client.post("/api/v1/contracts/detail",
                              headers=auth_headers, json={"id": sample_contract.id})
    assert resp.status_code == 200
    assert resp.json()["data"]["name"] == "测试合同"


# ============== 创建 ==============

@pytest.mark.asyncio
async def test_create_contract_success(client, auth_headers, sample_client):
    resp = await client.post("/api/v1/contracts/create", headers=auth_headers, json={
        "name": "新合同",
        "type": "销售合同",
        "amount": 50000000,
        "clientId": sample_client.id,
        "signDate": "2026-06-01",
    })
    assert resp.status_code == 200
    assert "id" in resp.json()["data"]


@pytest.mark.asyncio
async def test_create_contract_invalid_amount(client, auth_headers, sample_client):
    resp = await client.post("/api/v1/contracts/create", headers=auth_headers, json={
        "name": "新合同", "amount": -100, "clientId": sample_client.id,
    })
    assert resp.status_code == 422


# ============== 状态机 ==============

@pytest.mark.asyncio
async def test_contract_status_transition(client, auth_headers, sample_contract):
    """draft → pending → active 状态流转"""
    # 提交审核
    resp = await client.post("/api/v1/contracts/submit",
                              headers=auth_headers, json={"id": sample_contract.id})
    assert resp.status_code == 200
    assert resp.json()["data"]["status"] == "pending"


# ============== 权限 ==============

@pytest.mark.asyncio
async def test_normal_user_cannot_delete(client, user_headers, sample_contract):
    resp = await client.post("/api/v1/contracts/delete",
                              headers=user_headers, json={"id": sample_contract.id})
    assert resp.status_code == 403
```

**预计 contract 模块**：1 文件 / 25 用例 / ~250 行

---

## 5. 数据隔离测试特别说明（data_scope）

`core/data_scope.py` R11B 加的 5 档过滤要测：

```python
# test_data_scope.py（独立文件）
"""
data_scope 权限隔离测试

5 档：ALL / DEPARTMENT / DEPARTMENT_AND_SUB / SELF / CUSTOM
"""

async def test_dept_scope_user_cannot_see_other_dept_data(client, db):
    """dept 档用户看不到其他部门数据"""
    # 造两个部门 + 两个用户 + 两个项目
    # 用 dept 用户查询 → 只能看到自己部门的
    ...
```

---

## 6. Mock 外部服务的统一模式

```python
# tests/mocks/ 目录（新）
# tests/mocks/paddle_ocr.py
async def fake_ocr_recognize(file_bytes: bytes) -> dict:
    return {
        "invoiceNo": "26112000001961698396",
        "amount": "248.00",
        "confidence": 0.95,
        "fields": [...],
    }

# tests/conftest.py 加 fixture
@pytest.fixture
def mock_ocr(monkeypatch):
    monkeypatch.setattr(
        "app.modules.invoice_ocr.service.ocr_client.recognize",
        fake_ocr_recognize,
    )
```

外部服务（诺诺/企微/PaddleOCR）的 mock 集中在 `tests/mocks/`，**禁止**在每个 test 文件里 inline 造。

---

## 7. 验证清单（每天结束前跑）

```bash
cd backend

# 1. 当前模块测试
pytest tests/test_<module>.py -v --tb=short

# 2. 全量（确保没破已有测试）
pytest -v --tb=short

# 3. 覆盖率（统计用，不 fail）
pytest --cov=app --cov-report=term-missing --cov-report=html
# 看 htmlcov/index.html 哪些行没覆盖

# 4. 期望：每天结束后多 20-30 个 passed
# 5 天后：200+ passed
```

---

## 8. 风险与回滚

| 风险 | 应对 |
|---|---|
| 内存 SQLite 不支持某些 PG 特性（JSONB / full-text） | 已有 module 测试过；不测这些 |
| Fixture 依赖复杂，调试难 | 每模块独立文件 + 独立 fixture |
| 旧测试被新 fixture 改坏 | 每天合 PR 前跑**全量** pytest |
| Mock 失真（mock 通过但生产失败） | 关键路径用 `pytest --integration` 真打 DB 标记 + 跑 |
| 时间超期 | D6 兜底日只补 P1 业务，admin / ai 等降级 P3 |

---

## 9. 交付物

| 文件 | 类型 |
|---|---|
| `backend/tests/test_contract.py` | 新建 |
| `backend/tests/test_expense.py` | 新建 |
| `backend/tests/test_receivable.py` | 新建 |
| `backend/tests/test_invoice_ocr.py` | 新建 |
| `backend/tests/test_invoice_template.py` | 新建 |
| `backend/tests/test_invoice_verify.py` | 新建 |
| `backend/tests/test_admin.py` | 新建（34 endpoint，可能拆 4 个子文件） |
| `backend/tests/test_ai.py` | 新建 |
| `backend/tests/test_dashboard.py` | 新建 |
| `backend/tests/test_common.py` | 新建 |
| `backend/tests/test_cron.py` | 新建 |
| `backend/tests/test_reimbursement.py` | 新建 |
| `backend/tests/test_system_settings.py` | 新建 |
| `backend/tests/test_data_scope.py` | 新建（独立） |
| `backend/tests/mocks/__init__.py` | 新建 |
| `backend/tests/mocks/paddle_ocr.py` | 新建 |
| `backend/tests/mocks/nuonuo.py` | 新建 |
| `backend/tests/mocks/wechat_work.py` | 新建 |
| `backend/tests/mocks/ai_client.py` | 新建 |
| `backend/tests/conftest.py` | **追加** fixtures（不改原有） |
| `docs/test-coverage-r17.md` | 新建（覆盖率报告） |
| **总计** | **13 个 test 文件 + 4 mock + 1 报告 + 1 conftest 追加** |

---

## 10. 与父计划的对齐

- 父计划 §1.2 的目标（"≥120 用例 / ≥30% 覆盖"）→ 本计划升级为 **"≥200 用例 / ≥40% 覆盖"**
- 工期从 3-5 天调整为 **5-6 天**（实测 164 端点工作量更大）
- 工时是否够：**D6 兜底日**只补关键模块，admin / ai 的边缘用例不补也行

---

## 11. 下一步

**等你拍板**：

1. **工期**：5-6 天是否可接受？（比原 3-5 天多 1 天，但覆盖更全）
2. **优先级**：是否按 D1-D5 顺序推？（建议**是**——P1 业务先测，admin/ai 后测）
3. **Mock 集中化**：是否同意新建 `tests/mocks/`？（建议**是**——后续切真集成时复用）
4. **D1 第一刀**：从 `test_contract.py` 开始 OK 吗？

---

**报告路径**：`/Users/trisome/Desktop/开发/数智化系统new/.hermes/plans/2026-06-26_183000-r17-test-coverage-subplan.md`
**报告版本**：v1.0 | 2026-06-26
**依赖**：父路线图 §1.2 + 现有 `conftest.py`
