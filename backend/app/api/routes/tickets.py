from datetime import UTC, datetime
from zoneinfo import ZoneInfo
from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, Query, Response, UploadFile, status
from sqlalchemy import and_, or_, select
from sqlalchemy.orm import Session, joinedload

from app.api.deps import CurrentUser
from app.core.database import get_db
from app.models.department import Department
from app.models.enums import Role, TicketCategory, TicketPriority, TicketStatus
from app.models.ticket import Ticket, TicketAttachment, TicketComment, TicketStatusHistory
from app.models.user import User
from app.schemas.common import DepartmentOut, UserSummary
from app.schemas.ticket import (
    TicketAttachmentOut,
    TicketCommentCreate,
    TicketCommentOut,
    TicketCreate,
    TicketDetailOut,
    TicketOut,
    TicketPatch,
    TicketStatusHistoryOut,
    TicketStatusTransitionRequest,
)
from app.services.audit import log_audit
from app.services.notification import queue_notification
from app.services.sla import create_ticket_sla_events, is_ticket_overdue
from app.services.ticketing import (
    build_ticket_visibility_filter,
    ensure_ticket_visibility,
    generate_ticket_code,
    get_ticket_or_404,
    transition_ticket_status,
)

router = APIRouter(prefix="/tickets", tags=["tickets"])
try:
    PARIS_TZ = ZoneInfo("Europe/Paris")
except Exception:  # noqa: BLE001
    PARIS_TZ = datetime.now().astimezone().tzinfo or UTC

ALLOWED_ATTACHMENT_MIME = {
    "application/pdf",
    "image/png",
    "image/jpeg",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "text/plain",
}
MAX_ATTACHMENT_BYTES = 10 * 1024 * 1024


def _department_or_404(db: Session, department_id: int) -> Department:
    department = db.get(Department, department_id)
    if not department or not department.is_active:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Department not found")
    return department


def _user_or_404(db: Session, user_id: UUID) -> User:
    user = db.get(User, user_id)
    if not user or not user.is_active:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return user


def _serialize_ticket(ticket: Ticket) -> TicketOut:
    return TicketOut(
        id=ticket.id,
        ticket_code=ticket.ticket_code,
        title=ticket.title,
        description=ticket.description,
        category=ticket.category,
        priority=ticket.priority,
        status=ticket.status,
        is_department_broadcast=ticket.is_department_broadcast,
        emitter_department=DepartmentOut.model_validate(ticket.emitter_department, from_attributes=True),
        target_department=DepartmentOut.model_validate(ticket.target_department, from_attributes=True),
        creator=UserSummary.model_validate(ticket.creator, from_attributes=True),
        assignee=UserSummary.model_validate(ticket.assignee, from_attributes=True) if ticket.assignee else None,
        created_at=ticket.created_at,
        updated_at=ticket.updated_at,
        resolved_at=ticket.resolved_at,
        closed_at=ticket.closed_at,
    )


def _serialize_ticket_detail(ticket: Ticket) -> TicketDetailOut:
    return TicketDetailOut(
        **_serialize_ticket(ticket).model_dump(),
        comments=[
            TicketCommentOut(
                id=item.id,
                ticket_id=item.ticket_id,
                author=UserSummary.model_validate(item.author, from_attributes=True),
                body=item.body,
                is_internal=item.is_internal,
                created_at=item.created_at,
            )
            for item in sorted(ticket.comments, key=lambda c: c.created_at)
        ],
        attachments=[
            TicketAttachmentOut(
                id=item.id,
                filename=item.filename,
                mime_type=item.mime_type,
                size_bytes=item.size_bytes,
                uploaded_by=item.uploaded_by,
                uploaded_at=item.uploaded_at,
            )
            for item in sorted(ticket.attachments, key=lambda a: a.uploaded_at)
        ],
        status_history=[
            TicketStatusHistoryOut(
                id=item.id,
                from_status=item.from_status,
                to_status=item.to_status,
                changed_by=item.changed_by,
                reason=item.reason,
                changed_at=item.changed_at,
            )
            for item in sorted(ticket.status_history, key=lambda h: h.changed_at)
        ],
    )


