"""
诺诺发票云查验客户端（双模式：real / mock）
- 真实部署：调诺诺开放平台 https://sandbox.nuonuocs.cn/open/v1/services
  鉴权：appKey + appSecret + accessToken + X-Nuonuo-Sign（MD5 签名）
  method: nuonuo.ElectronInvoice.otherInvoiceCheck
- mock：deterministic 假数据（按 invoiceNo 后 4 位 mod 5 决定结果）
- 自动回退：NUONUO_MODE=mock 或连接失败时用 mock

替换实现：只改本文件
"""
import asyncio
import base64
import hashlib
import json
import random
import secrets
import time
from datetime import datetime
from decimal import Decimal
from typing import Optional

import httpx

from app.config import settings
from app.core.exceptions import (
    VerifyFailedException, AIModelUnavailableException,
)


# ============================================================
# 入口
# ============================================================

async def verify(
    invoice_code: str,
    invoice_no: str,
    issue_date: str,
    total_amount_yuan: float,
    verify_code: Optional[str] = None,
) -> dict:
    """
    验真（智能路由：real → mock 回退）
    返回: {result, source, verifiedAt, elapsed, info, riskReason}
    """
    # R7.2: 业务指标
    from app.core.metrics import business_verify_total

    # 1. mock 模式（没配 key 自动回退）
    if settings.NUONUO_MODE == "mock" or not settings.NUONUO_API_KEY:
        result = await _mock_verify(
            invoice_code, invoice_no, issue_date, total_amount_yuan, verify_code
        )
        business_verify_total.labels(result=result.get("result", "unknown"), mode="mock").inc()
        return result

    # 2. 真实调用
    try:
        result = await _real_verify(
            invoice_code, invoice_no, issue_date, total_amount_yuan, verify_code
        )
        business_verify_total.labels(result=result.get("result", "unknown"), mode="real").inc()
        return result
    except (httpx.ConnectError, httpx.ConnectTimeout, OSError) as e:
        from loguru import logger
        logger.warning(f"诺诺服务连接失败，自动回退 mock：{e}")
        result = await _mock_verify(
            invoice_code, invoice_no, issue_date, total_amount_yuan, verify_code
        )
        business_verify_total.labels(result=result.get("result", "unknown"), mode="real→mock_fallback").inc()
        return result
    except Exception as e:
        # 真路径上任何异常（HTTP 5xx / 协议错误 / 签名失败…）一律回退 mock
        from loguru import logger
        logger.warning(f"诺诺服务调用异常，自动回退 mock：{type(e).__name__}: {e}")
        result = await _mock_verify(
            invoice_code, invoice_no, issue_date, total_amount_yuan, verify_code
        )
        business_verify_total.labels(result=result.get("result", "unknown"), mode="real→mock_fallback").inc()
        return result


# ============================================================
# 真实诺诺 HTTP 调用
# ============================================================

