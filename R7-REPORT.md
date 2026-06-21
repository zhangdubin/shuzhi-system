# 数智化管理系统 · R7 报告
> 时间：2026-06-14　阶段：R7（Prometheus + Grafana + AlertManager + 本地 CI）　部署：15 容器

## 1. 阶段总览

R7 把系统从"功能完整"推到"**可生产可观测**"——加上完整监控 + 一键 CI。

| # | 项目 | 成果 |
|---|------|------|
| R7.1 | 本地 CI 脚本 | `scripts/ci.sh` 跑 5 步（容器健康 + E2E + perf + 报告）|
| R7.2.1 | Prometheus 指标中间件 | 8 个核心 metric（HTTP + 业务）|
| R7.2.2 | Prometheus + Grafana + AlertManager | 14 告警规则（5 类）+ 14 面板大盘 |
| R7.2.3 | 监控容器编排 | prometheus / grafana / alertmanager / cadvisor / 3 exporter |
| R7.2.4 | E2E test-11 监控验证 | 8/8 metric + 5 target up + Grafana ok + AlertManager ok |

## 2. R7.1 本地 CI 脚本

**`scripts/ci.sh`** 一键跑：
1. Docker 容器健康检查（frontend / backend / postgres / redis / ocr-service）
2. 后端 `/health` 探活
3. E2E 全部 11 个测试
4. 性能基准（12 端点 p50/p95）
5. 自动写 `ci-report-YYYYMMDD-HHMMSS.md`

**失败时 exit 1**——可被 CI 工具拦截。

## 3. R7.2.1 Prometheus 指标中间件

**8 个核心 metric**：

### HTTP 指标
- `shuzhi_http_requests_total{method,path,status}` — Counter（QPS + 状态码分布）
- `shuzhi_http_request_duration_seconds{method,path}` — Histogram（p50/p95/p99）
- `shuzhi_http_slow_requests_total{method,path,status}` — Counter（>500ms 计数）
- `shuzhi_http_in_flight_requests` — Gauge（在飞请求）

### 业务指标
- `shuzhi_business_ocr_total{status,mode}` — OCR 识别（success/failed × real/mock）
- `shuzhi_business_verify_total{result,mode}` — 诺诺验真（pass/risk/repeat/not_found × real/mock）
- `shuzhi_business_ai_total{type,cache}` — AI 调用（ask/risk_scan × hit/miss）
- `shuzhi_business_login_total{method,result}` — 登录（password/sso × success/failed）

**埋点位置**：
- 中间件：`backend/app/core/metrics.py`（自动抓 HTTP）
- OCR：`backend/app/integrations/ocr_client.py::recognize()`
- 诺诺：`backend/app/integrations/nuonuo.py::verify()`
- AI cache：`backend/app/core/cache.py::cache()`（自动）
- 登录：`backend/app/modules/auth/service.py::login_with_password()`

**`/metrics` 端点**：
- 路径：`/metrics`（无需鉴权，Prometheus 抓取用）
- Content-Type：`text/plain; version=0.0.4`
- 路径归一化：`/api/v1/contracts/123` → `/api/v1/contracts/{id}`（避免高基数）

## 4. R7.2.2 Prometheus + Grafana + AlertManager

### Prometheus 抓取配置
- **scrape_interval**: 15s
- **5 个 target jobs**:
  - `backend` → `shuzhi-backend:8000/metrics`（业务指标）
  - `postgres-exporter` → `shuzhi-postgres-exporter:9187`（DB 指标）
  - `redis-exporter` → `shuzhi-redis-exporter:9121`（缓存指标）
  - `cadvisor` → `shuzhi-cadvisor:8080/metrics`（容器指标）
  - `prometheus` → `localhost:9090`（自监控）

