# R12 PaddleOCR 真实切真报告

**日期**：2026-06-15
**耗时**：~5 分钟（摸底+切真+E2E+汇报）
**父 session 拍板**：直接切真

## 摸底结论
- 主机：**Apple M4**（macOS Apple Silicon，无 NVIDIA GPU）
- OCR 服务：**shuzhi-ocr-service 容器已部署**（172.19.0.4:8001，deploy_shuzhi-net 网络）
- 模型：**ch_PP-OCRv4**（CPU 版 PaddleOCR，无需 GPU）
- 容器内连通性：`http://shuzhi-ocr-service:8001/health` → 200 OK ✓
- 之前 /health OCR=down 真因：settings.OCR_SERVICE_URL 默认 `http://localhost:8001`（容器内 localhost = 自己，连不上）

## 切真动作
**Backend 三连**（stop+rm+run）加 env：
- `SHUZHI_OCR_SERVICE_URL=http://shuzhi-ocr-service:8001`
- `SHUZHI_OCR_MODE=real`

## 验证结果
### 1. /health 健康检查
```json
"integrations": {
  "ocr": {
    "status": "ok",
    "data": {"status":"ok","service":"paddleocr","version":"1.0.0","model":"ch_PP-OCRv4"}
  },
  "nuonuo": {"status": "mock", "mode": "mock"}
}
```
OCR status: **ok** ✓

### 2. Prometheus 指标
```
shuzhi_business_ocr_total{mode="real",status="success"} 1.0
```
mode=**real** ✓，识别成功 1 次

### 3. E2E test-08 真发票识别
测试发票：`e2e/fixtures/invoice-茶馆-20260517.png`（161KB）
- HTTP 200，ocrStatus=success
- 综合置信度：**0.941**
- 字段验证 **7/7 全通过**：
  - ✅ invoiceNo = 26112000001961698396
  - ✅ issueDate = 2026-05-17
  - ✅ buyerName = 中科世通亨奇（北京）科技有限公司
  - ✅ sellerName = 北京逐鹿茶艺有限责任公司西直门店
  - ✅ totalAmount = 248
  - ✅ taxAmount = 14.04
  - ✅ taxRate = 0.06

### 4. 性能
- 真实 PaddleOCR 识别耗时：**2528ms**（单张发票端到端）
- 期间 elapsed 2.4s 包含 OCR 推理（CPU 慢但可接受）

## 截图归档
- `docs/screenshots/compare/2-real-r12-01-health-ocr-real.png`（/health 状态）

## 结论
🎉 **R12 PaddleOCR 真接入切真 100% 成功**！OCR 集成从 mock 完整切到 real。
- 服务可达 + URL 配对 + 切真后接口/指标/E2E 全绿
- 后续可承接发票识别业务（R13 候选方向：发票/合同/项目 业务全用真 OCR）

## R13 候选（待父 session 拍板）
1. **真诺诺切真**（资质已申请，1-3 工作日到位）
2. **真实集成上线全流程**（一键脚本 + smoke test + 切真演练）
3. **PWA 移动端**（基于 R10 暗色模式 + 移动端适配）
4. **压测 + 性能极限**（locust/k6 压核心 12 接口）
