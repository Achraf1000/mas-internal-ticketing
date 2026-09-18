from dataclasses import dataclass

from passlib.context import CryptContext
from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.user import User

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


@dataclass
class LocalAuthResult:
    is_authenticated: bool
    user: User | None = None
    error: str | None = None


def _column_exists(db: Session, column_name: str) -> bool:
    query = text(
        """
        SELECT 1
        FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_SCHEMA = 'dbo'
          AND TABLE_NAME = 'users'
          AND COLUMN_NAME = :column_name
        """
    )
    return db.execute(query, {"column_name": column_name}).scalar() is not None


def _check_password_hash(db: Session, user: User, password: str) -> bool:
    if not _column_exists(db, "password_hash"):
        return False
    password_hash = db.execute(
        text("SELECT password_hash FROM dbo.users WHERE id = :user_id"),
        {"user_id": str(user.id)},
    ).scalar()
    if not password_hash:
        return False
    try:
        return bool(pwd_context.verify(password, password_hash))
    except Exception:  # noqa: BLE001
        return False


def _check_temp_password(db: Session, user: User, password: str) -> bool:
    if not settings.auth_local_allow_temp_password:
        return False
    if not _column_exists(db, "temp_password"):
        return False
    temp_password = db.execute(
        text("SELECT temp_password FROM dbo.users WHERE id = :user_id"),
        {"user_id": str(user.id)},
    ).scalar()
    return bool(temp_password and temp_password == password)


def authenticate_local_user(db: Session, email: str, password: str) -> LocalAuthResult:
    user = db.scalar(select(User).where(User.email == email))
    if not user:
        return LocalAuthResult(is_authenticated=False, error="User not found in local DB")
    if not user.is_active:
        return LocalAuthResult(is_authenticated=False, error="User is inactive")
    if not password:
        return LocalAuthResult(is_authenticated=False, error="Empty password")

    if _check_password_hash(db, user, password):
        return LocalAuthResult(is_authenticated=True, user=user)
    if _check_temp_password(db, user, password):
        return LocalAuthResult(is_authenticated=True, user=user)

    return LocalAuthResult(is_authenticated=False, error="Invalid local credentials")

