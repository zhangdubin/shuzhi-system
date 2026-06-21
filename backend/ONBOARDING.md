# 后端工程师进场指引（Onboarding）

> **目标读者**：新加入的后端工程师
> **目标**：1 小时内把项目跑起来，2 小时内改一个接口，1 周内交付第一个完整模块
> **后端栈**：Python 3.11 + FastAPI + PostgreSQL 15 + SQLAlchemy 2.0 + Redis 7

---

## 0. 先看这些文档（30 分钟）

| 文档 | 必读章节 | 时间 |
|------|---------|------|
| `../design/API.md` | 通用规范 §0 + 你要做的模块 | 15 分钟 |
| `../design/BACKEND.md` | §1 技术栈 + §2 项目结构 + §3 你要做的表的 DDL + §6 RBAC | 30 分钟 |
| `../design/ROADMAP.md` | §2 技术视角（看你的任务在哪一周） | 10 分钟 |

**选读**（如果你被分到 AI 模块）：

| 文档 | 必读章节 |
|------|---------|
| `../design/AI-API.md` | §0 设计原则 + §1-4 通用规范（与老 API 相同）+ 你负责的接口 |
| `../design/PaddleOCR-部署指南.md` | 如果做字段抽取 / OCR 集成 |

**不要先看** `app/` 下所有代码！先读文档，理解整体设计再下钻。

---

## 1. 5 分钟把项目跑起来

```bash
# 1. 进入目录
cd backend

# 2. 装 Python 依赖（用虚拟环境）
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 3. 启动数据库（docker 是最快的）
docker run -d --name shuzhi-pg -p 5432:5432 \
  -e POSTGRES_USER=shuzhi -e POSTGRES_PASSWORD=shuzhi -e POSTGRES_DB=shuzhi \
  postgres:15-alpine

docker run -d --name shuzhi-redis -p 6379:6379 redis:7-alpine

# 4. 配置环境变量
cp .env.example .env   # 如果有的话
# 至少改 JWT_SECRET_KEY（32 位随机字符串）
# macOS 生成：openssl rand -hex 32

# 5. 初始化数据库 + 种子数据
alembic upgrade head
python scripts/seed.py

# 6. 启动后端
uvicorn app.main:app --reload --port 8000

# 7. 打开浏览器
# http://localhost:8000/docs    ← Swagger UI（自动生成）
# http://localhost:8000/health  ← 健康检查
```

**预期看到**：
- `/health` 返回 `{"status": "ok", "version": "1.0.0", "env": "development"}`
- `/docs` 显示所有 API
- seed.py 输出"种子数据初始化完成"

**登录测试**：
```bash
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"account": "admin", "password": "admin123"}'
```

应该返回 `token` 和 `userInfo`。

---

## 2. 项目结构

```
backend/
├── app/
│   ├── main.py              ← 入口，看完就知道整个应用怎么起来的
│   ├── config.py            ← 环境变量配置
│   ├── core/                ← 跨模块通用能力
│   │   ├── database.py      ← SQLAlchemy async 引擎 + Base + get_db
│   │   ├── security.py      ← JWT 签发/校验 + 密码 + get_current_user
│   │   ├── exceptions.py    ← 业务异常类 + 异常处理器
│   │   ├── audit.py         ← 审计中间件（自动记录写接口）
│   │   └── sse.py           ← SSE 事件总线（Redis Pub/Sub）
│   ├── modules/             ← 业务模块
│   │   ├── auth/            ← 认证（已完成，作为样板之一）
│   │   └── project/         ← 项目（已完成，作为样板）
│   └── tasks/               ← Celery 任务（占位，后续填）
├── alembic/                 ← 数据库迁移
│   ├── env.py
│   └── versions/
├── scripts/
│   └── seed.py              ← 种子数据
├── tests/                   ← pytest 测试
├── requirements.txt
├── alembic.ini
└── pytest.ini
```

**核心模式（每个模块都按这个结构）**：
```
modules/<name>/
├── models.py      ← SQLAlchemy ORM（对应 DDL）
├── schemas.py     ← Pydantic DTO（对应 API 请求/响应）
├── service.py     ← 业务逻辑（不依赖 HTTP）
├── router.py      ← FastAPI 路由（薄薄一层，调 service）
└── __init__.py
```

---

## 3. 30 分钟改一个接口（练习）

