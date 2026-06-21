# 真实集成切真文档（R11C）

> 3 套真实集成（PaddleOCR / 诺诺 / 企业微信 SSO）的切真步骤、环境变量配置、资质清单

## 一、当前架构（已是切真友好）

3 套集成都实现了 **双模式**（real / mock）+ **自动 fallback**：
- 切真 = 改环境变量（**代码 0 改动**）
- mock fallback = 服务挂了不影响业务（**业务连续性**）
- 真实调用：自动 fallback mock（**永不挂**）

```
┌─────────────────────────────────────────────────┐
│              backend (FastAPI)                     │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐  │
│  │ ocr_client  │ │   nuonuo    │ │ wechat_work │  │
│  │ real→mock   │ │ real→mock   │ │ real→mock   │  │
│  └──────┬──────┘ └──────┬──────┘ └──────┬──────┘  │
└─────────┼───────────────┼───────────────┼──────────┘
          │               │               │
    ┌─────▼─────┐   ┌─────▼─────┐   ┌─────▼─────┐
    │ PaddleOCR │   │  诺诺开放  │   │  企业微信  │
    │  微服务   │   │   平台    │   │   SSO    │
    └───────────┘   └───────────┘   └───────────┘
```

每套集成有：
1. **配置文件**：`app/config.py` Settings 字段（pydantic-settings，env_prefix=SHUZHI_）
2. **客户端**：`app/integrations/{ocr_client,nuonuo,wechat_work}.py`（双模式 + fallback）
3. **健康检查**：每个 client 都有 `health_check()` 返回 `{status: real|mock|down}`
4. **环境变量**：`deploy/docker-compose.integration.yml` 注入 + backend Dockerfile 暴露

## 二、3 套集成切真步骤

### 集成 1：PaddleOCR 真实识别

#### A. 现状
- **代码状态**：`ocr_client.py` 完整实现真协议（POST {OCR_SERVICE_URL}/recognize，BACKEND.md §7.2）
- **当前状态**：`OCR_SERVICE_URL=http://localhost:8001` 默认值（在容器内 8001 端口无服务）→ `health: down`
- **自动 fallback**：连不上时回退 mock，**业务可用**

#### B. 切真步骤
1. **部署 PaddleOCR 微服务**（独立容器 / GPU 机器）
   - 推荐：`deploy/ocr-service/Dockerfile`（已有，git 仓库 `shuzhi-ocr-service`）
   - **GPU 推荐**（CPU 也跑得动但慢 5-10 倍）
   - 启动后暴露 8001 端口

2. **修改后端环境变量**（任一方式）
   - **方式 A**：`deploy/docker-compose.integration.yml`
     ```yaml
     backend:
       environment:
         OCR_MODE: real           # 启用真模式（默认 real，没配 URL 走 mock）
         OCR_SERVICE_URL: http://shuzhi-ocr-service:8001  # 容器内网
     ```
   - **方式 B**：直接 docker run
     ```bash
     docker run -d --name shuzhi-backend \
       -e SHUZHI_OCR_MODE=real \
       -e SHUZHI_OCR_SERVICE_URL=http://shuzhi-ocr-service:8001 \
       shuzhi-backend:latest
     ```

3. **验证**（后端自动）
   ```bash
   curl http://localhost:8000/health | python3 -m json.tool
   # 看 integrations.ocr.status:
   # - "ok" (real + 可达)
   # - "mock" (切 mock 自动 fallback)
   # - "down" (real 模式但服务不可达)
   ```

4. **E2E 测真接口**（用 E2E test-08）
   ```bash
   cd e2e && node test-08-paddleocr-real.js
   # 期望：识别出真实发票号 + 真实日期
   ```

#### C. 资质等待清单
| 项 | 状态 | 备注 |
|---|---|---|
| PaddleOCR 模型权重 | ✅ 开源 | 直接从 PaddlePaddle 官方下载 `ch_PP-OCRv4` |
| GPU 机器 | ⏳ 需申请 | 公司 GPU 资源池（1 张 A10/A100 就够） |
| OCR 微服务部署 | ⏳ 需运维 | 推荐 K8s 部署，独立扩缩容 |
| 票面样本（500+ 张） | ⏳ 需业务 | 收集真实发票做微调（可选） |

