"""add invoice template_id (R20: 批量上传时按用户选择的识别模板入库)

Revision ID: 20260622_1859
Revises: 20260621_1100
Create Date: 2026-06-22 18:59
"""
from alembic import op
import sqlalchemy as sa

revision = "20260622_1859"
down_revision = "20260621_1100"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("invoices", sa.Column("template_id", sa.BigInteger(), nullable=True))
    op.create_index("ix_invoices_template_id", "invoices", ["template_id"])


def downgrade():
    op.drop_index("ix_invoices_template_id", table_name="invoices")
    op.drop_column("invoices", "template_id")