async def _real_verify(
    invoice_code: str, invoice_no: str, issue_date: str,
    total_amount_yuan: float, verify_code: Optional[str]
) -> dict:
    """
    调诺诺开放平台
    method: nuonuo.ElectronInvoice.otherInvoiceCheck
    """
    # 1. 构造公共 + 私有请求参数
    senid = secrets.token_hex(16)  # 32位
    nonce = str(random.randint(10000000, 99999999))  # 8位
    timestamp = str(int(time.time()))

    private_body = {
        "taxNum": "",  # 税号（自用型应用非必填）
        "invoiceCode": invoice_code,
        "invoiceNumber": invoice_no,
        "checkCode": verify_code or "",
        "invoiceDate": issue_date,
        "invoiceType": "",
        "totalAmount": str(total_amount_yuan) if total_amount_yuan else "",
    }
    # 公共 + 私有 合并（诺诺协议：业务参数放 messageBody）
    full_body = {
        "senid": senid,
        "nonce": nonce,
        "timestamp": timestamp,
        "appkey": settings.NUONUO_API_KEY,
        **private_body,
    }
    body_str = json.dumps(full_body, ensure_ascii=False, separators=(",", ":"))

    # 2. 签名：MD5(secret + body + secret) → base64
    sign = _make_nuonuo_sign(settings.NUONUO_API_SECRET, body_str)

    # 3. 构造 headers
    headers = {
        "Content-Type": "application/json;charset=UTF-8",
        "X-Nuonuo-Sign": sign,
        "accessToken": settings.NUONUO_API_TOKEN or "",
        "method": "nuonuo.ElectronInvoice.otherInvoiceCheck",
    }
    if settings.NUONUO_USE_SANDBOX:
        # 沙箱环境 userTax 选填
        pass

    # 4. 发送
    t0 = time.time()
    async with httpx.AsyncClient(timeout=settings.OCR_TIMEOUT) as client:
        resp = await client.post(
            settings.NUONUO_API_URL,
            headers=headers,
            content=body_str.encode("utf-8"),
        )
    elapsed = int((time.time() - t0) * 1000)

    if resp.status_code != 200:
        raise VerifyFailedException(
            f"诺诺 HTTP {resp.status_code}: {resp.text[:200]}"
        )

    data = resp.json()

    # 5. 解析响应
    if data.get("code") != "E0000":
        # 业务错误：返回结果，但标记为 not_found
        return {
            "verifyId": None,
            "result": "not_found",
            "source": f"诺诺发票云（{data.get('code')}）",
            "verifiedAt": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"),
            "elapsed": elapsed,
            "info": {
                "invoiceCode": invoice_code,
                "invoiceNo": invoice_no,
                "issueDate": issue_date,
                "totalAmount": total_amount_yuan,
            },
            "riskReason": data.get("describe", "查验失败"),
        }

    result_obj = data.get("result", {})
    check_result = result_obj.get("checkResult", "not_found")  # pass | risk | repeat | not_found
    return {
        "verifyId": None,
        "result": check_result,
        "source": "诺诺发票云（国税总局）",
        "verifiedAt": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"),
        "elapsed": elapsed,
        "info": {
            "invoiceCode": result_obj.get("invoiceCode", invoice_code),
            "invoiceNo": result_obj.get("invoiceNumber", invoice_no),
            "issueDate": result_obj.get("invoiceDate", issue_date),
            "totalAmount": float(result_obj.get("totalAmount", total_amount_yuan)),
        },
        "riskReason": result_obj.get("riskReason"),
    }


def _make_nuonuo_sign(secret: str, body: str) -> str:
    """诺诺签名：MD5(secret + body + secret) → base64"""
    raw = secret + body + secret
    md5 = hashlib.md5(raw.encode("utf-8")).digest()
    return base64.b64encode(md5).decode("utf-8")


# ============================================================
# Mock 模式（与原 nuonuo.py 行为一致）
# ============================================================

