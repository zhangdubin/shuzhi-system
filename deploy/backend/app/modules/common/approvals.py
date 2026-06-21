"""
通用审批流引擎
- 业务方调用 `create_flow(db, business_type, business_id, steps, current_user_id)` 创建审批流
- `act(db, flow_id, action, operator_id, comment, transfer_to)` 推进审批
- 步骤规则支持 "amount >= 5000" 这类条件
"""
from datetime import datetime
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.exceptions import ParamErrorException, NotFoundException
# Approval 模型已迁移到 common.models，避开 approvals <-> expense 循环
from app.modules.common.models import ApprovalFlow, ApprovalStep


# ===== 步骤定义 =====
# (seq, name, approver_role_or_user_id_or_rule)

# 业务方可传入这种 list 触发引擎自动生成步骤
# 示例（销售费用 4 步）：
#   [
#     (1, "提交", "submitter"),
#     (2, "直属上级", "direct_leader"),
#     (3, "财务审核", "finance"),
#     (4, "总经理审批", "gm_if_over_5000"),
#   ]
# 引擎会把字符串规则解析成具体的 approver_id 或 trigger_rule


# 角色 code → 用户 role.code 反查用
ROLE_CODE_GM = "executive"
ROLE_CODE_FINANCE = "finance_director"  # 财务总监


async def _resolve_approver(db: AsyncSession, rule: str, applicant_id: int, amount: int = 0) -> tuple[Optional[int], Optional[str]]:
    """
    解析审批人规则。
    返回 (approver_id, trigger_rule)
    - rule="submitter": (applicant_id, None)
    - rule="direct_leader": (申请人 department.manager_id, None)
    - rule="finance": (任意 finance_director 角色用户, None)
    - rule="gm_if_over_5000": (None, "amount >= 5000") — 该步骤待触发
    """
    from app.modules.auth.models import User, Role
    if rule == "submitter":
        return (applicant_id, None)
    if rule == "direct_leader":
        # 查申请人部门负责人
        u = (await db.execute(select(User).where(User.id == applicant_id))).scalar_one_or_none()
        if u and u.department_id:
            dept = (await db.execute(select(User).where(User.id == u.department_id))).scalar_one_or_none()
            # 用 User 表 department 反查不方便，直接看 department.manager_id
            from app.modules.auth.models import Department
            d = (await db.execute(select(Department).where(Department.id == u.department_id))).scalar_one_or_none()
            return (d.manager_id if d else None, None)
        return (None, None)
    if rule == "finance":
        r = (await db.execute(select(Role).where(Role.code == ROLE_CODE_FINANCE))).scalar_one_or_none()
        if r:
            uls = (await db.execute(select(User.id).join(User.roles).where(Role.id == r.id).limit(1))).scalar_one_or_none()
            return (uls, None)
        return (None, None)
    if rule == "gm_if_over_5000":
        return (None, "amount >= 5000")
    if rule == "gm":
        r = (await db.execute(select(Role).where(Role.code == ROLE_CODE_GM))).scalar_one_or_none()
        if r:
            uls = (await db.execute(select(User.id).join(User.roles).where(Role.id == r.id).limit(1))).scalar_one_or_none()
            return (uls, None)
        return (None, None)
    return (None, None)


async def create_flow(
    db: AsyncSession,
    business_type: str,
    business_id: int,
    step_rules: list[str],  # ["submitter", "direct_leader", "finance", "gm_if_over_5000"]
    applicant_id: int,
    amount: int = 0,
) -> ApprovalFlow:
    """创建审批流 + 自动展开步骤"""
    flow = ApprovalFlow(
        business_type=business_type,
        business_id=business_id,
        status="in_progress",
        current_step=1,
        total_steps=len(step_rules),
    )
    db.add(flow)
    await db.flush()

    for seq, rule in enumerate(step_rules, start=1):
        approver_id, trigger_rule = await _resolve_approver(db, rule, applicant_id, amount)
        status = "todo"
        if seq == 1:
            status = "current"  # 第 1 步是"提交"，自动 current
        step = ApprovalStep(
            flow_id=flow.id,
            seq=seq,
            name=_rule_to_name(rule),
            approver_id=approver_id,
            status=status,
            trigger_rule=trigger_rule,
        )
        db.add(step)
    await db.commit()
    await db.refresh(flow)
    return flow


