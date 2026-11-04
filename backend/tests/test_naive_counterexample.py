"""The known-bad algorithm is deliberately isolated in a test, never used by the app."""
import pytest

def naive_dedupe(original: dict, retry: dict) -> str:
    # INTENTIONALLY BUGGY: identical ID is not evidence of identical data.
    return "DUPLICATE" if original["event_id"] == retry["event_id"] else "NEW"

@pytest.mark.xfail(strict=True, reason="Bug witness: ID-only dedupe misses payload tampering")
def test_naive_identity_check_fails_on_changed_payload():
    initial = {"event_id": "evt-001", "status": "PICKED_UP"}
    changed = {"event_id": "evt-001", "status": "DELIVERED"}
    assert naive_dedupe(initial, changed) == "CONFLICT"
