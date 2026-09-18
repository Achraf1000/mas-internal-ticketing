from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session
from uuid import UUID

from app.api.deps import require_roles
from app.core.database import get_db
from app.models.audit import AuditLog
from app.models.department import Department
from app.models.enums import NotificationStatus, Role
from app.models.notification import NotificationQueue
from app.models.user import User
from app.schemas.admin import AuditLogOut, FailedNotificationOut, UserCreate, UserOut, UserPatch
from app.services.audit import log_audit

router = APIRouter(tags=["admin"])


def _serialize_user(item: User) -> UserOut:
    return UserOut.model_validate(item, from_attributes=True)


@router.get("/users", response_model=list[UserOut], dependencies=[Depends(require_roles(Role.ADMIN))])
def list_users(
    db: Session = Depends(get_db),
    role: Role | None = None,
    department_id: int | None = None,
    is_active: bool | None = None,
) -> list[UserOut]:
    query = select(User).order_by(User.created_at.desc())
    if role is not None:
        query = query.where(User.role == role)
    if department_id is not None:
        query = query.where(User.department_id == department_id)
    if is_active is not None:
        query = query.where(User.is_active == is_active)
    rows = db.scalars(query).all()
    return [_serialize_user(item) for item in rows]


@router.post("/users", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def create_user(
    payload: UserCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(Role.ADMIN)),
) -> UserOut:
    existing = db.scalar(select(User).where(User.email == payload.email))
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="User already exists")
    if payload.department_id is not None:
        department = db.get(Department, payload.department_id)
        if not department:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Department not found")
    user = User(
        email=payload.email,
        full_name=payload.full_name,
        role=payload.role,
        department_id=payload.department_id,
        is_department_head=payload.is_department_head,
        is_active=payload.is_active,
    )
    db.add(user)
    db.flush()
    log_audit(
        db,
        actor=current_user,
        action="USER_CREATED",
        entity_type="user",
        entity_id=str(user.id),
        after={
            "email": user.email,
            "role": user.role.value,
            "department_id": user.department_id,
        },
    )
    db.commit()
    db.refresh(user)
    return _serialize_user(user)


@router.patch("/users/{user_id}", response_model=UserOut)
def patch_user(
    user_id: UUID,
    payload: UserPatch,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(Role.ADMIN)),
) -> UserOut:
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    before = {
        "full_name": user.full_name,
        "role": user.role.value,
        "department_id": user.department_id,
        "is_department_head": user.is_department_head,
        "is_active": user.is_active,
    }
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(user, field, value)
    log_audit(
        db,
        actor=current_user,
        action="USER_UPDATED",
        entity_type="user",
        entity_id=str(user.id),
        before=before,
        after={
            "full_name": user.full_name,
            "role": user.role.value,
            "department_id": user.department_id,
            "is_department_head": user.is_department_head,
            "is_active": user.is_active,
        },
    )
    db.commit()
    db.refresh(user)
    return _serialize_user(user)


@router.get("/audit-logs", response_model=list[AuditLogOut], dependencies=[Depends(require_roles(Role.ADMIN))])
def get_audit_logs(
    db: Session = Depends(get_db),
    limit: int = Query(default=200, le=1000),
    offset: int = 0,
) -> list[AuditLogOut]:
    rows = db.scalars(select(AuditLog).order_by(AuditLog.created_at.desc()).offset(offset).limit(limit)).all()
    return [AuditLogOut.model_validate(item, from_attributes=True) for item in rows]


@router.get(
    "/admin/notifications/failed",
    response_model=list[FailedNotificationOut],
    dependencies=[Depends(require_roles(Role.ADMIN, Role.IT_AGENT))],
)
def failed_notifications(
    db: Session = Depends(get_db),
    limit: int = Query(default=100, le=500),
) -> list[FailedNotificationOut]:
    rows = db.scalars(
        select(NotificationQueue)
        .where(NotificationQueue.status == NotificationStatus.FAILED)
        .order_by(NotificationQueue.created_at.desc())
        .limit(limit)
    ).all()
    return [FailedNotificationOut.model_validate(item, from_attributes=True) for item in rows]
