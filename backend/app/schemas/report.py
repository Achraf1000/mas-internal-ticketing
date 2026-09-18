from pydantic import BaseModel


class BucketValue(BaseModel):
    key: str
    count: int


class UserStatusRow(BaseModel):
    user_id: str
    user_name: str
    department_name: str | None
    new_count: int
    in_progress_count: int
    on_hold_count: int
    resolved_count: int
    closed_count: int
    total_count: int


class ReportOverviewOut(BaseModel):
    total_tickets: int
    open_tickets: int
    overdue_tickets: int
    by_status: list[BucketValue]
    by_priority: list[BucketValue]
    by_user_status: list[UserStatusRow]


class SlaPriorityOut(BaseModel):
    priority: str
    open_count: int
    overdue_count: int
    avg_resolution_hours: float | None


class ReportSlaOut(BaseModel):
    rows: list[SlaPriorityOut]


class DepartmentPerformanceRow(BaseModel):
    department_id: int
    department_name: str
    total_tickets: int
    resolved_tickets: int
    avg_resolution_hours: float | None


class ReportDepartmentPerformanceOut(BaseModel):
    rows: list[DepartmentPerformanceRow]


class MemberPerformanceRow(BaseModel):
    member_id: str
    member_name: str
    assigned_open: int
    resolved_closed: int
    sla_overdue: int
    avg_resolution_hours: float | None
    new_count: int
    in_progress_count: int
    on_hold_count: int
    resolved_count: int
    closed_count: int


class DepartmentHeadKpiOut(BaseModel):
    received_count: int
    open_count: int
    resolved_count: int
    closed_count: int
    sla_overdue_count: int
    avg_resolution_hours: float | None


class DepartmentHeadOverviewOut(BaseModel):
    year: int
    month: int
    department_id: int
    department_name: str
    kpi: DepartmentHeadKpiOut
    by_status: list[BucketValue]
    by_priority: list[BucketValue]
    members: list[MemberPerformanceRow]
