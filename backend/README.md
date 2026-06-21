# 数智化管理系统 · 后端

> **栈**：Python 3.11 + FastAPI + PostgreSQL 15 + Redis 7
> **新成员必读**：[`ONBOARDING.md`](./ONBOARDING.md)
> **API 契约**：[`../design/API.md`](../design/API.md)
> **架构基线**：[`../design/BACKEND.md`](../design/BACKEND.md)

---

## 快速开始

```bash
# 1. 装依赖
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 2. 启动依赖服务（用 docker 是最快的）
docker run -d -p 5432:5432 \
  -e POSTGRES_USER=shuzhi -e POSTGRES_PASSWORD=shuzhi -e POSTGRES_DB=shuzhi \
  postgres:15-alpine
docker run -d -p 6379:6379 redis:7-alpine

# 3. 配置
cp ../deploy/.env.example .env
# 编辑 .env 改 JWT_SECRET_KEY（32 位随机字符串）
# macOS 生成：openssl rand -hex 32

# 4. 初始化
alembic upgrade head
python scripts/seed.py

# 5. 启动
uvicorn app.main:app --reload --port 8000

# 6. 打开浏览器
# http://localhost:8000/docs  ← Swagger UI（自动生成所有接口）
# http://localhost:8000/health  ← 健康检查
# http://localhost:8000/redoc   ← ReDoc 文档
```

**默认账号**：`admin / admin123`（seed 写入，**生产必须改**）

---

## 项目结构

```
backend/
├── app/
│   ├── main.py              FastAPI 入口（lifespan + 中间件 + 路由挂载）
│   ├── config.py            配置（pydantic-settings，从 .env 读）
│   ├── core/                跨模块通用能力
│   │   ├── database.py      SQLAlchemy 2.0 async 引擎 + Base + get_db
│   │   ├── security.py      JWT 签发/校验 + bcrypt + 权限校验
│   │   ├── exceptions.py    业务异常类 + 异常处理器
│   │   ├── audit.py         写接口自动审计中间件
│   │   └── sse.py           SSE 事件总线（Redis Pub/Sub）
│   └── modules/             业务模块
│       ├── auth/            认证（已完成，样板之一）
│       │   ├── models.py    User/Role/Permission/Department/Dictionary
│       │   ├── schemas.py   Pydantic DTO
│       │   ├── service.py   业务逻辑
│       │   └── router.py    路由
│       └── project/         项目（已完成，样板）
│           ├── models.py    Project/Milestone/Client
│           ├── schemas.py   Pydantic
│           ├── service.py   业务（含权限过滤）
│           └── router.py    路由
├── alembic/                 数据库迁移（async）
│   ├── env.py
│   └── versions/
├── scripts/
│   └── seed.py              种子数据（部门/角色/权限/用户/客户/项目）
├── tests/                   pytest 测试
│   ├── conftest.py          fixtures（admin_user / normal_user / sample_project）
│   ├── test_auth.py         认证模块测试（18 用例）
│   └── test_project.py      项目模块测试（14 用例）
├── requirements.txt
├── alembic.ini
├── pytest.ini
├── README.md
└── ONBOARDING.md            新成员 1 小时上手指南
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

## 已有接口（Swagger 自动生成更多）

### 健康检查
- `GET /health` — 服务健康 + DB + Redis 检查

### 认证 `/api/v1/auth`
- `POST /login` — 账号密码登录
- `POST /logout` — 登出
- `POST /sso/qrcode/generate` — 生成 SSO 扫码二维码
- `POST /sso/qrcode/check` — 轮询扫码状态
- `POST /password/reset/request` — 发送重置密码验证码
- `POST /password/reset/confirm` — 确认重置密码
- `GET /me` — 获取当前登录用户信息

### 项目 `/api/v1/projects`
- `POST /list` — 列表（分页 + 筛选）
- `POST /detail` — 详情
- `POST /create` — 立项（需 `project:write`）
- `POST /update` — 更新（需 `project:write`）
- `POST /delete` — 删除（需 `project:write`）
- `POST /milestone/add` — 添加里程碑（需 `milestone:write`）
- `POST /stats` — 统计

---

## 配置项（.env）

```bash
# 环境
ENV=development              # development | testing | production
DEBUG=true
LOG_LEVEL=DEBUG

# 数据库
DATABASE_URL=postgresql+asyncpg://shuzhi:shuzhi@localhost:5432/shuzhi

# Redis
REDIS_URL=redis://localhost:6379/0

# JWT（生产必须改！）
JWT_SECRET_KEY=<32位随机字符串>
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=120    # 2 小时
JWT_REFRESH_TOKEN_EXPIRE_DAYS=7

