from datetime import UTC, datetime, timedelta
import csv
from io import StringIO
from uuid import UUID
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import and_, case, func, select
from sqlalchemy.orm import Session, joinedload

from app.api.deps import CurrentUser
from app.core.database import get_db
from app.models.department import Department
from app.models.enums import Role, TicketPriority, TicketStatus
from app.models.sla import SlaPolicy
from app.models.ticket import Ticket
from app.models.user import User
from app.schemas.report import (
    BucketValue,
    DepartmentHeadKpiOut,
    DepartmentHeadOverviewOut,
    DepartmentPerformanceRow,
    MemberPerformanceRow,
    ReportDepartmentPerformanceOut,
    ReportOverviewOut,
    ReportSlaOut,
    SlaPriorityOut,
    UserStatusRow,
)

router = APIRouter(prefix="/reports", tags=["reports"])
try:
    PARIS_TZ = ZoneInfo("Europe/Paris")
except Exception:  # noqa: BLE001
    PARIS_TZ = datetime.now().astimezone().tzinfo or UTC


def _require_management_role(user_role: Role) -> None:
    if user_role not in {Role.ADMIN, Role.IT_AGENT}:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")


def _policy_map(db: Session) -> dict[TicketPriority, SlaPolicy]:
    return {row.priority: row for row in db.scalars(select(SlaPolicy).where(SlaPolicy.is_active == True)).all()}


def _as_utc(dt: datetime | None) -> datetime | None:
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=UTC)
    return dt.astimezone(UTC)


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


def _resolution_minutes(priority: TicketPriority, policies: dict[TicketPriority, SlaPolicy]) -> int:
    policy = policies.get(priority)
    if policy:
        return policy.resolution_minutes
    fallback = {
        TicketPriority.LOW: 80 * 60,
        TicketPriority.MEDIUM: 40 * 60,
        TicketPriority.HIGH: 16 * 60,
        TicketPriority.CRITICAL: 8 * 60,
    }
    return fallback[priority]


def _is_overdue(ticket: Ticket, now: datetime, policies: dict[TicketPriority, SlaPolicy]) -> bool:
    if ticket.status in {TicketStatus.RESOLVED, TicketStatus.CLOSED}:
        return False
    created_at = _as_utc(ticket.created_at)
    if created_at is None:
        return False
    return now > created_at + timedelta(minutes=_resolution_minutes(ticket.priority, policies))


def _require_department_head_or_admin(user: CurrentUser) -> None:
    if user.role == Role.ADMIN:
        return
    if user.is_department_head and user.department_id is not None:
        return
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")


