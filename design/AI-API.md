# AI 数智化能力 · API 契约

> **版本**：v0.9（Phase 1）
> **读者**：前端工程师、后端工程师、算法工程师、PM
> **原则**：**不影响现有 API 任何接口**，所有 AI 接口统一挂 `/api/v1/ai/*`
> **配套设计稿**：`ai-center.html` / `ai-extract-demo.html` / `ai-panel-project.html` / `components-states.html`
> **配套样式**：`assets/common.css` 中 `.ai-*` 类
> **配套文档**：`design/API.md`（老接口） / `design/BACKEND.md`（老架构）

---

## 0. 设计原则

### 0.1 不破坏现有
- 老的 59 个接口 / 0 修改
- 数据库老表 / 0 schema 变更
- 老的 SSE 通道 / 0 改动
- 老的 `core/sse.py` / 0 改动（直接复用）

### 0.2 全部走 `/api/v1/ai/*` 前缀
- 老接口：`/api/v1/auth/*`、`/api/v1/project/*` ...
- AI 接口：`/api/v1/ai/*`（**统一前缀**，方便路由级限流、监控、开关）

### 0.3 同步优先，异步次之
- **同步**（< 3s）：字段抽取单图、风险扫描单条、问数
- **异步**（≥ 3s）：批量字段抽取、批量风险扫描、长文档分析
- 异步一律走 SSE（**复用** `design/API.md §实时通信约定`）

### 0.4 降级策略
**AI 服务挂了，老流程照样跑**。前端调用 AI 接口遇 5xxx 时：
- 字段抽取 → 切换到普通上传
- 风险扫描 → 隐藏"AI 风险评级"列
- 智能问答 → 切换到普通搜索

### 0.5 审计与可追溯
**所有 AI 写操作必须落审计日志**（`source = "ai"`，区别于用户操作）。
所有 AI 输出必须带**置信度**，用户修改后回流（用于模型迭代）。

### 0.6 成本与限流
每个租户/用户有 AI 用量配额，**触发配额告警但不直接拒绝**（先警示后限流，避免业务阻塞）。

---

## 1. 通用规范

### 1.1 Base URL（沿用 API.md）
```
生产：https://api.shuzhi.example.com/v1
测试：https://api-test.shuzhi.example.com/v1
```

### 1.2 请求格式（沿用 API.md）
- Method：POST（除 SSE 外）
- Headers：
  ```
  Content-Type: application/json
  Authorization: Bearer <token>
  X-Tenant-Id: <租户ID>
  X-Request-Id: <trace-id>     // 前端生成 UUID
  X-AI-Source: <source>        // AI 接口专用：web/ios/android/cli/cron
  ```

### 1.3 统一响应包装（沿用 API.md §统一响应包装）
```json
{
  "code": 0,
  "message": "success",
  "data": { /* 业务数据 */ },
  "traceId": "abc-123-xyz"
}
```

### 1.4 AI 接口扩展字段
AI 接口的 `data` 内部统一带：
```typescript
{
  // 业务字段
  result: { ... },

  // AI 元数据（所有 AI 输出必须带）
  meta: {
    model: string,            // "paddleocr-v3" | "qwen2.5-7b" | "risk-v2.3" ...
    version: string,          // 模型版本号 "1.2.3"
    confidence: number,       // 综合置信度 0-100
    durationMs: number,       // 处理耗时
    costCents: number,        // 成本（分）
    traceId: string,          // AI 调用链 ID（区别于请求 traceId）
  }
}
```

### 1.5 置信度标准
| 范围 | 含义 | 前端处理 |
|------|------|---------|
| **≥ 90** | 高 | 直接用，绿色 `.ai-confidence.high` |
| **70-89** | 中 | 提示复核，黄色 `.ai-confidence.mid` |
| **< 70** | 低 | 强制复核，红色 `.ai-confidence.low` |

**字段级置信度**（不是综合分）：
```typescript
{
  "invoiceNo": { "value": "12345678", "confidence": 99 },
  "taxRate":   { "value": 0.06,       "confidence": 72 }   // ← 中置信度，前端高亮
}
```

---

## 2. 错误码表（在 API.md 错误码基础上扩展）

| code | 含义 | 处理建议 |
|------|------|---------|
| 0 | 成功 | — |
| 1001 | 未登录 / Token 过期 | 跳转登录 |
| 1003 | 无权限 | 隐藏功能 |
| 2001 | 参数错误 | 高亮字段 |
| 2004 | 资源不存在 | 友好 404 |
| 2009 | 数据冲突 | 刷新重试 |
| **3001** | **AI 余额不足** | **引导充值 / 申请额度** |
| **3002** | **AI 配额超限（限流）** | **提示 + 重试退避** |
| **3003** | **AI 输入超限（图太大/文档太长）** | **提示压缩** |
| 5000 | 服务器异常 | 通用错误 |
| 5001 | OCR 服务异常 | 降级到普通上传 |
| 5002 | 国税查验异常 | 稍后重试 |
| **5101** | **AI 模型不可用** | **降级 + 隐藏 AI 入口** |
| **5102** | **AI 超时** | **降级 + 提示** |
| **5103** | **AI 内容安全审核拒绝** | **不展示给用户，记日志** |
| **5104** | **AI 返回格式异常** | **降级 + 报告** |

