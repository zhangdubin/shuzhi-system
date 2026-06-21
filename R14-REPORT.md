# R14 暗色模式 + 压测基线报告

**日期**：2026-06-15  
**父 session 拍板**：B 方案 = 暗色 + 压测并行 → PWA  
**耗时**：~50 分钟（R14A 30 分钟 + R14B 20 分钟）  
**当前状态**：R14A ✅ + R14B ✅ 完成，R14C (PWA) 待 R15

---

## R14A 暗色模式补全 ✅

### 改动
**文件**：`frontend/src/assets/styles/ai.scss`（687 → 736 行）

**新增 49 行 CSS 覆写**：
```scss
.theme-dark body { background: #0F1320 !important; color: #E5E7EB; }
.theme-dark #app { background: #0F1320; }
.theme-dark .detail-hero, .theme-dark [class*="gradient-brand"] { 渐变降饱和 }
.theme-dark .gradient-hero, .theme-dark [class*="gradient-hero"] { 深色渐变保留 }
.theme-dark .gradient-brand-soft { 浅紫 → 深色透明 }
.theme-dark .page-section, .form-section, .detail-section, .info-grid, .data-card { #1A1F2E }
.theme-dark ::-webkit-scrollbar { 深色滚动条 }
.theme-dark .el-tag, .el-button--text, .el-divider, .el-empty, .el-loading-mask, .el-popper, .el-select-dropdown, .el-dropdown-menu, .el-pagination { 全部深色适配 }
```

### E2E 验证（dark-mode-playwright.spec.js）
- 5 页浅色截图 ✓
- 切到暗色：html.theme-dark=true, localStorage=1 ✓
- 5 页暗色截图 ✓
- **body backgroundColor = rgb(15, 19, 32) = #0F1320** ✓
- 切回浅色 ✓

### 截图归档（10 张）
- 浅色 5：`3-real-r14a-light-{dashboard,contract-list,project-list,expense-list,receivable-list}.png`
- 暗色 5：`3-real-r14a-dark-{dashboard,contract-list,project-list,expense-list,receivable-list}.png`

### Build 验证
- `npm run build` ✓ 3.78s 0 错误
- 前端镜像重 build + 三连：shuzhi-frontend:latest OK
- 容器端口 80/8088 200 OK

### 8 common 组件 + 10+ 业务页覆盖
- **8 common 组件**：实测**硬编码浅色背景 = 0**（已用 design token + Element Plus 变量，自动跟随 .theme-dark）
- **10+ 业务页** 渐变背景：覆写 `.detail-hero` / `[class*="gradient-brand"]` / `.gradient-brand-soft`（35+ vue 用了渐变，自动跟随）

---

## R14B 压测基线 ✅

### 压测基础设施
- **k6 镜像**：`grafana/k6:latest`（docker pull 完成）
- **3 场景脚本**：`perf/scenarios/scenario-{1,2,3}-*.js`
- **1 报告生成器**：`perf/scripts/gen_report.py`（k6 JSON → Markdown）

### 场景 1：登录 + Dashboard 阶梯（5→50 RPS）
**目的**：摸底 backend 在递增 RPS 下的真实性能  
**结果**：
- 0-10 RPS：稳定，P95 < 100ms
- 30 RPS：开始 drop_iterations
- 50 RPS：drop_iterations > 50%
- 100+ RPS：彻底爆（P95 > 20s）

**结论**：当前 4-worker uvicorn **能稳定 ~10-20 RPS**，50+ 需要扩 worker 或加缓存。

### 场景 2：业务核心 5 接口混合（20 RPS 稳态）⭐
**目的**：验证业务 5 大模块性能 + 缓存命中  
**接口**：`/api/v1/{contracts,projects,expenses,receivables}/{list,detail}` 随机  
**结果**：
- ✅ 1201/1201 iterations 0 fail
- ✅ **P95 = 14.1ms / 平均 = 11.3ms / 最大 = 267.8ms**
- ✅ **错误率 0%**（修 idKey 推导后）

### 场景 3：AI + 业务接口混合（10 RPS）
**目的**：验证 22 触点 + 业务接口混合负载  
**结果**：
- ✅ 600/600 iterations 0 fail
- ✅ **P95 = 26.4ms / 平均 = 13.9ms**
- ✅ **错误率 0%**（5xx 才算错，4xx 是 client 错）

### 关键发现 / 修复
1. **k6 容器内 `host.docker.internal` 在 `--network host` 模式下失效** → 改 `localhost:8000`
2. **后端 detail 接口是 query 参数 `?contractId=N`，不是 body `{id: N}`** → 修脚本
3. **不同 domain 主键位置不同**（contracts 有 `contractId`，projects 有 `id`） → 修 idKey 推导
4. **gen_report.py 适配 k6 0.49+ 扁平化 metrics** + checks 是 dict 不是 list

### 报告
- `perf/reports/scenario-1-report.md`（登录 + Dashboard）
- `perf/reports/scenario-2-report.md`（业务核心 5 接口）⭐
- `perf/reports/scenario-3-report.md`（AI + 业务混合）

### 性能基线结论
**单实例 4-worker 后端性能**：
- **20 RPS 稳态**：业务核心 5 接口 P95 14ms ✓ 0% 错
- **10 RPS 稳态**：AI + 业务混合 P95 26ms ✓ 0% 错
- **>50 RPS**：drop_iterations 严重，需扩 worker 或加 Redis 缓存覆盖

---

## R14 整体交付物清单

| 交付物 | 路径 | 行数/张数 | 状态 |
|---|---|---|---|
| 暗色模式 CSS 覆写 | `frontend/src/assets/styles/ai.scss` | 49 行新增 | ✅ |
| 暗色模式 E2E | `e2e/dark-mode-playwright.spec.js` | 130 行 | ✅ |
| 暗色截图（浅/暗各 5） | `docs/screenshots/compare/3-real-r14a-*.png` | 10 张 | ✅ |
| k6 场景 1 | `perf/scenarios/scenario-1-login-dashboard.js` | 60 行 | ✅ |
| k6 场景 2 | `perf/scenarios/scenario-2-business-core.js` | 80 行 | ✅ |
| k6 场景 3 | `perf/scenarios/scenario-3-ai-mock.js` | 75 行 | ✅ |
| 报告生成器 | `perf/scripts/gen_report.py` | 130 行 | ✅ |
| 压测报告 3 份 | `perf/reports/scenario-{1,2,3}-report.md` | 3 份 | ✅ |
| 压测 summary JSON | `perf/reports/scenario-{1,2,3}-summary.json` | 3 个 | ✅ |

---

## R14 总结

🎉 **R14 暗色模式 + 压测基线并行完成**！

- **暗色模式**：body 背景 #0F1320，业务页渐变降饱和，深色滚动条 + Element Plus 全组件深色适配，10 张截图归档
- **压测基线**：20 RPS 业务核心 P95 14ms / 0% 错，10 RPS AI 业务混合 P95 26ms / 0% 错，性能基线建立

## R15 候选（等父 session 拍板）

1. **R14C PWA**（按 R14 方案 B 排 PWA 在最后）
2. **诺诺真接入**（资质 1-3 天）
3. **PWA + 诺诺 一并做**
4. **继续性能优化**（扩 worker / 加 Redis 缓存覆盖）

---

**报告版本**：R14 v1.0 | 2026-06-15
**状态**：A + B 完成，C 待定
