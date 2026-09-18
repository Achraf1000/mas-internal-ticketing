from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class DepartmentOut(BaseModel):
    id: int
    code: str
    name: str
    is_active: bool


class UserSummary(BaseModel):
    id: UUID
    email: str
    full_name: str


class PaginationMeta(BaseModel):
    total: int
    offset: int
    limit: int


class Timestamped(BaseModel):
    created_at: datetime
    updated_at: datetime

