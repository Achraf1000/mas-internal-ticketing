from enum import Enum


class Role(str, Enum):
    USER = "USER"
    IT_AGENT = "IT_AGENT"
    ADMIN = "ADMIN"


class TicketStatus(str, Enum):
    NEW = "NEW"
    IN_PROGRESS = "IN_PROGRESS"
    ON_HOLD = "ON_HOLD"
    RESOLVED = "RESOLVED"
    CLOSED = "CLOSED"


class TicketPriority(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class TicketCategory(str, Enum):
    REQUEST = "REQUEST"
    INCIDENT = "INCIDENT"
    ANOMALY = "ANOMALY"
    VALIDATION = "VALIDATION"


class NotificationStatus(str, Enum):
    PENDING = "PENDING"
    RETRY = "RETRY"
    SENT = "SENT"
    FAILED = "FAILED"