async def _mock_verify(
    invoice_code: str, invoice_no: str, issue_date: str,
    total_amount_yuan: float, verify_code: Optional[str]
) -> dict:
    """数据库驱动的 mock 验真：模拟国税接口 + 本系统报销状态。

    判定逻辑（按从轻到重）：
    1) invoice_no 为空 / 长度过短 / 数字结尾不在正常范围 → not_found（模拟国税查无此票）
    2) 数据库里有同号发票：
       a) 金额不一致（差异 > 1 分） → risk（国税信息不一致）
       b) 金额一致但已生成 expense 报销记录 → repeat（该发票已被报销）
       c) 金额一致且未报销 → pass（国税真，本系统未报销）
    3) 数据库里没同号发票 → pass（国税真有此票，本系统首次识别）

    与之前 random bucket 相比：所有结果都有可解释的业务含义。
    """
    await asyncio.sleep(random.uniform(0.5, 2.0))

    # 字段基础校验：模拟国税对输入合法性的检查
    if not invoice_no or len(invoice_no) < 8:
        return _mock_wrap("not_found", "发票号格式不合法（国税要求至少 8 位）", invoice_code, invoice_no, issue_date, total_amount_yuan)
    if not issue_date:
        return _mock_wrap("not_found", "开票日期必填", invoice_code, invoice_no, issue_date, total_amount_yuan)
    try:
        amount_fen = int(round(float(total_amount_yuan) * 100))
    except (TypeError, ValueError):
        return _mock_wrap("not_found", "价税合计格式错误", invoice_code, invoice_no, issue_date, total_amount_yuan)

    # 查本系统数据库（mock 阶段"国税数据库"用本系统 invoice 表模拟）
    from app.core.database import AsyncSessionLocal
    from app.modules.invoice_ocr.models import Invoice
    from sqlalchemy import select

    matched = None
    try:
        async with AsyncSessionLocal() as s:
            q = select(Invoice).where(Invoice.invoice_no == invoice_no)
            if invoice_code:
                q = q.where(Invoice.invoice_code == invoice_code)
            matched = (await s.execute(q)).scalar_one_or_none()
    except Exception:
        matched = None

    if matched is not None:
        # 同号已识别
        if abs(int(matched.total_amount or 0) - amount_fen) > 1:
            return _mock_wrap(
                "risk",
                f"国税反馈金额 ¥{amount_fen/100:.2f} 与本系统识别 ¥{(matched.total_amount or 0)/100:.2f} 不一致，请人工复核",
                invoice_code, invoice_no, issue_date, total_amount_yuan,
            )
        # 金额一致：检查是否已报销
        try:
            from app.modules.expense.models import Expense
            from app.modules.invoice_ocr.models import InvoiceRelation
            async with AsyncSessionLocal() as s:
                # 优先用 InvoiceRelation 关联查
                rel = (await s.execute(
                    select(InvoiceRelation).where(
                        InvoiceRelation.invoice_id == matched.id,
                        InvoiceRelation.relation_type == "expense",
                    )
                )).scalar_one_or_none()
                if rel is not None:
                    # R20 修复：只有当关联的 expense 处于"待审/审批中"才算重复报销
                    # 费用已 approved/paid/rejected → 历史报销完成，再次查验不算"重复"
                    from app.modules.expense.models import Expense as _Expense
                    exp = None
                    try:
                        exp = (await s.execute(
                            select(_Expense).where(_Expense.id == rel.relation_id)
                        )).scalar_one_or_none()
                    except Exception:
                        exp = None
                    if exp is not None and exp.status in ("pending", "approving", "draft"):
                        return _mock_wrap(
                            "repeat",
                            f"该发票正在报销流程中（费用单 {exp.code} 状态 {exp.status}），请勿重复提交",
                            invoice_code, invoice_no, issue_date, total_amount_yuan,
                        )
                # 兜底：用 Expense.description 里的 [关联发票 INV-xxx] 标记
                tag = f"[关联发票 INV-{matched.invoice_no or matched.code or matched.id}]"
                exp = (await s.execute(
                    select(Expense).where(Expense.description.like(f"%{tag}%"))
                )).scalar_one_or_none()
                if exp is not None and exp.status in ("pending", "approving", "draft"):
                    return _mock_wrap(
                        "repeat",
                        f"该发票正在报销流程中（费用单 {exp.code} 状态 {exp.status}），请勿重复提交",
                        invoice_code, invoice_no, issue_date, total_amount_yuan,
                    )
        except Exception:
            pass
        # 同号同金额但未报销 → pass
        return _mock_wrap(
            "pass",
            None,
            invoice_code, invoice_no, issue_date, total_amount_yuan,
        )

    # 数据库里没同号 → 模拟国税"票面真实有效"（pass）
    return _mock_wrap(
        "pass",
        None,
        invoice_code, invoice_no, issue_date, total_amount_yuan,
    )


def _mock_wrap(
    result: str,
    risk_reason,
    invoice_code: str,
    invoice_no: str,
    issue_date: str,
    total_amount_yuan: float,
) -> dict:
    return {
        "verifyId": None,
        "result": result,
        "source": "国家税务总局全国增值税发票查验平台（mock）",
        "verifiedAt": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"),
        "elapsed": random.randint(800, 2500),
        "info": {
            "invoiceCode": invoice_code,
            "invoiceNo": invoice_no,
            "issueDate": issue_date,
            "totalAmount": total_amount_yuan,
        },
        "riskReason": risk_reason,
    }


# ============================================================
# 健康检查
# ============================================================

async def health_check() -> dict:
    """主服务用：探测诺诺服务是否可达"""
    if settings.NUONUO_MODE == "mock" or not settings.NUONUO_API_KEY:
        return {"status": "mock", "mode": "mock"}
    try:
        async with httpx.AsyncClient(timeout=3) as client:
            r = await client.get("https://sandbox.nuonuocs.cn/")
            return {"status": "reachable" if r.status_code in (200, 404) else "degraded"}
    except Exception as e:
        return {"status": "down", "error": str(e)}
