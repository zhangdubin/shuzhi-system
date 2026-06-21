"""
AI 平台客户端（统一路由 + 多模型适配）
- 真实部署：调用 PaddleOCR / Qwen 等外部服务
- 当前是 deterministic mock（与 design/OCR-选型.md 一致）
- 替换实现：只改本文件
"""
import asyncio
import hashlib
import random
import re
import string
from datetime import datetime, date, timedelta
from decimal import Decimal
from typing import Optional

from app.config import settings
from sqlalchemy import select, func
from app.core.database import AsyncSessionLocal
from app.core.cache import cache


# ============================================================
# 样例数据（mock 用）
# ============================================================
_SAMPLE_BUYERS = [
    "万象科技有限公司",
    "北辰实业集团",
    "朗驰智能设备有限公司",
    "用友网络科技股份有限公司",
    "京东企业购",
    "上海数智信息技术有限公司",
]

_SAMPLE_SELLERS = [
    "上海数智信息技术有限公司",
    "用友网络科技股份有限公司",
    "阿里云计算有限公司",
    "携程计算机技术（上海）有限公司",
    "滴滴出行科技有限公司",
    "京东企业购",
    "美团点评",
]


# ============================================================
# OCR 抽取（同步 < 3s）
# ============================================================

async def ocr_extract(
    file_id: str,
    file_url: str,
    type: str = "invoice",  # invoice | contract | receipt | business-card | bank-statement
    template_id: Optional[str] = None,
    language: str = "zh-CN",
    options: Optional[dict] = None,
) -> dict:
    """
    OCR 字段抽取（mock）
    返回 fields / suggestions / meta
    """
    options = options or {}
    await asyncio.sleep(random.uniform(0.8, 2.5))  # 模拟 < 3s

    seed = _hash_seed(file_id or "default")
    rng = random.Random(seed)

    # 字段抽取（带字段级 confidence）
    fields = {}
    if type == "invoice":
        fields = _mock_invoice_fields(seed, rng)
    elif type == "contract":
        fields = _mock_contract_fields(seed, rng)
    elif type == "receipt":
        fields = _mock_receipt_fields(seed, rng)
    else:
        fields = _mock_invoice_fields(seed, rng)  # 兜底

    # 智能关联建议（mock 匹配数据库）
    suggestions = await _mock_suggestions(fields, type)

    # 置信度
    confidences = [v.get("confidence", 0) for v in fields.values() if isinstance(v, dict)]
    overall_conf = sum(confidences) / len(confidences) if confidences else 0

    return {
        "taskId": f"task_{_gen_id()}",
        "type": type,
        "fields": fields,
        "suggestions": suggestions,
        "meta": {
            "model": settings.AI_OCR_MODEL if hasattr(settings, 'AI_OCR_MODEL') else "paddleocr-v3",
            "version": "1.2.0",
            "confidence": round(overall_conf, 1),
            "durationMs": int(random.uniform(800, 2500)),
            "costCents": 0,  # PaddleOCR 自建免费
            "traceId": f"ai_{_gen_id()}",
        },
    }


def _mock_invoice_fields(seed: int, rng: random.Random) -> dict:
    """模拟发票字段抽取（字段级 confidence）"""
    # 模拟偶尔某个字段低分
    tax_rate_conf = rng.choice([99, 88, 72, 65, 95])  # 税率经常识别错

    return {
        "invoiceNo": {"value": "".join(random.choices(string.digits, k=18)),
                      "confidence": rng.randint(94, 99)},
        "invoiceCode": {"value": "".join(random.choices(string.digits, k=12)),
                        "confidence": rng.randint(92, 99)},
        "issueDate": {"value": (date.today() - timedelta(days=rng.randint(0, 30))).isoformat(),
                      "confidence": rng.randint(95, 99)},
        "buyerName": {"value": _SAMPLE_BUYERS[seed % len(_SAMPLE_BUYERS)],
                      "confidence": rng.randint(88, 99)},
        "buyerTaxId": {"value": "91310000MA1FL01X9G", "confidence": rng.randint(85, 99)},
        "sellerName": {"value": _SAMPLE_SELLERS[seed % len(_SAMPLE_SELLERS)],
                       "confidence": rng.randint(90, 99)},
        "amount": {"value": round(rng.uniform(500, 50000), 2),
                   "confidence": rng.randint(92, 99)},
        "taxAmount": {"value": round(rng.uniform(30, 3000), 2),
                      "confidence": rng.randint(90, 99)},
        "totalAmount": {"value": round(rng.uniform(500, 50000), 2),
                        "confidence": rng.randint(94, 99)},
        "totalAmountCn": {"value": "人民币整", "confidence": rng.randint(80, 99)},
        "taxRate": {"value": rng.choice([0.06, 0.13, 0.03, 0.09]),
                    "confidence": tax_rate_conf,
                    "needsReview": tax_rate_conf < 70},
        "lineItems": [
            {
                "name": "*信息技术服务*系统集成服务费",
                "quantity": 1, "unitPrice": round(rng.uniform(500, 20000), 2),
                "amount": round(rng.uniform(500, 20000), 2),
                "taxRate": 0.06,
                "taxAmount": round(rng.uniform(30, 1200), 2),
                "confidence": rng.randint(82, 95),
            }
        ],
        "remark": "合同号 C-2026-XXX",
    }