# CORS
CORS_ORIGINS=["http://localhost:5173","http://localhost:3000"]

# 上传
UPLOAD_DIR=./uploads
MAX_UPLOAD_SIZE_MB=20

# 监控（可选）
SENTRY_DSN=
```

**生产部署前必改**：`ENV=production`、`JWT_SECRET_KEY`、`CORS_ORIGINS`、`SENTRY_DSN`

---

## 常用命令

```bash
# 开发
uvicorn app.main:app --reload --port 8000

# 测试
pytest                                    # 全部
pytest tests/test_auth.py -v              # 单文件
pytest -k "test_login"                    # 按名字
pytest --cov=app --cov-report=term-missing  # 覆盖率

# 数据库迁移
alembic revision --autogenerate -m "msg"  # 生成 migration
alembic upgrade head                      # 跑 migration
alembic downgrade -1                      # 回滚一版
alembic history                           # 历史

# 代码质量
ruff check app/                           # Lint
ruff format app/                          # Format
mypy app/                                 # 类型检查

# 调试
# 在代码里加：
from loguru import logger
logger.debug("xxx {var}", var=var)
```

---

## 已有模块

| 模块 | 状态 | 接口数 | 测试 |
|------|------|--------|------|
| 认证（auth） | ✅ 完整 | 7 | 18 用例 |
| 项目（project） | ✅ 完整（样板） | 7 | 14 用例 |
| 合同 | ⚪ 待开发 | — | — |
| 销售费用 | ⚪ 待开发 | — | — |
| 发票识别 | ⚪ 待开发 | — | — |
| 发票模板 | ⚪ 待开发 | — | — |
| 回款 | ⚪ 待开发 | — | — |

**新增模块**：复制 `modules/project/` 的结构，参考 `ONBOARDING.md §5`。

---

## 关键设计点

### 1. 金额单位
数据库统一存**分**（BIGINT），返回前端时**除 100 转元**。
```python
# 写入
budget = 1000000  # 1 万（分）

# 读取
amount_yuan = Decimal(budget) / 100  # 10000.00
```

### 2. 异步一切
所有数据库操作必须 `async` + `await`，见 `project/service.py`。

### 3. 审计自动 + 手动
- **自动**：所有 POST/PUT/DELETE 走中间件，body 截断 2000 字符
- **手动**：重要操作显式 `await audit_log(...)` 补 diff

### 4. RBAC + 数据范围
- **菜单权限**：`Depends(require_permission("project:write"))`
- **数据范围**：`current_user.data_scope` (all/dept/self)
- **过滤示例**：
  ```python
  if current_user.data_scope == "self":
      q = q.where(Project.manager_id == current_user.id)
  ```

### 5. SSE 实时通信
```python
# 业务侧
await publish_event("project:123", "progress", {"percent": 80})

# 前端侧
const es = new EventSource(`/api/v1/sse/stream?topic=project:123&token=...`)
es.addEventListener("progress", e => {...})
```
多实例时 Redis Pub/Sub 自动解耦。

---

## 故障排查

| 问题 | 排查 |
|------|------|
| `alembic upgrade` 失败 | 检查 `DATABASE_URL`，确认 PG 已启动 |
| `pytest` 启动报 import 错 | 确认已激活 venv + `pip install -r requirements.txt` |
| `JWT 解码失败` | 确认 `JWT_SECRET_KEY` 在所有实例一致 |
| `SSE 立即断开` | 检查 nginx `proxy_buffering off` + `X-Accel-Buffering no` |
| `外部 IP 无法登录` | 确认 `CORS_ORIGINS` 包含前端域名 |
| `SQLAlchemy 跨 session 访问` | `await db.refresh(obj)` 后再读属性 |

---

## 上线检查清单

- [ ] pytest 全部通过（覆盖率 ≥ 60%）
- [ ] `JWT_SECRET_KEY` 已改为随机
- [ ] `ENV=production` + `DEBUG=false`
- [ ] `CORS_ORIGINS` 改为生产域名
- [ ] `alembic upgrade head` 已跑
- [ ] 备份策略 + 监控告警已配
- [ ] Sentry DSN 已配
- [ ] 默认 admin 密码已改

---

## 更多

- 进场指引：[`ONBOARDING.md`](./ONBOARDING.md)
- API 契约：[`../design/API.md`](../design/API.md)
- 架构基线：[`../design/BACKEND.md`](../design/BACKEND.md)
- 部署：[`../deploy/README.md`](../deploy/README.md)
- Roadmap：[`../design/ROADMAP.md`](../design/ROADMAP.md)
