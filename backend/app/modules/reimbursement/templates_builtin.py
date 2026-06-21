"""
内置报销模板
模板采用 JSON 配置，方便后续扩展。
schema 字段定义：
  - header:    顶部公司/标题/日期等
  - applicant: 报销人/部门
  - summary:   合计区域
  - details:   费用明细列定义
  - footer:    签字/审批区域
"""
from typing import List, Dict, Any

CNY = "¥"


def _common_footer():
    return {
        "signatures": [
            { "label": "报销人签字",   "key": "applicant" },
            { "label": "部门负责人",   "key": "dept_lead" },
            { "label": "财务审核",     "key": "finance" },
            { "label": "总经理审批",   "key": "gm" },
        ],
        "note": "本报销单一式两份，财务与报销人各执一份。",
    }


def _default_details():
    return [
        { "key": "seq",            "label": "#",             "width": 32,  "align": "center" },
        { "key": "expenseDate",    "label": "费用日期",      "width": 90,  "align": "center" },
        { "key": "expenseCode",    "label": "费用单号",      "width": 110, "align": "left"   },
        { "key": "expenseType",    "label": "费用类型",      "width": 70,  "align": "center" },
        { "key": "title",          "label": "摘要",          "width": 180, "align": "left"   },
        { "key": "clientName",     "label": "客户/供应商",   "width": 110, "align": "left"   },
        { "key": "amount",         "label": "金额(元)",      "width": 90,  "align": "right",  "type": "money" },
    ]


