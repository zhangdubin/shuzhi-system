"""UDPE ReimbursementResolver：根据报销单 ID 取数据。"""
from app.modules.reimbursement import service as reimburse_service
from app.modules.print_runtime.resolvers.base import BaseResolver


class ReimbursementResolver(BaseResolver):
    doc_type = "reimbursement"

    async def _resolve(self, identifier, ctx):
        form_id = int(identifier)
        db = ctx.extra["db"]
        data = await reimburse_service.get_form(db, form_id)
        # 报销 service 返回的 dict 字段在顶层，UDPE 模板期望 form.xxx，把数据归到 form 键
        return {"form": data}
