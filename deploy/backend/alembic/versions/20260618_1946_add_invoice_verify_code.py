"""add invoice verify_code

Revision ID: add_invoice_verify_code
Revises: 5dd5dc80fb22
Create Date: 2026-06-18
"""
from alembic import op
import sqlalchemy as sa

revision = "add_invoice_verify_code"
down_revision = "5dd5dc80fb22"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("invoices", sa.Column("verify_code", sa.String(64), nullable=True))
    op.add_column("invoices", sa.Column("remarks", sa.String(512), nullable=True))


def downgrade():
    op.drop_column("invoices", "remarks")
    op.drop_column("invoices", "verify_code")
