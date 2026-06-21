"""
种子数据脚本
初始化角色、权限、字典、用户、部门、示例项目

运行：python scripts/seed.py
"""
import asyncio
from datetime import datetime, date, timedelta
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

from app.config import settings
from app.core.database import Base
from app.core.security import hash_password
from app.modules.auth.models import (
    Department, User, Role, Permission, RolePermission, UserRole,
    Dictionary,
)
from app.modules.project.models import Project, ProjectMilestone, Client
from app.modules.common.models import Notification
from app.modules.contract.models import Contract, ContractTemplate
from app.modules.expense.models import Expense, ExpenseBreakdown
from app.modules.receivable.models import Receivable
from app.modules.invoice_template.models import InvoiceTemplate, InvoiceTemplateField
from app.modules.invoice_ocr.models import Invoice
from app.modules.ai.models import AIAlert


# ===== 初始化数据 =====

PERMISSIONS = [
    # 发票识别
    ("invoice:upload", "invoice", "upload", "上传发票"),
    ("invoice:read", "invoice", "read", "查看发票"),
    ("invoice:write", "invoice", "write", "编辑发票"),
    ("invoice:verify", "invoice", "verify", "核验发票"),
    ("invoice:submit", "invoice", "submit", "提交入账"),
    ("invoice:export", "invoice", "export", "导出发票"),

    # 发票模板
    ("template:read", "template", "read", "查看模板"),
    ("template:write", "template", "write", "管理模板"),

    # 销售费用
    ("expense:read", "expense", "read", "查看费用"),
    ("expense:write", "expense", "write", "录入费用"),
    ("expense:approve", "expense", "approve", "审批费用"),
    ("expense:export", "expense", "export", "导出费用"),

    # 项目管理
    ("project:read", "project", "read", "查看项目"),
    ("project:write", "project", "write", "管理项目"),
    ("milestone:write", "milestone", "write", "管理里程碑"),

    # 合同管理
    ("contract:read", "contract", "read", "查看合同"),
    ("contract:write", "contract", "write", "管理合同"),
    ("contract:approve", "contract", "approve", "审批合同"),

    # 回款管理
    ("receivable:read", "receivable", "read", "查看回款"),
    ("receivable:write", "receivable", "write", "管理回款"),

    # 系统
    ("user:read", "user", "read", "查看用户"),
    ("user:write", "user", "write", "管理用户"),
    ("audit:read", "audit", "read", "查看审计"),

    # AI 平台（AI-API.md §3）
    ("ai:extract", "ai", "extract", "AI 字段抽取"),
    ("ai:risk.scan", "ai", "risk_scan", "AI 风险扫描"),
    ("ai:ask", "ai", "ask", "AI 智能问答"),
    ("ai:model.manage", "ai", "model_manage", "AI 模型管理"),
]

ROLES = [
    ("超级管理员", "super_admin", "all", True),
    ("财务总监", "finance_director", "dept", False),
    ("财务专员", "finance_specialist", "self", False),
    ("销售经理", "sales_manager", "dept_sub", False),
    ("法务", "legal", "all", False),
    ("项目经理", "project_manager", "custom", False),
    ("成员", "project_member", "self", False),
]

# 角色 → 权限映射
ROLE_PERMS = {
    "super_admin": [p[0] for p in PERMISSIONS],  # 全部
    "finance_director": [
        "invoice:upload", "invoice:read", "invoice:write", "invoice:verify",
        "invoice:submit", "invoice:export",
        "template:read", "template:write",
        "expense:read", "expense:write", "expense:approve", "expense:export",
        "project:read",
        "contract:read", "contract:approve",
        "receivable:read", "receivable:write",
        "audit:read",
        "ai:extract", "ai:risk.scan", "ai:ask",
    ],
    "finance_specialist": [
        "invoice:upload", "invoice:read", "invoice:write", "invoice:verify",
        "template:read", "template:write",
        "expense:read", "expense:write",
        "project:read",
        "ai:extract", "ai:ask",
    ],
    "sales_manager": [
        "invoice:upload", "invoice:read", "expense:read", "expense:write",
        "project:read", "project:write",
        "contract:read", "contract:write",
        "receivable:read", "receivable:write",
        "ai:risk.scan",
    ],
    "legal": [
        "contract:read", "contract:write", "contract:approve",
    ],
    "project_manager": [
        "project:read", "project:write", "milestone:write",
        "contract:read",
        "ai:risk.scan", "ai:ask",
    ],
    "project_member": [
        "project:read",
    ],
}

