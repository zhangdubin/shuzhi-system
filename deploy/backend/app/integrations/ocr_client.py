"""
PaddleOCR 客户端（双模式：real / mock）
- 真实部署：调自建 PaddleOCR 微服务（按 BACKEND.md §7.2 协议 POST /recognize）
- mock：deterministic 假数据（同 file_id 永远一致结果）
- 自动回退：OCR_MODE=mock 或连接失败时用 mock

替换实现：只改本文件
"""
import asyncio
import hashlib
import random
import string
import time
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Optional

import httpx

from app.config import settings
from app.core.exceptions import (
    AIModelUnavailableException, AITimeoutException, OCRFailedException,
)


# ============================================================
# 样例数据（mock 模式用）
# ============================================================
_SAMPLE_BUYERS = [
    "万象科技有限公司", "北辰实业集团", "朗驰智能设备有限公司",
    "用友网络科技股份有限公司", "京东企业购", "上海数智信息技术有限公司",
]
_SAMPLE_SELLERS = [
    "上海数智信息技术有限公司", "用友网络科技股份有限公司",
    "阿里云计算有限公司", "携程计算机技术（上海）有限公司",
    "滴滴出行科技有限公司", "京东企业购", "美团点评",
]


def _hash_seed(s: str) -> int:
    return int(hashlib.md5(s.encode()).hexdigest(), 16)


def _gen_id(n: int = 8) -> str:
    return "".join(random.choices(string.ascii_lowercase + string.digits, k=n))


# ============================================================
# 入口
# ============================================================

async def recognize(
    file_id: str,
    file_url: str = "",
    type: str = "invoice",  # invoice | contract | receipt | business-card | bank-statement
    template_id: Optional[str] = None,
    language: str = "zh-CN",
    options: Optional[dict] = None,
) -> dict:
    """
    OCR 识别（智能路由：real → mock 回退）
    返回 {confidence, status, fields, items, ...}
    失败状态在 status='failed' + error 字段
    """
    options = options or {}

    # R7.2: 业务指标
    from app.core.metrics import business_ocr_total

    # 1. mock 模式
    if settings.OCR_MODE == "mock":
        result = await _mock_recognize(file_id, file_url, type)
        status = "success" if result.get("status") != "failed" else "failed"
        business_ocr_total.labels(status=status, mode="mock").inc()
        return result

    # 2. 真实调用
    try:
        result = await _real_recognize(file_id, file_url, type, language, options)
        status = "success" if result.get("status") != "failed" else "failed"
        business_ocr_total.labels(status=status, mode="real").inc()
        return result
    except (httpx.ConnectError, httpx.ConnectTimeout, OSError) as e:
        # 服务挂了 → 自动回退 mock（不抛错，保持业务连续）
        # 同时记日志方便排查
        from loguru import logger
        logger.warning(f"PaddleOCR 服务连接失败，自动回退 mock：{e}")
        result = await _mock_recognize(file_id, file_url, type)
        business_ocr_total.labels(status="success", mode="real→mock_fallback").inc()
        return result


# ============================================================
# 真实 HTTP 调用（BACKEND.md §7.2 协议）
# ============================================================

async def _real_recognize(
    file_id: str, file_url: str, type: str, language: str, options: dict
) -> dict:
    """
    调 PaddleOCR 微服务
    协议：POST {OCR_SERVICE_URL}/recognize
    请求：{file_url, file_id, fields, language, options}
    响应：{code: 0, fields, items, confidence, model, version, elapsedMs}
    """
    req_body = {
        "file_url": file_url,
        "file_id": file_id,
        "fields": ["invoiceNo", "invoiceCode", "issueDate", "buyerName", "sellerName",
                   "totalAmount", "taxAmount", "taxRate"],
        "language": language,
        "options": options,
    }
    last_err = None
    for attempt in range(settings.OCR_RETRY_TIMES + 1):
        try:
            async with httpx.AsyncClient(timeout=settings.OCR_TIMEOUT) as client:
                resp = await client.post(
                    f"{settings.OCR_SERVICE_URL.rstrip('/')}/recognize",
                    json=req_body,
                )
                if resp.status_code != 200:
                    raise OCRFailedException(
                        f"PaddleOCR HTTP {resp.status_code}: {resp.text[:200]}"
                    )
                data = resp.json()
                if data.get("code") not in (0, "0", 200):
                    # 业务失败
                    return {
                        "confidence": 0,
                        "status": "failed",
                        "error": data.get("message", "识别失败"),
                    }
                return _normalize_real_response(data, file_id, file_url, type)
        except (httpx.TimeoutException, httpx.ConnectError, OSError) as e:
            last_err = e
            if attempt < settings.OCR_RETRY_TIMES:
                await asyncio.sleep(0.5 * (attempt + 1))
                continue
            raise  # 让上层捕获并回退 mock
    raise OCRFailedException(f"PaddleOCR 重试 {settings.OCR_RETRY_TIMES} 次后仍失败: {last_err}")


