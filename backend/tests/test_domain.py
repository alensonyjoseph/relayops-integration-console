from datetime import datetime, timezone
from relayops.domain import qualify_transition, ALLOWED

def test_terminal_states():
    assert not ALLOWED["DELIVERED"]
    assert not ALLOWED["CANCELLED"]

def test_timezone_invariant():
    at = datetime(2026, 11, 4, 10, 0, tzinfo=timezone.utc)
    assert qualify_transition("CREATED", "PICKED_UP", at, None) is None
    assert qualify_transition("PICKED_UP", "IN_TRANSIT", at, at) == "STALE_EVENT"
