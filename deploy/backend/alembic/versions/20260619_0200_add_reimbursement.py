"""add reimbursement module

Revision ID: add_reimbursement_2026
Revises: 5dd5dc80fb22
Create Date: 2026-06-19 02:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '20260619_0200'
down_revision: Union[str, None] = '20260619_0100'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'reimbursement_forms',
        sa.Column('id', sa.BigInteger(), nullable=False),
        sa.Column('form_no', sa.String(length=32), nullable=False),
        sa.Column('template_type', sa.String(length=32), nullable=False, server_default='general'),
        sa.Column('title', sa.String(length=128), nullable=False),
        sa.Column('applicant_id', sa.BigInteger(), nullable=False),
        sa.Column('department_id', sa.BigInteger(), nullable=True),
        sa.Column('total_amount', sa.BigInteger(), nullable=False, server_default='0'),
        sa.Column('actual_amount', sa.BigInteger(), nullable=False, server_default='0'),
        sa.Column('currency', sa.String(length=8), nullable=False, server_default='CNY'),
        sa.Column('status', sa.String(length=16), nullable=False, server_default='draft'),
        sa.Column('expense_date', sa.Date(), nullable=True),
        sa.Column('payment_date', sa.Date(), nullable=True),
        sa.Column('voucher_no', sa.String(length=64), nullable=True),
        sa.Column('ai_description', sa.Text(), nullable=True),
        sa.Column('ai_risk_flag', sa.String(length=16), nullable=True),
        sa.Column('ai_risk_reason', sa.Text(), nullable=True),
        sa.Column('remark', sa.Text(), nullable=True),
        sa.Column('template_snapshot', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['applicant_id'], ['users.id'], name='fk_reimburse_applicant'),
        sa.ForeignKeyConstraint(['department_id'], ['departments.id'], name='fk_reimburse_dept'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('form_no', name='uq_reimburse_form_no'),
    )
    op.create_index('ix_reimbursement_forms_status', 'reimbursement_forms', ['status'])
    op.create_index('ix_reimbursement_forms_applicant_id', 'reimbursement_forms', ['applicant_id'])

    op.create_table(
        'reimbursement_details',
        sa.Column('id', sa.BigInteger(), nullable=False),
        sa.Column('form_id', sa.BigInteger(), nullable=False),
        sa.Column('expense_id', sa.BigInteger(), nullable=False),
        sa.Column('expense_code', sa.String(length=32), nullable=True),
        sa.Column('expense_type', sa.String(length=32), nullable=True),
        sa.Column('expense_date', sa.Date(), nullable=True),
        sa.Column('client_name', sa.String(length=128), nullable=True),
        sa.Column('project_name', sa.String(length=128), nullable=True),
        sa.Column('title', sa.String(length=128), nullable=True),
        sa.Column('amount', sa.BigInteger(), nullable=False, server_default='0'),
        sa.Column('reimbursed_amount', sa.BigInteger(), nullable=False, server_default='0'),
        sa.Column('remark', sa.Text(), nullable=True),
        sa.Column('seq', sa.Integer(), nullable=False, server_default='0'),
        sa.ForeignKeyConstraint(['form_id'], ['reimbursement_forms.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['expense_id'], ['expenses.id'], ondelete='RESTRICT'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_reimbursement_details_form_id', 'reimbursement_details', ['form_id'])
    op.create_index('ix_reimbursement_details_expense_id', 'reimbursement_details', ['expense_id'])


def downgrade() -> None:
    op.drop_index('ix_reimbursement_details_expense_id', 'reimbursement_details')
    op.drop_index('ix_reimbursement_details_form_id', 'reimbursement_details')
    op.drop_table('reimbursement_details')
    op.drop_index('ix_reimbursement_forms_applicant_id', 'reimbursement_forms')
    op.drop_index('ix_reimbursement_forms_status', 'reimbursement_forms')
    op.drop_table('reimbursement_forms')
