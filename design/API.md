# 数智化管理系统 · 前后端联调 API 文档

> **目标读者**：前端开发 / 后端开发 / QA / 产品经理  
> **版本**：v1.0 · 2026-06-12  
> **基础规范**：所有接口使用 `POST` + JSON Body；统一响应包装；鉴权采用 JWT Token

---

## 目录

- [通用规范](#通用规范)
- [认证模块](#认证模块)
- [Dashboard 总览](#dashboard-总览)
- [发票识别](#发票识别)
- [发票模板](#发票模板)
- [销售费用](#销售费用)
- [项目管理](#项目管理)
- [合同管理](#合同管理)
- [回款管理](#回款管理)
- [公共数据](#公共数据)
- [错误码表](#错误码表)
- [前端字段映射表](#前端字段映射表)

---

## 通用规范

### Base URL
```
生产：https://api.shuzhi.example.com/v1
测试：https://api-test.shuzhi.example.com/v1
```

### 请求格式
- Method：`POST`（所有接口）
- Headers：
  ```
  Content-Type: application/json
  Authorization: Bearer <token>
  X-Tenant-Id: <租户ID>      // 多租户场景
  X-Request-Id: <trace-id>    // 前端生成 UUID，用于链路追踪
  ```

### 统一响应包装
```json
{
  "code": 0,
  "message": "success",
  "data": { /* 业务数据 */ },
  "traceId": "abc-123-xyz"
}
```

| code | 含义 |
|------|------|
| 0 | 成功 |
| 1001 | 未登录 / Token 失效 |
| 1003 | 无权限访问 |
| 2001 | 参数错误 |
| 2004 | 资源不存在 |
| 2009 | 数据冲突 |
| 5000 | 服务器内部错误 |
| 5001 | 第三方服务异常（如 OCR、实名认证） |

### 分页约定
请求：
```json
{ "page": 1, "pageSize": 20, "keyword": "", "filters": {} }
```
响应：
```json
{
  "data": {
    "list": [ ... ],
    "total": 128,
    "page": 1,
    "pageSize": 20
  }
}
```

### 时间格式
- 入参：`YYYY-MM-DD` 或 `YYYY-MM-DD HH:mm:ss`
- 返回：统一 `YYYY-MM-DD HH:mm:ss`（带时区 Asia/Shanghai）
- 时间戳：毫秒

### 金额单位
- 内部存储与计算：**分**（int，避免浮点精度问题）
- 返回前端时，统一转 **元**（保留 2 位小数）
- 前端展示时，根据场景使用 `¥ 1,234.56` 格式

---

## 实时通信约定（SSE）

> 长任务、状态实时变化、协同通知统一使用 **Server-Sent Events (SSE)**，**禁止前端轮询**。

### 适用场景
| 场景 | 端点 | 备注 |
|------|------|------|
| 批量 OCR 识别进度 | `/sse/invoice/batch/:batchId` | 替代 `/invoices/ocr/batch/status` 轮询 |
| 批量查验真伪进度 | `/sse/verify/batch/:batchId` | 替代 `/invoices/verify/batch` 轮询 |
| 审批流状态变化 | `/sse/contract/:contractId/approval` | 合同/费用等审批节点推送 |
| 系统通知 | `/sse/notify` | 全局消息推送（待办、@提及等） |
| 数据看板实时刷新 | `/sse/dashboard/realtime` | 财务总览实时数字（可选） |

### 端点格式
```
GET /sse/<module>/<resource>
Headers:
  Accept: text/event-stream
  Authorization: Bearer <token>
  Last-Event-ID: <可选，用于断线重连>
```

### 事件类型
| 事件名 | 说明 | 数据结构 |
|--------|------|---------|
| `connected` | 连接成功 | `{ "connectionId": "...", "serverTime": "..." }` |
| `progress` | 进度更新 | `{ "fileId": "...", "status": "...", "progress": 0.5 }` |
| `item_done` | 单条完成 | `{ "fileId": "...", "invoiceId": "...", "confidence": 0.96 }` |
| `summary` | 汇总更新 | `{ "summary": { "total": 18, "success": 12, "warning": 2, "failed": 1 } }` |
| `completed` | 全部完成 | `{ "batchId": "...", "finishedAt": "..." }` |
| `error` | 错误 | `{ "code": 5001, "message": "OCR 服务超时" }` |
| `keepalive` | 心跳（30s 一次）| `{}` |

### 数据格式
每条消息：
```
event: progress
id: 12345
data: {"fileId":"F-001","status":"recognizing","progress":0.5}

```

### 前端使用示例（原生 EventSource）
```javascript
const evtSource = new EventSource(
  '/sse/invoice/batch/BATCH-2026-0612-001',
  { withCredentials: true }
);

evtSource.addEventListener('progress', (e) => {
  const data = JSON.parse(e.data);
  updateProgressBar(data.fileId, data.progress, data.status);
});

evtSource.addEventListener('item_done', (e) => {
  const data = JSON.parse(e.data);
  markItemSuccess(data.fileId, data.invoiceId, data.confidence);
});

evtSource.addEventListener('completed', (e) => {
  // 全部完成，关闭连接
  evtSource.close();
  showToast('批量识别完成', 'success');
});

evtSource.addEventListener('error', (e) => {
  // 自动重连机制：EventSource 内置
  if (evtSource.readyState === EventSource.CLOSED) {
    showToast('连接已断开', 'danger');
  }
});
```

### 鉴权
- SSE URL 通过 `?token=xxx` 传 token（因为 EventSource 不支持自定义 header）
- 或使用 cookie session
- Token 过期时，服务端先发 `error` 事件（code=1001）再关闭，前端收到后跳登录

### 断线重连
- EventSource 内置重连机制（默认 3s 后重试）
- 客户端传 `Last-Event-ID` header，服务端从该 ID 之后重发（避免漏数据）
- 重试上限 5 次，超过后提示用户刷新

### 兼容性
- 浏览器：Chrome/Firefox/Safari/Edge 全支持
- IE：不支持（但本系统不要求 IE）
- 移动端 WebView：iOS 14+ / Android Chrome 7+ 支持
- 代理层：注意 nginx 关闭 `proxy_buffering`、设置 `X-Accel-Buffering: no`

### nginx 配置示例
```nginx
location /sse/ {
    proxy_pass http://backend;
    proxy_http_version 1.1;
    proxy_set_header Connection '';
    proxy_buffering off;          # 关键
    proxy_cache off;              # 关键
    proxy_read_timeout 86400s;    # 长连接
    add_header X-Accel-Buffering no;  # 关键
}
```

---

## 认证模块

### POST /api/v1/auth/login
**说明**：账号密码登录

请求：
```json
{
  "account": "zhangming@shuzhi.com",
  "password": "encrypted_password",
  "rememberMe": true
}
```
响应：
```json
{
  "code": 0,
  "data": {
    "token": "eyJhbGciOi...",
    "refreshToken": "rt_xxxx",
    "expiresIn": 7200,
    "userInfo": {
      "userId": "U-2026-001",
      "name": "张明",
      "avatar": "https://cdn.shuzhi.com/avatar/u15.jpg",
      "role": "财务总监",
      "department": "财务部",
      "permissions": ["invoice:read", "invoice:write", "contract:approve"]
    }
  }
}
```

### POST /api/v1/auth/sso/qrcode/generate
**说明**：生成 SSO 扫码登录二维码（微信/钉钉/飞书）

请求：
```json
{ "provider": "wechat" }  // wechat | dingtalk | feishu
```
响应：
```json
{
  "data": {
    "qrToken": "qr_abc123",
    "qrImageUrl": "data:image/png;base64,...",
    "expiresIn": 120,
    "pollUrl": "/auth/sso/qrcode/check?token=qr_abc123"
  }
}
```

### POST /api/v1/auth/sso/qrcode/check
**说明**：前端轮询扫码状态

请求：
```json
{ "qrToken": "qr_abc123" }
```
响应（待扫码）：
```json
{ "code": 0, "data": { "status": "waiting" } }
```
响应（已确认）：
```json
{
  "code": 0,
  "data": {
    "status": "confirmed",
    "token": "eyJhbGciOi...",
    "userInfo": { ... }
  }
}
```

### POST /api/v1/auth/password/reset/request
**说明**：忘记密码 - 发送验证码

请求：
```json
{ "account": "zhangming@shuzhi.com", "verifyType": "email" }
```

### POST /api/v1/auth/password/reset/confirm
请求：
```json
{
  "account": "zhangming@shuzhi.com",
  "verifyCode": "836542",
  "newPassword": "encrypted_new_pwd"
}
```

### POST /api/v1/auth/logout
请求：`{}`

---

## Dashboard 总览

### POST /api/v1/dashboard/summary
**说明**：首页数据汇总

响应：
```json
{
  "data": {
    "greeting": { "name": "张明", "time": "afternoon" },
    "quarterRemainingDays": 19,
    "moduleStats": [
      { "module": "invoice_ocr",    "name": "发票识别", "value": 328,  "unit": "张",  "icon": "▤", "color": "#4F6BFF" },
      { "module": "invoice_tpl",    "name": "发票模板", "value": 12,   "unit": "个",  "icon": "▣", "color": "#06B6D4" },
      { "module": "sales_expense",  "name": "销售费用", "value": 86.5, "unit": "万",  "icon": "◈", "color": "#10B981" },
      { "module": "project",        "name": "项目管理", "value": 23,   "unit": "个",  "icon": "▥", "color": "#F59E0B" },
      { "module": "contract",       "name": "合同管理", "value": 47,   "unit": "份",  "icon": "▦", "color": "#EC4899" },
      { "module": "receivable",     "name": "回款管理", "value": 142,  "unit": "万",  "icon": "▩", "color": "#8B5CF6" }
    ],
    "kpi": [
      { "key": "monthRevenue",    "label": "本月收入",   "value": 2864000, "unit": "元",   "delta": 12.4,  "deltaType": "up" },
      { "key": "pendingReceivable","label": "待回款",   "value": 1423000, "unit": "元",   "extra": "23 笔 · 6 笔即将逾期" },
      { "key": "activeProjects",  "label": "在建项目",   "value": 23,      "unit": "个",  "delta": 3,     "deltaType": "up" },
      { "key": "invoicePending",  "label": "发票待核验", "value": 6,       "unit": "张",  "delta": -2,    "deltaType": "down" }
    ],
    "trendChart": {
      "period": "7d",
      "labels": ["06-06", "06-07", "06-08", "06-09", "06-10", "06-11", "06-12"],
      "series": [
        { "name": "收入", "color": "#4F6BFF", "data": [220000, 280000, 320000, 295000, 360000, 410000, 386000] },
        { "name": "支出", "color": "#7C3AED", "data": [180000, 195000, 210000, 200000, 220000, 215000, 184000] }
      ]
    },
    "todos": [
      { "type": "warning", "title": "6 张发票待人工核验", "meta": "OCR 置信度低于 90% · 1 小时前", "link": "/invoice-ocr?status=pending" },
      { "type": "normal",  "title": "3 份合同待法务审批", "meta": "HT-2026-029/030/031", "link": "/contract?status=approving" },
      { "type": "danger",  "title": "2 笔回款即将逾期",   "meta": "万象科技 ¥ 28,000 · 北辰集团 ¥ 86,500", "link": "/receivable?status=overdue" }
    ],
    "teamMembers": [
      { "userId": "U-001", "name": "张明",   "role": "财务总监", "avatar": "...", "online": true },
      { "userId": "U-002", "name": "王芳",   "role": "财务专员", "avatar": "...", "online": true },
      { "userId": "U-003", "name": "李明",   "role": "法务主管", "avatar": "...", "online": true },
      { "userId": "U-004", "name": "陈思琪", "role": "项目经理", "avatar": "...", "online": true },
      { "userId": "U-005", "name": "刘洋",   "role": "销售经理", "avatar": "...", "online": false }
    ]
  }
}
```

### POST /api/v1/dashboard/activities
**说明**：最近活动动态

请求：
```json
{ "page": 1, "pageSize": 10 }
```
响应：
```json
{
  "data": {
    "list": [
      {
        "id": "ACT-2026-001",
        "type": "invoice_upload",
        "icon": "▤",
        "color": "#4F6BFF",
        "title": "王芳 上传了 3 张发票，OCR 自动识别完成",
        "module": "发票识别",
        "operator": "王芳",
        "createdAt": "2026-06-12 21:24"
      }
    ]
  }
}
```

---

## 发票识别

### POST /api/v1/invoice/ocr/upload
**说明**：上传发票图片/PDF 进行 OCR 识别

请求（multipart/form-data）：
```
file: <binary>
```

响应：
```json
{
  "data": {
    "invoiceId": "INV-2026-0612-001",
    "ocrStatus": "success",
    "confidence": 0.968,
    "fields": {
      "invoiceType": "增值税电子普通发票",
      "invoiceCode": "011002600611",
      "invoiceNo": "25113300000012345678",
      "issueDate": "2026-06-08",
      "sellerName": "上海数智信息技术有限公司",
      "sellerTaxNo": "91310000MA1FL3X9G",
      "buyerName": "万象科技有限公司",
      "buyerTaxNo": "91310000MA1FL01X9G",
      "totalAmount": 28000.00,
      "totalAmountCn": "贰万捌仟元整",
      "taxRate": 0.06,
      "taxAmount": 1584.91,
      "items": [
        { "name": "*软件服务*技术服务费", "spec": "", "qty": 1, "unitPrice": 26415.09, "amount": 26415.09, "taxRate": 0.06, "taxAmount": 1584.91 }
      ]
    },
    "fileUrl": "https://cdn.shuzhi.com/invoice/xxx.pdf",
    "verifyStatus": "pending",   // pending | verified | rejected
    "verifyResult": {
      "verified": false,
      "fromTaxBureau": true,
      "verifiedAt": "2026-06-12 09:24"
    }
  }
}
```

### POST /api/v1/invoice/ocr/list
**说明**：识别记录列表

请求：
```json
{
  "page": 1,
  "pageSize": 20,
  "keyword": "",
  "filters": {
    "type": "电子普通发票",
    "status": "pending",
    "dateRange": ["2026-06-01", "2026-06-12"]
  }
}
```

### POST /api/v1/invoice/ocr/detail
**说明**：发票详情

请求：
```json
{ "invoiceId": "INV-2026-0612-001" }
```

### POST /api/v1/invoice/ocr/update
**说明**：编辑/核验发票

请求：
```json
{
  "invoiceId": "INV-2026-0612-001",
  "fields": { ... },
  "expenseInfo": {
    "contractId": "HT-2026-028",
    "projectId": "PRJ-2026-018",
    "expenseType": "软件服务费",
    "costCenter": "CC-2026-008",
    "reimburserId": "U-004",
    "remark": "第二季度服务费尾款"
  }
}
```

### POST /api/v1/invoice/ocr/submit
**说明**：提交入账（写入财务系统）

请求：
```json
{ "invoiceId": "INV-2026-0612-001" }
```

### POST /api/v1/invoice/ocr/recheck
**说明**：重新识别（针对一张已识别发票）

请求：
```json
{ "invoiceId": "INV-2026-0612-001" }
```

### POST /api/v1/invoice/ocr/batch/upload
**说明**：批量上传（支持文件夹/多文件）

请求（multipart/form-data）：
```
files[]: <binary1>
files[]: <binary2>
templateId: "TPL-TR-2026-001"   // 可选，应用识别模板
```

响应：
```json
{
  "data": {
    "batchId": "BATCH-2026-0612-001",
    "total": 18,
    "items": [
      {
        "fileId": "F-2026-001",
        "filename": "invoice_001.pdf",
        "size": 238000,
        "status": "queued",        // queued | uploading | recognizing | success | warning | failed
        "invoiceId": "INV-2026-0612-001"  // 仅识别成功后返回
      }
    ]
  }
}
```

### POST /api/v1/invoice/ocr/batch/status
**说明**：查询批量任务进度（建议使用 SSE，本接口仅作兼容保留）

请求：
```json
{ "batchId": "BATCH-2026-0612-001" }
```

响应：
```json
{
  "data": {
    "batchId": "BATCH-2026-0612-001",
    "summary": {
      "total": 18,
      "uploading": 1,
      "recognizing": 2,
      "success": 12,
      "warning": 2,        // 需人工核验
      "failed": 1
    },
    "items": [
      {
        "fileId": "F-2026-001",
        "filename": "invoice_001.pdf",
        "status": "success",
        "progress": 1.0,
        "invoiceId": "INV-2026-0612-001",
        "confidence": 0.968,
        "ocrResult": { ... }
      }
    ]
  }
}
```

### POST /api/v1/invoice/ocr/batch/submit
**说明**：批量提交入账

请求：
```json
{
  "invoiceIds": ["INV-2026-0612-001", "INV-2026-0612-002", "INV-2026-0612-004"]
}
```

### POST /api/v1/invoice/ocr/batch/retry
**说明**：批量重试失败项

请求：
```json
{ "batchId": "BATCH-2026-0612-001", "fileIds": ["F-2026-009"] }
```

---

## 发票查验真伪

### POST /api/v1/invoice/verify/single
**说明**：单张发票查验（国税总局接口）

请求：
```json
{
  "invoiceCode": "011002600611",
  "invoiceNo": "25113300000012345678",
  "issueDate": "2026-06-08",
  "totalAmount": 28000.00,
  "verifyCode": "836542"        // 可选，发票密码区后 6 位
}
```

响应：
```json
{
  "data": {
    "verifyId": "VR-2026-0612-001",
    "result": "pass",            // pass | repeat | fake | expired | not_found | risk
    "source": "国家税务总局全国增值税发票查验平台",
    "verifiedAt": "2026-06-12 10:24:18",
    "elapsed": 1800,              // 毫秒
    "info": {
      "invoiceCode": "011002600611",
      "invoiceNo": "25113300000012345678",
      "issueDate": "2026-06-08",
      "totalAmount": 28000.00,
      "sellerName": "上海数智信息技术有限公司",
      "sellerTaxNo": "91310000MA1FL3X9G",
      "buyerName": "万象科技有限公司"
    },
    "riskReason": null           // 失败/风险时返回
  }
}
```

### POST /api/v1/invoice/verify/batch
**说明**：批量查验（一次最多 50 张）

请求：
```json
{
  "invoices": [
    { "invoiceCode": "...", "invoiceNo": "...", "issueDate": "...", "totalAmount": ... }
  ]
}
```

响应：
```json
{
  "data": {
    "batchId": "VR-BATCH-2026-001",
    "total": 12,
    "summary": { "pass": 10, "risk": 2 },
    "items": [ ... ]   // 同 single 响应结构
  }
}
```

### POST /api/v1/invoice/verify/list
**说明**：查验记录列表

请求：
```json
{
  "page": 1, "pageSize": 20,
  "filters": {
    "result": "pass|risk|all",
    "dateRange": ["2026-06-01", "2026-06-12"]
  }
}
```

### POST /api/v1/invoice/verify/certificate
**说明**：下载查验凭证（PDF/图片）

请求：
```json
{ "verifyId": "VR-2026-0612-001" }
```

返回：PDF 二进制流或图片 URL

### POST /api/v1/invoice/verify/mark
**说明**：标记风险发票（标记/上报/隔离）

请求：
```json
{
  "verifyId": "VR-2026-0612-001",
  "action": "mark|isolate|report",
  "comment": "已上报税务部门"
}
```

---

## 发票识别记录（深度版）

> `POST /invoices/ocr/list` 在第一阶段已列出，此处补充高级筛选与批量操作接口

### POST /api/v1/invoice/ocr/advanced-search
**说明**：高级筛选（独立于普通列表，支持复杂条件）

请求：
```json
{
  "page": 1, "pageSize": 20,
  "filters": {
    "keyword": "25113300",
    "invoiceType": ["电子普通发票", "数电发票"],
    "sellerId": ["C-001", "C-002"],
    "contractId": "any|specific|null",
    "amountRange": [1000, 50000],
    "taxRate": [0.06, 0.13],
    "uploaderId": "U-002",
    "dateRange": ["2026-06-01", "2026-06-12"],
    "hasVerifyCert": true
  },
  "sort": [
    { "field": "issueDate", "order": "desc" },
    { "field": "totalAmount", "order": "desc" }
  ]
}
```

### POST /api/v1/invoice/ocr/batch-action
**说明**：批量操作

请求：
```json
{
  "action": "submit|link_contract|export|delete|tag",
  "invoiceIds": ["INV-001", "INV-002", "INV-003"],
  "params": {
    "contractId": "HT-2026-028",       // action=link_contract 时必填
    "tagIds": ["risk", "urgent"],      // action=tag 时必填
    "exportFormat": "xlsx"             // action=export 时必填
  }
}
```

### POST /api/v1/invoice/ocr/saved-view
**说明**：保存为常用视图

请求：
```json
{
  "viewName": "本月差旅发票",
  "filters": { ... },
  "isShared": false
}
```

### POST /api/v1/invoice/ocr/views
**说明**：获取已保存的视图

响应：
```json
{
  "data": {
    "list": [
      { "viewId": "V-001", "name": "本月差旅发票", "isShared": false },
      { "viewId": "V-002", "name": "需核验的发票", "isShared": true }
    ]
  }
}
```

---

## 发票模板

### POST /api/v1/invoice/templates/list
请求：
```json
{
  "page": 1, "pageSize": 12,
  "filters": { "category": "all|created|shared|market", "type": "差旅", "status": "enabled|disabled" }
}
```

响应（单条）：
```json
{
  "data": {
    "list": [
      {
        "templateId": "TPL-TR-2026-001",
        "name": "差旅报销模板",
        "code": "TPL-TR-2026-001",
        "description": "含机票/酒店/打车/餐补，自动汇总",
        "category": "差旅",
        "icon": "差",
        "iconColor": ["#4F6BFF", "#7C3AED"],
        "fieldCount": 12,
        "usageCount": 86,
        "relatedProjectCount": 8,
        "rating": 4.8,
        "status": "enabled",          // enabled | disabled
        "isPinned": true,
        "isMarket": false,
        "creator": { "userId": "U-001", "name": "张明", "avatar": "..." },
        "createdAt": "2026-06-10",
        "updatedAt": "2026-06-12"
      }
    ],
    "total": 12
  }
}
```

### POST /api/v1/invoice/templates/detail
请求：
```json
{ "templateId": "TPL-TR-2026-001" }
```

响应：
```json
{
  "data": {
    "templateId": "TPL-TR-2026-001",
    "name": "差旅报销模板",
    "fields": [
      {
        "id": "f_001",
        "label": "发票类型",
        "key": "invoiceType",
        "type": "text",                // text | date | amount | rate | user | ref | textarea
        "required": true,
        "aiSupport": true,
        "defaultValue": null,
        "linkedField": null
      },
      {
        "id": "f_002",
        "label": "发票号码",
        "key": "invoiceNo",
        "type": "text",
        "required": true,
        "aiSupport": true
      },
      {
        "id": "f_003",
        "label": "开票日期",
        "key": "issueDate",
        "type": "date",
        "required": true,
        "aiSupport": true
      },
      {
        "id": "f_010",
        "label": "价税合计",
        "key": "totalAmount",
        "type": "amount",
        "required": true,
        "aiSupport": true
      },
      {
        "id": "f_011",
        "label": "税率",
        "key": "taxRate",
        "type": "rate",
        "required": false,
        "defaultValue": "6%"
      },
      {
        "id": "f_020",
        "label": "报销人",
        "key": "reimburserId",
        "type": "user",
        "required": true,
        "defaultValue": "currentUser",
        "linkedField": "department"
      },
      {
        "id": "f_021",
        "label": "部门",
        "key": "departmentId",
        "type": "ref",
        "required": true
      },
      {
        "id": "f_022",
        "label": "关联合同",
        "key": "contractId",
        "type": "ref",
        "required": false,
        "refType": "contract"
      },
      {
        "id": "f_030",
        "label": "备注",
        "key": "remark",
        "type": "textarea",
        "required": false
      }
    ]
  }
}
```

### POST /api/v1/invoice/templates/save
**说明**：新建/保存模板

请求：
```json
{
  "templateId": "TPL-TR-2026-001",     // 新建时不传
  "name": "差旅报销模板",
  "category": "差旅",
  "description": "...",
  "defaultTaxRate": 0.06,
  "fields": [ ... ]                    // 同上字段结构
}
```

### POST /api/v1/invoice/templates/duplicate
请求：
```json
{ "templateId": "TPL-TR-2026-001" }
```

### POST /api/v1/invoice/templates/delete
请求：
```json
{ "templateId": "TPL-TR-2026-001" }
```

### POST /api/v1/invoice/templates/field-library
**说明**：获取可拖拽字段库（模板编辑器左侧）

响应：
```json
{
  "data": {
    "groups": [
      {
        "name": "基础信息",
        "fields": [
          { "label": "发票类型", "key": "invoiceType", "type": "text", "icon": "📄" },
          { "label": "发票代码", "key": "invoiceCode", "type": "text", "icon": "🔢" },
          { "label": "发票号码", "key": "invoiceNo",   "type": "text", "icon": "#" },
          { "label": "开票日期", "key": "issueDate",   "type": "date", "icon": "📅" }
        ]
      },
      {
        "name": "金额信息",
        "fields": [
          { "label": "价税合计",   "key": "totalAmount", "type": "amount", "icon": "💰" },
          { "label": "税率",       "key": "taxRate",     "type": "rate",   "icon": "%" },
          { "label": "税额",       "key": "taxAmount",   "type": "amount", "icon": "¥" }
        ]
      },
      {
        "name": "业务字段",
        "fields": [
          { "label": "报销人",     "key": "reimburserId", "type": "user", "icon": "👤" },
          { "label": "部门",       "key": "departmentId", "type": "text", "icon": "🏢" },
          { "label": "关联合同",   "key": "contractId",   "type": "ref",  "icon": "📂", "refType": "contract" },
          { "label": "关联项目",   "key": "projectId",    "type": "ref",  "icon": "📂", "refType": "project" },
          { "label": "成本中心",   "key": "costCenter",   "type": "ref",  "icon": "📂", "refType": "costCenter" },
          { "label": "备注",       "key": "remark",       "type": "textarea", "icon": "📝" }
        ]
      }
    ]
  }
}
```

---

## 销售费用

### POST /api/v1/expenses/list
请求：
```json
{
  "page": 1, "pageSize": 20,
  "filters": {
    "category": "差旅|招待|办公|推广|培训|其他",
    "status": "pending|approved|rejected",
    "departmentId": "DEPT-2026-001",
    "applicantId": "U-004",
    "dateRange": ["2026-06-01", "2026-06-12"]
  }
}
```

### POST /api/v1/expenses/detail
请求：`{ "expenseId": "EX-2026-0612-001" }`

响应：
```json
{
  "data": {
    "expenseId": "EX-2026-0612-001",
    "category": "差旅",
    "title": "上海-北京客户拜访（北辰集团）",
    "description": "...",
    "amount": 4820.00,
    "currency": "CNY",
    "expenseDate": "2026-06-12",
    "submitDate": "2026-06-12 09:23",
    "applicant": { "userId": "U-004", "name": "陈思琪", "avatar": "..." },
    "department": { "id": "DEPT-002", "name": "销售部" },
    "contractId": "HT-2026-029",
    "projectId": "PRJ-2026-022",
    "breakdown": [
      { "label": "机票", "amount": 2860.00 },
      { "label": "酒店", "amount": 1280.00 },
      { "label": "打车", "amount": 380.00 },
      { "label": "餐补", "amount": 300.00 }
    ],
    "attachments": [
      { "fileId": "F-001", "name": "机票行程单.pdf", "size": 131072, "type": "application/pdf", "ocrStatus": "success" }
    ],
    "approvalFlow": {
      "currentStep": 2,
      "steps": [
        { "step": 1, "name": "提交", "operator": { "userId": "U-004", "name": "陈思琪" }, "status": "done",   "time": "2026-06-12 09:23" },
        { "step": 2, "name": "直属上级", "operator": { "userId": "U-002", "name": "王芳" }, "status": "current", "time": null },
        { "step": 3, "name": "财务审核", "operator": { "userId": "U-001", "name": "张明" }, "status": "todo",  "time": null },
        { "step": 4, "name": "总经理审批", "operator": null, "status": "todo", "time": null, "trigger": "amount >= 5000" }
      ]
    },
    "status": "pending"
  }
}
```

### POST /api/v1/expenses/create
请求：
```json
{
  "category": "差旅",
  "title": "...",
  "description": "...",
  "amount": 4820.00,
  "expenseDate": "2026-06-12",
  "contractId": "HT-2026-029",
  "projectId": "PRJ-2026-022",
  "breakdown": [ ... ],
  "attachmentIds": ["F-001", "F-002"]
}
```

### POST /api/v1/expenses/approve
请求：
```json
{
  "expenseId": "EX-2026-0612-001",
  "action": "approve|reject|transfer",
  "comment": "同意",
  "transferTo": "U-005"           // 仅 action=transfer 时必填
}
```

### POST /api/v1/expenses/stats
**说明**：Dashboard 数据卡 + 图表

响应：
```json
{
  "data": {
    "kpi": {
      "totalAmount": 865000,
      "pendingCount": 12,
      "pendingAmount": 186000,
      "approvedCount": 68,
      "rejectedCount": 3
    },
    "trendChart": {
      "labels": ["06-01", "06-08", "06-15", "06-22", "今天"],
      "actual": [180000, 150000, 130000, 95000, 60000],
      "budgetLine": 2000000
    },
    "categoryChart": [
      { "name": "差旅", "amount": 329000, "ratio": 0.38, "color": "#4F6BFF" },
      { "name": "招待", "amount": 190000, "ratio": 0.22, "color": "#7C3AED" },
      { "name": "办公", "amount": 156000, "ratio": 0.18, "color": "#10B981" },
      { "name": "推广", "amount": 121000, "ratio": 0.14, "color": "#F59E0B" },
      { "name": "其他", "amount": 69000,  "ratio": 0.08, "color": "#EC4899" }
    ]
  }
}
```

---

## 项目管理

### POST /api/v1/projects/list
请求：
```json
{
  "page": 1, "pageSize": 20,
  "view": "list|kanban|gantt",        // list=卡片列表，kanban=看板，gantt=甘特
  "filters": {
    "status": "in_progress|completed|paused|archived",
    "managerId": "U-004",
    "clientId": "C-2026-001",
    "dateRange": ["2026-01-01", "2026-12-31"]
  }
}
```

### POST /api/v1/projects/detail
请求：`{ "projectId": "PRJ-2026-018" }`

响应：
```json
{
  "data": {
    "projectId": "PRJ-2026-018",
    "name": "数智化二期",
    "type": "SaaS 平台升级",
    "status": "in_progress",            // in_progress | completed | paused | archived | not_started
    "client": { "clientId": "C-001", "name": "万象科技有限公司" },
    "manager": { "userId": "U-004", "name": "陈思琪", "avatar": "..." },
    "team": [
      { "userId": "U-004", "name": "陈思琪", "role": "PM",   "avatar": "..." },
      { "userId": "U-002", "name": "王芳",   "role": "财务", "avatar": "..." }
    ],
    "startDate": "2026-03-15",
    "endDate": "2026-08-30",
    "contractAmount": 1280000.00,
    "budget": 280000.00,
    "spent": 186500.00,
    "progress": 0.68,
    "milestones": [
      {
        "milestoneId": "M1",
        "name": "项目启动会",
        "status": "done",               // done | current | todo
        "plannedDate": "2026-03-20",
        "completedDate": "2026-03-20",
        "operator": "张明 / 陈思琪"
      },
      {
        "milestoneId": "M5",
        "name": "试运行 & 数据迁移",
        "status": "current",
        "progress": 0.45,
        "plannedStart": "2026-06-15",
        "plannedEnd": "2026-07-30"
      }
    ],
    "contracts": [ "HT-2026-028", "HT-2026-031" ],
    "invoices": [ "INV-2026-XXX" ],
    "risks": [
      { "level": "warning", "title": "M5 试运行进度滞后", "description": "..." }
    ],
    "description": "..."
  }
}
```

### POST /api/v1/projects/milestone/list
请求：`{ "projectId": "PRJ-2026-018" }`

### POST /api/v1/projects/milestone/add
请求：
```json
{
  "projectId": "PRJ-2026-018",
  "name": "...",
  "plannedStart": "2026-08-01",
  "plannedEnd": "2026-08-30",
  "ownerId": "U-004"
}
```

### POST /api/v1/projects/stats
响应：
```json
{
  "data": {
    "kpi": {
      "active": 23,
      "newThisMonth": 3,
      "completedThisMonth": 5,
      "expiringSoon": 4,
      "totalContractAmount": 12860000
    }
  }
}
```

---

## 合同管理

### POST /api/v1/contracts/list
请求：
```json
{
  "page": 1, "pageSize": 20,
  "filters": {
    "type": "销售合同|采购合同|服务合同|框架协议",
    "status": "draft|approving|approved|signed|executed|expired|archived",
    "clientId": "C-001",
    "dateRange": ["2026-01-01", "2026-12-31"]
  }
}
```

### POST /api/v1/contracts/detail
请求：`{ "contractId": "HT-2026-031" }`

响应：
```json
{
  "data": {
    "contractId": "HT-2026-031",
    "name": "万象科技 SaaS 服务合同 2026Q2",
    "type": "销售合同",
    "client": {
      "clientId": "C-001",
      "name": "万象科技有限公司",
      "taxNo": "91310000MA1FL01X9G",
      "contactName": "李建国",
      "contactPhone": "138****8888"
    },
    "amount": 86500.00,
    "currency": "CNY",
    "signDate": "2026-06-11",
    "effectiveDate": "2026-06-15",
    "expireDate": "2027-06-10",
    "duration": "12 个月",
    "paymentMethod": "季付",
    "paymentTerm": "30 天",
    "projectId": "PRJ-2026-022",
    "status": "approving",            // draft | approving | approved | signed | executed | expired | archived
    "summary": "...",
    "terms": [
      { "id": "T1", "title": "服务内容", "content": "..." },
      { "id": "T2", "title": "付款条款", "content": "..." },
      { "id": "T3", "title": "SLA 保障", "content": "..." }
    ],
    "approvalFlow": {
      "currentStep": 3,
      "steps": [
        { "step": 1, "name": "起草",     "operator": { "userId": "U-003", "name": "李明"   }, "status": "done",    "time": "2026-06-11 10:23" },
        { "step": 2, "name": "法务审核", "operator": { "userId": "U-099", "name": "王律师" }, "status": "done",    "time": "2026-06-11 14:30" },
        { "step": 3, "name": "财务审核", "operator": { "userId": "U-001", "name": "张明"   }, "status": "current", "time": "2026-06-12 09:23" },
        { "step": 4, "name": "总经理审批","operator": null, "status": "todo", "trigger": "amount >= 50000" },
        { "step": 5, "name": "电子签",   "operator": null, "status": "todo" },
        { "step": 6, "name": "归档",     "operator": null, "status": "todo" }
      ]
    },
    "signatures": {
      "partyA": { "signed": true,  "name": "上海数智信息技术有限公司", "signedAt": "2026-06-15 14:23:08", "signUrl": "..." },
      "partyB": { "signed": false, "name": "万象科技有限公司", "signedAt": null }
    },
    "attachments": [
      { "fileId": "F-C001", "name": "合同主文件.pdf", "size": 1258291 }
    ],
    "performance": {
      "progress": 0.25,
      "invoicedAmount": 21625,
      "receivedAmount": 21625,
      "pendingReceivable": 64875
    }
  }
}
```

### POST /api/v1/contracts/approve
请求：
```json
{
  "contractId": "HT-2026-031",
  "action": "approve|reject|transfer",
  "comment": "...",
  "transferTo": "U-005"
}
```

### POST /api/v1/contracts/stats
响应：
```json
{
  "data": {
    "kpi": {
      "total": 86,
      "executed": 47,
      "totalAmount": 24860000,
      "pendingApproval": 5,
      "expiringSoon": 7
    }
  }
}
```

### POST /api/v1/contracts/template
**说明**：起草合同时可选用模板

响应：
```json
{
  "data": {
    "templates": [
      { "id": "CT-001", "name": "标准销售合同 v2.1", "type": "销售合同" },
      { "id": "CT-002", "name": "SaaS 服务合同",     "type": "服务合同" },
      { "id": "CT-003", "name": "采购框架协议",       "type": "采购合同" }
    ]
  }
}
```

---

## 回款管理

### POST /api/v1/receivables/list
请求：
```json
{
  "page": 1, "pageSize": 20,
  "filters": {
    "status": "pending|partial|completed|overdue",
    "clientId": "C-001",
    "managerId": "U-004",
    "dateRange": ["2026-06-01", "2026-12-31"]
  }
}
```

### POST /api/v1/receivables/detail
请求：`{ "receivableId": "HK-2026-018" }`

响应：
```json
{
  "data": {
    "receivableId": "HK-2026-018",
    "contractId": "HT-2026-030",
    "client": { "clientId": "C-001", "name": "万象科技有限公司" },
    "type": "合同尾款",
    "planAmount": 28000.00,
    "receivedAmount": 0,
    "pendingAmount": 28000,
    "planDate": "2026-06-04",
    "actualDate": null,
    "overdueDays": 8,
    "term": "30 天",
    "manager": { "userId": "U-004", "name": "陈思琪" },
    "bankAccount": { "name": "招行上海分行", "account": "6225****1234" },
    "status": "overdue",               // pending | partial | completed | overdue
    "remark": "...",
    "history": [
      {
        "type": "received",            // received | remind | status_change
        "amount": 0,
        "operator": null,
        "time": null
      }
    ],
    "remindLogs": [
      {
        "logId": "RL-001",
        "type": "phone",                // phone | email | wechat | letter
        "operator": { "userId": "U-004", "name": "陈思琪" },
        "content": "客户反馈：因内部季度结算，付款流程延迟至本周...",
        "contactPerson": "李建国（CTO）",
        "duration": "8 分钟",
        "createdAt": "2026-06-11 14:30"
      }
    ],
    "linkedInvoices": [
      { "invoiceId": "INV-2026-XXX", "invoiceNo": "25113300000012345678", "amount": 28000, "issueDate": "2026-06-02" }
    ],
    "clientPaymentHistory": [
      { "receivableId": "HK-2026-009", "amount": 86500, "status": "completed", "actualDate": "2026-03-15" }
    ],
    "riskAssessment": {
      "level": "medium",                // low | medium | high
      "label": "中度风险",
      "description": "客户历史回款准时率 83%，本次为首笔严重逾期...",
      "aiSuggestion": "建议持续跟进，无需升级法务"
    }
  }
}
```

### POST /api/v1/receivables/remind
**说明**：发起催收

请求：
```json
{
  "receivableId": "HK-2026-018",
  "type": "phone",                    // phone | email | wechat
  "contactPerson": "李建国",
  "content": "...",
  "attachments": ["F-XXX"]
}
```

### POST /api/v1/receivables/receive
**说明**：登记到账

请求：
```json
{
  "receivableId": "HK-2026-018",
  "receivedAmount": 28000.00,
  "receivedDate": "2026-06-12",
  "bankStatement": "F-XXX",            // 银行流水凭证
  "remark": "..."
}
```

### POST /api/v1/receivables/stats
响应：
```json
{
  "data": {
    "kpi": {
      "thisMonthReceived": 1423000,
      "pendingTotal": 2865000,
      "completionRate": 0.824,
      "overdueCount": 3,
      "overdueAmount": 114500
    },
    "monthTimeline": [
      { "month": "2026-06", "planned": 1800000, "actual": 1423000, "status": "in_progress" },
      { "month": "2026-07", "planned": 2480000, "actual": 0,        "status": "pending" },
      { "month": "2026-08", "planned": 1860000, "actual": 0,        "status": "pending" }
    ],
    "topClients": [
      { "clientId": "C-001", "name": "万象科技", "amount": 2865000, "count": 3, "avgDays": 32 }
    ]
  }
}
```

---

## 公共数据

### POST /api/v1/common/dict
**说明**：通用字典（费用类型、合同类型、回款状态等）

请求：
```json
{ "dictType": "expense_category" }
```
响应：
```json
{
  "data": {
    "list": [
      { "value": "差旅", "label": "差旅", "color": "#4F6BFF" },
      { "value": "招待", "label": "招待", "color": "#7C3AED" },
      { "value": "办公", "label": "办公", "color": "#10B981" },
      { "value": "推广", "label": "推广", "color": "#F59E0B" },
      { "value": "培训", "label": "培训", "color": "#8B5CF6" },
      { "value": "其他", "label": "其他", "color": "#94A3B8" }
    ]
  }
}
```

支持的 dictType：
- `expense_category` — 费用类型
- `contract_type` — 合同类型
- `invoice_type` — 发票类型
- `project_status` — 项目状态
- `approval_status` — 审批状态
- `receivable_status` — 回款状态
- `user_role` — 用户角色
- `cost_center` — 成本中心

### POST /api/v1/common/users
**说明**：用户列表（用于下拉选择）

请求：
```json
{ "keyword": "", "departmentId": "", "page": 1, "pageSize": 50 }
```

### POST /api/v1/common/clients
**说明**：客户列表

请求：
```json
{ "keyword": "", "page": 1, "pageSize": 50 }
```

### POST /api/v1/common/contracts/ref
**说明**：合同引用（用于下拉）

请求：
```json
{ "clientId": "C-001", "page": 1, "pageSize": 20 }
```

### POST /api/v1/common/projects/ref
请求：`{ "clientId": "C-001", "page": 1, "pageSize": 20 }`

### POST /api/v1/common/upload
**说明**：通用文件上传（multipart）

返回：
```json
{
  "data": {
    "fileId": "F-2026-001",
    "name": "...",
    "size": 131072,
    "url": "https://cdn.shuzhi.com/...",
    "type": "..."
  }
}
```

---

## 错误码表

| code | 含义 | 处理建议 |
|------|------|---------|
| 0 | 成功 | — |
| 1001 | 未登录 / Token 过期 | 跳转到登录页 |
| 1003 | 无权限 | 提示并隐藏功能按钮 |
| 1004 | 租户无效 | 提示联系管理员 |
| 2001 | 参数错误 | 高亮错误字段 |
| 2004 | 资源不存在 | 友好 404 提示 |
| 2009 | 数据冲突 | 刷新后重试 |
| 3001 | 余额不足 | 引导充值 |
| 3002 | 配额超限 | 提示升级 |
| 5000 | 服务器异常 | 通用错误提示 + 报告 traceId |
| 5001 | OCR 服务异常 | 提示稍后重试 |
| 5002 | 国税查验异常 | 提示稍后重试 |
| 5003 | 电子签服务异常 | 提示稍后重试 |

---

## 前端字段映射表

> 给前端开发的速查表：每个页面用到的关键字段，标注字段名、类型、来源接口

### Dashboard
| 字段 | 类型 | 来源 |
|------|------|------|
| moduleStats | 数组 | `/dashboards/summary` |
| kpi | 数组 | `/dashboards/summary` |
| trendChart | 对象 | `/dashboards/summary` |
| todos | 数组 | `/dashboards/summary` |

### 发票识别
| 字段 | 类型 | 来源 |
|------|------|------|
| invoiceId | string | OCR 上传返回 |
| invoiceType | enum | OCR |
| invoiceNo | string | OCR |
| totalAmount | decimal(2) | OCR |
| confidence | float | OCR |
| verifyStatus | enum | OCR / 详情 |

### 销售费用
| 字段 | 类型 | 来源 |
|------|------|------|
| expenseId | string | 系统生成 |
| category | enum | dict |
| amount | decimal(2) | 用户输入 |
| breakdown | array | 用户输入 |
| approvalFlow.steps[].status | enum | 审批流 |

### 项目管理
| 字段 | 类型 | 来源 |
|------|------|------|
| projectId | string | 系统生成 |
| progress | float(0-1) | 计算（基于里程碑） |
| milestones[].status | enum | 手动更新 |

### 合同管理
| 字段 | 类型 | 来源 |
|------|------|------|
| contractId | string | 系统生成 |
| amount | decimal(2) | 用户输入 |
| status | enum | 审批流决定 |
| signatures.partyA.signed | bool | 电子签回调 |

### 回款管理
| 字段 | 类型 | 来源 |
|------|------|------|
| receivableId | string | 系统生成 |
| planAmount | decimal(2) | 用户输入 |
| receivedAmount | decimal(2) | 累加 |
| overdueDays | int | 计算 |
| status | enum | 计算 |

---

## 附录

### A. 完整的接口清单（30 个）

| # | 接口 | 模块 |
|---|------|------|
| 1 | /auth/login | 认证 |
| 2 | /auth/sso/qrcode/generate | 认证 |
| 3 | /auth/sso/qrcode/check | 认证 |
| 4 | /auth/password/reset/request | 认证 |
| 5 | /auth/password/reset/confirm | 认证 |
| 6 | /auth/logout | 认证 |
| 7 | /dashboards/summary | Dashboard |
| 8 | /dashboards/activities | Dashboard |
| 9 | /invoices/ocr/upload | 发票识别 |
| 10 | /invoices/ocr/list | 发票识别 |
| 11 | /invoices/ocr/detail | 发票识别 |
| 12 | /invoices/ocr/update | 发票识别 |
| 13 | /invoices/ocr/submit | 发票识别 |
| 14 | /invoices/ocr/recheck | 发票识别 |
| 14a | /invoices/ocr/batch/upload | 发票识别（批量） |
| 14b | /invoices/ocr/batch/status | 发票识别（批量） |
| 14c | /invoices/ocr/batch/submit | 发票识别（批量） |
| 14d | /invoices/ocr/batch/retry | 发票识别（批量） |
| 14e | /invoices/ocr/advanced-search | 发票识别（记录） |
| 14f | /invoices/ocr/batch-action | 发票识别（记录） |
| 14g | /invoices/ocr/saved-view | 发票识别（记录） |
| 14h | /invoices/ocr/views | 发票识别（记录） |
| 14i | /invoices/verify/single | 发票查验 |
| 14j | /invoices/verify/batch | 发票查验 |
| 14k | /invoices/verify/list | 发票查验 |
| 14l | /invoices/verify/certificate | 发票查验 |
| 14m | /invoices/verify/mark | 发票查验 |
| 15 | /invoices/template/list | 发票模板 |
| 16 | /invoices/template/detail | 发票模板 |
| 17 | /invoices/template/save | 发票模板 |
| 18 | /invoices/template/duplicate | 发票模板 |
| 19 | /invoices/template/delete | 发票模板 |
| 20 | /invoices/template/field-library | 发票模板 |
| 21 | /expenses/list | 销售费用 |
| 22 | /expenses/detail | 销售费用 |
| 23 | /expenses/create | 销售费用 |
| 24 | /expenses/approve | 销售费用 |
| 25 | /expenses/stats | 销售费用 |
| 26 | /projects/list | 项目 |
| 27 | /projects/detail | 项目 |
| 28 | /projects/milestone/list | 项目 |
| 29 | /projects/milestone/add | 项目 |
| 30 | /projects/stats | 项目 |
| 31 | /contracts/list | 合同 |
| 32 | /contracts/detail | 合同 |
| 33 | /contracts/approve | 合同 |
| 34 | /contracts/stats | 合同 |
| 35 | /contracts/template | 合同 |
| 36 | /receivables/list | 回款 |
| 37 | /receivables/detail | 回款 |
| 38 | /receivables/remind | 回款 |
| 39 | /receivables/receive | 回款 |
| 40 | /receivables/stats | 回款 |
| 41 | /common/dict | 公共 |
| 42 | /common/users | 公共 |
| 43 | /common/clients | 公共 |
| 44 | /common/contracts/ref | 公共 |
| 45 | /common/projects/ref | 公共 |
| 46 | /common/upload | 公共 |

合计 **59 个接口**。

### B. 字段命名规范
- 所有字段使用 **camelCase**
- 时间字段统一后缀：`At` / `Date` / `Time`
- 状态字段使用：`status` / `state`
- ID 字段使用全名：`userId` / `projectId`
- 关联引用使用全名：`contractId` / `clientId`
- 金额单位：**分**（int）→ 转 **元**（decimal）给前端

### C. 性能要求
- 所有列表接口：P99 < 300ms
- 上传/OCR 接口：< 5s
- 详情接口：P99 < 200ms
- Dashboard：< 500ms
- 文件下载：< 1s (CDN 加速)

### D. 安全要求
- 所有接口走 HTTPS
- Token 有效期：2 小时，RefreshToken：7 天
- 敏感字段（银行卡、身份证）后端 AES 加密
- 金额字段后端二次校验
- 审计日志：所有写接口必须记录 `operator + timestamp + before/after`

---

**📝 维护说明：**
- 本文档随 API 变更同步更新
- 任何 breaking change 必须经 PM + 后端 + 前端三方确认
- 灰度发布：先 1% 流量，确认无问题后逐步放量


---

## 附录：自动补齐的端点（与后端 openapi 对齐）

> 本节为本次校准自动补齐，与后端 OpenAPI 一致。


### ADMIN

### GET /api/v1/admin/depts/tree

部门树（前端 AdminDept 用）

### POST /api/v1/admin/audit-logs/list

审计日志列表

### POST /api/v1/admin/depts/create

创建部门

### POST /api/v1/admin/depts/delete

删除部门

### POST /api/v1/admin/depts/list

部门列表（平铺）

### POST /api/v1/admin/depts/update

更新部门

### POST /api/v1/admin/dicts/create

新增字典项

### POST /api/v1/admin/dicts/delete

删除字典项

### POST /api/v1/admin/dicts/list

字典项列表（按 dictType）

### POST /api/v1/admin/dicts/update

更新字典项

### POST /api/v1/admin/permissions/list

权限点全量列表

### POST /api/v1/admin/roles/create

创建角色

### POST /api/v1/admin/roles/delete

删除角色

### POST /api/v1/admin/roles/detail

角色详情

### POST /api/v1/admin/roles/list

角色列表

### POST /api/v1/admin/roles/update

更新角色（含分配权限）

### POST /api/v1/admin/users/create

创建用户

### POST /api/v1/admin/users/delete

删除用户

### POST /api/v1/admin/users/detail

用户详情

### POST /api/v1/admin/users/list

用户列表

### POST /api/v1/admin/users/reset-password

重置密码

### POST /api/v1/admin/users/toggle-active

启用/禁用用户

### POST /api/v1/admin/users/update

更新用户


### AI

### GET /api/v1/ai/extract/batch/stream

批量抽取 SSE 流

### GET /api/v1/ai/stream

全局 SSE 入口（多事件流）

### POST /api/v1/ai/alert/dismiss

关闭 / 延后提醒

### POST /api/v1/ai/alert/today

今日 AI 助手提醒

### POST /api/v1/ai/ask/ask

自然语言提问

### POST /api/v1/ai/ask/feedback

问答反馈（👍/👎）

### POST /api/v1/ai/ask/suggestions

推荐问题

### POST /api/v1/ai/extract/apply

采纳 AI 抽取结果（数据回流）

### POST /api/v1/ai/extract/batch/upload

批量字段抽取（异步 SSE）

### POST /api/v1/ai/extract/upload

单张字段抽取（同步 < 3s）

### POST /api/v1/ai/feedback/submit

提交 AI 反馈

### POST /api/v1/ai/model/config

配置 AI 模型

### POST /api/v1/ai/model/list

AI 模型列表

### POST /api/v1/ai/risk/dismiss

忽略/采纳风险

### POST /api/v1/ai/risk/scan

单条风险扫描

### POST /api/v1/ai/risk/warnings

拉取某对象的所有风险

### POST /api/v1/ai/task/cancel

取消 AI 任务

### POST /api/v1/ai/task/list

AI 任务列表


### COMMON

### GET /api/v1/common/dict

通用字典（query 参数，前端默认调用）

### POST /api/v1/common/clients/create

创建客户

### POST /api/v1/common/clients/delete

删除客户（软删除）

### POST /api/v1/common/clients/detail

客户详情

### POST /api/v1/common/clients/update

更新客户


### BIZ

### POST /api/v1/contracts/create

新建合同

### POST /api/v1/contracts/delete

删除合同（仅 draft）

### POST /api/v1/contracts/submit

提交审批（draft → approving）

### POST /api/v1/contracts/update

更新合同（仅 draft）

### POST /api/v1/expenses/delete

删除费用

### POST /api/v1/expenses/submit

提交审批（draft → pending）

### POST /api/v1/expenses/update

编辑费用

### POST /api/v1/projects/create

项目立项

### POST /api/v1/projects/delete

删除项目

### POST /api/v1/projects/update

更新项目

### POST /api/v1/receivables/create

创建回款计划

### POST /api/v1/receivables/delete

删除回款

### POST /api/v1/receivables/update

编辑回款


### SSE

### GET /

Root

### GET /health

Health

### GET /sse/{channel}

Sse Endpoint


### MISC

### GET /api/v1/auth/me

获取当前登录用户信息
