"""UDPE ExpenseResolver：根据费用 ID 取数据。"""
from app.modules.expense import service as expense_service
from app.modules.print_runtime.resolvers.base import BaseResolver


class ExpenseResolver(BaseResolver):
    doc_type = "expense"

    async def _resolve(self, identifier, ctx):
        expense_id = int(identifier)
        db = ctx.extra["db"]
        data = await expense_service.get_expense(db, expense_id)
        return {"expense": data}