---

## 3. 鉴权

**沿用** `Authorization: Bearer <token>` 机制，AI 接口**不再单独鉴权**。

特殊点（仅 2 处）：
- **SSE 鉴权**用 query string：`/api/v1/ai/stream?token=xxx`（因 EventSource 不支持自定义 header）
- **回调/Webhook**（如 Agent 任务完成后推外部）用 `X-AI-Callback-Secret` 头

权限码前缀：`ai:*`（独立于业务权限）
| 权限码 | 含义 |
|--------|------|
| `ai:extract` | 字段抽取 |
| `ai:risk.scan` | 风险扫描 |
| `ai:ask` | 智能问答 |
| `ai:agent.run` | 运行 Agent |
| `ai:model.manage` | 模型管理（仅管理员） |

---

## 4. SSE 实时通信

**完全沿用** `design/API.md §实时通信约定`（事件名 `progress` / `completed` / `error` / `keepalive` 等）。

AI 任务多了 3 个事件：
| 事件名 | 触发时机 | 数据 |
|--------|---------|------|
| `extracted` | 单条字段抽取完成 | `{ field, value, confidence, bbox }` |
| `risk_detected` | 发现 1 个风险点 | `{ level, title, description, suggestion }` |
| `answer_chunk` | 问答流式返回一块 | `{ content, isFinal }` |

---

## 5. 接口清单（按模块）

```
/api/v1/ai/
├── extract/                 # 字段抽取（Phase 1 重点）
│   ├── upload               # 单图上传 → 同步抽取（< 3s）
│   ├── batch/upload         # 多图上传 → 异步（SSE）
│   ├── batch/status         # 查批量状态（兼容老前端）
│   ├── result/:id           # 查抽取结果
│   ├── apply/:id            # 采纳到表单（提交修正）
│   └── retry/:id            # 重新抽取
│
├── risk/                    # 风险识别
│   ├── scan                 # 扫描单条（项目/合同/费用/凭证）
│   ├── batch/scan           # 批量扫描（异步 + SSE）
│   ├── warnings             # 拉取某对象的所有风险
│   ├── dismiss/:id          # 忽略/采纳
│   └── similar              # 相似对象对比
│
├── match/                   # 智能匹配（银行流水）
│   ├── run                  # 触发匹配（异步）
│   ├── result/:id           # 查匹配结果
│   ├── confirm              # 人工确认/修正
│   └── rules                # 配置匹配规则
│
├── ask/                     # 智能问答
│   ├── ask                  # 提问（同步或 SSE 流式）
│   ├── history              # 历史对话
│   ├── feedback             # 反馈（👍/👎）
│   └── suggestions          # 推荐问题
│
├── generate/                # 智能起草
│   ├── draft                # 起草合同/邮件/通知
│   ├── list                 # 草稿列表
│   ├── save                 # 保存草稿
│   └── apply/:id            # 应用到业务表单
│
├── agent/                   # Agent 自动化
│   ├── run                  # 触发 Agent
│   ├── list                 # Agent 列表
│   ├── config               # 配置 Agent
│   └── history              # 执行历史
│
├── alert/                   # AI 提醒（Dashboard 顶部）
│   ├── today                # 今日提醒
│   ├── list                 # 历史提醒
│   ├── dismiss/:id          # 关闭
│   └── read-all             # 全部已读
│
├── task/                    # AI 任务中心
│   ├── list                 # 任务列表
│   ├── detail/:id           # 任务详情
│   ├── cancel/:id           # 取消
│   └── retry/:id            # 重试
│
├── feedback/                # 反馈中心
│   ├── submit               # 提交反馈
│   └── list                 # 反馈列表（管理员）
│
├── model/                   # 模型管理
│   ├── list                 # 模型列表 + 状态
│   ├── config               # 配置
│   ├── enable               # 启用/停用
│   └── usage                # 用量统计
│
├── stream                   # 全局 SSE 入口（多事件流）
│
└── stats                    # AI 使用统计
```

**Phase 1 实现**：标 ✦ 的 18 个接口必出，其他 8 个给 schema 占位

---

## 6. 详细接口

### 6.1 字段抽取（最高频，Phase 1 核心）

#### 6.1.1 ✦ POST /ai/extract/upload

**用途**：单张图片/扫描件 → 抽取结构化字段（同步，2s 内返回）

**请求**：
```json
{
  "fileId": "f_abc123",                // 已上传到 OSS 的文件 ID
  "fileUrl": "https://...",            // 或 URL
  "type": "invoice",                   // invoice | contract | receipt | business-card | bank-statement
  "templateId": "tpl_default",         // 可选，使用哪个模板
  "language": "zh-CN",                 // 可选，默认中文
  "options": {
    "enhanceImage": true,              // 是否先做图像增强
    "extractLineItems": true,          // 是否抽取明细行（如发票商品）
    "fallbackModels": ["nuonuo"]       // 主模型失败时兜底
  }
}
```