def _mock_contract_fields(seed: int, rng: random.Random) -> dict:
    return {
        "contractNo": {"value": f"HT-2026-{rng.randint(100, 999):03d}",
                        "confidence": rng.randint(95, 99)},
        "title": {"value": "技术开发服务合同", "confidence": rng.randint(90, 99)},
        "partyA": {"value": _SAMPLE_SELLERS[seed % len(_SAMPLE_SELLERS)],
                    "confidence": rng.randint(88, 99)},
        "partyB": {"value": _SAMPLE_BUYERS[seed % len(_SAMPLE_BUYERS)],
                    "confidence": rng.randint(88, 99)},
        "amount": {"value": round(rng.uniform(100000, 2000000), 2),
                   "confidence": rng.randint(94, 99)},
        "signDate": {"value": (date.today() - timedelta(days=rng.randint(0, 60))).isoformat(),
                     "confidence": rng.randint(96, 99)},
    }


def _mock_receipt_fields(seed: int, rng: random.Random) -> dict:
    return {
        "receiptNo": {"value": "RC" + "".join(random.choices(string.digits, k=10)),
                       "confidence": rng.randint(92, 99)},
        "amount": {"value": round(rng.uniform(20, 5000), 2),
                   "confidence": rng.randint(94, 99)},
        "date": {"value": (date.today() - timedelta(days=rng.randint(0, 30))).isoformat(),
                 "confidence": rng.randint(95, 99)},
        "merchant": {"value": _SAMPLE_SELLERS[seed % len(_SAMPLE_SELLERS)],
                     "confidence": rng.randint(85, 99)},
    }


async def _mock_suggestions(fields: dict, type: str) -> dict:
    """智能关联建议（真实部署：查客户/合同/项目库；mock：随便给个匹配）"""
    if type != "invoice":
        return {}

    buyer_name = fields.get("buyerName", {}).get("value", "")
    return {
        "linkToContract": f"HT-2026-{random.randint(100, 999):03d}" if buyer_name else None,
        "linkToClient": buyer_name,
        "linkToProject": "数智化二期" if "万象" in buyer_name else None,
    }


# ============================================================
# LLM 问答（同步 < 5s，mock 走数据库查）
# R6.5.3: 加 5min 缓存（同一问题不重算，p95 2.9s → <10ms）
# ============================================================

