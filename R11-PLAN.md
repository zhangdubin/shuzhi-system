# R11 摸底 + 拍板候选

> 父 session 要 R11 三方向（真实集成切真 / 性能优化 / 权限细化），先摸底估算工作量拍板分段走法

## 一、摸底结果

### 1. 真实集成切真（3 个，架构都就绪）
| 集成 | 状态 | 切真成本 | 阻塞 |
|---|---|---|---|
| **PaddleOCR** | 双模式完整（OCR_MODE=mock/real + 自动回退） | 改环境变量 + 配 PADDLEOCR_URL + GPU 机器 + 真接口 E2E | GPU 机器 |
| **诺诺** | 双模式完整（NUONUO_MODE + sandbox/prod + 签名 + 回退） | 改环境变量 + 配 API_KEY/SECRET + 真接口 E2E | 企业资质 |
| **企业微信 SSO** | 双模式完整（WECHAT_WORK_MODE + corp_id/secret 切真） | 改环境变量 + 配 corp_id/secret + 真接口 E2E | 企业资质 |

**总评**：3 套真协议代码完整，**只等资质**。切真工作量 ≈ 改环境变量 + docker-compose env 注入 + 真接口 E2E 验证 = 半天。

### 2. 性能优化

**前端 bundle 现状**：
- dist 2.8MB（gzip 后 ~900KB）
- element-plus 1.16MB 单独 chunk（已 manualChunks 切分但还可优化）
- index.js 99KB / index.css 385KB
- 多数 page JS 30-50KB

**可优化点**：
| 优化项 | 预计收益 | 工作量 |
|---|---|---|
| 路由懒加载 + 按 page 拆 chunk | FCP -30% | 0.5 天 |
| ECharts 按需引入（ECharts 全量 800KB+） | bundle -500KB | 0.5 天 |
| SCSS variables 拆包（按需注入） | 重复样式 -200KB | 0.3 天 |
| vite 压缩 gzip/brotli | 传输 -50% | 0.1 天 |
| 图片 lazy-load + CDN | 首屏 -200KB | 0.3 天 |
| **后端**：DB 查询 N+1 检测 | 查询 -40% | 0.5 天 |
| **后端**：Redis 缓存（hot data 列表 / 字典） | 接口 -60% | 0.5 天 |
| **后端**：慢查询日志 | 可观测 | 0.2 天 |

**总优化预计 1.5 天**

### 3. 权限细化

**现有资产**：
- 后端 admin 模块 24 个接口（depts/roles/permissions/users/dicts/audit-logs）✅
- User.data_scope 字段已存在（all/dept/dept_sub/self/custom 5 档）✅
- 前端 v-permission 工具：**无** ❌

**最大缺口**：5 业务 service 未应用 data_scope 过滤
- `contract/service.py` / `project/` / `expense/` / `receivable/` / `invoice_ocr/`
- 任何角色登入都看到全公司数据

**前端权限细化**：
- 4 详情页操作按钮（编辑/删除/审批）无 v-permission
- 5 列表操作列无角色判断

| 工作量 | 收益 |
|---|---|
| 后端 5 service 加 data_scope 过滤（SQL where + helper 函数） | 1 天 |
| 前端 v-permission 工具 + 4 详情页 + 5 列表应用 | 0.5 天 |

**总权限细化 1.5 天**

## 二、拍板候选

### 方案 A：3 段（C 方案延续）
- **R11A 性能优化** 1.5 天
- **R11B 权限细化** 1.5 天
- **R11C 真实集成切真** 0.5 天

总 3.5 天，每段独立汇报。

### 方案 B：2 段
- **R11A 性能 + 权限** 3 天
- **R11B 真实集成** 0.5 天

总 3.5 天，节奏紧凑。

### 方案 C：1 段
- 性能 + 权限 + 真实集成一起 5 天

总 5 天，但单次交付。

## 三、我的建议
**A 方案**（跟 R10 节奏一致）：
- 真实集成 0.5 天独立可等资质，**先做能做的（环境变量配置 + 文档）**
- 性能 / 权限可考虑并行（如用 mavis-team 协同）
- 总 3.5 天内交付

---

**R11 摸底稿** | 2026-06-15 | Mavis
