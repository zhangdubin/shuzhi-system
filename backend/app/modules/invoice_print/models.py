"""
发票打印工作台模块
Invoice Print Studio — 独立于发票识别模块，复用 Invoice 数据和文件
"""
from datetime import datetime
from sqlalchemy import String, Text, Integer, BigInteger, ForeignKey, Boolean
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from app.core.database import Base


class InvoicePrintTemplate(Base):
    """打印模板"""
    __tablename__ = "invoice_print_templates"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    name: Mapped[str] = mapped_column(String(64), nullable=False)
    paper: Mapped[str] = mapped_column(String(16), default="A4")  # A4/A3/A5/Letter
    orientation: Mapped[str] = mapped_column(String(16), default="portrait")  # portrait/landscape
    margin_top: Mapped[int] = mapped_column(Integer, default=10)  # mm
    margin_right: Mapped[int] = mapped_column(Integer, default=10)
    margin_bottom: Mapped[int] = mapped_column(Integer, default=10)
    margin_left: Mapped[int] = mapped_column(Integer, default=10)
    layout_cols: Mapped[int] = mapped_column(Integer, default=1)
    layout_rows: Mapped[int] = mapped_column(Integer, default=1)
    scale_mode: Mapped[str] = mapped_column(String(16), default="fit")  # fit/fitWidth/fitHeight/original
    auto_rotate: Mapped[bool] = mapped_column(Boolean, default=True)
    auto_center: Mapped[bool] = mapped_column(Boolean, default=True)
    header_text: Mapped[str] = mapped_column(String(256), nullable=True)
    footer_text: Mapped[str] = mapped_column(String(256), nullable=True)
    show_qrcode_margin: Mapped[bool] = mapped_column(Boolean, default=True)
    is_system: Mapped[bool] = mapped_column(Boolean, default=False)
    is_favorite: Mapped[bool] = mapped_column(Boolean, default=False)
    config_json: Mapped[dict] = mapped_column(JSONB, nullable=True)
    creator_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id, "name": self.name, "paper": self.paper,
            "orientation": self.orientation,
            "marginTop": self.margin_top, "marginRight": self.margin_right,
            "marginBottom": self.margin_bottom, "marginLeft": self.margin_left,
            "layoutCols": self.layout_cols, "layoutRows": self.layout_rows,
            "scaleMode": self.scale_mode, "autoRotate": self.auto_rotate,
            "autoCenter": self.auto_center, "headerText": self.header_text,
            "footerText": self.footer_text,
            "showQrcodeMargin": self.show_qrcode_margin,
            "isSystem": self.is_system, "isFavorite": self.is_favorite,
            "configJson": self.config_json,
            "createdAt": self.created_at.isoformat() if self.created_at else None,
            "updatedAt": self.updated_at.isoformat() if self.updated_at else None,
        }


class InvoicePrintHistory(Base):
    """打印历史"""
    __tablename__ = "invoice_print_history"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    invoice_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("invoices.id"), nullable=True, index=True)
    invoice_no: Mapped[str] = mapped_column(String(32), nullable=True)
    template_id: Mapped[int] = mapped_column(BigInteger, nullable=True)
    template_name: Mapped[str] = mapped_column(String(64), nullable=True)
    mode: Mapped[str] = mapped_column(String(16), default="single")  # single/layout/pdf
    layout_desc: Mapped[str] = mapped_column(String(32), nullable=True)  # e.g. "2x2"
    copies: Mapped[int] = mapped_column(Integer, default=1)
    status: Mapped[str] = mapped_column(String(16), default="success")  # success/failed/pending
    error_msg: Mapped[str] = mapped_column(Text, nullable=True)
    operator_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id"), nullable=True)
    operator_name: Mapped[str] = mapped_column(String(32), nullable=True)
    printed_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id, "invoiceId": self.invoice_id,
            "invoiceNo": self.invoice_no,
            "templateId": self.template_id, "templateName": self.template_name,
            "mode": self.mode, "layoutDesc": self.layout_desc,
            "copies": self.copies, "status": self.status,
            "errorMsg": self.error_msg,
            "operatorName": self.operator_name,
            "printedAt": self.printed_at.isoformat() if self.printed_at else None,
        }
