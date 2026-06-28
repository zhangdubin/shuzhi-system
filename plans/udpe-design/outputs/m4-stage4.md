# M4 阶段 4 — 模板版本历史

> **状态**: ✅ 已完成
> **日期**: 2026-06-28
> **前置**: M3 阶段 1 (模板编辑器, 含版本快照)
> **任务**: 版本历史 UI + 回滚功能

## 一、产出

✅ 后端 3 个端点: 版本列表 / 版本详情 / 回滚
✅ 前端 API 3 个方法: listVersions / getVersion / restoreVersion
✅ VersionHistoryDialog 组件: 版本时间线 + 预览 + 回滚

## 二、文件改动

### 新增
| 文件 | 用途 |
|------|------|
| `frontend/src/components/admin/print/VersionHistoryDialog.vue` | 版本历史对话框 |

### 修改
| 文件 | 改动 |
|------|------|
| `backend/app/modules/print_runtime/router.py` | +3 端点 (versions / version detail / restore) |
| `frontend/src/api/print.ts` | +3 方法 |
| `frontend/src/views/admin/AdminPrintTemplate.vue` | 接入版本历史按钮 + 对话框 |

## 三、接口设计

### GET /admin/print-templates/{tid}/versions
返回版本列表 (version, note, snapshotAt, snapshotBy)

### GET /admin/print-templates/{tid}/versions/{ver}
返回版本详情 (含完整 schemaJson)

### POST /admin/print-templates/{tid}/restore
回滚到指定版本。当前状态自动保存为快照 (回滚前快照)。

## 四、回滚安全策略

回滚前自动将当前状态保存为新版本快照，确保：
- 回滚操作可逆（不会丢失任何历史）
- 版本号单调递增（回滚后 version > 原 version）
- 打印日志保留（不因回滚丢失审计记录）

## 五、验证

```bash
cd frontend && npm run build → ✓ built in 5.59s, 0 错误
docker compose build backend → Image Built
docker compose up -d --no-deps backend → Started
```

## 六、列表页功能全景 (更新)

| 功能 | 来源 |
|------|------|
| 列表 + KPI + 筛选 | M2-7 |
| 创建 / 编辑 / 删除 / 发布 / 归档 | M2-7 + 修复 |
| JSON 可视化编辑器 + 设计器 | M3-1 ~ M3-6 |
| Excel / Word 导入 | M3-4 |
| JSON 导入/导出 | M4-3 |
| 预览 (HTML + PDF) | M2-8 |
| **版本历史 + 回滚** | **M4-4** |
