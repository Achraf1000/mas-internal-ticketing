from sqlalchemy import Boolean, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


class Department(Base, TimestampMixin):
    __tablename__ = "departments"

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(255), unique=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    users = relationship("User", back_populates="department")
    emitted_tickets = relationship(
        "Ticket",
        back_populates="emitter_department",
        foreign_keys="Ticket.emitter_department_id",
    )
    received_tickets = relationship(
        "Ticket",
        back_populates="target_department",
        foreign_keys="Ticket.target_department_id",
    )

