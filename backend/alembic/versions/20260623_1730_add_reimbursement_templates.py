"""add reimbursement_templates table (was missing in 20260619_0200_add_reimbursement)

Revision ID: 20260623_1730
Revises: 20260623_1700
Create Date: 2026-06-23 17:30:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '20260623_1730'
down_revision: Union[str, None] = '20260623_1700'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'reimbursement_templates',
        sa.Column('id', sa.BigInteger(), nullable=False),
        sa.Column('code', sa.String(length=64), nullable=False),
        sa.Column('name', sa.String(length=128), nullable=False),
        sa.Column('type', sa.String(length=32), nullable=False, server_default='custom'),
        sa.Column('icon', sa.String(length=8), nullable=False, server_default='📋'),
        sa.Column('color', sa.String(length=16), nullable=False, server_default='#4F6BFF'),
        sa.Column('description', sa.String(length=256), nullable=True),
        sa.Column('schema_json', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('is_system', sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column('created_by', sa.BigInteger(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['created_by'], ['users.id'], name='fk_reimburse_template_creator'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('code', name='uq_reimburse_template_code'),
    )
    op.create_index('ix_reimbursement_templates_code', 'reimbursement_templates', ['code'])
    op.create_index('ix_reimbursement_templates_type', 'reimbursement_templates', ['type'])


def downgrade() -> None:
    op.drop_index('ix_reimbursement_templates_type', 'reimbursement_templates')
    op.drop_index('ix_reimbursement_templates_code', 'reimbursement_templates')
    op.drop_table('reimbursement_templates')