@router.get("/overview", response_model=ReportOverviewOut)
def report_overview(
    current_user: CurrentUser,
    db: Session = Depends(get_db),
) -> ReportOverviewOut:
    _require_management_role(current_user.role)
    total_tickets = db.scalar(select(func.count()).select_from(Ticket)) or 0
    open_tickets = (
        db.scalar(
            select(func.count())
            .select_from(Ticket)
            .where(Ticket.status.not_in([TicketStatus.RESOLVED, TicketStatus.CLOSED]))
        )
        or 0
    )

    status_rows = db.execute(
        select(Ticket.status, func.count()).group_by(Ticket.status).order_by(Ticket.status.asc())
    ).all()
    by_status = [BucketValue(key=row[0].value, count=row[1]) for row in status_rows]

    priority_rows = db.execute(
        select(Ticket.priority, func.count()).group_by(Ticket.priority).order_by(Ticket.priority.asc())
    ).all()
    by_priority = [BucketValue(key=row[0].value, count=row[1]) for row in priority_rows]

    now = datetime.now(UTC)
    policies = _policy_map(db)
    open_rows = db.scalars(
        select(Ticket).where(Ticket.status.not_in([TicketStatus.RESOLVED, TicketStatus.CLOSED]))
    ).all()
    overdue = sum(1 for ticket in open_rows if _is_overdue(ticket, now, policies))

    ticket_rows = db.scalars(select(Ticket)).all()
    assignee_ids = {ticket.assignee_id for ticket in ticket_rows if ticket.assignee_id is not None}
    users_by_id = {}
    if assignee_ids:
        users_by_id = {
            user.id: user
            for user in db.scalars(
                select(User).options(joinedload(User.department)).where(User.id.in_(assignee_ids))
            ).all()
        }
    grouped: dict[str, dict[str, int | str | None]] = {}
    for ticket in ticket_rows:
        if ticket.assignee_id is None:
            bucket_id = "UNASSIGNED"
            bucket_name = "Non assigne"
            department_name = None
        else:
            bucket_id = str(ticket.assignee_id)
            assignee = users_by_id.get(ticket.assignee_id)
            bucket_name = assignee.full_name if assignee else "Utilisateur inconnu"
            department_name = assignee.department.name if assignee and assignee.department else None

        if bucket_id not in grouped:
            grouped[bucket_id] = {
                "user_id": bucket_id,
                "user_name": bucket_name,
                "department_name": department_name,
                "new_count": 0,
                "in_progress_count": 0,
                "on_hold_count": 0,
                "resolved_count": 0,
                "closed_count": 0,
                "total_count": 0,
            }
        grouped[bucket_id]["total_count"] = int(grouped[bucket_id]["total_count"]) + 1
        if ticket.status == TicketStatus.NEW:
            grouped[bucket_id]["new_count"] = int(grouped[bucket_id]["new_count"]) + 1
        elif ticket.status == TicketStatus.IN_PROGRESS:
            grouped[bucket_id]["in_progress_count"] = int(grouped[bucket_id]["in_progress_count"]) + 1
        elif ticket.status == TicketStatus.ON_HOLD:
            grouped[bucket_id]["on_hold_count"] = int(grouped[bucket_id]["on_hold_count"]) + 1
        elif ticket.status == TicketStatus.RESOLVED:
            grouped[bucket_id]["resolved_count"] = int(grouped[bucket_id]["resolved_count"]) + 1
        elif ticket.status == TicketStatus.CLOSED:
            grouped[bucket_id]["closed_count"] = int(grouped[bucket_id]["closed_count"]) + 1

    by_user_status = [
        UserStatusRow(
            user_id=str(row["user_id"]),
            user_name=str(row["user_name"]),
            department_name=str(row["department_name"]) if row["department_name"] is not None else None,
            new_count=int(row["new_count"]),
            in_progress_count=int(row["in_progress_count"]),
            on_hold_count=int(row["on_hold_count"]),
            resolved_count=int(row["resolved_count"]),
            closed_count=int(row["closed_count"]),
            total_count=int(row["total_count"]),
        )
        for row in sorted(
            grouped.values(),
            key=lambda item: (-int(item["total_count"]), str(item["user_name"])),
        )
    ]

    return ReportOverviewOut(
        total_tickets=total_tickets,
        open_tickets=open_tickets,
        overdue_tickets=overdue,
        by_status=by_status,
        by_priority=by_priority,
        by_user_status=by_user_status,
    )


@router.get("/sla", response_model=ReportSlaOut)
def report_sla(
    current_user: CurrentUser,
    db: Session = Depends(get_db),
) -> ReportSlaOut:
    _require_management_role(current_user.role)
    now = datetime.now(UTC)
    policies = _policy_map(db)
    rows: list[SlaPriorityOut] = []

    for priority in TicketPriority:
        tickets = db.scalars(select(Ticket).where(Ticket.priority == priority)).all()
        open_items = [t for t in tickets if t.status not in {TicketStatus.RESOLVED, TicketStatus.CLOSED}]
        overdue_count = sum(1 for item in open_items if _is_overdue(item, now, policies))
        resolved_items = [t for t in tickets if t.resolved_at is not None]
        avg_hours = None
        if resolved_items:
            durations: list[float] = []
            for item in resolved_items:
                created_at = _as_utc(item.created_at)
                resolved_at = _as_utc(item.resolved_at)
                if created_at is None or resolved_at is None:
                    continue
                durations.append((resolved_at - created_at).total_seconds() / 3600)
            if durations:
                avg_hours = round(sum(durations) / len(durations), 2)
        rows.append(
            SlaPriorityOut(
                priority=priority.value,
                open_count=len(open_items),
                overdue_count=overdue_count,
                avg_resolution_hours=avg_hours,
            )
        )

    return ReportSlaOut(rows=rows)


