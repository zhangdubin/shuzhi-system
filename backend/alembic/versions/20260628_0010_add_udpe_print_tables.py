"""
UDPE: 统一单据打印引擎 — 三张新表
- print_templates          模板主表
- print_template_versions  模板历史版本
- print_logs               渲染/导出日志

设计文档：plans/udpe-design/design.md §三
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB


revision = "20260628_0010"
down_revision = "20260623_1730"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1) 模板主表
    op.create_table(
        "print_templates",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("code", sa.String(64), nullable=False),
        sa.Column("name", sa.String(128), nullable=False),
        sa.Column("doc_type", sa.String(32), nullable=False),
        sa.Column("paper", sa.String(16), nullable=False, server_default="A4"),
        sa.Column("width_mm", sa.Numeric(8, 2), server_default="210"),
        sa.Column("height_mm", sa.Numeric(8, 2), server_default="297"),
        sa.Column("orientation", sa.String(16), nullable=False, server_default="portrait"),
        sa.Column("status", sa.String(16), nullable=False, server_default="draft"),
        sa.Column("is_default", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("schema_json", JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("created_by", sa.BigInteger(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.TIMESTAMP(), nullable=False, server_default=sa.text("now()")),
        sa.UniqueConstraint("code", name="uq_print_templates_code"),
    )
    op.create_index("ix_print_templates_doc_type", "print_templates", ["doc_type"])
    op.create_index("ix_print_templates_status", "print_templates", ["status"])
    op.create_index(
        "ix_print_templates_doc_type_is_default",
        "print_templates",
        ["doc_type", "is_default"],
    )

    # 2) 模板历史版本
    op.create_table(
        "print_template_versions",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("template_id", sa.BigInteger(), sa.ForeignKey("print_templates.id", ondelete="CASCADE"), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("schema_json", JSONB, nullable=False),
        sa.Column("snapshot_by", sa.BigInteger(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("snapshot_at", sa.TIMESTAMP(), nullable=False, server_default=sa.text("now()")),
        sa.Column("note", sa.Text(), nullable=True),
        sa.UniqueConstraint("template_id", "version", name="uq_ptv_template_version"),
    )
    op.create_index("ix_ptv_template_id", "print_template_versions", ["template_id"])

    # 3) 渲染/导出日志
    op.create_table(
        "print_logs",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("template_id", sa.BigInteger(), sa.ForeignKey("print_templates.id"), nullable=True),
        sa.Column("template_code", sa.String(64), nullable=False),
        sa.Column("doc_type", sa.String(32), nullable=False),
        sa.Column("action", sa.String(16), nullable=False),  # preview/pdf/print
        sa.Column("status", sa.String(16), nullable=False),  # success/failed
        sa.Column("operator_id", sa.BigInteger(), nullable=True),
        sa.Column("operator_name", sa.String(64), nullable=True),
        sa.Column("source_module", sa.String(32), nullable=True),
        sa.Column("source_id", sa.String(64), nullable=True),
        sa.Column("elapsed_ms", sa.Integer(), nullable=True),
        sa.Column("error_msg", sa.Text(), nullable=True),
        sa.Column("pdf_size", sa.Integer(), nullable=True),
        sa.Column("request_data", JSONB, nullable=True),
        sa.Column("ip", sa.String(45), nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(), nullable=False, server_default=sa.text("now()"), index=True),
    )
    op.create_index("ix_print_logs_template_code", "print_logs", ["template_code"])
    op.create_index("ix_print_logs_operator_id", "print_logs", ["operator_id"])


def downgrade() -> None:
    op.drop_index("ix_print_logs_operator_id", table_name="print_logs")
    op.drop_index("ix_print_logs_template_code", table_name="print_logs")
    op.drop_table("print_logs")

    op.drop_index("ix_ptv_template_id", table_name="print_template_versions")
    op.drop_table("print_template_versions")

    op.drop_index("ix_print_templates_doc_type_is_default", table_name="print_templates")
    op.drop_index("ix_print_templates_status", table_name="print_templates")
    op.drop_index("ix_print_templates_doc_type", table_name="print_templates")
    op.drop_table("print_templates")
