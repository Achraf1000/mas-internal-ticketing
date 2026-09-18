from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
import hashlib
import hmac
import secrets
from threading import Lock
from uuid import UUID


@dataclass
class CloseConfirmationToken:
    ticket_id: UUID
    creator_id: UUID
    code_hash: str
    expires_at: datetime
    attempts: int = 0
    max_attempts: int = 5


@dataclass
class CloseConfirmationRequestResult:
    code: str
    expires_at: datetime


_TOKENS: dict[UUID, CloseConfirmationToken] = {}
_LOCK = Lock()


def _hash_code(*, ticket_id: UUID, creator_id: UUID, code: str, secret_key: str) -> str:
    raw = f"{ticket_id}:{creator_id}:{code}:{secret_key}".encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _purge_expired(now: datetime) -> None:
    expired = [ticket_id for ticket_id, token in _TOKENS.items() if token.expires_at <= now]
    for ticket_id in expired:
        _TOKENS.pop(ticket_id, None)


def create_close_confirmation(
    *,
    ticket_id: UUID,
    creator_id: UUID,
    secret_key: str,
    ttl_minutes: int,
    max_attempts: int,
) -> CloseConfirmationRequestResult:
    now = datetime.now(UTC)
    expires_at = now + timedelta(minutes=ttl_minutes)
    code = f"{secrets.randbelow(1000000):06d}"
    token = CloseConfirmationToken(
        ticket_id=ticket_id,
        creator_id=creator_id,
        code_hash=_hash_code(ticket_id=ticket_id, creator_id=creator_id, code=code, secret_key=secret_key),
        expires_at=expires_at,
        attempts=0,
        max_attempts=max_attempts,
    )
    with _LOCK:
        _purge_expired(now)
        _TOKENS[ticket_id] = token
    return CloseConfirmationRequestResult(code=code, expires_at=expires_at)


def verify_close_confirmation(
    *,
    ticket_id: UUID,
    creator_id: UUID,
    provided_code: str,
    secret_key: str,
) -> tuple[bool, str | None]:
    now = datetime.now(UTC)
    with _LOCK:
        _purge_expired(now)
        token = _TOKENS.get(ticket_id)
        if token is None:
            return False, "Confirmation code missing or expired"
        if token.creator_id != creator_id:
            return False, "Invalid confirmation context"
        if token.expires_at <= now:
            _TOKENS.pop(ticket_id, None)
            return False, "Confirmation code expired"
        if token.attempts >= token.max_attempts:
            _TOKENS.pop(ticket_id, None)
            return False, "Maximum confirmation attempts reached"

        token.attempts += 1
        expected_hash = _hash_code(
            ticket_id=ticket_id,
            creator_id=creator_id,
            code=provided_code.strip(),
            secret_key=secret_key,
        )
        if not hmac.compare_digest(expected_hash, token.code_hash):
            if token.attempts >= token.max_attempts:
                _TOKENS.pop(ticket_id, None)
            return False, "Invalid confirmation code"

        _TOKENS.pop(ticket_id, None)
        return True, None
