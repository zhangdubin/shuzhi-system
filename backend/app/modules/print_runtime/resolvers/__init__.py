"""UDPE Resolver 集合：合同 / 报销 / 费用 / 发票。

设计文档：plans/udpe-design/design.md §六 6.4
"""
from app.modules.print_runtime.resolvers.base import BaseResolver
from app.modules.print_runtime.resolvers.contract_resolver import ContractResolver
from app.modules.print_runtime.resolvers.expense_resolver import ExpenseResolver
from app.modules.print_runtime.resolvers.invoice_resolver import InvoiceResolver
from app.modules.print_runtime.resolvers.reimbursement_resolver import ReimbursementResolver

__all__ = [
    "BaseResolver",
    "ContractResolver",
    "ReimbursementResolver",
    "ExpenseResolver",
    "InvoiceResolver",
]