#### D. 监控指标（已有 prometheus 暴露）
```
shuzhi_business_ocr_total{status="success",mode="real"}    # 真实成功
shuzhi_business_ocr_total{status="failed",mode="real"}     # 真实失败
shuzhi_business_ocr_total{status="success",mode="real→mock_fallback"}  # 回退
```

### 集成 2：诺诺发票云真实查验

#### A. 现状
- **代码状态**：`nuonuo.py` 完整实现真协议（POST 诺诺开放平台，MD5 签名 + X-Nuonuo-Sign）
- **当前状态**：`NUONUO_API_KEY=""` 默认空 → 自动 mock（`status: "mock", mode: "mock"`）
- **自动 fallback**：连不上 / 协议错 / 签名失败 → 回退 mock

#### B. 切真步骤
1. **申请诺诺开放平台账号**
   - 网址：`https://open.nuonuocs.cn`
   - 注册企业开发者账号
   - 创建自用型应用
   - 拿到 3 个关键凭证：
     - `appKey`（应用 ID）
     - `appSecret`（应用密钥）
     - `accessToken`（访问令牌，通过管理后台生成）

2. **配置环境变量**
   ```bash
   SHUZHI_NUONUO_API_KEY=your_app_key_here
   SHUZHI_NUONUO_API_SECRET=your_app_secret_here
   SHUZHI_NUONUO_API_TOKEN=your_access_token_here
   SHUZHI_NUONUO_MODE=real                # 启用真模式（默认 real，无 key 自动 mock）
   SHUZHI_NUONUO_USE_SANDBOX=true         # 沙箱环境先用（生产再关）
   SHUZHI_NUONUO_API_URL=https://sandbox.nuonuocs.cn/open/v1/services  # 沙箱
   # 生产环境：
   # SHUZHI_NUONUO_API_URL=https://sdk.nuonuo.com/open/v1/services
   # SHUZHI_NUONUO_USE_SANDBOX=false
   ```

3. **诺诺测试用例**（5 档确定性）
   ```
   invoiceNo 末 4 位 mod 5:
   - 0, 1 → pass
   - 2 → risk (购方比对异常)
   - 3 → repeat (已报销过)
   - 4 → not_found
   ```
   用真实发票号验证（生产环境查国税总局数据库）

4. **E2E 测真接口**（test-09）
   ```bash
   cd e2e && node test-09-nuonuo-verify.js
   ```

#### C. 资质等待清单
| 项 | 状态 | 备注 |
|---|---|---|
| 诺诺开放平台账号 | ⏳ 需申请 | 企业开发者注册，需营业执照 |
| 自用型应用 | ⏳ 需审批 | 创建应用，**1-3 工作日审核** |
| 沙箱环境测试 | ✅ 可用 | 拿到 key 即可在沙箱跑 |
| 生产环境切换 | ⏳ 需申请 | 需通过诺诺商务对接，签合同 |
| 调用配额 | ⏳ 看合同 | 默认 100 次/天，生产需扩容 |

#### D. 监控指标
```
shuzhi_business_verify_total{result="pass",mode="real"}     # 真实通过
shuzhi_business_verify_total{result="risk",mode="real"}     # 真实风险
shuzhi_business_verify_total{result="not_found",mode="real"} # 真不存在
shuzhi_business_verify_total{result="pass",mode="real→mock_fallback"}  # 回退
```

### 集成 3：企业微信 SSO

#### A. 现状
- **代码状态**：`wechat_work.py` 完整实现 OAuth 2.0（corpid/secret + access_token 缓存 7200s）
- **当前状态**：`WECHAT_WORK_CORP_ID=""` 默认空 → 自动 mock
- **当前 mock 用户**：扫码后返回 `mock_user_by_state` 的固定数据

#### B. 切真步骤
1. **企业微信管理后台配置**
   - 登录 `https://work.weixin.qq.com/wework_admin/`
   - 我的企业 → 记下 **CorpID**
   - 应用管理 → 创建自建应用 → 记下 **AgentID** + **Secret**
   - 自建应用 → 设置 → 授权回调域：填部署域名

2. **修改 OAuth 回调地址**
   ```bash
   SHUZHI_WECHAT_WORK_CORP_ID=ww1234567890abcdef
   SHUZHI_WECHAT_WORK_CORP_SECRET=your_app_secret_here
   SHUZHI_WECHAT_WORK_AGENT_ID=1000002
   SHUZHI_WECHAT_WORK_REDIRECT_URI=https://yourdomain.com/api/v1/auth/sso/wechat-work/callback
   SHUZHI_WECHAT_WORK_MODE=real
   ```