@cache(key_prefix="ai:ask", ttl=300)  # 5 分钟 TTL
async def llm_ask(
    question: str,
    context: Optional[dict] = None,
) -> dict:
    """
    智能问答（mock）
    - 简单意图识别 → 查数据库 → 拼答案
    - 真实部署：调 Qwen / 本地 LLM
    """
    await asyncio.sleep(random.uniform(1.0, 3.0))

    question_lower = question.lower()
    # 意图分类（mock）
    if any(kw in question for kw in ["逾期", "未回款", "未收"]):
        return await _answer_overdue(question)
    if any(kw in question for kw in ["费用", "花了多少", "花了", "成本"]):
        return await _answer_expense(question)
    if any(kw in question for kw in ["合同", "签约", "签署"]):
        return await _answer_contracts(question)
    if any(kw in question for kw in ["发票", "开了多少", "开了几张"]):
        return await _answer_invoices(question)
    if any(kw in question for kw in ["项目", "在做", "在建"]):
        return await _answer_projects(question)
    if any(kw in question for kw in ["客户", "客户列表"]):
        return await _answer_clients(question)

    # 兜底：通用答案
    return {
        "answer": f"收到你的问题：**{question}**\n\n当前为 Phase 1 mock 模式，暂未实现该问题类型。\n\n可尝试：\n- 本月哪些回款逾期了？\n- 销售费用花了多少？\n- 在建项目有哪些？",
        "answerType": "doc",
        "data": {"rows": []},
        "chart": None,
        "sources": [],
        "conversationId": (context or {}).get("conversationId", f"conv_{_gen_id()}"),
        "messageId": f"msg_{_gen_id()}",
        "meta": {
            "model": settings.AI_LLM_MODEL if hasattr(settings, 'AI_LLM_MODEL') else "qwen2.5-7b",
            "durationMs": int(random.uniform(1000, 3000)),
            "tokensUsed": 380,
            "costCents": 3,
            "traceId": f"ai_{_gen_id()}",
        },
    }


async def _answer_overdue(question: str) -> dict:
    """查回款逾期"""
    from app.modules.receivable.models import Receivable
    from app.modules.common.models import Client

    async with AsyncSessionLocal() as db:
        rows = (await db.execute(
            select(Receivable, Client)
            .join(Client, Client.id == Receivable.client_id, isouter=True)
            .where(Receivable.status.in_(["overdue", "pending"]))
            .order_by(Receivable.overdue_days.desc())
            .limit(10)
        )).all()

        data_rows = []
        total_amount = 0
        for r, c in rows:
            plan = r.plan_amount or 0
            received = r.received_amount or 0
            data_rows.append({
                "clientName": c.name if c else "",
                "code": r.code,
                "planAmount": float(Decimal(plan) / 100),
                "receivedAmount": float(Decimal(received) / 100),
                "overdueDays": r.overdue_days or 0,
                "status": r.status,
            })
            if r.status == "overdue":
                total_amount += plan - received

        if not data_rows:
            answer = "✅ 当前 **没有回款逾期的记录**，所有回款都按计划进行。"
        else:
            overdue_count = sum(1 for r in data_rows if r["status"] == "overdue")
            answer = f"⚠️ 当前共有 **{len(data_rows)} 笔**回款需关注（其中 **{overdue_count} 笔已逾期**），待收金额合计 **¥{Decimal(total_amount)/100:,.2f}**。\n\n**明细**：\n"
            for i, r in enumerate(data_rows[:5], 1):
                answer += f"{i}. {r['clientName']} - {r['code']} - 待收 ¥{r['planAmount']:,.2f}"
                if r['overdueDays'] > 0:
                    answer += f"（已逾期 {r['overdueDays']} 天）"
                answer += "\n"
            if len(data_rows) > 5:
                answer += f"\n...还有 {len(data_rows)-5} 笔"

        return {
            "answer": answer,
            "answerType": "data",
            "data": {"rows": data_rows},
            "chart": {
                "type": "bar",
                "config": {
                    "xAxis": {"type": "category", "data": [r["code"] for r in data_rows[:5]]},
                    "yAxis": {"type": "value"},
                    "series": [{"name": "待收金额", "data": [r["planAmount"] - r["receivedAmount"] for r in data_rows[:5]]}],
                },
            } if data_rows else None,
            "sources": [],
            "conversationId": f"conv_{_gen_id()}",
            "messageId": f"msg_{_gen_id()}",
            "meta": {
                "model": "qwen2.5-7b",
                "durationMs": 1850,
                "tokensUsed": 580,
                "costCents": 5,
                "traceId": f"ai_{_gen_id()}",
            },
        }


