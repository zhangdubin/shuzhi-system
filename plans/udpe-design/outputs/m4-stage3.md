# M4 阶段 3 — 模板导入/导出

> **状态**: ✅ 已完成
> **作者**: Codex (GPT-5)
> **日期**: 2026-06-28
> **前置**: M3 阶段 4 (Excel/Word 导入)
> **任务**: 模板列表页加 JSON 文件的导入导出

## 一、目标与边界

模板管理需要备份、迁移、共享能力。M4 阶段 3 添加：

✅ 导出单个模板 — 操作列 "📤 导出" 按钮，下载 .json 文件
✅ 导出全部模板 — 页面头部 "📤 导出全部" 按钮，批量导出
✅ 导入 JSON — 页面头部 "📥 导入 JSON" 按钮，支持单个/批量导入

## 二、文件改动

| 文件 | 改动 |
|------|------|
| `frontend/src/views/admin/AdminPrintTemplate.vue` | 新增 3 个函数 + 3 个按钮 |

## 三、导出格式

```json
{
  "_udpe_export_version": 1,
  "_exported_at": "2026-06-28T14:30:00.000Z",
  "code": "contract_v1",
  "name": "合同模板 V1",
  "docType": "contract",
  "paper": "A4",
  "orientation": "portrait",
  "description": "",
  "isDefault": true,
  "schemaJson": { "body": [...] }
}
```

批量导出时外层包 `{ _count, templates: [...] }`。

## 四、导入逻辑

- 支持单个模板 JSON 和批量 JSON（检测 `templates` 字段）
- 必填校验: code + name + schemaJson
- 批量导入时自动追加后缀避免 code 冲突
- 导入后自动刷新列表
- 失败的单条跳过，不中断批量

## 五、验证

```bash
cd frontend && npm run build
# ✓ built in 5.50s, 0 错误
```

## 六、模板管理页功能全景

经过 M2-M4 多个阶段，模板列表页已具备完整管理能力：

| 功能 | 来源 |
|------|------|
| 列表 + KPI 统计 | M2 阶段 7 |
| 按业务类型/状态筛选 | M2 阶段 7 |
| 创建模板 | M2 阶段 7 |
| 编辑模板（跳转编辑器） | M3 阶段 1 |
| 查看 JSON | M2 阶段 7 |
| 发布/归档生命周期 | M2 阶段 7 |
| 删除模板 | 本轮修复 |
| 预览（HTML + PDF） | M2 阶段 8 |
| Excel 导入 | M3 阶段 4 |
| Word 导入 | M3 阶段 4 下半 |
| JSON 导入/导出 | M4 阶段 3 |