3. **前端 SSO 入口**（已就位）
   - `/login` 页 → "💬 企业微信" 按钮 → 跳转到 `generate_qrcode_url()` 生成的二维码 URL
   - 用户扫码 → 企业微信 → 跳回 `redirect_uri?code=xxx&state=xxx`
   - 后端 `/api/v1/auth/sso/wechat-work/callback` 用 code 换 userId → 自动登录

4. **E2E 测真 SSO**（test-10）
   ```bash
   cd e2e && node test-10-wechat-work-sso.js
   ```

#### C. 资质等待清单
| 项 | 状态 | 备注 |
|---|---|---|
| 企业微信企业账号 | ⏳ 需开通 | 需企业认证（营业执照 + 法人微信） |
| CorpID | ⏳ 需申请 | 创建企业即可获得 |
| 自建应用 | ⏳ 需审批 | 创建应用免审，但**配置可见范围需成员授权** |
| OAuth 回调域 | ⏳ 需配置 | 必须是 HTTPS 公网域名 |
| 域名 SSL 证书 | ⏳ 需申请 | Let's Encrypt / 公司 CA |
| 公网 IP / 域名 | ⏳ 需申请 | 公司 IT 申请（不能 localhost） |

#### D. 监控指标
无（SSO 走前端 UI，后端只接 callback，暂未埋 prom）
可加：`shuzhi_sso_total{provider="wechat-work",result="success"}`

## 三、资质等待清单汇总

| 集成 | 必须资质 | 优先级 | 预估时间 | 阻塞点 |
|---|---|---|---|---|
| **PaddleOCR** | GPU 机器 | P1 | 1 周 | GPU 资源池申请 |
| **PaddleOCR** | 票面样本（可选） | P3 | 2 周 | 业务部门收集 |
| **诺诺** | 开放平台账号 | P1 | 1-3 工作日 | 企业营业执照 |
| **诺诺** | 自用型应用 | P1 | 1-3 工作日 | 应用审核 |
| **诺诺** | 生产环境配额 | P2 | 2-4 周 | 诺诺商务对接 |
| **企业微信** | 企业微信企业认证 | P1 | 3-5 工作日 | 营业执照 + 法人微信 |
| **企业微信** | 自建应用 | P1 | 即时 | 部门成员授权 |
| **企业微信** | 公网域名 + SSL | **P0** | 1-2 周 | IT 部门申请 |
| **企业微信** | 回调域配置 | P1 | 30 分钟 | 后端部署后填 |

**最快可切真的**：诺诺沙箱（1 周内）  
**最难可切真的**：企业微信（公网域名是硬门槛，1-2 周）  
**最易可切真的**：PaddleOCR（只要 GPU 机器，1 周）

## 四、端到端切真流程（资质到位后）

### Step 1：环境变量配置
编辑 `deploy/docker-compose.integration.yml`：
```yaml
backend:
  environment:
    # === 真实集成（资质到位后启用）===
    SHUZHI_OCR_MODE: real
    SHUZHI_OCR_SERVICE_URL: http://shuzhi-ocr-service:8001
    
    SHUZHI_NUONUO_API_KEY: ${NUONUO_API_KEY}
    SHUZHI_NUONUO_API_SECRET: ${NUONUO_API_SECRET}
    SHUZHI_NUONUO_API_TOKEN: ${NUONUO_API_TOKEN}
    SHUZHI_NUONUO_MODE: real
    SHUZHI_NUONUO_USE_SANDBOX: false  # 生产
    
    SHUZHI_WECHAT_WORK_CORP_ID: ${WECHAT_CORP_ID}
    SHUZHI_WECHAT_WORK_CORP_SECRET: ${WECHAT_SECRET}
    SHUZHI_WECHAT_WORK_AGENT_ID: ${WECHAT_AGENT_ID}
    SHUZHI_WECHAT_WORK_REDIRECT_URI: https://${DOMAIN}/api/v1/auth/sso/wechat-work/callback
    SHUZHI_WECHAT_WORK_MODE: real
```