@router.get("/department-performance", response_model=ReportDepartmentPerformanceOut)
def report_department_performance(
    current_user: CurrentUser,
    db: Session = Depends(get_db),
) -> ReportDepartmentPerformanceOut:
    _require_management_role(current_user.role)
    result = db.execute(
        select(
            Department.id,
            Department.name,
            func.count(Ticket.id),
            func.sum(case((Ticket.status.in_([TicketStatus.RESOLVED, TicketStatus.CLOSED]), 1), else_=0)),
            func.avg(
                case(
                    (
                        Ticket.resolved_at.is_not(None),
                        func.datediff("second", Ticket.created_at, Ticket.resolved_at) / 3600.0,
                    ),
                    else_=None,
                )
            ),
        )
        .select_from(Department)
        .join(Ticket, Ticket.target_department_id == Department.id, isouter=True)
        .group_by(Department.id, Department.name)
        .order_by(Department.name.asc())
    ).all()

    rows = [
        DepartmentPerformanceRow(
            department_id=dep_id,
            department_name=dep_name,
            total_tickets=total or 0,
            resolved_tickets=resolved or 0,
            avg_resolution_hours=round(float(avg_hours), 2) if avg_hours is not None else None,
        )
        for dep_id, dep_name, total, resolved, avg_hours in result
    ]
    return ReportDepartmentPerformanceOut(rows=rows)


@router.get("/export.csv")
def export_report_csv(
    current_user: CurrentUser,
    report: str = Query(..., pattern="^(overview|sla|department-performance)$"),
    db: Session = Depends(get_db),
) -> Response:
    _require_management_role(current_user.role)
    buffer = StringIO()
    writer = csv.writer(buffer)

    if report == "overview":
        data = report_overview(current_user=current_user, db=db)
        writer.writerow(["metric", "value"])
        writer.writerow(["total_tickets", data.total_tickets])
        writer.writerow(["open_tickets", data.open_tickets])
        writer.writerow(["overdue_tickets", data.overdue_tickets])
        writer.writerow([])
        writer.writerow(["status", "count"])
        for item in data.by_status:
            writer.writerow([item.key, item.count])
        writer.writerow([])
        writer.writerow(
            [
                "user_id",
                "user_name",
                "department_name",
                "new_count",
                "in_progress_count",
                "on_hold_count",
                "resolved_count",
                "closed_count",
                "total_count",
            ]
        )
        for row in data.by_user_status:
            writer.writerow(
                [
                    row.user_id,
                    row.user_name,
                    row.department_name or "",
                    row.new_count,
                    row.in_progress_count,
                    row.on_hold_count,
                    row.resolved_count,
                    row.closed_count,
                    row.total_count,
                ]
            )
    elif report == "sla":
        data = report_sla(current_user=current_user, db=db)
        writer.writerow(["priority", "open_count", "overdue_count", "avg_resolution_hours"])
        for row in data.rows:
            writer.writerow([row.priority, row.open_count, row.overdue_count, row.avg_resolution_hours or ""])
    else:
        data = report_department_performance(current_user=current_user, db=db)
        writer.writerow(
            ["department_id", "department_name", "total_tickets", "resolved_tickets", "avg_resolution_hours"]
        )
        for row in data.rows:
            writer.writerow(
                [
                    row.department_id,
                    row.department_name,
                    row.total_tickets,
                    row.resolved_tickets,
                    row.avg_resolution_hours or "",
                ]
            )

    return Response(
        content=buffer.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{report}.csv"'},
    )


