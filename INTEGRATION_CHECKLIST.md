# 真实集成资质等待清单（R11C）

> 3 套集成（OCR / 诺诺 / 企业微信 SSO）切真所需的资质 / 账号 / 审批项 + 预估时间

## 优先级：P0 = 硬阻塞（必须做才能切真），P1 = 强烈建议，P2 = 可选

---

## 集成 1：PaddleOCR 真实识别

### 资质清单
| 项 | 优先级 | 预估时间 | 负责人 | 当前状态 |
|---|---|---|---|---|
| GPU 机器（A10/A100 1 张） | **P0** | 1 周 | 运维 / IT | ⏳ 待申请 |
| 容器化部署（推荐 K8s） | P1 | 1-2 天 | 运维 | ⏳ 已有 Dockerfile，待部署 |
| 真实发票样本（500+ 张，可选） | P2 | 2 周 | 业务部 | ⏳ 不强制 |
| 域名 / 公网 IP（用于 OCR 服务调用） | P1 | 已有 | IT | ✅ |

### 切真 checklist
- [ ] 申请 GPU 机器（公司内部资源池 / 阿里云 GN5 / 腾讯云 GN6）
- [ ] 部署 PaddleOCR 微服务（`deploy/ocr-service/Dockerfile`）
- [ ] 验证 OCR 服务可达 `curl http://ocr-service:8001/health`
- [ ] 配置后端环境变量 `SHUZHI_OCR_MODE=real` + `SHUZHI_OCR_SERVICE_URL=...`
- [ ] 重启 backend，验证 `/health` 返回 `integrations.ocr.status: ok`
- [ ] 跑 E2E `test-08-paddleocr-real.js` 验证真实识别
- [ ] 配置 Prometheus 告警：`rate(shuzhi_business_ocr_total{mode="real→mock_fallback"}[5m]) > 0`

### 预估总时长
- **最快**：1 周（GPU 资源池直接批）
- **最慢**：3 周（含样本收集 + 模型微调）

---

## 集成 2：诺诺发票云真实查验

### 资质清单
| 项 | 优先级 | 预估时间 | 负责人 | 当前状态 |
|---|---|---|---|---|
| 诺诺开放平台账号 | **P0** | 1-3 工作日 | 业务部 / 财务 | ⏳ 待申请 |
| 企业营业执照 | **P0** | 已有 | 行政 | ✅ |
| 自用型应用审批 | **P0** | 1-3 工作日 | 业务部 | ⏳ 待申请 |
| 沙箱环境测试（拿到 key 即可用） | P1 | 即时 | 开发 | ✅ |
| 生产环境切换（含合同/配额） | P2 | 2-4 周 | 商务 | ⏳ 待对接 |
| 调用配额（默认 100 次/天） | P2 | 签合同时定 | 商务 | ⏳ |
| 真实发票号（用真号验真） | P1 | 即时 | 业务 | ✅ |

### 切真 checklist
- [ ] 注册诺诺开放平台：`https://open.nuonuocs.cn`（需企业营业执照 + 法人手机）
- [ ] 创建自用型应用（"应用管理" → "创建应用"）
- [ ] 拿到 3 个凭证：
  - `appKey`（应用 ID）
  - `appSecret`（应用密钥）
  - `accessToken`（管理后台生成的访问令牌）
- [ ] 沙箱环境测试（默认 `SHUZHI_NUONUO_USE_SANDBOX=true`）
- [ ] 配置环境变量（`deploy/scripts/cutover-real-integrations.sh nuonuo`）
- [ ] 跑 E2E `test-09-nuonuo-verify.js` 验证 5 档验真
- [ ] （可选）申请生产环境配额 + 签商务合同

### 预估总时长
- **最快**：1 周（沙箱 + 自用应用）
- **最慢**：4 周（含生产合同）

---

## 集成 3：企业微信 SSO

### 资质清单
| 项 | 优先级 | 预估时间 | 负责人 | 当前状态 |
|---|---|---|---|---|
| 企业微信企业账号 + 认证 | **P0** | 3-5 工作日 | 行政 / IT | ⏳ 待申请 |
| 企业营业执照 | **P0** | 已有 | 行政 | ✅ |
| 法人微信扫码 | **P0** | 已有 | 法人 | ✅ |
| CorpID | **P0** | 申请企业即得 | 行政 | ⏳ |
| 自建应用（AgentID + Secret） | **P0** | 即时（成员授权需时） | IT | ⏳ |
| **公网域名 + SSL 证书** | **P0 硬阻塞** | **1-2 周** | **IT 部门** | ⏳ 待申请 |
| 回调域配置（OAuth） | **P0** | 30 分钟 | IT | ⏳ 待配 |
| 自建应用可见范围（成员授权） | P1 | 1-3 天 | 部门主管 | ⏳ |

### 切真 checklist
- [ ] 申请企业微信企业认证（营业执照 + 法人微信）
- [ ] 我的企业 → 记下 CorpID
- [ ] 应用管理 → 创建自建应用 → 记下 AgentID + Secret
- [ ] 自建应用 → 设置 → **OAuth 授权回调域** 填部署域名
- [ ] IT 部门申请公网域名（如 `shuzhi.yourcompany.com`）
- [ ] IT 部门申请 SSL 证书（Let's Encrypt / 公司 CA）
- [ ] DNS 解析 + Nginx 反代 + HTTPS 配置
- [ ] 配置环境变量（`deploy/scripts/cutover-real-integrations.sh wechat-work`）
- [ ] 前端部署到公网（用户能访问）
- [ ] 后端部署到公网（OAuth 回调能通）
- [ ] 跑 E2E `test-10-wechat-work-sso.js`
- [ ] 手动验证：扫码真二维码 → 真登录成功