def _base_ticket_query():
    return (
        select(Ticket)
        .options(
            joinedload(Ticket.emitter_department),
            joinedload(Ticket.target_department),
            joinedload(Ticket.creator),
            joinedload(Ticket.assignee),
        )
        .order_by(Ticket.created_at.desc())
    )


def _apply_ticket_filters(
    query,
    *,
    status_filter: TicketStatus | None,
    priority: TicketPriority | None,
    category: TicketCategory | None,
    emitter_department_id: int | None,
    target_department_id: int | None,
    assignee_id: UUID | None,
    date_from: datetime | None,
    date_to: datetime | None,
):
    filters = []
    if status_filter:
        filters.append(Ticket.status == status_filter)
    if priority:
        filters.append(Ticket.priority == priority)
    if category:
        filters.append(Ticket.category == category)
    if emitter_department_id:
        filters.append(Ticket.emitter_department_id == emitter_department_id)
    if target_department_id:
        filters.append(Ticket.target_department_id == target_department_id)
    if assignee_id:
        filters.append(Ticket.assignee_id == assignee_id)
    if date_from:
        filters.append(Ticket.created_at >= date_from)
    if date_to:
        filters.append(Ticket.created_at <= date_to)
    if filters:
        query = query.where(and_(*filters))
    return query


def _month_window_utc(*, year: int | None = None, month: int | None = None) -> tuple[int, int, datetime, datetime]:
    now_local = datetime.now(PARIS_TZ)
    resolved_year = year or now_local.year
    resolved_month = month or now_local.month
    if resolved_month < 1 or resolved_month > 12:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="month must be between 1 and 12")
    if resolved_year < 2000 or resolved_year > 2100:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="year is out of range")

    start_local = datetime(resolved_year, resolved_month, 1, 0, 0, 0, tzinfo=PARIS_TZ)
    if resolved_month == 12:
        end_local = datetime(resolved_year + 1, 1, 1, 0, 0, 0, tzinfo=PARIS_TZ)
    else:
        end_local = datetime(resolved_year, resolved_month + 1, 1, 0, 0, 0, tzinfo=PARIS_TZ)

    start_utc = start_local.astimezone(UTC).replace(tzinfo=None)
    end_utc = end_local.astimezone(UTC).replace(tzinfo=None)
    return resolved_year, resolved_month, start_utc, end_utc


def _can_process_ticket(user: User, ticket: Ticket) -> bool:
    if user.role in {Role.ADMIN, Role.IT_AGENT}:
        return True
    if user.is_department_head and user.department_id and ticket.target_department_id == user.department_id:
        return True
    if ticket.assignee_id == user.id:
        return True
    return False


@router.post("", response_model=TicketOut, status_code=status.HTTP_201_CREATED)
def create_ticket(
    payload: TicketCreate,
    current_user: CurrentUser,
    db: Session = Depends(get_db),
) -> TicketOut:
    emitter_department_id = payload.emitter_department_id or current_user.department_id or payload.target_department_id
    if emitter_department_id is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Emitter department is required")
    if payload.is_department_broadcast and payload.assignee_id is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Broadcast ticket must be created without assignee",
        )

    _department_or_404(db, emitter_department_id)
    _department_or_404(db, payload.target_department_id)
    assignee = _user_or_404(db, payload.assignee_id) if payload.assignee_id else None

    ticket = Ticket(
        ticket_code=generate_ticket_code(db),
        title=payload.title,
        description=payload.description,
        category=payload.category,
        priority=payload.priority,
        status=TicketStatus.NEW,
        emitter_department_id=emitter_department_id,
        target_department_id=payload.target_department_id,
        creator_id=current_user.id,
        assignee_id=assignee.id if assignee else None,
        is_department_broadcast=payload.is_department_broadcast,
    )
    db.add(ticket)
    db.flush()
    db.add(
        TicketStatusHistory(
            ticket_id=ticket.id,
            from_status=None,
            to_status=TicketStatus.NEW,
            changed_by=current_user.id,
            reason="Ticket created",
        )
    )
    create_ticket_sla_events(db, ticket)

    if assignee:
        queue_notification(
            db,
            event_type="TICKET_ASSIGNED",
            recipient_email=assignee.email,
            subject=f"[{ticket.ticket_code}] Nouveau ticket assigne",
            payload={"ticket_id": str(ticket.id), "title": ticket.title},
        )

    log_audit(
        db,
        actor=current_user,
        action="TICKET_CREATED",
        entity_type="ticket",
        entity_id=str(ticket.id),
        after={
            "ticket_code": ticket.ticket_code,
            "status": ticket.status.value,
            "priority": ticket.priority.value,
            "is_department_broadcast": ticket.is_department_broadcast,
        },
    )
    db.commit()
    db.refresh(ticket)
    ticket = db.scalar(
        select(Ticket)
        .options(
            joinedload(Ticket.emitter_department),
            joinedload(Ticket.target_department),
            joinedload(Ticket.creator),
            joinedload(Ticket.assignee),
        )
        .where(Ticket.id == ticket.id)
    )
    if not ticket:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ticket not found after creation")
    return _serialize_ticket(ticket)


