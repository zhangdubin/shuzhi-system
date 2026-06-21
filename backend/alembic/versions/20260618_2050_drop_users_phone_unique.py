"""drop unique constraint on users.phone

Revision ID: drop_users_phone_unique
Revises: add_dict_types_table
Create Date: 2026-06-18
"""
from alembic import op
import sqlalchemy as sa

revision = "drop_users_phone_unique"
down_revision = "add_dict_types_table"
branch_labels = None
depends_on = None


def upgrade():
    op.drop_constraint("users_phone_key", "users", type_="unique")


def downgrade():
    op.create_unique_constraint("users_phone_key", "users", ["phone"])