DEPARTMENTS = [
    ("财务部", "DEPT-FIN", None),
    ("销售部", "DEPT-SAL", None),
    ("法务部", "DEPT-LEG", None),
    ("项目管理部", "DEPT-PRJ", None),
    ("信息技术部", "DEPT-IT", None),
]

USERS = [
    ("admin", "admin@shuzhi.com", "13800000001", "张明（管理员）", "DEPT-FIN", ["super_admin"]),
    ("zhangming", "zhangming@shuzhi.com", "13800000002", "张明", "DEPT-FIN", ["finance_director"]),
    ("wangfang", "wangfang@shuzhi.com", "13800000003", "王芳", "DEPT-FIN", ["finance_specialist"]),
    ("chensiqi", "chensiqi@shuzhi.com", "13800000004", "陈思琪", "DEPT-PRJ", ["project_manager"]),
    ("liming", "liming@shuzhi.com", "13800000005", "李明", "DEPT-LEG", ["legal"]),
    ("liuyang", "liuyang@shuzhi.com", "13800000006", "刘洋", "DEPT-SAL", ["sales_manager"]),
]

CLIENTS = [
    ("C-2026-001", "万象科技有限公司", "万象科技", "91310000MA1FL01X9G", "B"),
    ("C-2026-002", "北辰实业集团", "北辰集团", "91110000MA1BC2X9P", "A"),
    ("C-2026-003", "朗驰智能设备有限公司", "朗驰智能", "91310112MA1GK3X9Q", "B"),
    ("C-2026-004", "用友网络科技股份有限公司", "用友网络", "91110000MA1U8X9PK", "A"),
    ("C-2026-005", "京东企业购", "京东企业购", "91110300MA1JD4X9C0", "C"),
]

DICTIONARIES = [
    # 费用类型
    ("expense_category", "差旅", "差旅", "#4F6BFF"),
    ("expense_category", "招待", "招待", "#7C3AED"),
    ("expense_category", "办公", "办公", "#10B981"),
    ("expense_category", "推广", "推广", "#F59E0B"),
    ("expense_category", "培训", "培训", "#8B5CF6"),
    ("expense_category", "其他", "其他", "#94A3B8"),
    # 合同类型
    ("contract_type", "sales", "销售合同", "#4F6BFF"),
    ("contract_type", "purchase", "采购合同", "#10B981"),
    ("contract_type", "service", "服务合同", "#06B6D4"),
    ("contract_type", "framework", "框架协议", "#7C3AED"),
    # 发票类型
    ("invoice_type", "电子普通发票", "电子普通发票", "#4F6BFF"),
    ("invoice_type", "数电发票", "数电发票", "#7C3AED"),
    ("invoice_type", "专用发票", "专用发票", "#06B6D4"),
]