你接到任务："项目列表增加按合同金额范围筛选"。

### 3.1 改 schemas（请求 DTO）
```python
# app/modules/project/schemas.py
class ProjectListRequest(BaseModel):
    page: int = 1
    pageSize: int = 20
    keyword: str = ""
    amountMin: Optional[Decimal] = None  # 新增
    amountMax: Optional[Decimal] = None  # 新增
    filters: dict = {}
```

### 3.2 改 service（业务逻辑）
```python
# app/modules/project/service.py - list_projects 函数
# 在 conditions 拼接处加：
if req.amountMin is not None:
    conditions.append(Project.contract_amount >= req.amountMin)
if req.amountMax is not None:
    conditions.append(Project.contract_amount <= req.amountMax)
```

### 3.3 跑测试
```bash
pytest tests/test_project.py -v
```

### 3.4 浏览器测试
打开 `http://localhost:8000/docs`，找到 `POST /api/v1/projects/list`，Swagger UI 直接试。

**搞定。** 这就是完整流程。

---

## 4. 60 分钟创建新模块（合同模块样板）

按以下步骤，**完全照搬"项目"模块的结构**：

### 4.1 1) 创建目录 + 复制文件

```bash
mkdir -p app/modules/contract
cp app/modules/project/models.py app/modules/contract/models.py
cp app/modules/project/schemas.py app/modules/contract/schemas.py
cp app/modules/project/service.py app/modules/contract/service.py
cp app/modules/project/router.py app/modules/contract/router.py
touch app/modules/contract/__init__.py
```

### 4.2 2) 改 models.py

改表名、字段（参考 `../design/BACKEND.md §3.2 合同表 DDL`）。

```python
class Contract(Base):
    __tablename__ = "contracts"
    id = Column(Integer, primary_key=True)
    # ...
```

### 4.3 3) 改 schemas.py

改类名 + 字段。

### 4.4 4) 改 service.py

改函数 + SQL。

### 4.5 5) 改 router.py

改接口路径和参数。

### 4.6 6) 注册到 main.py

```python
# app/main.py
from app.modules.contract.router import router as contract_router
# ...
app.include_router(contract_router, prefix="/api/v1/contracts", tags=["合同"])
```

### 4.7 7) 生成 migration

```bash
alembic revision --autogenerate -m "add contracts table"
alembic upgrade head
```

### 4.8 8) 写测试

```bash
cp tests/test_project.py tests/test_contract.py
# 改测试用例
```

### 4.9 9) 跑测试 + 浏览器验证

```bash
pytest tests/test_contract.py -v
# 浏览器打开 http://localhost:8000/docs 看新接口
```

**预计耗时**：1-2 小时（第一个模块），后续模块 30-60 分钟。

---

## 5. 必须知道的"坑"

| 坑 | 说明 | 怎么避免 |
|------|------|---------|
| **金额单位** | 数据库存**分**（int），返回前端时**除 100 转元** | 用 `Decimal(amount_cents) / 100`，**不要用 float** |
| **异步 session** | 所有数据库操作必须 `async` + `await` | 看 project/service.py 的写法，照搬 |
| **跨模块引用** | `auth` 和 `project` 互相 import 会循环 | 跨模块引用放 `core/` 或通过 `__init__.py` 暴露 |
| **审计日志** | 写接口自动记录（中间件），但 **diff 要手动补** | 业务代码里显式 `await audit(...)` 调 |
| **权限检查** | 用 `Depends(require_permission("code:action"))` | 不要在 service 里检查 |
| **状态字段** | 用字符串 + 应用层校验（如 `status in [...]`） | 不要用 PostgreSQL ENUM（改起来麻烦） |
| **日期** | 数据库 `Date` / `DateTime(timezone=True)` | 返回给前端统一 `datetime`，前端格式化 |
| **JSONB** | 灵活字段（发票商品明细、模板字段） | 读写用 `json.dumps/loads`，不要存字符串 |

---

## 6. 常用命令速查

```bash
# 开发
uvicorn app.main:app --reload --port 8000    # 热重载

# 数据库
alembic revision --autogenerate -m "msg"     # 生成 migration
alembic upgrade head                          # 跑 migration
alembic downgrade -1                           # 回滚
alembic history                                # 历史

# 测试
pytest                                         # 全部
pytest tests/test_project.py -v               # 单文件
pytest -k "test_login"                         # 按名字
pytest --cov=app --cov-report=term-missing     # 覆盖率

# 代码质量
ruff check app/                                # Lint
ruff format app/                               # Format
mypy app/                                      # 类型检查

# 调试
# 在代码里加：
from loguru import logger
logger.debug("xxx {var}", var=var)
```

