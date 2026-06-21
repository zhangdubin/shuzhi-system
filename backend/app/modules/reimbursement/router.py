"""
报销中心路由
- /api/v1/reimbursements/*
"""
from datetime import date
from fastapi import APIRouter, Depends, Query, UploadFile, File, Form
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_user, require_permission, CurrentUser
from app.modules.reimbursement import service
from app.modules.reimbursement.schemas import (
    ReimburseListRequest, ReimburseCreate, ReimburseUpdate,
    ReimburseFillback, ReimburseDelete, AiDescriptionRequest, AiRiskRequest,
    ReimburseTemplateCreate, ReimburseTemplateUpdate, ReimburseTemplateDelete, ReimburseTemplateClone,
)
from app.modules.expense.models import Expense

router = APIRouter()


@router.post("/list", summary="报销单列表")
async def list_forms(
    req: ReimburseListRequest,
    db: AsyncSession = Depends(get_db),
    _user: CurrentUser = Depends(get_current_user),
):
    items, total = await service.list_forms(db, req.page, req.pageSize, req.keyword, req.filters)
    return {"code": 0, "data": {"list": items, "total": total, "page": req.page, "pageSize": req.pageSize}}


@router.post("/detail", summary="报销单详情")
async def get_form(
    formId: int = Query(...),
    db: AsyncSession = Depends(get_db),
    _user: CurrentUser = Depends(get_current_user),
):
    return {"code": 0, "data": await service.get_form(db, formId)}


@router.post("/create", summary="从销售费用生成报销单")
async def create_form(
    req: ReimburseCreate,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("expense:write")),
):
    data = await service.create_from_expenses(db, req, current_user.id)
    return {"code": 0, "data": data, "message": "已生成报销单"}


@router.post("/update", summary="编辑报销单")
async def update_form(
    req: ReimburseUpdate,
    db: AsyncSession = Depends(get_db),
    _user: CurrentUser = Depends(require_permission("expense:write")),
):
    data = await service.update_form(db, req)
    return {"code": 0, "data": data, "message": "已保存"}


@router.post("/delete", summary="删除报销单")
async def delete_form(
    req: ReimburseDelete,
    db: AsyncSession = Depends(get_db),
    _user: CurrentUser = Depends(require_permission("expense:write")),
):
    await service.delete_form(db, req.formId)
    return {"code": 0, "message": "已删除"}


@router.post("/mark-printed", summary="标记为已打印")
async def mark_printed(
    req: ReimburseDelete,
    db: AsyncSession = Depends(get_db),
    _user: CurrentUser = Depends(get_current_user),
):
    data = await service.mark_printed(db, req.formId)
    return {"code": 0, "data": data, "message": "已标记为已打印"}


@router.post("/fillback", summary="回填实际报销结果")
async def fillback(
    req: ReimburseFillback,
    db: AsyncSession = Depends(get_db),
    _user: CurrentUser = Depends(require_permission("expense:write")),
):
    data = await service.fillback(db, req)
    return {"code": 0, "data": data, "message": "已回填并同步到销售费用"}


# ===== 模板（含自定义）=====
@router.get("/templates", summary="所有模板列表（内置+自定义）")
async def list_templates(
    db: AsyncSession = Depends(get_db),
    _user: CurrentUser = Depends(get_current_user),
):
    return {"code": 0, "data": await service.list_all_templates(db)}


@router.get("/templates/{code}", summary="获取单个模板")
async def get_template(
    code: str,
    db: AsyncSession = Depends(get_db),
    _user: CurrentUser = Depends(get_current_user),
):
    t = await service.get_template_by_code_async(db, code)
    if not t:
        return {"code": 404, "message": "模板不存在", "data": None}
    return {"code": 0, "data": t}