**响应**：
```json
{
  "code": 0,
  "data": {
    "taskId": "task_xyz",
    "type": "invoice",
    "fields": {
      "invoiceNo":   { "value": "12345678",         "confidence": 99, "bbox": [120, 80, 220, 100] },
      "invoiceCode": { "value": "011002000000",     "confidence": 99, "bbox": [120, 60, 240, 80] },
      "issueDate":   { "value": "2024-05-21",       "confidence": 98 },
      "buyerName":   { "value": "示例客户有限公司",  "confidence": 97, "bbox": [180, 110, 380, 130] },
      "buyerTaxId":  { "value": "91110000XXXX",     "confidence": 92 },
      "sellerName":  { "value": "数智科技...",       "confidence": 99 },
      "amount":      { "value": 95000.00,            "confidence": 96 },
      "taxAmount":   { "value": 5700.00,             "confidence": 96 },
      "totalAmount": { "value": 100700.00,           "confidence": 99 },
      "totalAmountCn":{ "value": "壹拾万零柒佰元整", "confidence": 98 },
      "taxRate":     { "value": 0.06,                "confidence": 72, "needsReview": true },  // ← 低分
      "lineItems": [                                  // 明细行
        {
          "name": "*信息技术服务*系统集成服务费",
          "quantity": 1, "unitPrice": 80000.00, "amount": 80000.00,
          "taxRate": 0.06, "taxAmount": 4800.00,
          "confidence": 88
        }
      ],
      "remark": "合同号 C-2024-123"                  // 自由文本
    },
    "suggestions": {
      "linkToContract": "C-2024-123",                // 智能关联建议
      "linkToClient":   "示例客户有限公司",
      "linkToProject":  "数智化二期"
    },
    "meta": {
      "model": "paddleocr-v3",
      "version": "1.2.0",
      "confidence": 94,
      "durationMs": 1820,
      "costCents": 0
    }
  }
}
```

**错误**：
- 5101 模型不可用
- 5102 超时（> 10s）
- 3003 图片太大（> 20MB）

#### 6.1.2 ✦ POST /ai/extract/batch/upload

**用途**：多图批量抽取（异步，5-30s）→ SSE 推送进度

**请求**：
```json
{
  "fileIds": ["f_1", "f_2", "f_3", ...],  // 最多 100
  "type": "invoice",
  "templateId": "tpl_default"
}
```

**响应**（任务创建）：
```json
{
  "code": 0,
  "data": {
    "batchId": "batch_xyz",
    "total": 58,
    "streamUrl": "/api/v1/ai/extract/batch/stream?batchId=batch_xyz&token=..."
  }
}
```

**SSE 事件**（`/api/v1/ai/extract/batch/stream?batchId=batch_xyz`）：
```
event: connected
data: {"connectionId":"...","serverTime":"..."}

event: progress
data: {"batchId":"batch_xyz","done":12,"total":58,"percent":21,"stage":"识别中"}

event: extracted
data: {
  "fileId": "f_5",
  "taskId": "task_5",
  "fields": { "invoiceNo": {"value":"12345678","confidence":99}, ... },
  "needsReview": true
}

event: summary
data: {"total":58,"success":45,"warning":10,"failed":3}

event: completed
data: {"batchId":"batch_xyz","finishedAt":"2024-05-21T10:23:18","costCents":12}

event: error
data: {"code":5102,"message":"单张图片识别超时","fileId":"f_23"}
```

#### 6.1.3 ✦ POST /ai/extract/apply

**用途**：用户修改 AI 抽取结果后，提交"实际值 vs AI 推测值"（用于模型迭代）

**请求**：
```json
{
  "taskId": "task_xyz",
  "type": "invoice",
  "originalFields": {                        // AI 原始输出
    "invoiceNo": {"value":"12345678","confidence":99},
    "taxRate":   {"value":0.06,"confidence":72}
  },
  "correctedFields": {                       // 用户修正后
    "taxRate":   {"value":0.13,"corrected":true}
  },
  "action": "save-to-form"                   // save-to-form | discard | re-extract
}
```

**响应**：
```json
{ "code": 0, "data": { "taskId": "task_xyz", "appliedToForm": true, "invoiceId": "inv_xxx" } }
```

**用途**：数据回流，模型持续学习。

---

### 6.2 风险识别

#### 6.2.1 ✦ POST /ai/risk/scan

**用途**：扫描单条业务对象的风险（项目/合同/费用/凭证）

**请求**：
```json
{
  "objectType": "project",                   // project | contract | expense | voucher
  "objectId": 123,
  "scanTypes": ["progress", "budget", "quality", "client", "compliance"],
                                              // 只扫指定类型（可选，默认全扫）
  "options": {
    "compareSimilar": true,                  // 与历史相似对象对比
    "deepScan": false                        // 是否深度分析（慢但准）
  }
}
```

