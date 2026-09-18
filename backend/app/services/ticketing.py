from datetime import UTC, datetime
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import and_, func, or_, select
from sqlalchemy.orm import Session

from app.models.enums import Role, TicketStatus
from app.models.ticket import Ticket, TicketStatusHistory
from app.models.user import User

ALLOWED_TRANSITIONS: dict[TicketStatus, set[TicketStatus]] = {
    TicketStatus.NEW: {TicketStatus.IN_PROGRESS},
    TicketStatus.IN_PROGRESS: {TicketStatus.ON_HOLD, TicketStatus.RESOLVED},
    TicketStatus.ON_HOLD: {TicketStatus.IN_PROGRESS},
    TicketStatus.RESOLVED: {TicketStatus.CLOSED, TicketStatus.IN_PROGRESS},
    TicketStatus.CLOSED: set(),
}


def generate_ticket_code(db: Session) -> str:
    today = datetime.now(UTC).strftime("%Y%m%d")
    prefix = f"TCK-{today}"
    count = db.scalar(
        select(func.count()).select_from(Ticket).where(Ticket.ticket_code.like(f"{prefix}%"))
    )
    sequence = (count or 0) + 1
    return f"{prefix}-{sequence:04d}"


def ensure_ticket_visibility(user: User, ticket: Ticket) -> None:
    if user.role == Role.ADMIN:
        return
    if ticket.creator_id == user.id or ticket.assignee_id == user.id:
        return

    if not user.department_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    is_target_department = ticket.target_department_id == user.department_id
    if not is_target_department:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    if user.is_department_head:
        return

    if ticket.is_department_broadcast:
        return

    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")


def build_ticket_visibility_filter(user: User):
    if user.role == Role.ADMIN:
        return True
    clauses = [Ticket.creator_id == user.id, Ticket.assignee_id == user.id]
    if user.department_id:
        if user.is_department_head:
            clauses.append(Ticket.target_department_id == user.department_id)
        else:
            clauses.append(
                and_(
                    Ticket.target_department_id == user.department_id,
                    Ticket.is_department_broadcast == True,
                )
            )
    return or_(*clauses)


def transition_ticket_status(
    db: Session,
    *,
    ticket: Ticket,
    to_status: TicketStatus,
    actor: User,
    reason: str | None = None,
) -> Ticket:
    if to_status not in ALLOWED_TRANSITIONS[ticket.status]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Transition {ticket.status} -> {to_status} is not allowed",
        )

    from_status = ticket.status
    ticket.status = to_status
    if to_status == TicketStatus.RESOLVED:
        ticket.resolved_at = datetime.now(UTC)
    if to_status == TicketStatus.CLOSED:
        ticket.closed_at = datetime.now(UTC)
    if to_status == TicketStatus.IN_PROGRESS and from_status == TicketStatus.RESOLVED:
        ticket.resolved_at = None
        ticket.closed_at = None

    history = TicketStatusHistory(
        ticket_id=ticket.id,
        from_status=from_status,
        to_status=to_status,
        changed_by=actor.id,
        reason=reason,
    )
    db.add(history)
    db.flush()
    return ticket


def get_ticket_or_404(db: Session, ticket_id: UUID) -> Ticket:
    ticket = db.get(Ticket, ticket_id)
    if not ticket:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ticket not found")
    return ticket