---

## 6.5. AI 数智化模块接入指引（独立里程碑，**不阻塞主线**）

> **重要**：AI 模块是**独立研发线**，和合同/销售费用/回款 3 个业务模块**完全解耦**。
> 你可以**先不读这一节**，等主线模块做完了再回来看。

### 6.5.1 怎么找 AI 模块的代码位置

```
backend/app/modules/ai/    ← 未来的 AI 模块（你创建）
├── models.py        # ai_tasks / ai_feedback / ai_alerts
├── schemas.py       # 沿用 AI-API.md 的 request/response 结构
├── service.py       # 业务逻辑（不直接调模型，调 ai_client）
├── ai_client.py     # ← 重点：模型调用的统一封装
└── router.py        # /api/v1/ai/* 路由
```

**唯一改主线的点**：`app/main.py` 加一行：
```python
from app.modules.ai.router import router as ai_router
app.include_router(ai_router, prefix="/api/v1/ai", tags=["AI 数智化"])
```

### 6.5.2 必读（按顺序）

1. **`../design/AI-API.md`** — 18 个必出接口契约（**这是你唯一的真相来源**）
2. **`../design/PaddleOCR-部署指南.md`** — 如果做字段抽取
3. **`../design/ai-extract-demo.html`** — 打开看交互（用浏览器，`file://` 也能跑）

### 6.5.3 几个核心原则（不破坏老系统）

| 原则 | 怎么落地 |
|------|---------|
| **路径独立** | 所有路由在 `/api/v1/ai/*` 前缀下，老路由 0 改动 |
| **服务独立** | OCR/LLM 调外部服务（`ai-service` 容器），本地用 `ai_client.py` 封装 |
| **降级兜底** | 任何 AI 调用 try/except 5000/5101，返回老流程结果 |
| **数据回流** | 用户修正字段后调 `/ai/extract/apply`（不是直接改库） |
| **审计** | 老审计中间件自动接管，只用 `source = "ai"` 标识 |

### 6.5.4 第一个 AI 接口的样板（10 分钟）

```python
# app/modules/ai/router.py
from fastapi import APIRouter, Depends
from app.core.security import require_permission, CurrentUser
from app.modules.ai import service
from app.modules.ai.schemas import ExtractRequest, ExtractResponse

router = APIRouter()

@router.post("/extract/upload", response_model=ExtractResponse)
async def extract_upload(
    req: ExtractRequest,
    current_user: CurrentUser = Depends(require_permission("ai:extract")),
):
    return await service.extract(req, current_user.id)
```

```python
# app/modules/ai/service.py
from app.modules.ai.ai_client import call_ocr
from app.core.exceptions import OCRFailedException

async def extract(req, user_id: int) -> dict:
    try:
        result = await call_ocr(req.file_url, req.type)
    except (TimeoutError, ConnectionError) as e:
        # 降级：返回空结果，前端用普通上传
        raise OCRFailedException("OCR 服务不可用，请稍后重试")

    # 落 ai_tasks 表（用于审计 + 历史查询）
    # ... 见 AI-API.md §8 DDL
    return result
```

### 6.5.5 怎么和算法工程师协作

| 你要做的 | 算法交付 | 你怎么接 |
|---------|---------|---------|
| 调 OCR 服务 | 算法给 `POST /ocr/recognize`（输入文件 URL，输出结构化 JSON） | 在 `ai_client.py` 写一个 `call_ocr()` 包装 |
| 调 LLM 服务 | 算法给 `POST /llm/chat`（流式 OpenAI 兼容） | 写 `call_llm_stream()` 处理 SSE |
| 风险模型 | 算法给 `POST /risk/score`（输入业务对象 ID，输出健康度） | 写 `call_risk_scan()` 同步调用 |

**对接的关键文档**：`../design/PaddleOCR-部署指南.md` 的 §6 接口规范。

### 6.5.6 测试要点

