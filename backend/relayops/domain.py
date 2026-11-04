"""Pure transition rules, deliberately independent of Flask and SQLAlchemy."""
from datetime import datetime

STATES = ("CREATED", "PICKED_UP", "IN_TRANSIT", "DELIVERED", "CANCELLED")
ALLOWED = {
    "CREATED": {"PICKED_UP", "CANCELLED"},
    "PICKED_UP": {"IN_TRANSIT", "CANCELLED"},
    "IN_TRANSIT": {"DELIVERED"},
    "DELIVERED": set(),
    "CANCELLED": set(),
}

def qualify_transition(current: str, target: str, occurred_at: datetime, last_at: datetime | None) -> str | None:
    """Return a stable rejection code or None for an allowed transition."""
    if last_at is not None:
        # SQLite may return naive values even with timezone=True; normalize UTC.
        from datetime import timezone
        previous = last_at if last_at.tzinfo else last_at.replace(tzinfo=timezone.utc)
        if occurred_at <= previous:
            return "STALE_EVENT"
    if target not in ALLOWED.get(current, set()):
        return "INVALID_TRANSITION"
    return None