async def _answer_expense(question: str) -> dict:
    """查费用统计"""
    from app.modules.expense.models import Expense
    async with AsyncSessionLocal() as db:
        total = (await db.execute(
            select(func.coalesce(func.sum(Expense.amount), 0))
        )).scalar() or 0
        pending = (await db.execute(
            select(func.count()).where(Expense.status == "pending")
        )).scalar() or 0
        rows = (await db.execute(
            select(Expense.category, func.coalesce(func.sum(Expense.amount), 0))
            .group_by(Expense.category)
        )).all()
    cat_data = [{"name": cat, "amount": float(Decimal(amt) / 100)} for cat, amt in rows]
    return {
        "answer": f"💰 当前销售费用合计 **¥{Decimal(total)/100:,.2f}**，待审批 {pending} 笔。\n\n**类目分布**：\n" +
                  "\n".join(f"- {c['name']}: ¥{c['amount']:,.2f}" for c in cat_data),
        "answerType": "data",
        "data": {"rows": cat_data, "totalCents": total, "pendingCount": pending},
        "chart": {
            "type": "pie",
            "config": {
                "series": [{"type": "pie", "data": [{"name": c["name"], "value": c["amount"]} for c in cat_data]}],
            },
        },
        "sources": [],
        "conversationId": f"conv_{_gen_id()}",
        "messageId": f"msg_{_gen_id()}",
        "meta": {"model": "qwen2.5-7b", "durationMs": 1320, "tokensUsed": 420, "costCents": 3, "traceId": f"ai_{_gen_id()}"},
    }


async def _answer_contracts(question: str) -> dict:
    from app.modules.contract.models import Contract
    async with AsyncSessionLocal() as db:
        total = (await db.execute(select(func.count()).select_from(Contract))).scalar() or 0
        approved = (await db.execute(select(func.count()).where(Contract.status == "approved"))).scalar() or 0
    return {
        "answer": f"📄 合同总数 **{total}** 份，已审批 {approved} 份。\n\n（详细合同列表请到 `/contract` 模块查看）",
        "answerType": "data",
        "data": {"total": total, "approved": approved},
        "chart": None, "sources": [],
        "conversationId": f"conv_{_gen_id()}",
        "messageId": f"msg_{_gen_id()}",
        "meta": {"model": "qwen2.5-7b", "durationMs": 980, "tokensUsed": 320, "costCents": 2, "traceId": f"ai_{_gen_id()}"},
    }


async def _answer_invoices(question: str) -> dict:
    from app.modules.invoice_ocr.models import Invoice
    async with AsyncSessionLocal() as db:
        total = (await db.execute(select(func.count()).select_from(Invoice))).scalar() or 0
    return {
        "answer": f"📊 发票识别记录 **{total}** 张。\n\n（详细列表请到 `/invoice-ocr` 模块查看）",
        "answerType": "data",
        "data": {"total": total},
        "chart": None, "sources": [],
        "conversationId": f"conv_{_gen_id()}",
        "messageId": f"msg_{_gen_id()}",
        "meta": {"model": "qwen2.5-7b", "durationMs": 760, "tokensUsed": 280, "costCents": 2, "traceId": f"ai_{_gen_id()}"},
    }


async def _answer_projects(question: str) -> dict:
    from app.modules.project.models import Project
    async with AsyncSessionLocal() as db:
        active = (await db.execute(
            select(func.count()).where(Project.status == "in_progress")
        )).scalar() or 0
        rows = (await db.execute(
            select(Project.code, Project.name, Project.progress)
            .where(Project.status == "in_progress")
            .limit(10)
        )).all()
    project_data = [{"code": c, "name": n, "progress": float(p or 0)} for c, n, p in rows]
    return {
        "answer": f"📁 在建项目 **{active}** 个。\n\n" +
                  "\n".join(f"- **{p['name']}** ({p['code']}) - 进度 {p['progress']:.0f}%" for p in project_data),
        "answerType": "data",
        "data": {"rows": project_data, "activeCount": active},
        "chart": None, "sources": [],
        "conversationId": f"conv_{_gen_id()}",
        "messageId": f"msg_{_gen_id()}",
        "meta": {"model": "qwen2.5-7b", "durationMs": 1100, "tokensUsed": 380, "costCents": 3, "traceId": f"ai_{_gen_id()}"},
    }


