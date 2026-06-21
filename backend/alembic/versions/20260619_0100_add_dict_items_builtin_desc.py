"""add is_builtin + description to dictionaries
Revision ID: 20260619_0100
Revises: 20260618_2050
Create Date: 2026-06-19 01:00:00
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers
revision = '20260619_0100'
down_revision = 'drop_users_phone_unique'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('dictionaries', sa.Column('is_builtin', sa.Boolean(), nullable=False, server_default='false'))
    op.add_column('dictionaries', sa.Column('description', sa.String(length=256), nullable=True))
    # 内置分类下的所有项标记为 builtin
    op.execute("""
        UPDATE dictionaries d
        SET is_builtin = true
        FROM dict_types t
        WHERE d.dict_type = t.code AND t.is_builtin = true
    """)


def downgrade():
    op.drop_column('dictionaries', 'description')
    op.drop_column('dictionaries', 'is_builtin')
