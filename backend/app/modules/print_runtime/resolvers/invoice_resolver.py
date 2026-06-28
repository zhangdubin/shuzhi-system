"""UDPE InvoiceResolver：根据发票 ID 取数据。"""
from app.modules.invoice_ocr import service as invoice_service
from app.modules.print_runtime.resolvers.base import BaseResolver


class InvoiceResolver(BaseResolver):
    doc_type = "invoice"

    async def _resolve(self, identifier, ctx):
        invoice_id = int(identifier)
        db = ctx.extra["db"]
        data = await invoice_service.get_invoice(db, invoice_id)
        return {"invoice": data}
