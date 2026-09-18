from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.enums import TicketPriority, TicketStatus
from app.models.sla import SlaEvent, SlaPolicy
from app.models.ticket import Ticket


DEFAULT_SLA_MINUTES: dict[TicketPriority, tuple[int, int]] = {
    TicketPriority.LOW: (16 * 60, 80 * 60),
    TicketPriority.MEDIUM: (8 * 60, 40 * 60),
    TicketPriority.HIGH: (4 * 60, 16 * 60),
    TicketPriority.CRITICAL: (60, 8 * 60),
}


def _as_utc(dt: datetime | None) -> datetime | None:
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=UTC)
    return dt.astimezone(UTC)


def ensure_default_policies(db: Session) -> None:
    existing = {
        policy.priority
        for policy in db.scalars(select(SlaPolicy).where(SlaPolicy.is_active == True)).all()
    }
    for priority, (first_response, resolution) in DEFAULT_SLA_MINUTES.items():
        if priority in existing:
            continue
        db.add(
            SlaPolicy(
                priority=priority,
                first_response_minutes=first_response,
                resolution_minutes=resolution,
                is_active=True,
            )
        )
    db.commit()


def get_policy_by_priority(db: Session, priority: TicketPriority) -> SlaPolicy:
    policy = db.scalar(
        select(SlaPolicy).where(
            SlaPolicy.priority == priority,
            SlaPolicy.is_active == True,
        )
    )
    if policy:
        return policy
    first_response, resolution = DEFAULT_SLA_MINUTES[priority]
    policy = SlaPolicy(
        priority=priority,
        first_response_minutes=first_response,
        resolution_minutes=resolution,
        is_active=True,
    )
    db.add(policy)
    db.commit()
    db.refresh(policy)
    return policy


def create_ticket_sla_events(db: Session, ticket: Ticket) -> None:
    policy = get_policy_by_priority(db, ticket.priority)
    now = datetime.now(UTC)
    db.add_all(
        [
            SlaEvent(
                ticket_id=ticket.id,
                event_type="FIRST_RESPONSE",
                deadline_at=now + timedelta(minutes=policy.first_response_minutes),
            ),
            SlaEvent(
                ticket_id=ticket.id,
                event_type="RESOLUTION",
                deadline_at=now + timedelta(minutes=policy.resolution_minutes),
            ),
        ]
    )


def is_ticket_overdue(db: Session, ticket: Ticket) -> bool:
    if ticket.status in {TicketStatus.RESOLVED, TicketStatus.CLOSED}:
        return False
    policy = get_policy_by_priority(db, ticket.priority)
    created_at = _as_utc(ticket.created_at)
    if created_at is None:
        return False
    deadline = created_at + timedelta(minutes=policy.resolution_minutes)
    return datetime.now(UTC) > deadline
