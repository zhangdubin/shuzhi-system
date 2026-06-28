# M3 阶段 2 — Excel 模板转 UDPE schemaJson

> 阶段：M3 阶段 2（基于 M3 阶段 1 的编辑器）  
> 完成日期：2026-06-28  
> 源文件：`/Users/trisome/Desktop/报销单模板自行打印.xlsx`  
> 产物：`plans/udpe-design/outputs/m3-stage2-excel-reimbursement.json`

## 任务

把 Excel 模板「报销单模板自行打印.xlsx」转成 UDPE 体系的 `schemaJson`，形成可用的打印模板。

## Excel 模板分析

**结构**（每张单据占 15 行 × 7 列）：

| 行 | 内容 | 合并 |
|---|------|------|
| 1 | 标题「费 用 报 销 单」 | A1:G1 |
| 2 | 年月日 | C2:E2 |
| 3-6 | 费用摘要（label + value） | A3:A6 / B3:G6 |
| 7-10 | 金额大写 + 金额小写 | A7:A10 / B7:E10 / F7:F10 / G7:G10 |
| 11-14 | 备注 + 附单据张数 | A11:A14 / B11:D14 / E11:E14 / F11:G14 |
| 15 | 签字栏（核准/审批/会计/报销人） | 4 列分别 |

**示例**（Sheet1 内 2 张单据）：
- 单据 1：退票费 ¥98.50（98.5 元 / 2 张附单据）
- 单据 2：商务采购 ¥4,698.00（4698 元 / 1 张附单据）

**视觉特征**：黑体 11pt / 24pt 标题黑体加粗 / 列合并 / 单元格边框。

## 复刻策略

| Excel 视觉 | UDPE 渲染 |
|----------|----------|
| 单元格边框 | 用 `<hr>` 线条替代（renderer 不支持边框） |
| 多列布局 | 用 text + spacer 串接（label 一行 + value 一行） |
| 标题加粗 | title type 渲染为 `<h1>` 加粗 |
| 字号 | 复刻 11pt / 14pt / 16pt / 22pt |
| 颜色 | 蓝/红强调色保留 |

**注意**：HTML renderer 当前不支持单元格边框（要等 M3 阶段 2+ 上设计器时升级 box 类型）。本阶段以"信息完整 + 结构清晰"为优先，视觉差异可接受。

## 数据字段映射

| Excel 字段 | UDPE 绑定 | 备注 |
|----------|----------|------|
| 标题「费 用 报 销 单」 | 硬编码 | - |
| 年月日 | `{{ printTime \| date }}` | 复用 system 变量 |
| 费用摘要 | `{{ form.title }}` | 报销单标题 |
| 金额（大写） | `{{ form.totalAmount \| chinese_money }}` | 分转大写元 |
| 金额（小写） | `{{ form.totalAmount \| money }}` | 分转元（已含 ¥） |
| 备注 | `{{ form.remark \| default('（无）') }}` | 报销单备注 |
| 附单据张数 | `{{ form.detailCount }}` | 明细项数 |
| 报销人 | `{{ form.applicantName \| default(form.applicant.name) }}` | 多字段兜底 |
| 核准/审批/会计 | `____________________` | 数据库无字段，留空下划线 |
| 打印时间 | `{{ printTime \| datetime }}` | system |
| 打印人 | `{{ printUser }}` | system |

**关键适配**：
- `form.totalAmount` 数据库存的是**分（int）**，`money` / `chinese_money` filter 自动转元
- `form.applicant` 在数据库有多个字段（`applicantName` 顶层 + `applicant.name` 对象），用 `default` 兜底

## 创建的模板

```
code:        reimbursement_simple_v1
name:        费用报销单（Excel 复刻·极简版）
docType:     reimbursement
paper:       A4 portrait
schemaJson:  { body: [49 blocks] }
status:      active
```

**与现有 reimbursement_v1 的区别**：
- 现有 v1：含明细表（5 笔以上费用时用）
- 新 simple_v1：极简版（单笔费用，字段对照 Excel）

## 端到端验证

### 1. 后端预览 (`/print/preview-schema`)

```
Form 3 (RB-20260624-1CE6):
  费 用 报 销 单
  报销编号：RB-20260624-1CE6
  费用摘要：长沙国科大论证出差
  金额（大写）：叁拾肆万零玖佰伍拾元整
  金额（小写）：¥ 340,950.00
  备注：长沙国科大论证出差
  附单据张数：8 张
  报销人：张斌

Form 4 (RB-20260624-59D4):
  费 用 报 销 单
  报销编号：RB-20260624-59D4
  费用摘要：标书打印费
  金额（大写）：贰佰捌拾贰万玖仟贰佰柒拾伍元整
  金额（小写）：¥ 2,829,275.00
  附单据张数：2 张
  报销人：张斌
```

### 2. 后端走模板路径 (`/print/preview`)

- `templateCode: reimbursement_simple_v1` + `data: {_resolver: "4"}`
- 200 OK, elapsedMs=2

### 3. PDF 导出 (`/print/pdf`)

- 200 OK, Content-Type: application/pdf
- 文件大小 3973 字节 / 2 pages
- X-Print-Log-Id: 78

### 4. 模板编辑器 (`/admin/print-template/editor/6`)

- 加载模板成功
- 实时预览 iframe 显示完整渲染
- 已发布状态 / v2 版本

### 5. 打印模板列表 (`/admin/print-template`)

- 显示 5 个模板（含新 reimbursement_simple_v1）
- KPI 自动更新（5 / 5 / 0 / 0 / 4）

## 修复的 SDK bug

**前端 `printApi.updateTemplate` 用 body 传 id，后端要 query `tid=`**：

```ts
// 修复前 (错)
return (await http.post('/admin/print-templates/update', { id, ...payload }))

// 修复后 (对)
return (await http.post(`/admin/print-templates/update?tid=${tid}`, payload))
```

之前前端调更新会 422，现在修复后正常。

## 截图

- `/tmp/expense_editor.png` — 编辑器中查看 reimbursement_simple_v1
- `/tmp/expense_list.png` — 列表页显示 5 个模板
- `/tmp/expense_detail_print.png` — 报销详情页按模板打印（旧模板仍生效）

## 产物文件

| 文件 | 说明 |
|------|------|
| `plans/udpe-design/outputs/m3-stage2-excel-reimbursement.json` | 模板 JSON 完整结构 |
| `plans/udpe-design/outputs/m3-stage2.md` | 本报告 |
| 数据库 `print_templates` id=6 | 已发布 active |

## 后续可做

- 报销详情页的「按模板打印」按钮改 hardcode 到 `reimbursement_simple_v1`（单笔时）或保留 `reimbursement_v1`（明细时）
- M3 阶段 2+ 上 box 类型 block 后，可以 1:1 复刻 Excel 单元格边框
- 同一 Excel 复刻到合同 / 发票 / 费用 / 付款申请等单据
