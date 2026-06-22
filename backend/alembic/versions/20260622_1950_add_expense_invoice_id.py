"""add expense invoice_id (手动关联识别后的发票到已有费用)

Revision ID: 20260622_1950
Revises: 20260622_1859
Create Date: 2026-06-22 19:50
"""
from alembic import op
import sqlalchemy as sa

revision = "20260622_1950"
down_revision = "20260622_1859"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("expenses", sa.Column("invoice_id", sa.BigInteger(), nullable=True))
    op.create_index("ix_expenses_invoice_id", "expenses", ["invoice_id"])
    # 不加 FK 约束（避免影响 OCR → 入账的老链路；只在 service 层校验存在性）


def downgrade():
    op.drop_index("ix_expenses_invoice_id", table_name="expenses")
    op.drop_column("expenses", "invoice_id")
