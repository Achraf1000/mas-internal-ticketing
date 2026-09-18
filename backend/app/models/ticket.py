from datetime import UTC, datetime
import uuid

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Index, Integer, LargeBinary, String, UnicodeText
from sqlalchemy.dialects.mssql import UNIQUEIDENTIFIER
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin
from app.models.enums import TicketCategory, TicketPriority, TicketStatus


class Ticket(Base, TimestampMixin):
    __tablename__ = "tickets"
    __table_args__ = (
        Index(
            "ix_tickets_filter_core",
            "status",
            "priority",
            "target_department_id",
            "assignee_id",
            "created_at",
        ),
        Index(
            "ix_tickets_target_broadcast_status_assignee_created",
            "target_department_id",
            "is_department_broadcast",
            "status",
            "assignee_id",
            "created_at",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UNIQUEIDENTIFIER,
        primary_key=True,
        default=uuid.uuid4,
    )
    ticket_code: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    title: Mapped[str] = mapped_column(String(255))
    description: Mapped[str] = mapped_column(UnicodeText)
    category: Mapped[TicketCategory] = mapped_column(Enum(TicketCategory), index=True)
    priority: Mapped[TicketPriority] = mapped_column(Enum(TicketPriority), index=True)
    status: Mapped[TicketStatus] = mapped_column(Enum(TicketStatus), default=TicketStatus.NEW, index=True)
    emitter_department_id: Mapped[int] = mapped_column(ForeignKey("departments.id"), index=True)
    target_department_id: Mapped[int] = mapped_column(ForeignKey("departments.id"), index=True)
    creator_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), index=True)
    assignee_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"), nullable=True, index=True)
    is_department_broadcast: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    creator = relationship("User", back_populates="created_tickets", foreign_keys=[creator_id])
    assignee = relationship("User", back_populates="assigned_tickets", foreign_keys=[assignee_id])
    emitter_department = relationship("Department", foreign_keys=[emitter_department_id], back_populates="emitted_tickets")
    target_department = relationship("Department", foreign_keys=[target_department_id], back_populates="received_tickets")
    comments = relationship("TicketComment", back_populates="ticket", cascade="all, delete-orphan")
    attachments = relationship("TicketAttachment", back_populates="ticket", cascade="all, delete-orphan")
    status_history = relationship("TicketStatusHistory", back_populates="ticket", cascade="all, delete-orphan")
    sla_events = relationship("SlaEvent", back_populates="ticket", cascade="all, delete-orphan")


class TicketComment(Base):
    __tablename__ = "ticket_comments"

    id: Mapped[int] = mapped_column(primary_key=True)
    ticket_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tickets.id"), index=True)
    author_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), index=True)
    body: Mapped[str] = mapped_column(UnicodeText)
    is_internal: Mapped[bool] = mapped_column(default=False)
    created_at: Mapped[datetime] = mapped_column(default=lambda: datetime.now(UTC), index=True)

    ticket = relationship("Ticket", back_populates="comments")
    author = relationship("User", back_populates="comments")


class TicketAttachment(Base):
    __tablename__ = "ticket_attachments"

    id: Mapped[int] = mapped_column(primary_key=True)
    ticket_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tickets.id"), index=True)
    filename: Mapped[str] = mapped_column(String(255))
    mime_type: Mapped[str] = mapped_column(String(150))
    size_bytes: Mapped[int] = mapped_column(Integer)
    content: Mapped[bytes] = mapped_column(LargeBinary)
    uploaded_by: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    uploaded_at: Mapped[datetime] = mapped_column(default=lambda: datetime.now(UTC), index=True)

    ticket = relationship("Ticket", back_populates="attachments")


class TicketStatusHistory(Base):
    __tablename__ = "ticket_status_history"

    id: Mapped[int] = mapped_column(primary_key=True)
    ticket_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tickets.id"), index=True)
    from_status: Mapped[TicketStatus | None] = mapped_column(Enum(TicketStatus), nullable=True)
    to_status: Mapped[TicketStatus] = mapped_column(Enum(TicketStatus), index=True)
    changed_by: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    reason: Mapped[str | None] = mapped_column(UnicodeText, nullable=True)
    changed_at: Mapped[datetime] = mapped_column(default=lambda: datetime.now(UTC), index=True)

    ticket = relationship("Ticket", back_populates="status_history")