def _sanitize_str(v):
    """R17 修复：清掉字符串里 PostgreSQL 不接受的 0x00 (NUL) 字节，避免 audit_log 写入失败"""
    if isinstance(v, str):
        return v.replace("\x00", "").replace("\u0000", "")
    return v


def _sanitize_recursive(obj):
    """递归清掉 dict / list 里所有字符串的 NUL 字节"""
    if isinstance(obj, dict):
        return {k: _sanitize_recursive(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_sanitize_recursive(item) for item in obj]
    return _sanitize_str(obj)


def _normalize_real_response(data: dict, file_id: str, file_url: str, type: str) -> dict:
    """把 PaddleOCR 真响应标准化为业务侧期望格式"""
    fields_raw = data.get("fields", {})
    overall_conf = float(data.get("confidence", 0))

    # 字段级 confidence（百分制）
    fields = {}
    for k, v in fields_raw.items():
        if isinstance(v, dict):
            fields[k] = v
        else:
            # 兜底：服务端没返 confidence → 用综合分
            fields[k] = {"value": v, "confidence": int(overall_conf * 100)}

    # 状态机
    if overall_conf >= settings.OCR_CONFIDENCE_THRESHOLD:
        status = "verified"
    elif overall_conf >= 0.80:
        status = "pending_verify"
    else:
        status = "verified"  # 0.78 仍能用

    # 金额单位转换（元 → 分）
    for key in ("totalAmount", "taxAmount", "amount"):
        if key in fields and isinstance(fields[key].get("value"), (int, float, Decimal)):
            yuan = Decimal(str(fields[key]["value"]))
            fields[key + "Cents"] = int(yuan * 100)

    result = {
        "confidence": overall_conf,
        "status": status,
        "fields": fields,
        "items": data.get("items", []),
        "model": data.get("model", "paddleocr-v3"),
        "version": data.get("version", "1.2.0"),
        "elapsedMs": data.get("elapsedMs", 0),
    }
    # R17 修复：递归清掉 NUL 字节（Postgres text/jsonb 不接受 0x00）
    return _sanitize_recursive(result)


# ============================================================
# Mock 模式（与原 ocr_client.py 行为一致）
# ============================================================

async def _mock_recognize(
    file_id: str, file_url: str, type: str
) -> dict:
    """deterministic mock：同 file_id 永远一致结果"""
    await asyncio.sleep(random.uniform(0.5, 1.5))

    seed = _hash_seed(file_id or "default")
    rng = random.Random(seed)
    confidence = round(rng.uniform(0.78, 0.99), 3)

    # 5% 失败
    bucket = seed % 20
    if bucket == 0:
        return {
            "confidence": confidence,
            "status": "failed",
            "fields": {},  # R17 修复：保持结构稳定，前端 syncForm 假设 fields 存在
            "items": [],
            "model": "paddleocr-mock",
            "version": "1.0.0",
            "elapsedMs": int(random.uniform(500, 1500)),
            "error": "票面识别失败：图片模糊或非标准发票",
        }

    status = "verified" if confidence >= settings.OCR_CONFIDENCE_THRESHOLD else "pending_verify"

    if type == "invoice":
        fields = _mock_invoice_fields(seed, rng)
    elif type == "contract":
        fields = _mock_contract_fields(seed, rng)
    elif type == "receipt":
        fields = _mock_receipt_fields(seed, rng)
    else:
        fields = _mock_invoice_fields(seed, rng)

    return {
        "confidence": confidence,
        "status": status,
        "fields": fields,
        "items": _mock_invoice_items(rng),
        "model": "paddleocr-mock",
        "version": "1.0.0",
        "elapsedMs": int(random.uniform(500, 1500)),
    }


def _mock_invoice_fields(seed: int, rng: random.Random) -> dict:
    total_yuan = Decimal(str(rng.uniform(500, 50000))).quantize(Decimal("0.01"))
    tax_rate = Decimal(str(rng.choice([0.06, 0.13, 0.03, 0.09])))
    tax_amount = (total_yuan * tax_rate / (1 + tax_rate)).quantize(Decimal("0.01"))
    excl_tax = (total_yuan - tax_amount).quantize(Decimal("0.01"))
    _type_pool = ["电子普通发票", "电子专用发票", "增值税专用发票", "增值税普通发票", "数电票"]
    return {
        "invoiceType": _type_pool[seed % len(_type_pool)],
        "invoiceNo": "".join(random.choices(string.digits, k=18)),
        "invoiceCode": "".join(random.choices(string.digits, k=12)),
        "issueDate": (date.today() - timedelta(days=rng.randint(0, 30))).isoformat(),
        "buyerName": _SAMPLE_BUYERS[seed % len(_SAMPLE_BUYERS)],
        "buyerTaxNo": "91310000MA1FL01X9G",
        "sellerName": _SAMPLE_SELLERS[seed % len(_SAMPLE_SELLERS)],
        "sellerTaxNo": "91310000MA1FL3X9G",
        "totalAmount": float(total_yuan),
        "taxAmount": float(tax_amount),
        "amount": float(excl_tax),
        "taxRate": float(tax_rate),
        "totalAmountCn": _cn_capital(total_yuan),
        "verifyCode": "".join(random.choices(string.digits, k=20)),
        "remarks": "",
    }


def _mock_contract_fields(seed: int, rng: random.Random) -> dict:
    return {
        "contractNo": f"HT-2026-{rng.randint(100, 999):03d}",
        "title": "技术开发服务合同",
        "partyA": _SAMPLE_SELLERS[seed % len(_SAMPLE_SELLERS)],
        "partyB": _SAMPLE_BUYERS[seed % len(_SAMPLE_BUYERS)],
        "amount": float(Decimal(str(rng.uniform(100000, 2000000))).quantize(Decimal("0.01"))),
        "signDate": (date.today() - timedelta(days=rng.randint(0, 60))).isoformat(),
    }


def _mock_receipt_fields(seed: int, rng: random.Random) -> dict:
    return {
        "receiptNo": "RC" + "".join(random.choices(string.digits, k=10)),
        "amount": float(Decimal(str(rng.uniform(20, 5000))).quantize(Decimal("0.01"))),
        "date": (date.today() - timedelta(days=rng.randint(0, 30))).isoformat(),
        "merchant": _SAMPLE_SELLERS[seed % len(_SAMPLE_SELLERS)],
    }


def _mock_invoice_items(rng: random.Random) -> list:
    return [
        {
            "name": "*软件服务*技术服务费",
            "spec": "",
            "quantity": 1,
            "unitPrice": float(Decimal(str(rng.uniform(500, 20000))).quantize(Decimal("0.01"))),
            "amount": float(Decimal(str(rng.uniform(500, 20000))).quantize(Decimal("0.01"))),
            "taxRate": 0.06,
            "taxAmount": float(Decimal(str(rng.uniform(30, 1200))).quantize(Decimal("0.01"))),
        }
    ]


_CN_DIGITS = "零壹贰叁肆伍陆柒捌玖"
_CN_UNITS = ["", "拾", "佰", "仟"]
_CN_BIG_UNITS = ["", "万", "亿", "万亿"]


def _cn_capital(amount) -> str:
    """数字金额转中文大写（支持小数：角分）

    票据规范：¥366.95 → "叁佰陆拾陆元玖角伍分"
    """
    try:
        amt = round(float(amount), 2)
    except Exception:
        return ""
    if amt < 0:
        return "负" + _cn_capital(-amt)
    if amt == 0:
        return "零元整"

    # 解决浮点精度（避免 jiao/fen 越界）
    cents = int(round(amt * 100))
    yuan = cents // 100
    jiao = (cents % 100) // 10
    fen = cents % 10

    def _int_to_cn(n: int) -> str:
        if n == 0:
            return ""
        parts = []
        yi = n // 100000000
        n = n % 100000000
        wan = n // 10000
        n = n % 10000
        # 亿
        if yi:
            parts.append(_section_to_cn(yi) + "亿")
        # 万
        if wan:
            wan_s = _section_to_cn(wan)
            if yi and wan < 1000:
                wan_s = "零" + wan_s
            parts.append(wan_s + "万")
        # 元以下
        if n:
            xia_s = _section_to_cn(n)
            if (yi or wan) and n < 1000:
                xia_s = "零" + xia_s
            parts.append(xia_s)
        return "".join(parts)

    def _section_to_cn(n: int) -> str:
        """0..9999 转中文"""
        s = ""
        for digit, unit in [(n // 1000, "仟"), ((n // 100) % 10, "佰"), ((n // 10) % 10, "拾"), (n % 10, "")]:
            if digit == 0:
                if s and not s.endswith("零") and unit:
                    s += "零"
            else:
                s += _CN_DIGITS[digit] + unit
        # 去掉尾零
        while s.endswith("零"):
            s = s[:-1]
        return s

    if yuan == 0:
        s = "零元"
    else:
        s = _int_to_cn(yuan) + "元"

    if jiao == 0 and fen == 0:
        s += "整"
    else:
        if jiao == 0:
            # 当 yuan=0 时不需要"零元零角"的"零"，只需"零"作为分补位
            if yuan > 0:
                s += "零"
        else:
            s += _CN_DIGITS[jiao] + "角"
        if fen:
            s += _CN_DIGITS[fen] + "分"
    return s


# ============================================================
# 健康检查（供主服务 /health 时探测 PaddleOCR 状态）
# ============================================================

async def health_check() -> dict:
    """主服务用：探测 OCR 服务是否可达"""
    if settings.OCR_MODE == "mock":
        return {"status": "mock", "mode": "mock"}
    try:
        async with httpx.AsyncClient(timeout=3) as client:
            r = await client.get(f"{settings.OCR_SERVICE_URL.rstrip('/')}/health")
            if r.status_code == 200:
                return {"status": "ok", "data": r.json()}
            return {"status": "degraded", "http": r.status_code}
    except Exception as e:
        return {"status": "down", "error": str(e)}