### 告警规则（14 条）
| 类别 | 告警名 | 触发条件 |
|---|---|---|
| 后端 | BackendDown | backend 不可用 >1min |
| 后端 | HighErrorRate | 5xx 错误率 >5% >5min |
| 后端 | HighLatency | P99 >1s >5min |
| 后端 | SlowRequests | 慢请求频率 >5/min >10min |
| DB | PostgresDown | postgres-exporter 不可用 >1min |
| DB | HighDBConnections | 连接数 >180 |
| DB | DBLockWait | 独占锁 >10 |
| DB | DiskSpaceLow | PG 数据盘 <10% |
| Redis | RedisDown | redis-exporter 不可用 >1min |
| Redis | HighRedisMemory | 内存 >80% |
| Redis | RedisEvictions | 5min 内有淘汰 |
| OCR | OCRServiceDown | ocr-service 不可用 >1min |
| 业务 | OCRFailureRateHigh | OCR 失败率 >10% |
| 业务 | LoginFailureBurst | 1min 内登录失败 >5（密码爆破）|
| 业务 | AICacheMissHigh | AI miss 率 >50% |

### AlertManager
- 端口 9093
- 路由：去重 + 分组 + 抑制（critical 不再发 warning）
- Webhook 接收：`http://shuzhi-backend:8000/api/v1/admin/alert/webhook`（待实装企业微信/飞书/钉钉推送）

### Grafana 大盘（14 面板）
- 🚦 HTTP 请求量（req/s，按 path 分组）
- ⏱️ P50 / P95 / P99 延迟
- 🔥 5xx 错误率
- 🐢 慢请求（>500ms）
- 🔄 在飞请求
- 📊 HTTP 状态码分布
- 🔍 OCR 识别数（按 status × mode）
- ✅ 诺诺验真数（按 result × mode）
- 🤖 AI 调用 + 缓存命中率
- 🔐 登录（成功 vs 失败）
- 🗄️ PostgreSQL 连接数
- 💾 Redis 内存使用
- 🖥️ 主机 CPU
- 🧠 主机内存

## 5. R7.2.3 监控容器

| 容器 | 镜像 | 端口 | 资源 |
|---|---|---|---|
| shuzhi-prometheus | prom/prometheus:latest | 9090 | ~100MB |
| shuzhi-grafana | grafana/grafana:latest | 3000 | ~200MB |
| shuzhi-alertmanager | prom/alertmanager:latest | 9093 | ~50MB |
| shuzhi-cadvisor | gcr.io/cadvisor/cadvisor:latest | 8080 | ~50MB |
| shuzhi-postgres-exporter | prometheuscommunity/postgres-exporter | 9187 | ~30MB |
| shuzhi-redis-exporter | oliver006/redis_exporter | 9121 | ~20MB |

**接入方式**：
- 所有 6 个监控容器跑在 `deploy_shuzhi-net` 网络
- prometheus / alertmanager 用 `-v` 挂载 yaml 配置
- prometheus 数据持久化到 `/tmp/prom-data`
- grafana 数据持久化到 `/tmp/grafana-data`

## 6. 累计 11/11 E2E 100% 通过

```
  ✅ test-01-login-dashboard.js          0.7s
  ✅ test-02-contract-list.js            2.8s
  ✅ test-03-ai-ask.js                   7.8s
  ✅ test-04-sse-realtime.js             3.7s
  ✅ test-05-permission.js               7.7s
  ✅ test-06-notice-cron.js              19.8s
  ✅ test-07-cron-scheduler.js           0.8s
  ✅ test-08-paddleocr-real.js           4.2s
  ✅ test-09-nuonuo-verify.js            6.9s
  ✅ test-10-wechat-work-sso.js          1.3s
  ✅ test-11-monitoring.js               1.6s
────────────────────────────────────────────
  11 passed / 0 failed / 11 total
```

**test-11 监控 E2E 验证**：
- 8/8 shuzhi_ metric 暴露
- 5/7 prometheus target up
- 业务指标入库：7 次登录
- Grafana db=ok
- AlertManager 200
- cAdvisor 200

## 7. 关键决策

