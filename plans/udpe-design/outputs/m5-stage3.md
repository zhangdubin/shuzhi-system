# M5 阶段 3 — 搜索增强 + 用量仪表盘

> **状态**: ✅ 已完成
> **日期**: 2026-06-28

## 一、搜索增强

✅ 全文搜索 — 搜索模板名称/code/描述 (客户端 computed 过滤)
✅ 排序选项 — 更新时间/名称/业务类型/状态
✅ 筛选栏新增搜索框 + 排序下拉

## 二、用量仪表盘

✅ 后端统计接口 GET /admin/print-stats (30 天维度)
✅ 统计指标: 总调用/成功/失败/平均耗时/PDF 总量
✅ 最近 7 天趋势条形图
✅ Top 5 热门模板标签
✅ 打印日志页顶部展示

## 三、文件改动

| 文件 | 改动 |
|------|------|
| `backend/app/modules/print_runtime/router.py` | +print-stats 端点 |
| `frontend/src/api/print.ts` | +getStats 方法 |
| `frontend/src/views/admin/AdminPrintTemplate.vue` | +搜索框 +排序 +filteredTemplates |
| `frontend/src/views/admin/AdminPrintLog.vue` | +用量统计仪表盘 |

## 四、统计接口响应

```json
{
  "total": 156, "success": 150, "failed": 6,
  "avgElapsedMs": 234.5, "totalPdfSizeMb": 12.3,
  "topTemplates": [{"code": "contract_v1", "count": 45}, ...],
  "daily": [{"date": "2026-06-22", "count": 12}, ...]
}
```

## 五、验证

```bash
cd frontend && npm run build → ✓ built in 5.90s, 0 错误
docker compose build backend → Image Built
```
