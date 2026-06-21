"""add dict_types table for category management

Revision ID: add_dict_types_table
Revises: add_invoice_verify_code
Create Date: 2026-06-18
"""
from alembic import op
import sqlalchemy as sa

revision = "add_dict_types_table"
down_revision = "add_invoice_verify_code"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "dict_types",
        sa.Column("id", sa.BigInteger, primary_key=True),
        sa.Column("code", sa.String(32), unique=True, nullable=False, index=True),
        sa.Column("name", sa.String(64), nullable=False),
        sa.Column("description", sa.String(256), nullable=True),
        sa.Column("is_builtin", sa.Boolean, default=False),
        sa.Column("sort", sa.Integer, default=0),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
    )
    # 把现有 7 个 dictType 灌进 dict_types 表（用之前 list_dict_types 的中文映射）
    _MAP = {
        "invoice_type": "发票类型",
        "expense_category": "费用类别",
        "project_status": "项目状态",
        "contract_type": "合同类型",
        "approval_status": "审批状态",
        "receivable_status": "回款状态",
        "cost_center": "成本中心",
    }
    for code, name in _MAP.items():
        op.execute(
            f"INSERT INTO dict_types (code, name, is_builtin, sort) VALUES ('{code}', '{name}', true, 0) ON CONFLICT (code) DO NOTHING"
        )


def downgrade():
    op.drop_table("dict_types")