```python
# tests/test_ai.py 的关键 mock 点
@pytest.fixture
def mock_ocr_service(monkeypatch):
    async def fake_call_ocr(file_url, type):
        return {
            "invoiceNo": {"value": "12345678", "confidence": 99},
            # ...
        }
    monkeypatch.setattr("app.modules.ai.ai_client.call_ocr", fake_call_ocr)
```

- 测**正常路径**：mock 外部服务
- 测**降级路径**：mock 抛 500，让 service 捕获并返回兜底
- 测**回流路径**：用户调 `/ai/extract/apply`，验证 `ai_feedback` 表有记录

---

## 7. 与其他团队协作

| 团队 | 找谁 | 沟通什么 |
|------|------|---------|
| **前端** | 找 PM 要 `API.md` / `AI-API.md` | 接口契约、字段含义、错误码、置信度高亮 |
| **PM** | 找产品经理 | 需求变更、字段命名、状态流转 |
| **运维** | 找 DevOps | Docker 部署、监控告警 |
| **OCR 算法** | 找算法工程师 | PaddleOCR 服务调用、字段抽取（参考 `PaddleOCR-部署指南.md`） |
| **LLM 算法** | 找算法工程师 | Qwen2.5 调用、流式响应 |
| **QA** | 找测试 | 测试用例、bug 反馈 |

---

## 8. 上线前自检清单

新模块上线前必须：

- [ ] pytest 通过（覆盖率 ≥ 60%）
- [ ] API.md 已更新（接口、字段）
- [ ] BACKEND.md 已更新（如果有新表）
- [ ] 数据库 migration 已生成
- [ ] 审计日志接入（写接口）
- [ ] 权限检查（用 `require_permission`）
- [ ] 错误处理（用 `AppException`）
- [ ] 性能：列表查询 P99 < 300ms
- [ ] 监控：慢查询、错误率埋点
- [ ] 安全：金额字段用分、敏感字段加密

---

## 9. 进阶：水平扩展

| 场景 | 怎么扩展 |
|------|---------|
| 单实例 QPS 上限 | 加 gunicorn worker：`gunicorn -w 4 -k uvicorn.workers.UvicornWorker` |
| 数据库读压力 | 加 PgBouncer + 读写分离 |
| OCR 慢 | PaddleOCR 服务独立扩展，CPU → GPU 镜像 |
| 大文件上传 | 对象存储（OSS/S3），分片上传 |
| 实时推送慢 | Redis Cluster + Pub/Sub 分片 |
| SSE 长连接多 | 多实例负载均衡 + 黏性会话 |

---

## 10. 找谁问问题

- **架构问题 / 数据库设计** → 看 `BACKEND.md`，没有就问 PM
- **老 API 字段问题** → 看 `API.md`
- **AI 接口 / 数智化能力** → 看 `AI-API.md`（独立契约）
- **样式/交互问题** → 看前端 `design/` 目录（AI 组件看 `assets/common.css` 的 `.ai-*` 类）
- **OCR 问题** → 看 `OCR-选型.md` + `PaddleOCR-部署指南.md`
- **部署问题** → 看 `../deploy/README.md` + `../deploy/monitoring/README.md`

**不要在群里问"这个字段是什么意思"**——文档都有。找不到再问，**问的时候带具体文档名 + 链接**。

---

## 11. 开发期 vs 生产期

| 配置 | 开发 | 生产 |
|------|------|------|
| ENV | development | production |
| DEBUG | True | False |
| LOG_LEVEL | DEBUG | INFO |
| CORS_ORIGINS | localhost | 真实域名 |
| JWT_SECRET_KEY | 默认值（不安全） | 64 位随机字符串 |
| 数据库 | localhost | 内网地址 |
| Sentry DSN | 空 | 真实 DSN |
| Swagger | 开启 | 关闭 |

**生产部署前必须改 JWT_SECRET_KEY**！否则 token 会被伪造。

---

**第 1 周结束，你应该能交付：**
- ✅ 完整跑通项目（docker compose up -d）
- ✅ 完成 1-2 个模块（基于"项目"模块样板）
- ✅ 测试覆盖率 ≥ 60%
- ✅ 接入审计日志
- ✅ 接入权限检查

**第 2-3 周**：完成剩余 4-5 个业务模块

**第 4 周**：联调 + bug 修复

**第 5-9 周**：见 ROADMAP.md

---

最后一句话：**遇到问题先查文档，文档没写才问。** 这套文档覆盖 90% 的常见问题。
