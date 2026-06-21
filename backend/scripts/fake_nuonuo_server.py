"""
本地测试用 诺诺发票云 mock 服务（端口 8002）
按诺诺开放平台真实协议：
  POST /open/v1/services  →  鉴权 + 签名 + 业务 body  →  {code: E0000, result: {success, ...}}
  GET  /health
"""
import hashlib
import hmac
import base64
import secrets
import time
import json
import random
import string
from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

app = FastAPI(title="Nuonuo Mock Service", version="1.0")
app.add_middleware(
    CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"],
)

# 模拟沙箱的 appKey / appSecret
SANDBOX_APP_KEY = "SD63236305"
SANDBOX_APP_SECRET = "SDDED2523BED4643"


def _make_sign(secret: str, payload: str) -> str:
    """诺诺签名：MD5(secret + body + secret) → base64"""
    raw = secret + payload + secret
    md5 = hashlib.md5(raw.encode("utf-8")).digest()
    return base64.b64encode(md5).decode("utf-8")


@app.get("/health")
async def health():
    return {"status": "ok", "service": "nuonuo-mock", "version": "v1"}


@app.post("/open/v1/services")
async def services(request: Request):
    """诺诺开放平台统一入口"""
    body_bytes = await request.body()
    body = json.loads(body_bytes)

    # 鉴权
    sign = request.headers.get("X-Nuonuo-Sign", "")
    access_token = request.headers.get("accessToken", "")
    method = request.headers.get("method", "")
    user_tax = request.headers.get("userTax", "")

    # 验签（mock 总是通过，因为签的是 secret）
    expected_sign = _make_sign(SANDBOX_APP_SECRET, body_bytes.decode("utf-8"))
    # mock 模式不严格验签（防止本地测试时差）

    if method == "nuonuo.ElectronInvoice.otherInvoiceCheck":
        return _handle_invoice_check(body, sign, access_token, method, user_tax)
    elif method == "nuonuo.ElectronInvoice.queryInvoiceCheck":
        return _handle_query_invoice_check(body)
    else:
        return {"code": "E1001", "describe": f"未知 method: {method}", "result": {}}


def _handle_invoice_check(body, sign, access_token, method, user_tax):
    """发票查验"""
    invoice_no = body.get("invoiceNumber", "")
    invoice_code = body.get("invoiceCode", "")
    tax_num = body.get("taxNum", "")
    total_amount = body.get("totalAmount", "")

    # mock 结果按 invoiceNumber 后 4 位 mod 5 决定
    if not invoice_no or len(invoice_no) < 4:
        bucket = 4
    else:
        try:
            bucket = int(invoice_no[-4:]) % 5
        except ValueError:
            bucket = 4

    result_map = {
        0: ("pass", None, "查得该发票正常，购销方信息一致"),
        1: ("pass", None, "查得该发票正常"),
        2: ("risk", "购方企业名称与历史比对存在差异，建议人工复核", "查得该发票存在疑点"),
        3: ("repeat", "该发票已被报销过，请检查是否重复入账", "查得该发票存在重复报销"),
        4: ("not_found", "未在国税总局数据库中查到该发票", "查无此发票"),
    }
    result, risk_reason, describe = result_map[bucket]

    return {
        "code": "E0000",
        "describe": "成功",
        "result": {
            "success": "true",
            "checkResult": result,
            "invoiceNumber": invoice_no,
            "invoiceCode": invoice_code,
            "taxNum": tax_num,
            "totalAmount": total_amount,
            "describe": describe,
            "riskReason": risk_reason,
            "invoiceDate": body.get("invoiceDate", ""),
            "invoiceType": body.get("invoiceType", ""),
        },
    }


def _handle_query_invoice_check(body):
    """批量查验（占位）"""
    return {
        "code": "E0000",
        "describe": "成功",
        "result": {"success": "true", "items": []},
    }


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8002, log_level="warning")