**响应**：
```json
{
  "code": 0,
  "data": {
    "objectType": "project",
    "objectId": 123,
    "overallScore": 82,                      // 综合健康度 0-100
    "riskLevel": "medium",                   // low | medium | high
    "dimensions": {
      "progress": { "score": 90, "weight": 0.25 },
      "budget":   { "score": 75, "weight": 0.20, "issues": ["预计超支 8%"] },
      "quality":  { "score": 85, "weight": 0.20 },
      "risk":     { "score": 65, "weight": 0.20, "issues": ["M4 延期 5 天"] },
      "client":   { "score": 95, "weight": 0.15 }
    },
    "warnings": [
      {
        "id": "w_1",
        "level": "high",
        "type": "schedule_delay",
        "title": "M4 里程碑延期 5 天",
        "description": "M4 里程碑延期将影响 M5 启动时间，预计 M5 启动时间将推迟 5 天",
        "suggestion": "增派 1 名后端工程师 / 每日站会跟踪 / 提前与客户对齐 M5 范围",
        "confidence": 88,
        "dataPoints": {                       // 支撑这个警告的证据
          "milestoneId": 4,
          "plannedEnd": "2024-05-15",
          "actualEnd": null,
          "delayedDays": 5
        },
        "createdAt": "2024-05-21T10:00:00"
      }
    ],
    "suggestions": [
      {
        "id": "s_1",
        "title": "本周三组织 M5 验收对齐会",
        "description": "基于历史项目数据...",
        "action": {                           // 可执行动作
          "type": "create-meeting",
          "params": { "title": "M5 验收对齐会", "date": "2024-05-22" }
        },
        "confidence": 88
      }
    ],
    "similarObjects": [                       // 相似对象对比
      {
        "objectType": "project", "objectId": 100, "name": "数智化一期",
        "healthScore": 91, "delayDays": 0, "overBudget": -0.02
      }
    ],
    "meta": { "model": "risk-v2.3", "version": "2.3.1", "durationMs": 320, "costCents": 1 }
  }
}
```

#### 6.2.2 ✦ POST /ai/risk/warnings

**用途**：拉取某对象的所有风险（不含扫描，避免重复计算）

**请求**：
```json
{ "objectType": "project", "objectId": 123, "onlyActive": true }
```

**响应**：
```json
{
  "code": 0,
  "data": {
    "warnings": [ /* 同 6.2.1 warnings 结构 */ ],
    "lastScanAt": "2024-05-21T09:00:00",
    "stale": true                              // 是否需要重新扫描（> 24h）
  }
}
```

#### 6.2.3 ✦ POST /ai/risk/dismiss

**用途**：忽略/采纳某个风险

**请求**：
```json
{
  "warningId": "w_1",
  "action": "dismiss",                        // dismiss | accept | fix
  "remark": "已与客户沟通，延期可控"
}
```

---

### 6.3 智能问答（"问数"）

#### 6.3.1 ✦ POST /ai/ask/ask

**用途**：自然语言提问 → 查数据/文档/图表/草稿

**请求**：
```json
{
  "question": "本月哪些项目回款逾期了？",
  "context": {                                // 可选上下文
    "currentPage": "project",
    "currentFilters": { "status": "active" },
    "conversationId": "conv_xyz"              // 多轮对话
  },
  "options": {
    "stream": true,                           // 是否流式返回（SSE）
    "returnChart": true,                      // 是否生成图表
    "maxSources": 5                           // 最多引用数
  }
}
```

**响应（同步）**：
```json
{
  "code": 0,
  "data": {
    "answer": "本月共有 **3 个项目**回款逾期，合计金额 **¥2,340,000**：\n\n1. 数智化二期（逾期 3 天）\n2. 客户A 业务中台（逾期 7 天）\n3. 数据治理项目（逾期 15 天）\n\n[查看完整报告](#)",
    "answerType": "data",                     // data | doc | chart | draft
    "data": {                                  // 结构化数据（如有）
      "rows": [
        { "project": "数智化二期", "amount": 1580000, "overdueDays": 3 },
        { "project": "客户A 业务中台", "amount": 500000, "overdueDays": 7 },
        { "project": "数据治理项目", "amount": 260000, "overdueDays": 15 }
      ]
    },
    "chart": {                                 // 图表配置（如有）
      "type": "bar",
      "config": { /* ECharts option */ }
    },
    "sources": [                               // 引用
      {
        "type": "report",                      // report | record | doc
        "id": "r_123",
        "title": "6月回款统计表",
        "url": "/reports/123",
        "snippet": "...回款逾期 3 项..."
      }
    ],
    "conversationId": "conv_xyz",
    "messageId": "msg_abc",
    "meta": {
      "model": "qwen2.5-7b",
      "durationMs": 1820,
      "tokensUsed": 580,
      "costCents": 5
    }
  }
}
```

**SSE 流式响应**（`stream: true` 时）：
```
event: connected
data: {}

event: answer_chunk
data: {"content":"本月共有","isFinal":false}

event: answer_chunk
data: {"content":" **3 个项目**","isFinal":false}

event: answer_chunk
data: {"content":"回款逾期...","isFinal":true}

event: sources
data: [{"type":"report","id":"r_123",...}]

event: completed
data: {"messageId":"msg_abc","durationMs":1820,"tokensUsed":580}
```

#### 6.3.2 ✦ POST /ai/ask/feedback

**用途**：用户对答案反馈（数据回流）

**请求**：
```json
{
  "messageId": "msg_abc",
  "rating": "up",                            // up | down
  "reason": "incorrect",                     // 可选：incorrect | incomplete | not-helpful | other
  "comment": "漏了 5 月份已结清的 1 个"
}
```