BUILTIN_TEMPLATES: List[Dict[str, Any]] = [
    {
        "code": "general",
        "name": "通用费用报销单",
        "type": "general",
        "icon": "📋",
        "color": "#4F6BFF",
        "description": "适用于日常销售费用报销，含明细、合计、签字栏。",
        "schema": {
            "header": {
                "company": "上海数智信息技术有限公司",
                "title": "费用报销单",
                "subtitle": "Reimbursement Form",
            },
            "applicant": {
                "fields": [
                    { "key": "applicant",  "label": "报销人" },
                    { "key": "department", "label": "部门" },
                    { "key": "expenseDate","label": "费用日期" },
                    { "key": "formNo",     "label": "单据编号" },
                ],
            },
            "summary": {
                "fields": [
                    { "key": "totalAmount",   "label": "申请报销金额", "type": "money" },
                    { "key": "actualAmount",  "label": "实际报销金额", "type": "money" },
                    { "key": "voucherNo",     "label": "凭证号" },
                ],
            },
            "details": { "columns": _default_details() },
            "footer": _common_footer(),
        },
    },
    {
        "code": "travel",
        "name": "差旅费报销单",
        "type": "travel",
        "icon": "✈️",
        "color": "#7C3AED",
        "description": "适用于差旅费报销，含机票/酒店/打车/餐补。",
        "schema": {
            "header": {
                "company": "上海数智信息技术有限公司",
                "title": "差旅费报销单",
                "subtitle": "Travel Reimbursement",
            },
            "applicant": {
                "fields": [
                    { "key": "applicant",  "label": "出差人" },
                    { "key": "department", "label": "部门" },
                    { "key": "expenseDate","label": "出差起止" },
                    { "key": "formNo",     "label": "单据编号" },
                ],
            },
            "summary": {
                "fields": [
                    { "key": "totalAmount",   "label": "差旅费合计", "type": "money" },
                    { "key": "actualAmount",  "label": "实报金额",   "type": "money" },
                    { "key": "voucherNo",     "label": "凭证号" },
                ],
            },
            "details": {
                "columns": [
                    { "key": "seq",            "label": "#",           "width": 32,  "align": "center" },
                    { "key": "expenseDate",    "label": "发生日期",     "width": 90,  "align": "center" },
                    { "key": "expenseType",    "label": "费用类别",     "width": 80,  "align": "center" },
                    { "key": "title",          "label": "事项/票据",   "width": 200, "align": "left"   },
                    { "key": "clientName",     "label": "起止地点",     "width": 130, "align": "left"   },
                    { "key": "amount",         "label": "金额(元)",     "width": 100, "align": "right",  "type": "money" },
                ],
            },
            "footer": _common_footer(),
        },
    },
    {
        "code": "hospitality",
        "name": "业务招待费报销单",
        "type": "hospitality",
        "icon": "🍷",
        "color": "#F59E0B",
        "description": "适用于业务招待用餐、礼品等费用。",
        "schema": {
            "header": {
                "company": "上海数智信息技术有限公司",
                "title": "业务招待费报销单",
                "subtitle": "Hospitality Reimbursement",
            },
            "applicant": {
                "fields": [
                    { "key": "applicant",  "label": "经办人" },
                    { "key": "department", "label": "部门" },
                    { "key": "expenseDate","label": "招待日期" },
                    { "key": "formNo",     "label": "单据编号" },
                ],
            },
            "summary": {
                "fields": [
                    { "key": "totalAmount",   "label": "招待费合计", "type": "money" },
                    { "key": "actualAmount",  "label": "实报金额",   "type": "money" },
                    { "key": "voucherNo",     "label": "凭证号" },
                ],
            },
            "details": {
                "columns": [
                    { "key": "seq",            "label": "#",          "width": 32,  "align": "center" },
                    { "key": "expenseDate",    "label": "日期",        "width": 90,  "align": "center" },
                    { "key": "clientName",     "label": "招待对象",     "width": 140, "align": "left"   },
                    { "key": "expenseType",    "label": "类别",        "width": 70,  "align": "center" },
                    { "key": "title",          "label": "场所/事项",   "width": 200, "align": "left"   },
                    { "key": "amount",         "label": "金额(元)",     "width": 100, "align": "right",  "type": "money" },
                ],
            },
            "footer": _common_footer(),
        },
    },
    {
        "code": "marketing",
        "name": "市场推广费用报销单",
        "type": "marketing",
        "icon": "📣",
        "color": "#10B981",
        "description": "适用于市场推广、广告投放、展会等费用。",
        "schema": {
            "header": {
                "company": "上海数智信息技术有限公司",
                "title": "市场推广费报销单",
                "subtitle": "Marketing Expense Reimbursement",
            },
            "applicant": {
                "fields": [
                    { "key": "applicant",  "label": "申请人" },
                    { "key": "department", "label": "部门" },
                    { "key": "expenseDate","label": "活动日期" },
                    { "key": "formNo",     "label": "单据编号" },
                ],
            },
            "summary": {
                "fields": [
                    { "key": "totalAmount",   "label": "推广费合计", "type": "money" },
                    { "key": "actualAmount",  "label": "实报金额",   "type": "money" },
                    { "key": "voucherNo",     "label": "凭证号" },
                ],
            },
            "details": {
                "columns": [
                    { "key": "seq",            "label": "#",          "width": 32,  "align": "center" },
                    { "key": "expenseDate",    "label": "日期",        "width": 90,  "align": "center" },
                    { "key": "expenseType",    "label": "渠道",        "width": 80,  "align": "center" },
                    { "key": "title",          "label": "活动/项目",   "width": 200, "align": "left"   },
                    { "key": "clientName",     "label": "供应商",      "width": 140, "align": "left"   },
                    { "key": "amount",         "label": "金额(元)",     "width": 100, "align": "right",  "type": "money" },
                ],
            },
            "footer": _common_footer(),
        },
    },
]


def get_builtin_templates() -> List[Dict[str, Any]]:
    return [dict(t) for t in BUILTIN_TEMPLATES]


def get_template_by_code(code: str) -> Dict[str, Any] | None:
    for t in BUILTIN_TEMPLATES:
        if t["code"] == code:
            return dict(t)
    return None
