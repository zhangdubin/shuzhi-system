# R17 · 优化路线图（基于实际扫描）

> **生成时间**：2026-06-26 18:20
> **当前 HEAD**：`4446af6 修改标题`（R16 暗色重构后）
> **基础**：R1-R16 已完成；38 vue + 128 API + PaddleOCR 已切真 + PWA + 暗色
> **目标**：把"基本完整的功能"打磨成"可长期维护的生产级系统"
> **范围**：本次仅做计划，不动任何代码

---

## 0. 调研结论（5 个事实 + 1 个判断）

### 事实 1 · 前端"技术债集中区"
| 指标 | 实测 | 风险 |
|---|---|---|
| `.vue` 文件总数 | **73 个** | OK |
| 重复 mock 业务编号（HT-/INV-/EXP-/RV-）的 vue | **≥10 个** | ⚠️ mock 数据散落业务页 |
| 22 个 TS 文件中，Pinia store | **仅 2 个**（ai.ts、user.ts） | ⚠️ 大部分状态用组件内 ref |
| 业务页 error 提示 `ElMessage.error` 直接调用 | **37 个 vue** | ⚠️ 错误处理未集中 |
| 巨型 vue 文件 (>30KB) | 6 个，最大 65KB（ExpenseDetail.vue） | ⚠️ 单文件职责过重 |
| `frontend/dist` 体积 | 3.5M | 中性，可接受 |
| `tsconfig` strict 模式 | ✅ 已开 | ✓ |

### 事实 2 · 后端"质量缺口"
| 指标 | 实测 | 风险 |
|---|---|---|
| Python 业务文件 | 88 个 | 规模大 |
| pytest 测试文件 | **仅 2 个**（test_auth、test_project） | ⚠️⚠️ **测试覆盖率极低** |
| 缓存装饰器（`@cache`）覆盖 | 3 个文件（core/cache.py、dashboard、ai_client） | ⚠️ 业务模块缓存稀少（PERF-REPORT 已说"待优化") |
| API 限流（rate limit） | 0 处（搜不到 slowapi / fastapi-limiter） | ⚠️⚠️ **P0 安全风险** |
| CORS / 审计 / 异常中间件 | ✅ 已有 | ✓ |
| 启动调度器 | ✅ 已有 | ✓ |

### 事实 3 · 部署/工具链
| 指标 | 实测 |
|---|---|
| CI/CD（GitHub Actions / GitLab CI） | **❌ 完全没有**（项目根 + deploy 都没有 .github/ 或 .gitlab-ci.yml） |
| 截图库 `docs/screenshots/compare/` | 122 张（很多 R 阶段对比） |
| 自动生成的 OpenAPI | ✅ 根目录有 `openapi.json`（249KB） |
| Mock 数据集中管理 | ❌ 散落在各 vue 文件内 |

### 事实 4 · 用户留下的明确线索
- `R16-REPORT.md` 末尾「R17 优化方向」未列出
- `PROJECT_HANDBOOK.md` 5.x 列出待办：**worker 4→8 / 缓存扩 12 接口 / 慢 SQL / PWA 真机 / 暗色剩余 33 页 / 告警通知渠道 / 审计日志查询 UI / 数据导入 / API 限流 / CI/CD**
- `PERF-REPORT.md` 列了 4 个明确"待优化项"（AI 缓存 / select_fields / 字典内存 / SSE 连接池）

### 事实 5 · 项目已经"基本完整"
不是从零起步——是"用着没问题但维护起来累"的阶段。优化方向应是**减债 + 提质 + 加安全**，而不是"加新功能"。

### 综合判断
按 ROI（影响 / 成本）排序，**5 块优化值得做**，分 P0 / P1 / P2 三档。

---

## 1. P0 · 安全 + 测试（必做，影响生产可信度）

### 1.1 API 限流（P0 / 半天 / 1 个 PR）
**为什么**：128 个 API 0 限流 → 内部系统被刷数据/拒绝服务无任何保护。
**做法**：
- 引入 `slowapi`（轻量、基于 Redis 共享）
- `main.py` 注册 `SlowAPIMiddleware` + `Limiter`
- 全局默认：同 IP **60 req/min**
- 特殊接口（登录、OCR 上传、AI 问答）单独再低：**登录 5 req/min / OCR 10 req/min / AI 20 req/min**
- 给 `@limiter.limit("30/minute")` 加到关键路由
**验证**：
```bash
for i in {1..10}; do curl -s -X POST http://localhost:8000/api/v1/auth/login -d '{}' -H 'Content-Type: application/json' | head -1; done
# 期望：前 5 次正常，第 6 次 429
```