#### 6.3.3 ✦ POST /ai/ask/suggestions

**用途**：推荐问题（Dashboard / 空状态展示）

**请求**：
```json
{ "page": "dashboard", "limit": 5 }
```

**响应**：
```json
{
  "code": 0,
  "data": {
    "suggestions": [
      { "text": "本月回款逾期了哪些？", "icon": "💰", "category": "risk" },
      { "text": "上周销售费用汇总",     "icon": "📊", "category": "report" },
      { "text": "客户A 今年的合同",     "icon": "🤝", "category": "client" }
    ]
  }
}
```

---

### 6.4 AI 提醒

#### 6.4.1 ✦ POST /ai/alert/today

**用途**：Dashboard 顶部"今日 AI 助手提醒"卡片

**请求**：
```json
{ "limit": 3 }
```

**响应**：
```json
{
  "code": 0,
  "data": {
    "total": 12,                              // 总未读
    "items": [
      {
        "id": "alert_1",
        "level": "high",                      // high | medium | low
        "type": "contract_overdue",           // 业务类型
        "title": "合同 C-2024-123 已逾期 3 天未签字",
        "summary": "金额 158 万，建议立即催办客户法务",
        "actionUrl": "/contract/detail/123",   // 点击跳转
        "actionLabel": "立即处理",
        "createdAt": "2024-05-21T09:00:00"
      }
    ]
  }
}
```

#### 6.4.2 ✦ POST /ai/alert/dismiss

```json
{ "alertId": "alert_1", "snoozeHours": 24 }
```

---

### 6.5 AI 任务中心

#### 6.5.1 ✦ POST /ai/task/list

**请求**：
```json
{
  "page": 1, "pageSize": 20,
  "status": "running",                       // running | done | failed | all
  "type": "extract"                          // extract | risk | match | agent | all
}
```

**响应**：
```json
{
  "code": 0,
  "data": {
    "list": [
      {
        "id": "task_xyz",
        "type": "extract",
        "name": "批量发票识别 - 差旅报销 5月",
        "status": "running",
        "progress": 0.4,
        "doneCount": 23, "totalCount": 58,
        "startedAt": "2024-05-21T10:00:00",
        "estimatedRemainingSec": 12
      }
    ],
    "total": 35
  }
}
```

#### 6.5.2 ✦ POST /ai/task/cancel
```json
{ "taskId": "task_xyz" }
```

---

### 6.6 模型管理（仅管理员）

#### 6.6.1 ✦ POST /ai/model/list

**响应**：
```json
{
  "code": 0,
  "data": {
    "models": [
      {
        "id": "paddleocr-v3",
        "name": "PaddleOCR 发票识别",
        "type": "ocr",
        "status": "healthy",                  // healthy | degraded | down | disabled
        "version": "1.2.0",
        "metrics": { "latencyMs": 400, "accuracy": 0.962, "qps": 5 },
        "config": {                           // 可调参数
          "confidenceThreshold": 0.7,
          "enableLineItems": true
        },
        "costPerCallCents": 0,
        "monthlyUsage": 18230
      }
    ]
  }
}
```

#### 6.6.2 ✦ POST /ai/model/config

```json
{
  "modelId": "paddleocr-v3",
  "config": { "confidenceThreshold": 0.6 },
  "enabled": true
}
```

---

### 6.7 反馈中心

#### 6.7.1 ✦ POST /ai/feedback/submit

**通用反馈**（用于所有 AI 输出的反馈，不限于 ask）：

```json
{
  "targetType": "extract",                   // extract | risk | ask | generate | match
  "targetId": "task_xyz",
  "rating": "up",                            // up | down
  "category": "accurate",                    // accurate | inaccurate | incomplete | not-helpful | other
  "comment": "税率识别有误，6% 应该是 13%",
  "tags": ["税率", "专票"]
}
```

---

### 6.8 全局 SSE 入口

#### 6.8.1 ✦ GET /api/v1/ai/stream

**用途**：多事件统一订阅入口（前端可一次性订阅所有 AI 事件）

**Query**：
```
?token=xxx&topics=task,risk,alert,ask
```

**事件**：
- `task.*`：所有任务事件
- `risk.*`：所有风险事件
- `alert.*`：所有提醒事件
- `ask.*`：问答完成事件
- `extract.*`：抽取完成事件

**数据**：
```
event: alert.new
data: {"alertId":"alert_1","level":"high","title":"..."}

event: extract.done
data: {"taskId":"task_xyz","invoiceId":"inv_xxx"}

event: risk.detected
data: {"objectType":"project","objectId":123,"level":"high","title":"..."}
```

---

## 7. 前端集成示例

### 7.1 字段抽取（一次性）