@router.post("/templates/custom", summary="创建自定义模板")
async def create_custom_template(
    req: ReimburseTemplateCreate,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    data = await service.create_custom_template(db, req, user.id)
    return {"code": 0, "data": data, "message": "已创建"}


@router.post("/templates/custom/update", summary="更新自定义模板")
async def update_custom_template(
    req: ReimburseTemplateUpdate,
    db: AsyncSession = Depends(get_db),
    _user: CurrentUser = Depends(get_current_user),
):
    data = await service.update_custom_template(db, req)
    return {"code": 0, "data": data, "message": "已更新"}


@router.post("/templates/custom/delete", summary="删除自定义模板")
async def delete_custom_template(
    req: ReimburseTemplateDelete,
    db: AsyncSession = Depends(get_db),
    _user: CurrentUser = Depends(get_current_user),
):
    await service.delete_custom_template(db, req.templateId)
    return {"code": 0, "message": "已删除"}


@router.post("/templates/clone", summary="复制内置模板为自定义")
async def clone_template(
    req: ReimburseTemplateClone,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    data = await service.clone_builtin_to_custom(db, req.code, user.id)
    return {"code": 0, "data": data, "message": "已复制"}


@router.post("/templates/recognize-text", summary="从文本识别模板")
async def recognize_template(
    text: str = Form(...),
    _user: CurrentUser = Depends(get_current_user),
):
    """从用户粘贴的文本中识别出 schema 字段（启发式）"""
    return {"code": 0, "data": service.recognize_template_from_text(text)}


@router.post("/templates/recognize-file", summary="从文件识别模板")
async def recognize_template_file(
    file: UploadFile = File(...),
    _user: CurrentUser = Depends(get_current_user),
):
    """从上传的文件中识别 schema 字段
    支持格式：
    - .xlsx：openpyxl 读真实合并单元格 → table 结构
    - .txt/.md/.csv/.json：按文本读取（自动检测 utf-8 / gbk）
    """
    raw = await file.read()
    fname = file.filename or ""
    name_lower = fname.lower()
    # xlsx 走真实表格路径
    if name_lower.endswith(".xlsx") or raw[:2] == b"PK":
        table = service.extract_xlsx_table(raw)
        if table and table.get("rows"):
            schema = service.build_schema_from_table(table)
            # 同时给前端一个"文本预览"
            text_preview = "\n".join(
                "\t".join(c["text"] for c in row) for row in table["rows"][:8]
            )
            confidence = 0.95  # xlsx 真实表格，置信度高
            return {
                "code": 0,
                "data": {
                    "detectedFields": [{"key": f.get("key", "text"), "label": f.get("label", ""), "type": f.get("type", "text")} for f in schema.get("summary", {}).get("fields", [])],
                    "suggestedSchema": schema,
                    "textPreview": text_preview,
                    "confidence": confidence,
                },
                "filename": fname,
            }
    # 文本降级
    text = service.extract_text_from_bytes(raw, fname)
    if not text.strip():
        return {"code": 400, "message": f"无法从文件 {fname} 提取文本", "data": None}
    return {"code": 0, "data": service.recognize_template_from_text(text), "filename": fname}


# ===== AI =====
@router.post("/ai-description", summary="AI 生成报销说明")
async def ai_description(
    req: AiDescriptionRequest,
    db: AsyncSession = Depends(get_db),
    _user: CurrentUser = Depends(get_current_user),
):
    expense_data = None
    if req.expenseIds:
        rows = (await db.execute(
            Expense.__table__.select().where(Expense.id.in_(req.expenseIds))
        )).mappings().all()
        expense_data = [dict(r) for r in rows]
    text = service.ai_generate_description(req.expenseIds, expense_data)
    return {"code": 0, "data": {"description": text}}


@router.post("/ai-risk", summary="AI 风险检测")
async def ai_risk(
    req: AiRiskRequest,
    db: AsyncSession = Depends(get_db),
    _user: CurrentUser = Depends(get_current_user),
):
    data = await service.ai_risk_check(db, req.expenseIds, req.formId)
    return {"code": 0, "data": data}


# ===== 导出 PDF =====
@router.get("/export-data", summary="导出 PDF/打印所需的数据（含模板 schema）")
async def export_data(
    formId: int = Query(...),
    db: AsyncSession = Depends(get_db),
    _user: CurrentUser = Depends(get_current_user),
):
    """前端 jsPDF/print 模板所需的所有数据"""
    f = await service.get_form(db, formId)
    return {"code": 0, "data": f}
