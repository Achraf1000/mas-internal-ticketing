from fastapi import APIRouter, Depends
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.api.deps import CurrentUser
from app.core.database import get_db
from app.models.department import Department
from app.models.enums import TicketCategory, TicketPriority
from app.models.user import User
from app.schemas.common import DepartmentOut
from app.schemas.common import UserSummary

router = APIRouter(tags=["reference"])


@router.get("/departments", response_model=list[DepartmentOut])
def get_departments(db: Session = Depends(get_db)) -> list[DepartmentOut]:
    rows = db.scalars(select(Department).where(Department.is_active == True).order_by(Department.name.asc())).all()
    return [DepartmentOut.model_validate(dep, from_attributes=True) for dep in rows]


@router.get("/ticket-categories", response_model=list[str])
def get_ticket_categories() -> list[str]:
    return [item.value for item in TicketCategory]


@router.get("/priorities", response_model=list[str])
def get_priorities() -> list[str]:
    return [item.value for item in TicketPriority]


@router.get("/users/assignable", response_model=list[UserSummary])
def get_assignable_users(
    current_user: CurrentUser,
    db: Session = Depends(get_db),
    department_id: int | None = None,
) -> list[UserSummary]:
    query = select(User).where(User.is_active == True).order_by(User.full_name.asc())
    if department_id is not None:
        query = query.where(or_(User.department_id == department_id, User.department_id.is_(None)))
    rows = db.scalars(query).all()
    return [UserSummary.model_validate(item, from_attributes=True) for item in rows]