```typescript
async function extractInvoice(file: File) {
  // 1. 上传文件到 OSS
  const { fileId, fileUrl } = await uploadToOSS(file);

  // 2. 调用抽取
  const resp = await fetch('/api/v1/ai/extract/upload', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${getToken()}`,
      'X-Request-Id': uuid(),
    },
    body: JSON.stringify({
      fileId,
      fileUrl,
      type: 'invoice',
      options: { extractLineItems: true },
    }),
  });
  const { data } = await resp.json();

  // 3. 把字段填到表单（带置信度高亮）
  for (const [field, info] of Object.entries(data.fields)) {
    setFormField(field, info.value, info.confidence);  // ← confidence 决定高亮颜色
  }

  // 4. 智能关联建议
  if (data.suggestions.linkToContract) {
    showSuggestion(`关联到合同 ${data.suggestions.linkToContract}？`);
  }

  // 5. 标记需要复核的字段
  for (const [field, info] of Object.entries(data.fields)) {
    if (info.confidence < 70) {
      markFieldNeedReview(field, info.value, info.confidence);
    }
  }
}
```

### 7.2 批量抽取（SSE）

```typescript
async function batchExtract(fileIds: string[]) {
  // 1. 创建任务
  const { batchId, streamUrl } = await api('/ai/extract/batch/upload', { fileIds });

  // 2. 订阅 SSE
  const es = new EventSource(`${streamUrl}&token=${getToken()}`);

  es.addEventListener('extracted', (e) => {
    const { fileId, fields, needsReview } = JSON.parse(e.data);
    // 实时把单条结果加到列表
    addExtractedRow(fileId, fields, needsReview);
  });

  es.addEventListener('progress', (e) => {
    const { done, total, percent, stage } = JSON.parse(e.data);
    updateProgressBar(percent, `${stage} ${done}/${total}`);
  });

  es.addEventListener('completed', (e) => {
    es.close();
    showToast('批量识别完成', 'success');
  });

  es.addEventListener('error', (e) => {
    if (e.eventPhase === EventSource.CLOSED) {
      // 主动关闭
    } else {
      // 网络错误，30s 后重连
      showToast('连接中断，正在重连...', 'warning');
    }
  });

  return () => es.close();  // 返回 unsubscribe
}
```

### 7.3 风险扫描（详情页 Tab）

```typescript
async function loadProjectRiskTab(projectId: number) {
  const { data } = await api('/ai/risk/scan', {
    objectType: 'project',
    objectId: projectId,
  });

  // 健康度雷达图
  renderRadarChart(data.dimensions);

  // 风险列表
  renderWarnings(data.warnings);

  // 智能建议
  renderSuggestions(data.suggestions);

  // 相似项目对比
  renderSimilarProjects(data.similarObjects);

  // 时间线
  renderTimeline(data.warnings);
}
```

### 7.4 智能问答（流式）

```typescript
async function askAI(question: string, conversationId?: string) {
  const resp = await fetch('/api/v1/ai/ask/ask', {
    method: 'POST',
    body: JSON.stringify({
      question,
      context: { conversationId },
      options: { stream: true, returnChart: true },
    }),
  });

  const reader = resp.body.getReader();
  const decoder = new TextDecoder();
  let buffer = '';

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value);

    // 解析 SSE
    const lines = buffer.split('\n');
    buffer = lines.pop()!;
    for (const line of lines) {
      if (line.startsWith('data: ')) {
        const data = JSON.parse(line.slice(6));
        appendAnswerChunk(data.content);  // 实时追加
        if (data.isFinal) {
          // 流结束
        }
      }
    }
  }
}
```

---

## 8. 数据库扩展（在 BACKEND.md 之后追加）

> **原则**：新表 2 张，老表 0 schema 变更（只加可空字段）

### 8.1 新表

```sql
-- AI 任务表
CREATE TABLE ai_tasks (
    id BIGSERIAL PRIMARY KEY,
    task_id VARCHAR(64) UNIQUE NOT NULL,         -- 业务 ID（task_xxx）
    tenant_id BIGINT NOT NULL,
    type VARCHAR(32) NOT NULL,                    -- extract | risk | match | agent | generate
    sub_type VARCHAR(64),                          -- extract.invoice / risk.scan
    name VARCHAR(255),
    status VARCHAR(16) NOT NULL DEFAULT 'pending',-- pending | running | done | failed | cancelled
    progress DECIMAL(5,4) DEFAULT 0,
    total_count INT DEFAULT 0,
    done_count INT DEFAULT 0,
    failed_count INT DEFAULT 0,
    input JSONB,                                  -- 输入参数
    output JSONB,                                 -- 输出结果
    error JSONB,                                  -- 错误信息
    cost_cents INT DEFAULT 0,                     -- AI 调用成本
    created_by BIGINT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    started_at TIMESTAMPTZ,
    finished_at TIMESTAMPTZ,
    source VARCHAR(32) DEFAULT 'web',             -- web/ios/android/cron/api
    request_id VARCHAR(64),                       -- 关联请求 traceId
    ai_trace_id VARCHAR(64)                       -- AI 服务的 traceId
);
CREATE INDEX idx_ai_tasks_tenant_status ON ai_tasks(tenant_id, status);
CREATE INDEX idx_ai_tasks_created_at ON ai_tasks(created_at DESC);