@router.get("", response_model=list[TicketOut])
def list_tickets(
    current_user: CurrentUser,
    db: Session = Depends(get_db),
    status_filter: TicketStatus | None = Query(default=None, alias="status"),
    priority: TicketPriority | None = None,
    category: TicketCategory | None = None,
    emitter_department_id: int | None = None,
    target_department_id: int | None = None,
    assignee_id: UUID | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    sla_overdue: bool | None = None,
    offset: int = 0,
    limit: int = Query(default=50, le=200),
) -> list[TicketOut]:
    query = _base_ticket_query()

    visibility_filter = build_ticket_visibility_filter(current_user)
    if visibility_filter is not True:
        query = query.where(visibility_filter)

    query = _apply_ticket_filters(
        query,
        status_filter=status_filter,
        priority=priority,
        category=category,
        emitter_department_id=emitter_department_id,
        target_department_id=target_department_id,
        assignee_id=assignee_id,
        date_from=date_from,
        date_to=date_to,
    )
    query = query.offset(offset).limit(limit)

    rows = db.scalars(query).all()
    if sla_overdue is not None:
        rows = [row for row in rows if is_ticket_overdue(db, row) == sla_overdue]
    return [_serialize_ticket(row) for row in rows]


@router.get("/received", response_model=list[TicketOut])
def list_received_tickets(
    current_user: CurrentUser,
    db: Session = Depends(get_db),
    status_filter: TicketStatus | None = Query(default=None, alias="status"),
    priority: TicketPriority | None = None,
    category: TicketCategory | None = None,
    emitter_department_id: int | None = None,
    target_department_id: int | None = None,
    assignee_id: UUID | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    sla_overdue: bool | None = None,
    include_closed: bool = False,
    offset: int = 0,
    limit: int = Query(default=50, le=200),
) -> list[TicketOut]:
    query = _base_ticket_query()

    if current_user.role != Role.ADMIN:
        scopes = [Ticket.assignee_id == current_user.id]
        if current_user.department_id and not current_user.is_department_head:
            scopes.append(
                and_(
                    Ticket.target_department_id == current_user.department_id,
                    Ticket.is_department_broadcast == True,
                )
            )
        query = query.where(or_(*scopes))

    if not include_closed:
        query = query.where(Ticket.status != TicketStatus.CLOSED)

    query = _apply_ticket_filters(
        query,
        status_filter=status_filter,
        priority=priority,
        category=category,
        emitter_department_id=emitter_department_id,
        target_department_id=target_department_id,
        assignee_id=assignee_id,
        date_from=date_from,
        date_to=date_to,
    )
    query = query.offset(offset).limit(limit)

    rows = db.scalars(query).all()
    if sla_overdue is not None:
        rows = [row for row in rows if is_ticket_overdue(db, row) == sla_overdue]
    return [_serialize_ticket(row) for row in rows]


