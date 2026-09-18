from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, EmailStr

from app.models.enums import Role


class UserCreate(BaseModel):
    email: EmailStr
    full_name: str
    role: Role = Role.USER
    department_id: int | None = None
    is_department_head: bool = False
    is_active: bool = True


class UserPatch(BaseModel):
    full_name: str | None = None
    role: Role | None = None
    department_id: int | None = None
    is_department_head: bool | None = None
    is_active: bool | None = None


class UserOut(BaseModel):
    id: UUID
    email: EmailStr
    full_name: str
    role: Role
    department_id: int | None
    is_department_head: bool
    is_active: bool
    ldap_groups: str
    last_login_at: datetime | None
    created_at: datetime
    updated_at: datetime


class AuditLogOut(BaseModel):
    id: int
    actor_id: UUID | None
    action: str
    entity_type: str
    entity_id: str
    before_json: str | None
    after_json: str | None
    ip: str | None
    created_at: datetime


class FailedNotificationOut(BaseModel):
    id: int
    event_type: str
    recipient_email: str
    subject: str
    attempts: int
    last_error: str | None
    created_at: datetime