### 1.2 后端测试覆盖从 5% 提到 30%+（P0 / 3-5 天 / 多 PR）
**为什么**：88 个 Python 文件只有 2 个测试，**改一行就可能炸**。R11A 加的缓存、监控、限流都要有回归测试才敢上线。
**做法**：
- 优先覆盖**已有、未测**的 11 个业务模块：contract / expense / receivable / invoice_ocr / invoice_template / invoice_verify / admin / ai / dashboard / common / cron
- 每个模块至少 3 个测试：list / create / 权限拒绝
- 引入 `pytest-asyncio` 现有（看看 conftest）+ `httpx` 测 API
- 目标：tests/ 目录从 2 个文件 → **≥12 个文件**，pytest 用例从 ~30 → **≥120**
- 集成到 CI（见 3.1）

### 1.3 错误处理集中化（P0 / 1 天 / 1 个 PR）
**为什么**：37 个 vue 各自 `ElMessage.error(...)`，产品升级时改个文案要改 37 处。
**做法**：
- 前端：建 `frontend/src/utils/notify.ts`，提供 `notify.success/error/warn/loading` 统一封装
- 全仓 `grep -l "ElMessage.error" frontend/src` 改成 `notify.error`
- 后端：`app/core/exceptions.py` 已有 `AppException` 和 `app_exception_handler` → 校验**所有 router 都 raise AppException**，不再直接 `HTTPException(500)`
- 加 `notify.error` 单元测试

---

## 2. P1 · 代码质量 + 性能（建议下个 sprint）

### 2.1 Mock 数据集中化（P1 / 1 天 / 1 个 PR）
**为什么**：10+ 个 vue 重复 `HT-2026-994`、`INV-2026-06-15-8DC` 这类演示数据。新增演示数据要改 10 处。
**做法**：
- 新建 `frontend/src/mock/seed.ts`：集中导出 `MOCK_CONTRACTS`、`MOCK_INVOICES`、`MOCK_EXPENSES`...
- 各 vue `import { MOCK_CONTRACTS } from '@/mock/seed'`
- 类型化（用 `Contract` / `Invoice` interface 不用 `any`）
- `design/` 下原 HTML 内嵌的 mock 复制进来作为兜底数据

### 2.2 Pinia store 补齐 + 状态提升（P1 / 2 天 / 多 PR）
**为什么**：73 vue 大量用 `ref`，跨页状态只能路由 query 带过去，复杂。
**做法**（按需分批）：
- `useTableStore`：列表查询条件 / 分页 / loading 缓存（5 个列表页共用）
- `useNoticeStore`：通知中心全局（已存在但要重构）
- `useThemeStore`：暗色模式（目前用 localStorage 直接读，未来要支持跨标签页同步 → 走 store）
- `useFilterStore`：合同/项目/费用 通用筛选条件（避免切 tab 丢失）
**验证**：列表页切走再回来，滚动位置 / 筛选条件还在。

### 2.3 缓存覆盖扩展（PERF-REPORT 已列）（P1 / 2 天 / 多 PR）
**为什么**：`@cache` 现在只 3 处用，dashboard 缓存 99% 命中率已被验证。
**做法**：
- admin：users / roles / depts 列表（静态字典性质）→ 5min TTL
- common：dict / notice-types / project-templates → 5min TTL
- contract：status 字典、type 字典 → 启动时加载到内存
- AI 端点缓存：同一问题 5min 内不重算（PERF-REPORT 5.1 明确）
**验证**：`ab -c 10 -n 1000 ...` 看 p95 是否下降，Prometheus `cache_hit_total` 指标新增。

### 2.4 SSE 长连接池化（PERF-REPORT 5.4）（P1 / 1 天 / 1 个 PR）
**为什么**：当前每连接一个 consume_task，100 用户同时在线 = 100 个 task。
**做法**：
- 改 `app/core/sse.py`：`asyncio.create_task` 改为 `asyncio.Queue` 池
- 单 Redis 订阅 → 多个用户共享一个 channel consumer
- 写 Prometheus 指标 `sse_active_consumers` 和 `sse_messages_broadcast_total`

---

## 3. P1 · 工程化（DevOps / 质量门）