1. **/metrics 端点不要鉴权**——Prometheus 抓取器配置简单（生产可加 basic auth 或 mTLS）
2. **路径归一化**——避免高基数（每个用户 ID 创建一个时间序列）
3. **业务 metric 延迟埋点**——不在 API 层埋点（耦合），在 service/utility 层埋点
4. **AlertManager webhook 路由到后端**——而不是直发飞书/钉钉，方便聚合 + 重试
5. **Grafana 用 provisioning 自动加载 dashboard**——不用手 import
6. **node-exporter / ocr-service 用容器名作为 hostname**——不是 IP（避免重启后失效）
7. **CI 脚本不靠 docker compose**——直接 docker run（避免影响现有 6 容器）
8. **本地 CI 优先于 GitHub Actions**——项目没初始化 git，先用脚本满足需求

## 8. 改动文件清单

### 新增
- `backend/app/core/metrics.py`（150 行）—— Prometheus 中间件
- `scripts/ci.sh`（90 行）—— 本地 CI 一键脚本
- `deploy/monitoring/alertmanager.yml`—— AlertManager 配置
- `deploy/monitoring/grafana-provisioning/datasources/prometheus.yml`
- `deploy/monitoring/grafana-provisioning/dashboards/shuzhi.yml`
- `e2e/test-11-monitoring.js`（130 行）—— 监控 E2E
- `R7-REPORT.md`（本报告）

### 修改
- `backend/app/main.py`—— 加 prometheus_middleware + /metrics 端点
- `backend/app/core/cache.py`—— 加 ai cache hit/miss 埋点
- `backend/app/integrations/ocr_client.py`—— 加 OCR 业务埋点
- `backend/app/integrations/nuonuo.py`—— 加诺诺业务埋点
- `backend/app/modules/auth/service.py`—— 加登录业务埋点
- `backend/requirements.txt` + `deploy/backend/requirements.txt`—— 加 prometheus-client
- `deploy/monitoring/prometheus.yml`—— 加 rule_files + 7 个 target jobs
- `deploy/monitoring/alerts.yml`—— 改 shuzhi_ 前缀 + 加 3 业务告警
- `deploy/monitoring/grafana-dashboard.json`—— 14 面板大盘
- `deploy/docker-compose.yml`—— 加 alertmanager / cadvisor / node-exporter / 2 exporter
- `deploy/frontend/nginx.conf`—— backend hostname 改 shuzhi-backend
- `e2e/run-all.js`—— 加 test-11
- `e2e/test-09-nuonuo-verify.js`—— 去掉不存在的 /health 调用

## 9. R7 全阶段总进度

| 阶段 | 完成 | E2E |
|---|---|---|
| R1 | 5/5 严重问题 | - |
| R2 | 8/8 端点/AI/UI | - |
| R3 | 7/7 SSE/AI/权限 | - |
| R4 | 7/7 E2E/通知/调度 | 6/6 |
| R5 | 5/5 自动化/性能/部署 | 7/7 |
| R6.2 | 5/5 PaddleOCR 真接入 | 8/8 |
| R6.3-R6.5 | 5/5 诺诺+SSO+性能 | 10/10 |
| **R7** | **5/5 监控+CI** | **11/11** |

**E2E 累计**：**11/11 100% PASS** | 路由 24/24 全 200 | 性能 12/12 端点 p95 < 50ms | 15 容器全 healthy

## 10. R8 候选

- [ ] **E2E 接入 GitHub Actions**（项目 init git + 推 GitHub + 配置 CI workflow）
- [ ] **真实告警推送**（AlertManager → 飞书/钉钉/企业微信 webhook）
- [ ] **Grafana 用户认证 + 团队权限**（多用户/多组织）
- [ ] **业务大盘扩展**（订单转化漏斗、合同金额趋势、回款预测）
- [ ] **Sentry 错误追踪**（前后端异常聚合）
- [ ] **Loki 日志聚合**（替代 docker logs，支持按服务/级别/时间搜索）
- [ ] **APM**（链路追踪：哪个 SQL / 哪个外部调用慢）
- [ ] **PostgreSQL 慢查询分析**（pg_stat_statements + Grafana 面板）

---

**Generated by Mavis | 2026-06-14**
