from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.models.enums import TicketCategory, TicketPriority, TicketStatus
from app.schemas.common import DepartmentOut, UserSummary


class TicketCreate(BaseModel):
    title: str = Field(min_length=3, max_length=255)
    description: str = Field(min_length=3)
    category: TicketCategory
    priority: TicketPriority
    target_department_id: int
    emitter_department_id: int | None = None
    assignee_id: UUID | None = None
    is_department_broadcast: bool = False


class TicketPatch(BaseModel):
    title: str | None = Field(default=None, min_length=3, max_length=255)
    description: str | None = Field(default=None, min_length=3)
    category: TicketCategory | None = None
    priority: TicketPriority | None = None
    assignee_id: UUID | None = None


class TicketStatusTransitionRequest(BaseModel):
    to_status: TicketStatus
    reason: str | None = None


class TicketCommentCreate(BaseModel):
    body: str = Field(min_length=1)
    is_internal: bool = False


class TicketCommentOut(BaseModel):
    id: int
    ticket_id: UUID
    author: UserSummary
    body: str
    is_internal: bool
    created_at: datetime


class TicketAttachmentOut(BaseModel):
    id: int
    filename: str
    mime_type: str
    size_bytes: int
    uploaded_by: UUID
    uploaded_at: datetime


class TicketStatusHistoryOut(BaseModel):
    id: int
    from_status: TicketStatus | None
    to_status: TicketStatus
    changed_by: UUID
    reason: str | None
    changed_at: datetime


class TicketOut(BaseModel):
    id: UUID
    ticket_code: str
    title: str
    description: str
    category: TicketCategory
    priority: TicketPriority
    status: TicketStatus
    is_department_broadcast: bool
    emitter_department: DepartmentOut
    target_department: DepartmentOut
    creator: UserSummary
    assignee: UserSummary | None
    created_at: datetime
    updated_at: datetime
    resolved_at: datetime | None
    closed_at: datetime | None


class TicketDetailOut(TicketOut):
    comments: list[TicketCommentOut]
    attachments: list[TicketAttachmentOut]
    status_history: list[TicketStatusHistoryOut]