@router.get("/to-assign", response_model=list[TicketOut])
def list_tickets_to_assign(
    current_user: CurrentUser,
    db: Session = Depends(get_db),
    status_filter: TicketStatus | None = Query(default=None, alias="status"),
    priority: TicketPriority | None = None,
    category: TicketCategory | None = None,
    target_department_id: int | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    offset: int = 0,
    limit: int = Query(default=50, le=200),
) -> list[TicketOut]:
    query = _base_ticket_query().where(Ticket.assignee_id.is_(None), Ticket.status != TicketStatus.CLOSED)

    if current_user.role in {Role.ADMIN, Role.IT_AGENT}:
        if target_department_id is not None:
            query = query.where(Ticket.target_department_id == target_department_id)
    else:
        if not (current_user.is_department_head and current_user.department_id is not None):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only department heads can access this view")
        query = query.where(Ticket.target_department_id == current_user.department_id)

    query = _apply_ticket_filters(
        query,
        status_filter=status_filter,
        priority=priority,
        category=category,
        emitter_department_id=None,
        target_department_id=None,
        assignee_id=None,
        date_from=date_from,
        date_to=date_to,
    )
    query = query.offset(offset).limit(limit)

    rows = db.scalars(query).all()
    return [_serialize_ticket(row) for row in rows]


@router.get("/sent", response_model=list[TicketOut])
def list_sent_tickets(
    current_user: CurrentUser,
    db: Session = Depends(get_db),
    status_filter: TicketStatus | None = Query(default=None, alias="status"),
    priority: TicketPriority | None = None,
    category: TicketCategory | None = None,
    target_department_id: int | None = None,
    assignee_id: UUID | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    include_closed: bool = False,
    offset: int = 0,
    limit: int = Query(default=50, le=200),
) -> list[TicketOut]:
    query = _base_ticket_query().where(Ticket.creator_id == current_user.id)
    if not include_closed:
        query = query.where(Ticket.status != TicketStatus.CLOSED)
    query = _apply_ticket_filters(
        query,
        status_filter=status_filter,
        priority=priority,
        category=category,
        emitter_department_id=None,
        target_department_id=target_department_id,
        assignee_id=assignee_id,
        date_from=date_from,
        date_to=date_to,
    )
    query = query.offset(offset).limit(limit)
    rows = db.scalars(query).all()
    return [_serialize_ticket(row) for row in rows]


@router.get("/archive", response_model=list[TicketOut])
def list_ticket_archive(
    current_user: CurrentUser,
    db: Session = Depends(get_db),
    year: int | None = None,
    month: int | None = Query(default=None, ge=1, le=12),
    offset: int = 0,
    limit: int = Query(default=50, le=200),
) -> list[TicketOut]:
    _, _, start_utc, end_utc = _month_window_utc(year=year, month=month)

    query = _base_ticket_query().where(
        Ticket.status == TicketStatus.CLOSED,
        Ticket.closed_at.is_not(None),
        Ticket.closed_at >= start_utc,
        Ticket.closed_at < end_utc,
    )
    if current_user.role not in {Role.ADMIN, Role.IT_AGENT}:
        query = query.where(Ticket.creator_id == current_user.id)

    rows = db.scalars(query.offset(offset).limit(limit)).all()
    return [_serialize_ticket(row) for row in rows]


@router.get("/{ticket_id}", response_model=TicketDetailOut)
def get_ticket(
    ticket_id: UUID,
    current_user: CurrentUser,
    db: Session = Depends(get_db),
) -> TicketDetailOut:
    ticket = db.scalar(
        select(Ticket)
        .options(
            joinedload(Ticket.emitter_department),
            joinedload(Ticket.target_department),
            joinedload(Ticket.creator),
            joinedload(Ticket.assignee),
            joinedload(Ticket.comments).joinedload(TicketComment.author),
            joinedload(Ticket.attachments),
            joinedload(Ticket.status_history),
        )
        .where(Ticket.id == ticket_id)
    )
    if not ticket:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ticket not found")
    ensure_ticket_visibility(current_user, ticket)
    return _serialize_ticket_detail(ticket)