-- AI 反馈表
CREATE TABLE ai_feedback (
    id BIGSERIAL PRIMARY KEY,
    tenant_id BIGINT NOT NULL,
    target_type VARCHAR(32) NOT NULL,             -- extract | risk | ask | generate
    target_id VARCHAR(64) NOT NULL,               -- 关联 ai_tasks.task_id
    user_id BIGINT NOT NULL,
    rating VARCHAR(8) NOT NULL,                   -- up | down
    category VARCHAR(32),                         -- accurate | inaccurate | ...
    comment TEXT,
    tags TEXT[],
    created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX idx_ai_feedback_target ON ai_feedback(target_type, target_id);
CREATE INDEX idx_ai_feedback_user ON ai_feedback(user_id, created_at DESC);

-- AI 提醒表（每日推送）
CREATE TABLE ai_alerts (
    id BIGSERIAL PRIMARY KEY,
    tenant_id BIGINT NOT NULL,
    user_id BIGINT,                               -- NULL = 全员
    level VARCHAR(8) NOT NULL,                    -- high | medium | low
    type VARCHAR(64) NOT NULL,                    -- 业务类型
    title VARCHAR(255) NOT NULL,
    summary TEXT,
    action_url VARCHAR(512),
    action_label VARCHAR(64),
    object_type VARCHAR(32),                      -- 关联对象
    object_id BIGINT,
    status VARCHAR(16) DEFAULT 'unread',          -- unread | read | dismissed
    dismiss_remark TEXT,
    snooze_until TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    read_at TIMESTAMPTZ
);
CREATE INDEX idx_ai_alerts_user_status ON ai_alerts(user_id, status, created_at DESC);
```

### 8.2 老表加可空字段（可选）

```sql
-- 项目表加 AI 字段
ALTER TABLE projects ADD COLUMN ai_health_score SMALLINT;
ALTER TABLE projects ADD COLUMN ai_risk_level VARCHAR(8);
ALTER TABLE projects ADD COLUMN ai_summary TEXT;
ALTER TABLE projects ADD COLUMN ai_last_scan_at TIMESTAMPTZ;
ALTER TABLE projects ADD COLUMN ai_extracted JSONB;  -- 通用 AI 数据
ALTER TABLE projects ADD COLUMN ai_confidence DECIMAL(5,2);

-- 合同表同样（用 script 一键加）
-- ALTER TABLE contracts ADD COLUMN ...
-- ALTER TABLE expenses ADD COLUMN ...
```

**所有字段都 NULLABLE**，不破坏老数据。

---

## 9. 配置项（.env 扩展）

```bash
# AI 总开关
AI_ENABLED=true
AI_DEFAULT_TIMEOUT=30                          # 秒
AI_MAX_FILE_SIZE_MB=20
AI_MAX_DOC_LENGTH_CHARS=50000

# 模型路由
AI_PROVIDER=paddleocr                          # paddleocr | qwen | local
AI_OCR_ENDPOINT=http://ocr-service:8001
AI_LLM_ENDPOINT=http://qwen-service:8002
AI_LLM_API_KEY=sk-xxx
AI_LLM_MODEL=qwen2.5-7b-instruct

# 兜底
AI_FALLBACK_OCR_ENABLED=true
AI_FALLBACK_NUONUO_APP_KEY=xxx
AI_FALLBACK_NUONUO_SECRET=xxx

# 限流
AI_RATE_LIMIT_PER_USER_PER_MIN=30              # 每用户每分钟
AI_RATE_LIMIT_PER_TENANT_PER_HOUR=5000
AI_COST_LIMIT_PER_TENANT_PER_DAY_CENTS=50000   # 每租户每天 500 元

# 提醒
AI_ALERT_SCAN_CRON=0 9 * * *                   # 每天 9 点扫一次
AI_ALERT_MAX_PER_USER_PER_DAY=10

# Sentry
SENTRY_DSN_AI=
```

---

## 10. 限流与降级

### 10.1 限流策略

| 维度 | 限制 | 超限返回 |
|------|------|---------|
| 单用户 | 30 次/分钟 | 3002 + `Retry-After` |
| 单租户 | 5000 次/小时 | 3002 |
| 单租户成本 | 500 元/天 | 3001 |
| 单图片 | 20MB | 3003 |
| 单文档 | 5 万字 | 3003 |

### 10.2 降级策略

| 场景 | 降级方案 |
|------|---------|
| AI 服务 5xx | 老流程照跑，UI 隐藏 AI 入口 |
| AI 超时 | 同上，提示"AI 服务繁忙" |
| 配额超限 | 软提示，3 次警告后才硬限 |
| 内容审核拒绝 | 静默降级 + 记日志（不告诉用户） |

**前端降级代码**（伪代码）：
```typescript
async function safeAICall<T>(api: () => Promise<T>, fallback: () => T): Promise<T> {
  try {
    return await api();
  } catch (e) {
    if (e.code >= 5000) {
      // AI 挂了，用老流程
      showToast('AI 服务暂不可用，已切换到普通模式', 'warning');
      reportSentry(e, { tags: { ai_degraded: true } });
      return fallback();
    }
    throw e;
  }
}
```

---

## 11. 性能与成本目标

| 指标 | 目标 | 监控 |
|------|------|------|
| 字段抽取单图 P95 | < 3s | Prometheus histogram |
| 风险扫描单条 P95 | < 1s | Prometheus histogram |
| 问答 P95 | < 5s | Prometheus histogram |
| SSE 连接数 | < 2000/实例 | Gauge |
| AI 服务可用性 | > 99.5% | Up{} 探针 |
| 每月 AI 成本 | < 2000 元/租户 | costCents 累加 |
| 字段抽取准确率 | > 90% | feedback 反馈回流 |
| 风险命中率 | > 70% | 用户采纳率 |

---

## 12. 与老 API 的关系（**无破坏**）

| 关系 | 说明 |
|------|------|
| **路径** | 老 `/api/v1/project/*` 不变；新 `/api/v1/ai/*` |
| **响应包装** | 沿用 `{code, message, data, traceId}` |
| **鉴权** | 沿用 Bearer Token |
| **错误码** | 沿用 1001-5003，**新增 3001-3003 + 5101-5104** |
| **SSE 协议** | 沿用 §实时通信约定，**新增 3 个事件**（extracted/risk_detected/answer_chunk） |
| **数据库** | 老表 0 schema 变更，新表 3 张 |
| **环境变量** | 老变量不动，新变量 `AI_*` 前缀 |
| **Redis** | 老 key 不动，新 key `ai:*` 前缀 |
| **审计** | 老审计中间件不动，新加 `source = "ai"` 标识 |

---

## 13. 上线检查清单

### 13.1 算法工程师交付前
- [ ] 模型服务已 Docker 化
- [ ] `/health` 端点返回正常
- [ ] 批量接口 P95 < 5s（100 张图）
- [ ] 准确率 > 90%（自测集）
- [ ] 接口文档（OpenAPI）已生成

### 13.2 后端交付前
- [ ] `ai_tasks` / `ai_feedback` / `ai_alerts` 3 张表 migration 已生成
- [ ] 限流配置已生效（Redis token bucket）
- [ ] 降级策略已测（断网 mock 5000）
- [ ] 监控指标已埋（costCents / durationMs / confidence）
- [ ] Sentry DSN 已配
- [ ] 审计日志已配（source = "ai"）

### 13.3 前端交付前
- [ ] `ai-*.html` 设计稿已实现
- [ ] SSE 客户端封装完成（含重连）
- [ ] 置信度高亮已统一封装
- [ ] 降级 UI 已处理
- [ ] 用户反馈按钮（👍👎）已加
- [ ] Loading 态已加（SSE 长任务）

### 13.4 PM 上线前
- [ ] AI 使用指南已写
- [ ] 用户培训已完成
- [ ] 反馈渠道已建（群/邮件）
- [ ] 成本监控已配（每日报表）
- [ ] 降级 SOP 已写（运维手册）

---

## 14. 未来扩展（Phase 2+）

| Phase | 能力 | 接口 |
|-------|------|------|
| **Phase 2** | 智能起草（合同/邮件） | `/ai/generate/*` |
| **Phase 2** | 银行流水智能匹配 | `/ai/match/*` |
| **Phase 3** | Agent 自动化（定时任务） | `/ai/agent/*` |
| **Phase 3** | 多轮对话 + 记忆 | `/ai/ask/conversation/:id` |
| **Phase 4** | 私有模型微调 | `/ai/model/train` |
| **Phase 4** | 跨租户共享知识库 | `/ai/kb/*` |

---

## 附录 A：完整接口清单（Phase 1，必出 18 个）

| # | 接口 | 类型 | 必出 |
|---|------|------|------|
| 1 | `POST /ai/extract/upload` | 同步 | ✦ |
| 2 | `POST /ai/extract/batch/upload` | 异步 | ✦ |
| 3 | `GET /ai/extract/batch/stream` | SSE | ✦ |
| 4 | `POST /ai/extract/apply` | 同步 | ✦ |
| 5 | `POST /ai/risk/scan` | 同步 | ✦ |
| 6 | `POST /ai/risk/warnings` | 同步 | ✦ |
| 7 | `POST /ai/risk/dismiss` | 同步 | ✦ |
| 8 | `POST /ai/ask/ask` | 同步/SSE | ✦ |
| 9 | `POST /ai/ask/feedback` | 同步 | ✦ |
| 10 | `POST /ai/ask/suggestions` | 同步 | ✦ |
| 11 | `POST /ai/alert/today` | 同步 | ✦ |
| 12 | `POST /ai/alert/dismiss` | 同步 | ✦ |
| 13 | `POST /ai/task/list` | 同步 | ✦ |
| 14 | `POST /ai/task/cancel` | 同步 | ✦ |
| 15 | `POST /ai/feedback/submit` | 同步 | ✦ |
| 16 | `POST /ai/model/list` | 同步 | ✦ |
| 17 | `POST /ai/model/config` | 同步 | ✦ |
| 18 | `GET /ai/stream` | SSE | ✦ |

占位（Phase 2/3）：
- `POST /ai/match/*` (3)
- `POST /ai/generate/*` (4)
- `POST /ai/agent/*` (4)

---

## 附录 B：变更历史

| 版本 | 日期 | 变更 |
|------|------|------|
| v0.9 | 2024-05-21 | 初稿（Phase 1） |

---

**核心承诺：这份接口契约落地后，老的 59 个接口 + 老架构 + 老数据库 0 变更。后端 leader 可以继续安心做合同/销售费用/回款模块，AI 这部分完全独立开发。**