`deploy/.env.production`：
```bash
# 真实集成凭证（不进 git，运维保管）
NUONUO_API_KEY=your_real_key
NUONUO_API_SECRET=your_real_secret
NUONUO_API_TOKEN=your_real_token

WECHAT_CORP_ID=ww1234567890abcdef
WECHAT_SECRET=your_real_secret
WECHAT_AGENT_ID=1000002

DOMAIN=shuzhi.yourcompany.com
JWT_SECRET_KEY=$(openssl rand -hex 32)  # 强随机
```

### Step 2：PaddleOCR 部署
```bash
# 部署 OCR 微服务（独立 GPU 节点）
cd deploy/ocr-service
docker build -t shuzhi-ocr-service:latest .

# 启动（需要 GPU + 8001 端口）
docker run -d --name shuzhi-ocr-service \
  -p 8001:8001 \
  --gpus all \
  --network deploy_shuzhi-net \
  --restart unless-stopped \
  shuzhi-ocr-service:latest
```

### Step 3：后端三连
```bash
cd /path/to/shuzhi-new
docker compose -f deploy/docker-compose.integration.yml up -d backend
sleep 7
curl http://localhost:8000/health
# 期望 integrations.ocr.status: "ok"
# 期望 integrations.nuonuo.status: "real"
```

### Step 4：前端三连（如果有 dist 改动）
```bash
cd frontend
docker build -t shuzhi-frontend:latest -f deploy/frontend/Dockerfile .
docker stop shuzhi-frontend && docker rm shuzhi-frontend
docker run -d --name shuzhi-frontend \
  -p 8088:80 --network deploy_shuzhi-net \
  shuzhi-frontend:latest
```

### Step 5：端到端验证
```bash
# 1. OCR 真接口
cd e2e && node test-08-paddleocr-real.js
# 期望：✅ 真实发票号 + 真实日期

# 2. 诺诺真接口
node test-09-nuonuo-verify.js
# 期望：✅ 5 个 bucket 真实验真结果

# 3. 企微真接口
node test-10-wechat-work-sso.js
# 期望：✅ 真实 OAuth 流程

# 4. 手动验证（打开浏览器）
open https://shuzhi.yourcompany.com/login
# 期望：
#   - OCR: 上传真实发票，识别出真实字段
#   - 诺诺: 查验真实发票，返回真实结果
#   - 企微: 点"💬 企业微信"按钮，跳出真二维码
```

### Step 6：监控告警（已就位）
- Prometheus 抓 `/metrics` 端点
- 关键告警：
  - `rate(shuzhi_business_ocr_total{mode="real→mock_fallback"}[5m]) > 0` → OCR 服务挂了
  - `rate(shuzhi_business_verify_total{mode="real→mock_fallback"}[5m]) > 0` → 诺诺挂了
  - Grafana Dashboard：R7 已有监控大盘

## 五、当前状态（2026-06-15）

| 集成 | 代码 | 环境变量 | 真服务 | 资质 | 阻塞 |
|---|---|---|---|---|---|
| PaddleOCR | ✅ real 模式完整 | ⏳ 默认 mock | ⏳ 未部署 | ⏳ GPU 待申请 | 1 周 |
| 诺诺 | ✅ real 模式完整 | ⏳ 默认 mock | ⏳ 未申请 | ⏳ 待申请 | 1-3 工作日 |
| 企业微信 | ✅ real 模式完整 | ⏳ 默认 mock | N/A | ⏳ 公网域名 + SSL | 1-2 周 |

**全部代码 ready，只等资质到位。**

## 六、降级策略

切真过程中可能遇到问题，按以下顺序降级：

```
真服务挂了 → 自动回退 mock（业务不停）
            ↓
        监控告警
            ↓
    运维介入排查
            ↓
 修好后自动切回真（无需重启，因为 connect 实时检测）
```

**前端 /health 端点** 显示每个集成的 `status: real | mock | down`：
```bash
curl http://localhost:8000/health
{
  "integrations": {
    "ocr": {"status": "ok", "data": {...}},      # real 模式 + 可达
    "nuonuo": {"status": "real", "mode": "real"}, # real 模式
    "wechat_work": {"status": "real"}             # OAuth 配好 corp_id
  }
}
```

**降级原则**：
1. **永远不挂**：任何异常自动 mock，**业务连续性第一**
2. **监控先行**：fallback 触发即告警，运维 1 小时内介入
3. **降级开关**：环境变量 `_MODE=mock` 立即切 mock（紧急情况）

---

**文档版本**：R11C v1.0 | 2026-06-15
**状态**：3 套集成代码 + 切真文档完成，等资质到位执行
