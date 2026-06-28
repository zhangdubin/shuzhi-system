# M4 阶段 7 — 二维码/条码组件

> **状态**: ✅ 已完成
> **日期**: 2026-06-28
> **前置**: M3 阶段 3 (可视化设计器), qrcode 库已安装
> **任务**: 模板中支持 QR Code 和 Code128 条码

## 一、产出

✅ qrcode 组件 (QR Code, 支持模板插值 + 自定义尺寸 + 标签)
✅ barcode 组件 (Code128 条码, 支持模板插值 + 自定义高度 + 标签)
✅ HTML 渲染器: QR 生成 PNG data URI, 条码用纯 CSS 竖条
✅ 前端: 组件库 + 画布预览 + 属性面板

## 二、文件改动

| 文件 | 改动 |
|------|------|
| `backend/app/modules/print_runtime/renderers/html_renderer.py` | +QR/barcode 渲染 |
| `frontend/src/components/admin/print/compTemplates.ts` | +qrcode/barcode 类型 |
| `frontend/src/components/admin/print/CanvasItem.vue` | +QR/barcode 预览 |
| `frontend/src/components/admin/print/PropertyPanel.vue` | +QR/barcode 属性 |

## 三、组件 Schema

```json
{ "type": "qrcode", "data": "{{ form.code }}", "size": 120, "label": "扫码查看" }
{ "type": "barcode", "data": "{{ form.formNo }}", "height": 50, "label": "单据编号" }
```

- `data`: 支持 `{{ path | filter }}` 模板插值
- `size/height`: 像素尺寸
- `label`: 可选标签文字

## 四、渲染方式

- **HTML 预览**: QR 生成 PNG → base64 data URI `<img>`, 条码用 CSS 竖条模拟
- **PDF (reportlab)**: 复用 HTML 渲染器输出 → WeasyPrint 转 PDF
- **PDF (WeasyPrint)**: 原生支持 `<img>` 标签

## 五、验证

```bash
cd frontend && npm run build → ✓ built in 5.55s, 0 错误
docker compose build backend → Image Built
```

## 六、设计器中的使用

1. 左侧组件库新增 "二维码" 和 "条码"
2. 点击/拖入画布
3. 右侧属性面板编辑: 数据路径 (支持字段树点选) + 尺寸 + 标签
4. 实时预览 iframe 显示渲染后的 QR/条码
