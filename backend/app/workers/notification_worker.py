import logging

from app.core.database import SessionLocal
from app.services.notification import process_notification_queue

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def run_once() -> None:
    with SessionLocal() as db:
        result = process_notification_queue(db)
    logger.info(
        "Notification worker complete: processed=%s sent=%s failed=%s",
        result["processed"],
        result["sent"],
        result["failed"],
    )


if __name__ == "__main__":
    run_once()