### 3.1 GitHub Actions CI（P1 / 1 天 / 1 个 PR）
**为什么**：当前手工 `npm run build` + `docker compose build`，**改完不知道什么时候坏的**。
**做法**：
- 根目录建 `.github/workflows/ci.yml`
- 3 个 job：
  1. `frontend-lint-build`：`pnpm i && pnpm run type-check && pnpm run build`
  2. `backend-test`：`cd backend && pytest -v --cov=app --cov-report=xml`
  3. `docker-build`：`docker build -f frontend/Dockerfile .`（不 push，只验证 Dockerfile 可用）
- 触发：PR + push to main
- 失败时阻断 merge

### 3.2 前端 ESLint + Prettier（P1 / 0.5 天 / 1 个 PR）
**为什么**：根 `package.json` 没有 lint 脚本（只有 start/build/test）。
**做法**：
- 引入 `@vue/eslint-config-typescript` + `eslint-plugin-vue` + `prettier`
- 配 `.eslintrc.cjs` 继承 vue3-recommended + ts
- `lint` 脚本加进 `package.json`
- 配 `lint-staged` + `husky` 提交时自动 fix

### 3.3 Dockerfile 多阶段 + 镜像瘦身（P1 / 0.5 天 / 1 个 PR）
**为什么**：R16 报告未提镜像大小，先看实际。
**做法**：
- 验证 `frontend/Dockerfile` 是否多阶段（vite build → nginx 静态）
- 后端：检查 `backend/Dockerfile` 是否用 `slim` 而非 `full` 基础镜像
- 加 `.dockerignore` 排除 `node_modules/` `dist/` `tests/` `.git/`
**验证**：`docker images | grep shuzhi` 看镜像大小

---

## 4. P2 · 体验补全（有余力再做）

### 4.1 暗色模式 33 页视觉验收（R16 遗留）
- 已有 3 页 100% 协调，剩余 33 业务页要逐页切暗色截图
- 截图归档到 `docs/screenshots/compare/5-real-r17-dark-*.png`
- 发现问题 → dark-theme.scss 修一次（设计系统级，仍是单点改全网生效）

### 4.2 审计日志查询 UI
- 后端 `audit_logs` 表已记录（90+ 行）
- 新建 `frontend/src/views/admin/AuditLog.vue`：分页查询、按用户/时间/资源类型筛选
- 后端补 `GET /api/v1/admin/audit-logs` 分页接口

### 4.3 数据导入
- Excel 导入（合同/项目/客户）
- 用 `xlsx` 库 + 模板下载
- 列映射 + 校验 + 错误行高亮

### 4.4 告警通知渠道
- Alertmanager 已配规则，未配接收人
- 加 Webhook → 飞书 / 钉钉 / 邮件
- `deploy/monitoring/alertmanager.yml` 加 `webhook_config`

### 4.5 PWA 真机验证
- iOS Safari / Android Chrome 安装到主屏
- DevTools 切 offline → 走离线降级页
- 7 天冷却逻辑真机触发

---

## 5. 暂不建议做的（避免 scope creep）

| 想法 | 不做的理由 |
|---|---|
| 引入 Tailwind / UnoCSS | 已用 SCSS + design tokens，迁移成本远大于收益 |
| 微服务拆分 | 单体 FastAPI 仍 20 RPS p95 14ms，过早拆分 |
| 引入 TypeScript 5.x / Vite 6 | 当前 Vite 5 + TS 5.4 稳定，没必要追新 |
| 写客户端测试 | 后端测试覆盖先搞，73 vue 测起来 ROI 极低 |
| Storybook | 单人项目，组件复用靠 README + 复制粘贴足够 |

---

## 6. 推荐执行顺序（按 ROI）