@router.get("/department-head-overview", response_model=DepartmentHeadOverviewOut)
def department_head_overview(
    current_user: CurrentUser,
    db: Session = Depends(get_db),
    year: int | None = None,
    month: int | None = Query(default=None, ge=1, le=12),
    member_id: UUID | None = None,
    department_id: int | None = None,
) -> DepartmentHeadOverviewOut:
    _require_department_head_or_admin(current_user)
    resolved_year, resolved_month, start_utc, end_utc = _month_window_utc(year=year, month=month)

    scope_department_id = current_user.department_id
    if current_user.role == Role.ADMIN:
        scope_department_id = department_id
    if scope_department_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="department_id is required for this user",
        )

    department = db.get(Department, scope_department_id)
    if not department:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Department not found")

    base_scope = [
        Ticket.target_department_id == scope_department_id,
        Ticket.created_at >= start_utc,
        Ticket.created_at < end_utc,
    ]
    if member_id is not None:
        base_scope.append(Ticket.assignee_id == member_id)

    tickets = db.scalars(select(Ticket).where(and_(*base_scope))).all()
    policies = _policy_map(db)
    now = datetime.now(UTC)

    received_count = len(tickets)
    open_count = sum(1 for item in tickets if item.status not in {TicketStatus.RESOLVED, TicketStatus.CLOSED})
    resolved_count = sum(1 for item in tickets if item.status == TicketStatus.RESOLVED)
    closed_count = sum(1 for item in tickets if item.status == TicketStatus.CLOSED)
    sla_overdue_count = sum(1 for item in tickets if _is_overdue(item, now, policies))

    resolution_durations = []
    for item in tickets:
        if item.resolved_at is None:
            continue
        created_at = _as_utc(item.created_at)
        resolved_at = _as_utc(item.resolved_at)
        if not created_at or not resolved_at:
            continue
        resolution_durations.append((resolved_at - created_at).total_seconds() / 3600)
    avg_resolution_hours = round(sum(resolution_durations) / len(resolution_durations), 2) if resolution_durations else None

    status_rows = db.execute(
        select(Ticket.status, func.count())
        .where(and_(*base_scope))
        .group_by(Ticket.status)
        .order_by(Ticket.status.asc())
    ).all()
    by_status = [BucketValue(key=item[0].value, count=item[1]) for item in status_rows]

    priority_rows = db.execute(
        select(Ticket.priority, func.count())
        .where(and_(*base_scope))
        .group_by(Ticket.priority)
        .order_by(Ticket.priority.asc())
    ).all()
    by_priority = [BucketValue(key=item[0].value, count=item[1]) for item in priority_rows]

    members_query = select(User).where(User.department_id == scope_department_id, User.is_active == True)
    if member_id is not None:
        members_query = members_query.where(User.id == member_id)
    members = db.scalars(members_query.order_by(User.full_name.asc())).all()

    member_rows: list[MemberPerformanceRow] = []
    for member in members:
        member_tickets = [item for item in tickets if item.assignee_id == member.id]
        assigned_open = sum(
            1 for item in member_tickets if item.status not in {TicketStatus.RESOLVED, TicketStatus.CLOSED}
        )
        resolved_closed = sum(1 for item in member_tickets if item.status in {TicketStatus.RESOLVED, TicketStatus.CLOSED})
        new_count = sum(1 for item in member_tickets if item.status == TicketStatus.NEW)
        in_progress_count = sum(1 for item in member_tickets if item.status == TicketStatus.IN_PROGRESS)
        on_hold_count = sum(1 for item in member_tickets if item.status == TicketStatus.ON_HOLD)
        resolved_count = sum(1 for item in member_tickets if item.status == TicketStatus.RESOLVED)
        closed_count = sum(1 for item in member_tickets if item.status == TicketStatus.CLOSED)
        member_sla_overdue = sum(1 for item in member_tickets if _is_overdue(item, now, policies))
        member_durations = []
        for item in member_tickets:
            if item.resolved_at is None:
                continue
            created_at = _as_utc(item.created_at)
            resolved_at = _as_utc(item.resolved_at)
            if not created_at or not resolved_at:
                continue
            member_durations.append((resolved_at - created_at).total_seconds() / 3600)
        member_avg = round(sum(member_durations) / len(member_durations), 2) if member_durations else None
        member_rows.append(
            MemberPerformanceRow(
                member_id=str(member.id),
                member_name=member.full_name,
                assigned_open=assigned_open,
                resolved_closed=resolved_closed,
                sla_overdue=member_sla_overdue,
                avg_resolution_hours=member_avg,
                new_count=new_count,
                in_progress_count=in_progress_count,
                on_hold_count=on_hold_count,
                resolved_count=resolved_count,
                closed_count=closed_count,
            )
        )

    return DepartmentHeadOverviewOut(
        year=resolved_year,
        month=resolved_month,
        department_id=department.id,
        department_name=department.name,
        kpi=DepartmentHeadKpiOut(
            received_count=received_count,
            open_count=open_count,
            resolved_count=resolved_count,
            closed_count=closed_count,
            sla_overdue_count=sla_overdue_count,
            avg_resolution_hours=avg_resolution_hours,
        ),
        by_status=by_status,
        by_priority=by_priority,
        members=member_rows,
    )