def _rule_to_name(rule: str) -> str:
    return {
        "submitter": "提交",
        "direct_leader": "直属上级",
        "finance": "财务审核",
        "gm_if_over_5000": "总经理审批",
        "gm": "总经理审批",
    }.get(rule, rule)


async def act(
    db: AsyncSession,
    flow_id: int,
    action: str,  # approve / reject / transfer
    operator_id: int,
    comment: Optional[str] = None,
    transfer_to: Optional[int] = None,
) -> ApprovalFlow:
    """
    审批动作：
    - approve: 当前 step → done；下一步 → current；末步 approve → flow 标 approved
    - reject: 当前 step → rejected；flow 标 rejected
    - transfer: 当前 step → transferred；替换 approver_id（不推进）
    """
    flow = (await db.execute(
        select(ApprovalFlow)
        .where(ApprovalFlow.id == flow_id)
    )).scalar_one_or_none()
    if not flow:
        raise NotFoundException(f"审批流不存在：{flow_id}")
    if flow.status != "in_progress":
        raise ParamErrorException(f"审批流已结束：{flow.status}")

    steps = (await db.execute(
        select(ApprovalStep)
        .where(ApprovalStep.flow_id == flow_id)
        .order_by(ApprovalStep.seq.asc())
    )).scalars().all()

    current = next((s for s in steps if s.status == "current"), None)
    if not current:
        raise ParamErrorException("没有进行中的审批节点")

    if action == "approve":
        current.action = "approve"
        current.comment = comment
        current.status = "done"
        current.finished_at = datetime.utcnow()
        # 推进下一步
        next_step = next((s for s in steps if s.seq == current.seq + 1), None)
        if next_step:
            next_step.status = "current"
            flow.current_step = next_step.seq
        else:
            # 最后一步
            flow.status = "approved"
            flow.finished_at = datetime.utcnow()
    elif action == "reject":
        current.action = "reject"
        current.comment = comment
        current.status = "rejected"
        current.finished_at = datetime.utcnow()
        flow.status = "rejected"
        flow.finished_at = datetime.utcnow()
    elif action == "transfer":
        if not transfer_to:
            raise ParamErrorException("转交必须指定 transferTo")
        current.action = "transfer"
        current.comment = comment
        current.status = "transferred"
        current.approver_id = transfer_to
        current.finished_at = datetime.utcnow()
        # 不推进；新建一个"待转交接手"的 current step
        from app.modules.common.models import ApprovalStep as _Step
        new_step = _Step(
            flow_id=flow.id,
            seq=current.seq,
            name=current.name,
            approver_id=transfer_to,
            status="current",
        )
        db.add(new_step)
    else:
        raise ParamErrorException(f"未知 action：{action}")

    await db.commit()
    await db.refresh(flow)
    return flow


async def get_flow(db: AsyncSession, business_type: str, business_id: int) -> Optional[ApprovalFlow]:
    """按业务对象查审批流（取最新一条；含步骤）"""
    flow = (await db.execute(
        select(ApprovalFlow)
        .where(
            ApprovalFlow.business_type == business_type,
            ApprovalFlow.business_id == business_id,
        )
        .order_by(ApprovalFlow.id.desc())
        .limit(1)
    )).scalar_one_or_none()
    if not flow:
        return None
    steps = (await db.execute(
        select(ApprovalStep)
        .where(ApprovalStep.flow_id == flow.id)
        .order_by(ApprovalStep.seq.asc())
    )).scalars().all()
    flow.__dict__["_steps_cache"] = steps
    return flow


def serialize_flow(flow: ApprovalFlow, steps: list[ApprovalStep]) -> dict:
    """序列化为 API.md 期望的 approvalFlow 结构"""
    from app.modules.auth.models import User
    # steps 传进来时从外部注入更好
    return {
        "flowId": flow.id,
        "status": flow.status,
        "currentStep": flow.current_step,
        "totalSteps": flow.total_steps,
        "startedAt": flow.started_at.isoformat() if flow.started_at else None,
        "finishedAt": flow.finished_at.isoformat() if flow.finished_at else None,
        "steps": [
            {
                "stepId": s.id,
                "seq": s.seq,
                "name": s.name,
                "approverId": s.approver_id,
                "status": s.status,
                "action": s.action,
                "comment": s.comment,
                "triggerRule": s.trigger_rule,
                "finishedAt": s.finished_at.isoformat() if s.finished_at else None,
            }
            for s in steps
        ],
    }
