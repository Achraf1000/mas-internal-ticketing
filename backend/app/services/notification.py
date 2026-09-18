from __future__ import annotations

from datetime import UTC, datetime, timedelta
import json
import logging
import smtplib
from email.message import EmailMessage

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.enums import NotificationStatus
from app.models.notification import NotificationQueue

logger = logging.getLogger(__name__)


def queue_notification(
    db: Session,
    *,
    event_type: str,
    recipient_email: str,
    subject: str,
    payload: dict,
) -> NotificationQueue:
    item = NotificationQueue(
        event_type=event_type,
        recipient_email=recipient_email,
        subject=subject,
        payload_json=json.dumps(payload, ensure_ascii=False, default=str),
        status=NotificationStatus.PENDING,
        max_attempts=settings.notification_max_attempts,
    )
    db.add(item)
    return item


def _build_email_message(item: NotificationQueue) -> EmailMessage:
    body = [
        f"Type d'evenement: {item.event_type}",
        "",
        "Details:",
        item.payload_json,
    ]
    msg = EmailMessage()
    msg["Subject"] = item.subject
    msg["From"] = settings.smtp_sender
    msg["To"] = item.recipient_email
    msg.set_content("\n".join(body))
    return msg


def _send_email(item: NotificationQueue) -> None:
    message = _build_email_message(item)
    with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=10) as server:
        if settings.smtp_use_tls:
            server.starttls()
        if settings.smtp_username and settings.smtp_password:
            server.login(settings.smtp_username, settings.smtp_password)
        server.send_message(message)


def process_notification_queue(db: Session, *, batch_size: int | None = None) -> dict[str, int]:
    now = datetime.now(UTC)
    batch = batch_size or settings.notification_batch_size
    rows = db.scalars(
        select(NotificationQueue)
        .where(
            NotificationQueue.status.in_([NotificationStatus.PENDING, NotificationStatus.RETRY]),
            NotificationQueue.next_attempt_at <= now,
        )
        .order_by(NotificationQueue.created_at.asc())
        .limit(batch)
    ).all()

    processed = 0
    sent = 0
    failed = 0

    for row in rows:
        processed += 1
        row.attempts += 1
        try:
            _send_email(row)
            row.status = NotificationStatus.SENT
            row.sent_at = now
            row.last_error = None
            sent += 1
        except Exception as exc:  # noqa: BLE001
            logger.exception("SMTP send failure for queue item %s", row.id)
            row.last_error = str(exc)
            if row.attempts >= row.max_attempts:
                row.status = NotificationStatus.FAILED
                failed += 1
            else:
                row.status = NotificationStatus.RETRY
                row.next_attempt_at = now + timedelta(minutes=2 ** min(row.attempts, 6))

    db.commit()
    return {"processed": processed, "sent": sent, "failed": failed}

