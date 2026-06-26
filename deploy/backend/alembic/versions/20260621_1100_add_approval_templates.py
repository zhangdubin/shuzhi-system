"""add approval templates

Revision ID: 20260621_1100
Revises: 20260619_0200
Create Date: 2026-06-21 11:00:00.000000
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = '20260621_1100'
down_revision: Union[str, None] = '20260619_0200'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'approval_templates',
        sa.Column('id', sa.BigInteger(), nullable=False),
        sa.Column('name', sa.String(length=64), nullable=False),
        sa.Column('business_type', sa.String(length=32), nullable=False),
        sa.Column('rules', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='[]'),
        sa.Column('condition', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('is_default', sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column('sort_order', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('remark', sa.String(length=256), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_approval_templates_business_type', 'approval_templates', ['business_type'])
    op.create_index('ix_approval_templates_is_default', 'approval_templates', ['is_default'])
    op.create_index('ix_approval_templates_is_active', 'approval_templates', ['is_active'])
    # 升级时让既有 approval_flows.template_id 也能接住（虽然 ApprovalFlow 模型里已存在，列可能缺）
    # 兼容旧表：加列（如果不存在）
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    cols = [c['name'] for c in inspector.get_columns('approval_flows')]
    if 'template_id' not in cols:
        op.add_column('approval_flows', sa.Column('template_id', sa.BigInteger(), nullable=True))


def downgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    cols = [c['name'] for c in inspector.get_columns('approval_flows')]
    if 'template_id' in cols:
        op.drop_column('approval_flows', 'template_id')
    op.drop_index('ix_approval_templates_is_active', 'approval_templates')
    op.drop_index('ix_approval_templates_is_default', 'approval_templates')
    op.drop_index('ix_approval_templates_business_type', 'approval_templates')
    op.drop_table('approval_templates')
