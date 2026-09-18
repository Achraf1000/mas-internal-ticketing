from app.models.enums import TicketStatus
from app.services.ticketing import ALLOWED_TRANSITIONS


def test_transition_matrix_contains_required_paths() -> None:
    assert TicketStatus.IN_PROGRESS in ALLOWED_TRANSITIONS[TicketStatus.NEW]
    assert TicketStatus.RESOLVED in ALLOWED_TRANSITIONS[TicketStatus.IN_PROGRESS]
    assert TicketStatus.CLOSED in ALLOWED_TRANSITIONS[TicketStatus.RESOLVED]
    assert TicketStatus.IN_PROGRESS in ALLOWED_TRANSITIONS[TicketStatus.RESOLVED]


def test_closed_has_no_outgoing_transition() -> None:
    assert ALLOWED_TRANSITIONS[TicketStatus.CLOSED] == set()

