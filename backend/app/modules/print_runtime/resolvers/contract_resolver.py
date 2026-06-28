"""UDPE ContractResolver：根据 contract ID 取合同数据。"""
from app.modules.contract import service as contract_service
from app.modules.print_runtime.resolvers.base import BaseResolver


class ContractResolver(BaseResolver):
    doc_type = "contract"

    async def _resolve(self, identifier, ctx):
        contract_id = int(identifier)
        db = ctx.extra["db"]
        data = await contract_service.get_contract(db, contract_id)
        return {"contract": data}