@router.patch("/{ticket_id}", response_model=TicketOut)
def patch_ticket(
    ticket_id: UUID,
    payload: TicketPatch,
    current_user: CurrentUser,
    db: Session = Depends(get_db),
) -> TicketOut:
    ticket = get_ticket_or_404(db, ticket_id)
    ensure_ticket_visibility(current_user, ticket)

    before = {
        "title": ticket.title,
        "description": ticket.description,
        "category": ticket.category.value,
        "priority": ticket.priority.value,
        "assignee_id": str(ticket.assignee_id) if ticket.assignee_id else None,
    }

    if payload.title is not None:
        ticket.title = payload.title
    if payload.description is not None:
        ticket.description = payload.description
    if payload.category is not None:
        ticket.category = payload.category
    if payload.priority is not None:
        ticket.priority = payload.priority
    if payload.assignee_id is not None:
        can_assign = current_user.role in {Role.ADMIN, Role.IT_AGENT} or (
            current_user.is_department_head
            and current_user.department_id is not None
            and ticket.target_department_id == current_user.department_id
        )
        if not can_assign:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only department head or management can assign this ticket",
            )
        assignee = _user_or_404(db, payload.assignee_id)
        ticket.assignee_id = assignee.id
        queue_notification(
            db,
            event_type="TICKET_ASSIGNED",
            recipient_email=assignee.email,
            subject=f"[{ticket.ticket_code}] Ticket assigne",
            payload={"ticket_id": str(ticket.id), "title": ticket.title},
        )

    log_audit(
        db,
        actor=current_user,
        action="TICKET_UPDATED",
        entity_type="ticket",
        entity_id=str(ticket.id),
        before=before,
        after={
            "title": ticket.title,
            "description": ticket.description,
            "category": ticket.category.value,
            "priority": ticket.priority.value,
            "assignee_id": str(ticket.assignee_id) if ticket.assignee_id else None,
        },
    )
    db.commit()
    db.refresh(ticket)
    ticket = db.scalar(
        select(Ticket)
        .options(
            joinedload(Ticket.emitter_department),
            joinedload(Ticket.target_department),
            joinedload(Ticket.creator),
            joinedload(Ticket.assignee),
        )
        .where(Ticket.id == ticket.id)
    )
    if not ticket:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ticket not found")
    return _serialize_ticket(ticket)


@router.post("/{ticket_id}/status-transitions", response_model=TicketOut)
def create_status_transition(
    ticket_id: UUID,
    payload: TicketStatusTransitionRequest,
    current_user: CurrentUser,
    db: Session = Depends(get_db),
) -> TicketOut:
    ticket = get_ticket_or_404(db, ticket_id)
    ensure_ticket_visibility(current_user, ticket)

    if ticket.is_department_broadcast and ticket.assignee_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Broadcast ticket must be assigned by department head before status transition",
        )

    if payload.to_status == TicketStatus.CLOSED:
        if ticket.creator_id != current_user.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only creator can close this ticket")
    elif not _can_process_ticket(current_user, ticket):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only processing team can change this status",
        )

    transition_ticket_status(
        db,
        ticket=ticket,
        to_status=payload.to_status,
        actor=current_user,
        reason=payload.reason,
    )

    if ticket.assignee:
        queue_notification(
            db,
            event_type="TICKET_STATUS_CHANGED",
            recipient_email=ticket.assignee.email,
            subject=f"[{ticket.ticket_code}] Statut -> {ticket.status.value}",
            payload={"ticket_id": str(ticket.id), "status": ticket.status.value},
        )
    if ticket.creator:
        queue_notification(
            db,
            event_type="TICKET_STATUS_CHANGED",
            recipient_email=ticket.creator.email,
            subject=f"[{ticket.ticket_code}] Statut -> {ticket.status.value}",
            payload={"ticket_id": str(ticket.id), "status": ticket.status.value},
        )

    log_audit(
        db,
        actor=current_user,
        action="TICKET_STATUS_CHANGED",
        entity_type="ticket",
        entity_id=str(ticket.id),
        after={"status": ticket.status.value, "reason": payload.reason},
    )

    db.commit()
    db.refresh(ticket)
    ticket = db.scalar(
        select(Ticket)
        .options(
            joinedload(Ticket.emitter_department),
            joinedload(Ticket.target_department),
            joinedload(Ticket.creator),
            joinedload(Ticket.assignee),
        )
        .where(Ticket.id == ticket.id)
    )
    if not ticket:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ticket not found")
    return _serialize_ticket(ticket)