async def _answer_clients(question: str) -> dict:
    from app.modules.common.models import Client
    async with AsyncSessionLocal() as db:
        total = (await db.execute(select(func.count()).select_from(Client))).scalar() or 0
        rows = (await db.execute(
            select(Client.code, Client.name, Client.level)
            .where(Client.is_active == True)
            .limit(10)
        )).all()
    client_data = [{"code": c, "name": n, "level": lv} for c, n, lv in rows]
    return {
        "answer": f"🏢 共 **{total}** 家客户。\n\n" +
                  "\n".join(f"- **{c['name']}** ({c['code']}) - {c.get('level', 'C')}级" for c in client_data),
        "answerType": "data",
        "data": {"rows": client_data, "total": total},
        "chart": None, "sources": [],
        "conversationId": f"conv_{_gen_id()}",
        "messageId": f"msg_{_gen_id()}",
        "meta": {"model": "qwen2.5-7b", "durationMs": 920, "tokensUsed": 350, "costCents": 2, "traceId": f"ai_{_gen_id()}"},
    }


# ============================================================
# 风险扫描
# R6.5.3: 加 5min 缓存（同一对象不重算，p95 0.96s → <10ms）
# ============================================================

@cache(key_prefix="ai:risk_scan", ttl=300)  # 5 分钟 TTL
async def risk_scan(object_type: str, object_id: int) -> dict:
    """
    风险扫描（mock）
    返回 overallScore / riskLevel / dimensions / warnings / suggestions / similarObjects
    """
    await asyncio.sleep(random.uniform(0.3, 1.0))

    seed = _hash_seed(f"{object_type}:{object_id}")
    rng = random.Random(seed)

    overall = rng.randint(60, 95)
    if overall >= 85:
        level = "low"
    elif overall >= 70:
        level = "medium"
    else:
        level = "high"

    # 4 维度评分
    dimensions = {
        "progress": {"score": rng.randint(60, 100), "weight": 0.25},
        "budget": {"score": rng.randint(50, 100), "weight": 0.25},
        "quality": {"score": rng.randint(70, 100), "weight": 0.25},
        "client": {"score": rng.randint(60, 100), "weight": 0.25},
    }

    warnings = []
    if level in ("medium", "high"):
        warnings.append({
            "id": f"w_{_gen_id()[:6]}",
            "level": "high" if level == "high" else "medium",
            "type": f"{object_type}_attention",
            "title": f"{object_type_name_zh(object_type)} {object_id} 需关注",
            "description": f"基于历史数据分析，{object_type_name_zh(object_type)} {object_id} 在进度/预算/质量/客户满意度上存在 1-2 项风险。",
            "suggestion": "建议本周组织评审会，明确下一步推进计划。",
            "confidence": rng.randint(75, 95),
            "dataPoints": {"objectId": object_id, "scanAt": datetime.utcnow().isoformat()},
            "createdAt": datetime.utcnow().isoformat(),
        })

    suggestions = []
    if warnings:
        suggestions.append({
            "id": f"s_{_gen_id()[:6]}",
            "title": "组织评审会，明确推进计划",
            "description": "基于历史项目数据，建议本周内组织一次评审会。",
            "action": {"type": "create-meeting", "params": {"title": f"{object_type} 评审会"}},
            "confidence": 88,
        })

    similar = []
    if object_type == "project":
        similar.append({
            "objectType": "project", "objectId": 1, "name": "数智化一期",
            "healthScore": 91, "delayDays": 0, "overBudget": -0.02,
        })

    return {
        "objectType": object_type,
        "objectId": object_id,
        "overallScore": overall,
        "riskLevel": level,
        "dimensions": dimensions,
        "warnings": warnings,
        "suggestions": suggestions,
        "similarObjects": similar,
        "meta": {
            "model": "risk-v2.3",
            "version": "2.3.1",
            "durationMs": int(random.uniform(300, 800)),
            "costCents": 1,
            "traceId": f"ai_{_gen_id()}",
        },
    }


def object_type_name_zh(t: str) -> str:
    return {"project": "项目", "contract": "合同", "expense": "费用", "voucher": "凭证"}.get(t, t)


# ============================================================
# 工具
# ============================================================

def _hash_seed(s: str) -> int:
    return int(hashlib.md5(s.encode()).hexdigest(), 16)


def _gen_id(n: int = 8) -> str:
    return "".join(random.choices(string.ascii_lowercase + string.digits, k=n))