### 预估总时长
- **最快**：2 周（域名 + SSL 走加急 + 全部自助）
- **最慢**：4 周（含企业微信企业认证 3-5 工作日）

---

## 资质等待时长汇总

```
                          P0 阻塞项                 总时长
PaddleOCR:    [1 周] GPU 机器                   1-3 周
诺诺:         [1-3 天] 开放平台 + 应用           1-4 周
企业微信:     [3-5 天] 企业认证 + 1-2 周域名    2-4 周
                                              ─────────
                                              总: 2-4 周
```

**最快可切真顺序**（按阻塞时长）：
1. **诺诺**（沙箱 + 自用应用 1 周内搞定）
2. **PaddleOCR**（GPU 1 周）
3. **企业微信**（公网域名 1-2 周）

**推荐优先级**：诺诺 > PaddleOCR > 企业微信

---

## 资质申请操作步骤（详细版）

### 诺诺（最简单）
1. 打开 `https://open.nuonuocs.cn`
2. 点"立即注册" → 选择"企业开发者"
3. 填写企业信息（营业执照号 + 法人姓名 + 法人手机号）
4. 法人手机扫码验证
5. 注册成功 → 进入"应用管理" → "创建应用"
6. 选择"自用型应用"（内部用，免费）
7. 填写应用名（"数智化管理系统"）+ 应用简介
8. 提交 → 1-3 工作日审核通过
9. 审核通过后 → "应用详情" 看到：
   - `appKey` = 应用 ID
   - `appSecret` = 应用密钥
10. "获取 accessToken" 按钮 → 生成 token（首次）
11. 把 3 个凭证配置到后端

### PaddleOCR（需运维）
1. 提交工单：公司资源池 / 阿里云 / 腾讯云申请 GPU 机器
   - 型号建议：A10 (24G) / A100 (40G+)
   - 系统：Ubuntu 22.04 + Docker
   - 网络：能访问外网（pip install paddlepaddle）
2. 拿到机器后：SSH 登录
3. `git clone <shuzhi-repo>` + `cd deploy/ocr-service`
4. `docker build -t shuzhi-ocr-service:latest .`
5. `docker run -d --name shuzhi-ocr-service -p 8001:8001 --gpus all shuzhi-ocr-service:latest`
6. 验证：`curl http://localhost:8001/health` 应返回 200

### 企业微信（最复杂）
1. 法人微信扫 `https://work.weixin.qq.com/wework_admin/` 登录
2. 第一次登录需要"企业注册"：
   - 企业名称（必须和营业执照一致）
   - 营业执照照片
   - 法人姓名 + 身份证号
   - 法人微信扫码验证
3. 提交 → 1-3 工作日通过认证
4. 认证通过后 → 我的企业 → 记下 **CorpID**（"企业 ID"）
5. 应用管理 → 创建应用：
   - 应用 logo（可后补）
   - 应用名称（"数智化管理系统"）
   - 应用介绍
   - 可见范围：选部门
6. 创建成功后 → 应用详情 → 记下 **AgentID** + **Secret**
7. **关键步骤**：应用详情 → 设置 → "Web 授权" → "OAuth 2.0 授权回调域"：
   - 填：`shuzhi.yourcompany.com`（**不带 https://，不带路径**）
   - 填后等 5-10 分钟生效
8. 部门主管需要把应用"可见范围"加部门成员
9. IT 申请公网域名（`shuzhi.yourcompany.com`）
10. IT 申请 SSL 证书（Let's Encrypt 免费 / 公司 CA 付费）
11. 配置 DNS A 记录 + Nginx 反代 + HTTPS
12. 后端部署到能访问公网的服务器
13. 前端部署 + 配置 `VITE_API_BASE_URL=https://shuzhi.yourcompany.com/api`
14. 配置 SSO 入口：`SHUZHI_WECHAT_WORK_REDIRECT_URI=https://shuzhi.yourcompany.com/api/v1/auth/sso/wechat-work/callback`

---

## 风险与回滚

| 集成 | 切真风险 | 自动回退 | 手动回滚 |
|---|---|---|---|
| PaddleOCR | GPU 机器挂 / 模型推理慢 | mock（业务不停） | `SHUZHI_OCR_MODE=mock` 重启 |
| 诺诺 | 签名错 / 配额耗尽 / 网络断 | mock（业务不停） | `SHUZHI_NUONUO_MODE=mock` 重启 |
| 企业微信 | corpsecret 改 / 回调域失效 | OAuth 失败，前端跳"登录失败" | `SHUZHI_WECHAT_WORK_MODE=mock` 重启 |

**回滚时间**：< 5 分钟（改 env + 重启）

---

## 切真期间的业务影响

| 切真动作 | 业务影响 |
|---|---|
| 诺诺切真 | 验真结果从"mock 5 档"变成"真实国税总局查询"（准确性 + 真实性 ↑↑） |
| PaddleOCR 切真 | OCR 识别从"mock 假数据"变成"真实 AI 识别"（准确率 70% → 95%+） |
| 企业微信切真 | 用户可用企业微信扫码登录（不用输密码） |

**不会有任何业务中断**（fallback 机制保证）。

---

**清单版本**：R11C v1.0 | 2026-06-15
**总览**：3 套集成代码 + 切真文档 + 切真脚本 + 资质清单全部完成
**状态**：等业务/IT 部门申请资质