@router.post("/{ticket_id}/comments", response_model=TicketCommentOut, status_code=status.HTTP_201_CREATED)
def add_comment(
    ticket_id: UUID,
    payload: TicketCommentCreate,
    current_user: CurrentUser,
    db: Session = Depends(get_db),
) -> TicketCommentOut:
    ticket = get_ticket_or_404(db, ticket_id)
    ensure_ticket_visibility(current_user, ticket)
    comment = TicketComment(
        ticket_id=ticket.id,
        author_id=current_user.id,
        body=payload.body,
        is_internal=payload.is_internal,
    )
    db.add(comment)

    recipients = {ticket.creator.email}
    if ticket.assignee:
        recipients.add(ticket.assignee.email)
    recipients.discard(current_user.email)
    for email in recipients:
        queue_notification(
            db,
            event_type="TICKET_COMMENTED",
            recipient_email=email,
            subject=f"[{ticket.ticket_code}] Nouveau commentaire",
            payload={"ticket_id": str(ticket.id), "comment": payload.body[:200]},
        )

    log_audit(
        db,
        actor=current_user,
        action="TICKET_COMMENT_ADDED",
        entity_type="ticket",
        entity_id=str(ticket.id),
        after={"comment_id": "pending"},
    )
    db.commit()
    db.refresh(comment)
    author_summary = UserSummary.model_validate(current_user, from_attributes=True)
    return TicketCommentOut(
        id=comment.id,
        ticket_id=comment.ticket_id,
        author=author_summary,
        body=comment.body,
        is_internal=comment.is_internal,
        created_at=comment.created_at,
    )


@router.post("/{ticket_id}/attachments", response_model=TicketAttachmentOut, status_code=status.HTTP_201_CREATED)
async def upload_attachment(
    ticket_id: UUID,
    current_user: CurrentUser,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
) -> TicketAttachmentOut:
    ticket = get_ticket_or_404(db, ticket_id)
    ensure_ticket_visibility(current_user, ticket)

    mime_type = file.content_type or "application/octet-stream"
    if mime_type not in ALLOWED_ATTACHMENT_MIME:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unsupported file type")

    content = await file.read()
    if len(content) > MAX_ATTACHMENT_BYTES:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="File too large")

    attachment = TicketAttachment(
        ticket_id=ticket.id,
        filename=file.filename or "attachment.bin",
        mime_type=mime_type,
        size_bytes=len(content),
        content=content,
        uploaded_by=current_user.id,
    )
    db.add(attachment)
    log_audit(
        db,
        actor=current_user,
        action="TICKET_ATTACHMENT_ADDED",
        entity_type="ticket",
        entity_id=str(ticket.id),
        after={"filename": attachment.filename, "size": attachment.size_bytes},
    )
    db.commit()
    db.refresh(attachment)
    return TicketAttachmentOut(
        id=attachment.id,
        filename=attachment.filename,
        mime_type=attachment.mime_type,
        size_bytes=attachment.size_bytes,
        uploaded_by=attachment.uploaded_by,
        uploaded_at=attachment.uploaded_at,
    )


@router.get("/{ticket_id}/attachments/{attachment_id}")
def download_attachment(
    ticket_id: UUID,
    attachment_id: int,
    current_user: CurrentUser,
    db: Session = Depends(get_db),
) -> Response:
    ticket = get_ticket_or_404(db, ticket_id)
    ensure_ticket_visibility(current_user, ticket)

    attachment = db.scalar(
        select(TicketAttachment).where(
            TicketAttachment.id == attachment_id,
            TicketAttachment.ticket_id == ticket.id,
        )
    )
    if not attachment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Attachment not found")

    return Response(
        content=attachment.content,
        media_type=attachment.mime_type,
        headers={
            "Content-Disposition": f'attachment; filename="{attachment.filename}"',
        },
    )