| # | 任务 | 估时 | 风险 | 收益 |
|---|---|---|---|---|
| 1 | **API 限流**（1.1） | 0.5 天 | 低 | 高（防刷） |
| 2 | **错误处理集中化**（1.3） | 1 天 | 低 | 中（维护性） |
| 3 | **后端测试覆盖**（1.2） | 3-5 天 | 中 | 高（重构底气） |
| 4 | **GitHub Actions CI**（3.1） | 1 天 | 低 | 高（防回归） |
| 5 | **前端 ESLint + Prettier**（3.2） | 0.5 天 | 低 | 中 |
| 6 | **Mock 数据集中化**（2.1） | 1 天 | 低 | 中 |
| 7 | **Pinia store 补齐**（2.2） | 2 天 | 中 | 中 |
| 8 | **缓存扩展**（2.3） | 2 天 | 中 | 高（性能） |
| 9 | **SSE 连接池化**（2.4） | 1 天 | 中 | 中（生产稳定性） |
| 10 | **Docker 优化**（3.3） | 0.5 天 | 低 | 低 |
| 11 | **暗色 33 页验收**（4.1） | 2 天 | 低 | 中（体验） |
| 12 | **审计日志 UI**（4.2） | 1 天 | 低 | 中 |
| 13 | **数据导入**（4.3） | 2 天 | 中 | 中 |
| 14 | **告警通知**（4.4） | 0.5 天 | 低 | 中 |
| 15 | **PWA 真机**（4.5） | 1 天 | 低 | 低（体验） |

**总量**：约 17-22 天工作量（1 个 dev 1 个月）

---

## 7. 验证清单（任意一项完成后）

```bash
# 前端
cd frontend && npm run build 2>&1 | tail -10   # 期望 0 错
cd frontend && npm run type-check               # 期望 0 错

# 后端
cd backend && pytest -v --tb=short               # 期望全过
cd backend && python -m app.main 2>&1 | head -3  # 期望启动 OK

# 限流验证
for i in {1..8}; do curl -s -X POST http://localhost:8000/api/v1/auth/login \
  -H 'Content-Type: application/json' -d '{}' -w "%{http_code}\n"; done
# 期望 422,422,422,422,422,429,429,429

# 缓存验证
docker exec shuzhi-redis redis-cli INFO stats | grep -E "keyspace|expired"
# 期望 keyspace_hits 持续增长
```

---

## 8. 文件改动预期（粗估）

| 路径 | 改动规模 | 备注 |
|---|---|---|
| `backend/app/main.py` | +30 行（限流 + 异常 handler 校验） | P0 |
| `backend/tests/**` | +10 个文件 / +90 用例 | P0 |
| `backend/app/modules/*/router.py` | 各 +5 行（@limiter.limit） | P0 |
| `frontend/src/utils/notify.ts` | 新建 50 行 | P0 |
| `frontend/src/views/**/*.vue` | 37 处 ElMessage.error → notify.error | P0 |
| `frontend/src/mock/seed.ts` | 新建 200 行 | P1 |
| `frontend/src/stores/*.ts` | 新建 3-4 个 store | P1 |
| `frontend/.eslintrc.cjs` + `.prettierrc` | 新建 | P1 |
| `.github/workflows/ci.yml` | 新建 80 行 | P1 |
| `frontend/Dockerfile` + `backend/Dockerfile` | 各 +5 行（多阶段验证） | P1 |
| `frontend/src/views/admin/AuditLog.vue` | 新建 300 行 | P2 |
| `deploy/monitoring/alertmanager.yml` | +20 行（webhook） | P2 |
| **总计** | **约 12 个新文件 / 30+ 个文件改动** | |

---

## 9. 风险与回滚

| 风险 | 应对 |
|---|---|
| 限流误伤正常用户 | 默认 60/min 宽松；先 dry-run 日志观察 1 周 |
| 测试覆盖率提升慢 | 不要求一次性达到 30%，**每个新模块 PR 必带测试** |
| Pinia 重构破坏现有功能 | **渐进式**——新功能用 store，旧的不动 |
| CI 配置错误阻塞开发 | 第一次跑用 `continue-on-error: true`，稳定后改必须 |
| 暗色微调改坏亮色 | 改 dark-theme.scss 的 `.theme-dark` 段，不动 `:root` |

---

## 10. 下一步动作

**等你拍板**：

1. **路线图选哪几项？**（我建议先做 P0 的 1.1 + 1.3 + P1 的 3.1，1 周内见效）
2. **要不要拆 PR？**（建议每项独立 PR，便于 review 和回滚）
3. **是否需要建 R17 系列 REPORT 模板**？（参考 R11A / R11B 命名）
4. **要先攻哪一块？**（我个人建议从 **API 限流 + 错误处理** 开始——半天就有安全感）

---

**报告生成**：`/Users/trisome/Desktop/开发/数智化系统new/.hermes/plans/2026-06-26_182000-r17-optimization-roadmap.md`
**报告版本**：v1.0 | 2026-06-26
**依据**：R1-R16 全部 REPORT + AGENTS.md + 实测代码扫描
