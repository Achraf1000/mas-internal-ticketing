from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
import uuid

from jose import JWTError, jwt

from app.core.config import settings


class TokenError(Exception):
    """Raised when a token is invalid or expired."""


@dataclass
class RefreshTokenPayload:
    token: str
    token_id: str
    expires_at: datetime


def _encode_token(data: dict, expires_delta: timedelta) -> tuple[str, datetime]:
    expire = datetime.now(UTC) + expires_delta
    payload = data.copy()
    payload.update({"exp": expire})
    encoded = jwt.encode(payload, settings.secret_key, algorithm=settings.algorithm)
    return encoded, expire


def create_access_token(user_id: str, role: str) -> tuple[str, datetime]:
    return _encode_token(
        {
            "sub": user_id,
            "role": role,
            "type": "access",
        },
        timedelta(minutes=settings.access_token_expire_minutes),
    )


def create_refresh_token(user_id: str) -> RefreshTokenPayload:
    token_id = str(uuid.uuid4())
    token, expires = _encode_token(
        {
            "sub": user_id,
            "jti": token_id,
            "type": "refresh",
        },
        timedelta(minutes=settings.refresh_token_expire_minutes),
    )
    return RefreshTokenPayload(token=token, token_id=token_id, expires_at=expires)


def decode_token(token: str) -> dict:
    try:
        return jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
    except JWTError as exc:
        raise TokenError("Invalid token") from exc

