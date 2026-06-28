# M4 阶段 6 — 列表批量操作

> **状态**: ✅ 已完成
> **日期**: 2026-06-28

## 一、产出

✅ el-table 复选框列
✅ 批量操作栏（选中后浮现）
✅ 批量发布 / 批量归档 / 批量删除

## 二、文件改动

| 文件 | 改动 |
|------|------|
| `frontend/src/views/admin/AdminPrintTemplate.vue` | +selection 列 + batch bar + 3 个批量函数 |

## 三、批量操作逻辑

- **批量发布**: 过滤出 draft 状态的模板，逐个调 publishTemplate
- **批量归档**: 过滤出 active 状态的模板，逐个调 archiveTemplate
- **批量删除**: 过滤出非 active 状态的模板，逐个调 deleteTemplate
- 每个操作前弹确认框
- 操作完成后刷新列表 + 清空选中

## 四、验证

```bash
cd frontend && npm run build → ✓ built in 5.84s, 0 错误
```
