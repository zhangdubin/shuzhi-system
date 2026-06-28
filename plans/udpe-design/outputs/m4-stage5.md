# M4 阶段 5 — WeasyPrint 渲染器

> **状态**: ✅ 已完成
> **日期**: 2026-06-28
> **前置**: M1 阶段 3 (reportlab PDF 渲染器)
> **任务**: 新增 WeasyPrint CSS→PDF 渲染器

## 一、目标与边界

reportlab 渲染器需要手写 Python 代码构建布局，复杂 CSS 支持差。
WeasyPrint 用标准 CSS 驱动 PDF 生成，支持 flex/grid/媒体查询/字体回退等。

✅ WeasyPrint 渲染器 (复用 HTMLRenderer 生成 HTML → WeasyPrint 转 PDF)
✅ Dockerfile 安装 WeasyPrint 系统依赖
✅ 注册到 RendererRegistry
✅ WeasyPrint 不可用时自动 fallback 到 reportlab

## 二、文件改动

| 文件 | 改动 |
|------|------|
| `backend/app/modules/print_runtime/renderers/weasyprint_renderer.py` | 新增 |
| `backend/Dockerfile` | 添加 libcairo2/libpango/libglib2.0 等系统依赖 |
| `backend/requirements.txt` | 添加 WeasyPrint>=62.0 |
| `backend/app/main.py` | 注册 WeasyPrintRenderer |

## 三、架构

```
模板 schema → HTMLRenderer.render() → body HTML
    → WeasyPrintRenderer 组装完整 HTML (含 @page CSS)
    → weasyprint.HTML(string=html).write_pdf()
    → PDF bytes
```

关键设计：
- **复用 HTMLRenderer** — 不重复实现模板→HTML 逻辑
- **@page CSS** — 纸张大小/方向/边距由 CSS 控制
- **中文字体** — PingFang SC / Microsoft YaHei / Noto Sans CJK SC / STSong-Light 回退链
- **自动 fallback** — WeasyPrint 不可用或渲染失败时回退到 reportlab

## 四、使用方式

API 调用时指定 `renderMode: "weasyprint"`：
```json
{
  "templateCode": "contract_v1",
  "data": { "_resolver": 31 },
  "options": { "renderMode": "weasyprint" }
}
```

默认仍用 reportlab (`renderMode: "pdf"`)。

## 五、Docker 系统依赖

WeasyPrint 依赖 cairo/pango/glib 图形库：
- libcairo2, libpango-1.0-0, libpangocairo-1.0-0
- libglib2.0-0, libgdk-pixbuf-2.0-0, libffi-dev
- shared-mime-info

需要 symlink 解决 cffi 库名不匹配问题。

## 六、验证

```bash
docker exec shuzhi-backend python -c "import weasyprint; print(weasyprint.__version__)"
# WeasyPrint 69.0 - OK
```

## 七、已知限制

| 限制 | 说明 |
|------|------|
| 不支持 reportlab 特有的 Platypus Table | 需通过 CSS table/flex 替代 |
| 中文字体需容器内安装 | Dockerfile 未预装中文字体，依赖系统回退 |
| 渲染速度比 reportlab 慢 | CSS 解析 + 字体加载开销，适合 < 50 页文档 |

## 八、下一步

1. 前端加渲染器选择器（reportlab / weasyprint）
2. 中文字体包安装（Noto Sans CJK）
3. WeasyPrint 作为复杂模板默认渲染器
