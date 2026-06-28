"""UDPE ORM 模型（与 alembic migration 1:1 对齐）。

设计文档：plans/udpe-design/design.md §三
"""
from datetime import datetime
from typing import Optional

from sqlalchemy import (
    BigInteger, Boolean, ForeignKey, Integer, Numeric, String, Text, TIMESTAMP, Index,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class PrintTemplate(Base):
    __tablename__ = "print_templates"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    doc_type: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    paper: Mapped[str] = mapped_column(String(16), nullable=False, server_default="A4")
    width_mm: Mapped[float] = mapped_column(Numeric(8, 2), server_default="210")
    height_mm: Mapped[float] = mapped_column(Numeric(8, 2), server_default="297")
    orientation: Mapped[str] = mapped_column(String(16), nullable=False, server_default="portrait")
    status: Mapped[str] = mapped_column(String(16), nullable=False, server_default="draft", index=True)
    is_default: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    schema_json: Mapped[dict] = mapped_column(JSONB, nullable=False, server_default="{}")
    version: Mapped[int] = mapped_column(Integer, nullable=False, server_default="1")
    created_by: Mapped[Optional[int]] = mapped_column(BigInteger, ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP, nullable=False, server_default="now()")
    updated_at: Mapped[datetime] = mapped_column(TIMESTAMP, nullable=False, server_default="now()")

    # 同 doc_type 只能有一个 is_default=true（DB 层不强约束，应用层保证）
    __table_args__ = (
        Index("ix_print_templates_doc_type_is_default", "doc_type", "is_default"),
    )

    versions: Mapped[list["PrintTemplateVersion"]] = relationship(
        back_populates="template",
        cascade="all, delete-orphan",
        order_by="PrintTemplateVersion.version.desc()",
    )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "code": self.code,
            "name": self.name,
            "docType": self.doc_type,
            "paper": self.paper,
            "widthMm": float(self.width_mm or 210),
            "heightMm": float(self.height_mm or 297),
            "orientation": self.orientation,
            "status": self.status,
            "isDefault": self.is_default,
            "description": self.description,
            "schemaJson": self.schema_json,
            "version": self.version,
            "createdBy": self.created_by,
            "createdAt": self.created_at.isoformat() if self.created_at else None,
            "updatedAt": self.updated_at.isoformat() if self.updated_at else None,
        }


class PrintTemplateVersion(Base):
    __tablename__ = "print_template_versions"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    template_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("print_templates.id", ondelete="CASCADE"), nullable=False, index=True,
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    schema_json: Mapped[dict] = mapped_column(JSONB, nullable=False)
    snapshot_by: Mapped[Optional[int]] = mapped_column(BigInteger, ForeignKey("users.id"), nullable=True)
    snapshot_at: Mapped[datetime] = mapped_column(TIMESTAMP, nullable=False, server_default="now()")
    note: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    template: Mapped["PrintTemplate"] = relationship(back_populates="versions")

    __table_args__ = (
        Index("uq_ptv_template_version", "template_id", "version", unique=True),
    )


class PrintLog(Base):
    __tablename__ = "print_logs"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    template_id: Mapped[Optional[int]] = mapped_column(BigInteger, ForeignKey("print_templates.id"), nullable=True)
    template_code: Mapped[str] = mapped_column(String(64), nullable=False)
    doc_type: Mapped[str] = mapped_column(String(32), nullable=False)
    action: Mapped[str] = mapped_column(String(16), nullable=False)   # preview/pdf/print
    status: Mapped[str] = mapped_column(String(16), nullable=False)   # success/failed
    operator_id: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True, index=True)
    operator_name: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    source_module: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    source_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    elapsed_ms: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    error_msg: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    pdf_size: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    request_data: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    ip: Mapped[Optional[str]] = mapped_column(String(45), nullable=True)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP, nullable=False, server_default="now()", index=True)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "templateId": self.template_id,
            "templateCode": self.template_code,
            "docType": self.doc_type,
            "action": self.action,
            "status": self.status,
            "operatorId": self.operator_id,
            "operatorName": self.operator_name,
            "sourceModule": self.source_module,
            "sourceId": self.source_id,
            "elapsedMs": self.elapsed_ms,
            "errorMsg": self.error_msg,
            "pdfSize": self.pdf_size,
            "createdAt": self.created_at.isoformat() if self.created_at else None,
        }