async def seed():
    engine = create_async_engine(settings.DATABASE_URL, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False)

    async with AsyncSessionLocal() as db:
        # 1. 部门
        dept_map = {}
        for name, code, parent in DEPARTMENTS:
            existing = await db.execute(select(Department).where(Department.code == code))
            dept = existing.scalar_one_or_none()
            if not dept:
                dept = Department(name=name, code=code, parent_id=parent)
                db.add(dept)
                await db.flush()
            dept_map[code] = dept

        # 2. 角色
        role_map = {}
        for name, code, scope, builtin in ROLES:
            existing = await db.execute(select(Role).where(Role.code == code))
            role = existing.scalar_one_or_none()
            if not role:
                role = Role(name=name, code=code, data_scope=scope, is_builtin=builtin)
                db.add(role)
                await db.flush()
            role_map[code] = role

        # 3. 权限
        perm_map = {}
        for code, resource, action, name in PERMISSIONS:
            existing = await db.execute(select(Permission).where(Permission.code == code))
            perm = existing.scalar_one_or_none()
            if not perm:
                perm = Permission(code=code, resource=resource, action=action, name=name)
                db.add(perm)
                await db.flush()
            perm_map[code] = perm

        # 4. 角色-权限
        for role_code, perm_codes in ROLE_PERMS.items():
            role = role_map[role_code]
            for perm_code in perm_codes:
                existing = await db.execute(
                    select(RolePermission).where(
                        RolePermission.role_id == role.id,
                        RolePermission.permission_id == perm_map[perm_code].id,
                    )
                )
                if not existing.scalar_one_or_none():
                    db.add(RolePermission(
                        role_id=role.id,
                        permission_id=perm_map[perm_code].id,
                    ))

        # 5. 用户
        user_map = {}
        for username, email, phone, name, dept_code, role_codes in USERS:
            existing = await db.execute(select(User).where(User.username == username))
            user = existing.scalar_one_or_none()
            if not user:
                user = User(
                    username=username,
                    email=email,
                    phone=phone,
                    name=name,
                    department_id=dept_map[dept_code].id if dept_code in dept_map else None,
                    password_hash=hash_password("admin123"),
                    is_admin=(username == "admin"),
                )
                db.add(user)
                await db.flush()
            user_map[username] = user

        # 6. 用户-角色
        for username, _, _, _, _, role_codes in USERS:
            user = user_map[username]
            for role_code in role_codes:
                existing = await db.execute(
                    select(UserRole).where(
                        UserRole.user_id == user.id,
                        UserRole.role_id == role_map[role_code].id,
                    )
                )
                if not existing.scalar_one_or_none():
                    db.add(UserRole(
                        user_id=user.id,
                        role_id=role_map[role_code].id,
                    ))

        # 7. 字典
        for dict_type, value, label, color in DICTIONARIES:
            existing = await db.execute(
                select(Dictionary).where(
                    Dictionary.dict_type == dict_type,
                    Dictionary.value == value,
                )
            )
            if not existing.scalar_one_or_none():
                db.add(Dictionary(
                    dict_type=dict_type, value=value, label=label, color=color,
                ))

        # 8. 客户
        client_map = {}
        for code, name, short, tax_no, level in CLIENTS:
            existing = await db.execute(select(Client).where(Client.code == code))
            client = existing.scalar_one_or_none()
            if not client:
                client = Client(code=code, name=name, short_name=short, tax_no=tax_no, level=level)
                db.add(client)
                await db.flush()
            client_map[code] = client

        # 9. 示例项目
        existing_project = await db.execute(select(Project).limit(1))
        if not existing_project.scalar_one_or_none():
            project = Project(
                code="PRJ-2026-001",
                name="数智化二期",
                type="SaaS 平台升级",
                client_id=client_map["C-2026-001"].id,
                manager_id=user_map["chensiqi"].id,
                status="in_progress",
                start_date=date(2026, 3, 15),
                end_date=date(2026, 8, 30),
                contract_amount=128000000,  # 128 万 = 1280000 元 = 128000000 分
                budget=28000000,  # 28 万
                progress=68,
                description="在万象科技一期基础上扩展发票识别、模板管理、回款管理等功能模块。",
            )
            db.add(project)
            await db.flush()

            for seq, name, status, progress in [
                (1, "项目启动会", "done", 100),
                (2, "需求调研", "done", 100),
                (3, "系统集成", "done", 100),
                (4, "UAT 测试", "current", 60),
                (5, "试运行", "todo", 0),
                (6, "正式上线", "todo", 0),
            ]:
                db.add(ProjectMilestone(
                    project_id=project.id,
                    name=name,
                    seq=seq,
                    status=status,
                    progress=progress,
                ))

        await db.commit()

        # ============================================================
        # 10. 补充字典（项目状态 / 审批状态 / 回款状态 / 成本中心）
        # ============================================================
        EXTRA_DICTS = [
            ("project_status", "planning", "未开始", "#94A3B8"),
            ("project_status", "in_progress", "进行中", "#4F6BFF"),
            ("project_status", "paused", "已暂停", "#F59E0B"),
            ("project_status", "completed", "已完成", "#10B981"),
            ("project_status", "archived", "已归档", "#6B7280"),
            ("approval_status", "in_progress", "审批中", "#4F6BFF"),
            ("approval_status", "approved", "已通过", "#10B981"),
            ("approval_status", "rejected", "已驳回", "#EF4444"),
            ("approval_status", "cancelled", "已撤回", "#94A3B8"),
            ("receivable_status", "pending", "待回款", "#4F6BFF"),
            ("receivable_status", "partial", "部分回款", "#F59E0B"),
            ("receivable_status", "completed", "已完成", "#10B981"),
            ("receivable_status", "overdue", "已逾期", "#EF4444"),
            ("receivable_status", "cancelled", "已取消", "#94A3B8"),
            ("cost_center", "CC-2026-001", "财务部-运营", "#4F6BFF"),
            ("cost_center", "CC-2026-002", "销售部-华东区", "#7C3AED"),
            ("cost_center", "CC-2026-003", "研发部-平台", "#10B981"),
            ("cost_center", "CC-2026-004", "项目管理部", "#F59E0B"),
        ]
        for dt, val, label, color in EXTRA_DICTS:
            existing = await db.execute(
                select(Dictionary).where(Dictionary.dict_type == dt, Dictionary.value == val)
            )
            if not existing.scalar_one_or_none():
                db.add(Dictionary(dict_type=dt, value=val, label=label, color=color))

        # ============================================================
        # 11. 合同模板（3 套）
        # ============================================================
        for code, name, ctype in [
            ("CT-001", "标准销售合同 v2.1", "sales"),
            ("CT-002", "SaaS 服务合同", "service"),
            ("CT-003", "采购框架协议", "framework"),
        ]:
            existing = await db.execute(select(ContractTemplate).where(ContractTemplate.code == code))
            if not existing.scalar_one_or_none():
                db.add(ContractTemplate(
                    code=code, name=name, type=ctype,
                    content={"terms": [{"id": "T1", "title": "服务内容", "content": "..."}]},
                    is_active=True,
                ))

        # ============================================================
        # 12. 合同样例（2 份）
        # ============================================================
        contract_seed = [
            ("HT-2026-001", "万象科技 SaaS 服务合同 2026Q2", "sales", "C-2026-001", 4, 8650000, "approved", date(2026, 6, 11)),
            ("HT-2026-002", "北辰集团系统集成合同", "service", "C-2026-002", 4, 24800000, "approving", date(2026, 6, 12)),
        ]
        for code, name, ctype, client_code, manager_user_id, amount_cents, status, sign_date in contract_seed:
            existing = await db.execute(select(Contract).where(Contract.code == code))
            if not existing.scalar_one_or_none():
                cm = await db.execute(select(Client).where(Client.code == client_code))
                client = cm.scalar_one_or_none()
                if client:
                    db.add(Contract(
                        code=code, name=name, type=ctype, client_id=client.id,
                        manager_id=manager_user_id, amount=amount_cents, currency="CNY",
                        sign_date=sign_date, status=status,
                        payment_method="季付", payment_term="30 天",
                        summary=f"{name} - 自动种子数据",
                    ))

        # ============================================================
        # 13. 销售费用样例（3 笔）
        # ============================================================
        expense_seed = [
            ("EX-2026-001", "差旅", "上海-北京客户拜访（北辰集团）", 482000, 4, "draft"),
            ("EX-2026-002", "招待", "万象科技季度合作晚宴", 120000, 5, "pending"),
            ("EX-2026-003", "办公", "Q2 部门办公用品采购", 35000, 2, "approved"),
        ]
        for code, category, title, amount, applicant_id, status in expense_seed:
            existing = await db.execute(select(Expense).where(Expense.code == code))
            if not existing.scalar_one_or_none():
                db.add(Expense(
                    code=code, category=category, title=title,
                    amount=amount, currency="CNY",
                    expense_date=date.today(),
                    applicant_id=applicant_id,
                    department_id=None,  # 让数据库按申请人实际部门存（运行时由 service 填）
                    status=status,
                    submit_at=datetime.utcnow() if status != "draft" else None,
                ))

        # ============================================================
        # 14. 回款样例（2 笔，contract_id / client_id 动态查）
        # ============================================================
        first_contract = (await db.execute(select(Contract).order_by(Contract.id.asc()).limit(1))).scalar_one_or_none()
        first_client = (await db.execute(select(Client).order_by(Client.id.asc()).limit(1))).scalar_one_or_none()
        if first_contract and first_client:
            recv_seed = [
                ("HK-2026-001", first_contract.id, first_client.id, "合同尾款", 2800000, date(2026, 6, 4), "overdue", 8, 4),
                ("HK-2026-002", first_contract.id, first_client.id, "第二笔", 8650000, date(2026, 7, 1), "pending", 0, 4),
            ]
            for code, contract_pk, client_pk, rtype, plan_amount, plan_date, status, overdue_days, manager_id in recv_seed:
                existing = await db.execute(select(Receivable).where(Receivable.code == code))
                if not existing.scalar_one_or_none():
                    db.add(Receivable(
                        code=code, contract_id=contract_pk, client_id=client_pk,
                        type=rtype, plan_amount=plan_amount, received_amount=0,
                        plan_date=plan_date, term_days=30, manager_id=manager_id,
                        status=status, overdue_days=overdue_days,
                    ))

        # ============================================================
        # 15. 发票模板样例（1 套差旅 + 字段）
        # ============================================================
        existing_tpl = await db.execute(select(InvoiceTemplate).where(InvoiceTemplate.code == "TPL-TR-2026-001"))
        if not existing_tpl.scalar_one_or_none():
            tpl = InvoiceTemplate(
                code="TPL-TR-2026-001", name="差旅报销模板",
                category="差旅",
                description="含机票/酒店/打车/餐补，自动汇总",
                icon="差", icon_colors="#4F6BFF,#7C3AED",
                default_tax_rate=Decimal("0.06"),
                is_pinned=True, usage_count=86, rating=Decimal("4.80"),
                status="enabled", creator_id=1,
            )
            db.add(tpl)
            await db.flush()
            for seq, (label, key, ftype, required) in enumerate([
                ("发票类型", "invoiceType", "text", True),
                ("发票号码", "invoiceNo", "text", True),
                ("开票日期", "issueDate", "date", True),
                ("价税合计", "totalAmount", "amount", True),
                ("税率", "taxRate", "rate", False),
                ("报销人", "reimburserId", "user", True),
                ("关联合同", "contractId", "ref", False),
                ("备注", "remark", "textarea", False),
            ], start=1):
                db.add(InvoiceTemplateField(
                    template_id=tpl.id, seq=seq, label=label, key=key,
                    type=ftype, is_required=required, ai_support=True,
                    default_value=None if required else ("currentUser" if key == "reimburserId" else None),
                    ref_type="contract" if key == "contractId" else None,
                    sort=seq,
                ))

        # ============================================================
        # 16. 通知样例（2 条）
        # ============================================================
        from app.modules.common.models import Notification as _N
        for user_id, ntype, title, content in [
            (1, "todo", "HT-2026-002 待你审批", "北辰集团系统集成合同已提交审批"),
            (2, "mention", "@提及了你", "陈思琪在项目评论中 @了你"),
        ]:
            existing = await db.execute(select(_N).where(_N.user_id == user_id, _N.title == title))
            if not existing.scalar_one_or_none():
                db.add(_N(user_id=user_id, type=ntype, title=title, content=content, link="/"))

        # ============================================================
        # 17. AI Alert 样例（3 条）
        # ============================================================
        for user_id, level, atype, title, summary, action_url in [
            (None, "high", "contract_overdue", "合同 HT-2026-001 已逾期 3 天未签字",
             "金额 8.65 万，建议立即催办客户法务", "/contracts/7"),
            (None, "medium", "receivable_overdue", "回款 HK-2026-001 逾期 9 天",
             "万象科技 2.8 万尾款待催收", "/receivables/4"),
            (1, "low", "expense_pending", "EX-2026-002 待你审批",
             "招待费 1,200 元，已提交 1 天", "/expenses/9"),
        ]:
            existing = await db.execute(select(AIAlert).where(AIAlert.title == title))
            if not existing.scalar_one_or_none():
                db.add(AIAlert(
                    tenant_id=1, user_id=user_id,
                    level=level, type=atype, title=title, summary=summary,
                    action_url=action_url, action_label="立即处理",
                    status="unread",
                ))

        await db.commit()
        print("✅ 种子数据初始化完成！")
        print(f"   部门: {len(DEPARTMENTS)}")
        print(f"   角色: {len(ROLES)}")
        print(f"   权限: {len(PERMISSIONS)}")
        print(f"   用户: {len(USERS)} (默认密码: admin123)")
        print(f"   字典: {len(DICTIONARIES) + 18}（含扩展）")
        print(f"   客户: {len(CLIENTS)}")
        print(f"   合同模板: 3")
        print(f"   合同样例: 2 / 销售费用: 3 / 回款: 2")
        print(f"   发票模板: 1 套（差旅）")


if __name__ == "__main__":
    asyncio.run(seed())
