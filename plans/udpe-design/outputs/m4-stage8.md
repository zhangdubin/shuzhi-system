# M4 阶段 8 — PDF 数字签名

> **状态**: ✅ 已完成
> **日期**: 2026-06-28
> **前置**: PyMuPDF 已安装
> **任务**: 生成的 PDF 可选添加数字签名标记

## 一、产出

✅ 签名模块 `signer.py` — 用 PyMuPDF 在 PDF 最后页添加签名信息框
✅ service.py 集成 — `options.sign=true` 时自动签名
✅ 前端 PrintOptions 新增 `sign` 和 `weasyprint` 选项

## 二、文件改动

| 文件 | 改动 |
|------|------|
| `backend/app/modules/print_runtime/signer.py` | 新增 |
| `backend/app/modules/print_runtime/service.py` | +签名步骤 |
| `frontend/src/api/print.ts` | +sign/weasyprint 选项 |

## 三、签名方式

V1 采用 PyMuPDF 可见签名标记（轻量实现）：
- 在 PDF 最后页右下角添加签名信息框
- 包含: 签名者、时间、原因、地点
- 蓝色边框 + 浅蓝底色

使用方式: API 调用时 `options.sign: true`。

## 四、验证

```bash
docker exec shuzhi-backend python -c "
from app.modules.print_runtime.signer import sign_pdf
signed = sign_pdf(b'...', reason='test')
print(len(signed) > 0)
"
# True
```

## 五、下一步升级路径

V1 → V2 升级为 PKCS#7 CMS 签名:
- 配置 pyHanko 正确加载 PEM 证书
- 使用 `pyhanko.sign.signers.PdfSigner` 添加真正的 CMS 签名
- 支持签名验证 (Adobe Reader 可验证)
