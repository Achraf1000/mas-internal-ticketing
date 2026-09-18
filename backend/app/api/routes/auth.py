from datetime import UTC, datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import CurrentUser
from app.core.config import settings
from app.core.database import get_db
from app.core.security import create_access_token, create_refresh_token, decode_token
from app.models.user import RefreshToken, User
from app.schemas.auth import LoginRequest, LogoutRequest, MeResponse, RefreshRequest, TokenResponse
from app.services.audit import log_audit
from app.services.ldap_auth import LDAPService
from app.services.local_auth import authenticate_local_user
from app.services.rbac import resolve_role_from_ldap_groups

router = APIRouter(prefix="/auth", tags=["auth"])
ldap_service = LDAPService()


def _as_utc(dt: datetime | None) -> datetime | None:
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=UTC)
    return dt.astimezone(UTC)


def _issue_tokens(db: Session, user: User) -> TokenResponse:
    user.last_login_at = datetime.now(UTC)
    access_token, access_expires_at = create_access_token(str(user.id), user.role.value)
    refresh_payload = create_refresh_token(str(user.id))
    db.add(
        RefreshToken(
            token_id=refresh_payload.token_id,
            user_id=user.id,
            expires_at=refresh_payload.expires_at,
        )
    )
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_payload.token,
        access_token_expires_at=access_expires_at,
        refresh_token_expires_at=refresh_payload.expires_at,
    )


@router.post("/login", response_model=TokenResponse)
def login(
    payload: LoginRequest,
    request: Request,
    db: Session = Depends(get_db),
) -> TokenResponse:
    ip = request.client.host if request.client else None
    local_attempt_error: str | None = None

    if settings.auth_enable_local_fallback:
        local_result = authenticate_local_user(db, payload.email, payload.password)
        if local_result.is_authenticated and local_result.user:
            tokens = _issue_tokens(db, local_result.user)
            log_audit(
                db,
                actor=local_result.user,
                action="AUTH_LOGIN_SUCCESS_LOCAL",
                entity_type="auth",
                entity_id=str(local_result.user.id),
                ip=ip,
            )
            db.commit()
            return tokens
        local_attempt_error = local_result.error

    result = ldap_service.authenticate(payload.email, payload.password)
    if not result.is_authenticated:
        log_audit(
            db,
            action="AUTH_LOGIN_FAILED",
            entity_type="auth",
            entity_id=payload.email,
            after={
                "error": result.error,
                "local_error": local_attempt_error,
                "local_fallback_enabled": settings.auth_enable_local_fallback,
            },
            ip=ip,
        )
        db.commit()
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    user = db.scalar(select(User).where(User.email == payload.email))
    if not user:
        user = User(
            email=payload.email,
            full_name=result.full_name or payload.email.split("@")[0],
            role=resolve_role_from_ldap_groups(result.groups or []),
            ldap_groups=";".join(result.groups or []),
            is_active=True,
        )
        db.add(user)
        db.flush()
    else:
        user.full_name = result.full_name or user.full_name
        user.role = resolve_role_from_ldap_groups(result.groups or [])
        user.ldap_groups = ";".join(result.groups or [])

    tokens = _issue_tokens(db, user)
    log_audit(
        db,
        actor=user,
        action="AUTH_LOGIN_SUCCESS",
        entity_type="auth",
        entity_id=str(user.id),
        ip=ip,
    )
    db.commit()
    return tokens


@router.post("/refresh", response_model=TokenResponse)
def refresh_tokens(payload: RefreshRequest, db: Session = Depends(get_db)) -> TokenResponse:
    token_data = decode_token(payload.refresh_token)
    if token_data.get("type") != "refresh":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token type")

    token_id = token_data.get("jti")
    subject = token_data.get("sub")
    if not token_id or not subject:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token payload")

    stored = db.scalar(select(RefreshToken).where(RefreshToken.token_id == token_id))
    expires_at = _as_utc(stored.expires_at) if stored else None
    if not stored or stored.revoked_at is not None or expires_at is None or expires_at < datetime.now(UTC):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token revoked or expired")

    user = db.get(User, UUID(subject))
    if not user or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid user")

    stored.revoked_at = datetime.now(UTC)
    access_token, access_expires_at = create_access_token(str(user.id), user.role.value)
    refresh_payload = create_refresh_token(str(user.id))
    db.add(
        RefreshToken(
            token_id=refresh_payload.token_id,
            user_id=user.id,
            expires_at=refresh_payload.expires_at,
        )
    )
    db.commit()
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_payload.token,
        access_token_expires_at=access_expires_at,
        refresh_token_expires_at=refresh_payload.expires_at,
    )


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(payload: LogoutRequest, db: Session = Depends(get_db)) -> None:
    token_data = decode_token(payload.refresh_token)
    if token_data.get("type") != "refresh":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token type")
    token_id = token_data.get("jti")
    if token_id:
        stored = db.scalar(select(RefreshToken).where(RefreshToken.token_id == token_id))
        if stored and stored.revoked_at is None:
            stored.revoked_at = datetime.now(UTC)
            db.commit()


@router.get("/me", response_model=MeResponse)
def me(current_user: CurrentUser) -> MeResponse:
    return MeResponse(
        id=current_user.id,
        email=current_user.email,
        full_name=current_user.full_name,
        role=current_user.role,
        department_id=current_user.department_id,
        department_name=current_user.department.name if current_user.department else None,
        is_department_head=current_user.is_department_head,
    )
