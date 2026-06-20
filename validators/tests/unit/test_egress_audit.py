"""Unit tests for the egress-broker append-only audit.

Every broker decision — allow OR deny — appends one immutable JSONL record: the seat, the
commit sha + author, what was verified (the policy checks/reasons), which App/installation was
used, the push/PR result, and a timestamp. The audit is the signed-authorship/transport anchor
ADR-0007 calls for, and it feeds the rate guard (count recent pushes in the window).

Hard invariant: the audit is SECRET-FREE. ``append_audit`` refuses (fail-closed) any record
carrying a token/secret/PEM key or token-shaped value — a belt-and-suspenders guard so a future
caller can never leak a credential into the durable log.
"""

from datetime import datetime, timedelta, timezone

import pytest

from egress_broker.audit import AuditSecretLeak, append_audit, count_recent_pushes

_T0 = datetime(2026, 6, 20, 12, 0, 0, tzinfo=timezone.utc)


def _at(dt):
    return lambda: dt


def test_append_creates_file_and_parent_dir(tmp_path):
    path = tmp_path / "nested" / "audit.jsonl"
    rec = append_audit(path, {"seat_id": "dev-4", "decision": "allow"}, now=_at(_T0))
    assert path.is_file()
    assert rec["recorded_at"].startswith("2026-06-20T12:00:00")
    assert rec["seat_id"] == "dev-4"


def test_append_is_append_only(tmp_path):
    path = tmp_path / "audit.jsonl"
    append_audit(path, {"seat_id": "dev-4", "decision": "deny"}, now=_at(_T0))
    append_audit(path, {"seat_id": "dev-2", "decision": "allow"}, now=_at(_T0))
    lines = [l for l in path.read_text().splitlines() if l.strip()]
    assert len(lines) == 2
    import json

    assert json.loads(lines[0])["seat_id"] == "dev-4"
    assert json.loads(lines[1])["seat_id"] == "dev-2"


@pytest.mark.parametrize(
    "record",
    [
        {"seat_id": "dev-4", "token": "ghs_whatever"},
        {"seat_id": "dev-4", "value": "secret"},
        {"seat_id": "dev-4", "pem_path_contents": "-----BEGIN"},
        {"seat_id": "dev-4", "note": "ghp_0123456789abcdef0123456789abcdef0123"},
        {"seat_id": "dev-4", "nested": {"private_key": "x"}},
    ],
)
def test_append_refuses_secret_shaped_records(tmp_path, record):
    path = tmp_path / "audit.jsonl"
    with pytest.raises(AuditSecretLeak):
        append_audit(path, record, now=_at(_T0))
    assert not path.exists()  # nothing was written


def test_non_secret_record_with_sha_and_owner_is_fine(tmp_path):
    path = tmp_path / "audit.jsonl"
    rec = append_audit(
        path,
        {
            "seat_id": "dev-4",
            "head_sha": "a" * 40,
            "author_email": "9+cedev4vps-coder@users.noreply.github.com",
            "app_owner": "cedev4vps-coder",
            "installation_id": 555,
            "decision": "allow",
            "pushed": True,
        },
        now=_at(_T0),
    )
    assert rec["installation_id"] == 555  # an installation id is an identifier, not a secret


# ---------------------------------------------------------------------------
# Rate guard — count recent ALLOWED+PUSHED records for a seat within the window
# ---------------------------------------------------------------------------
def test_count_recent_pushes_counts_only_allowed_pushed_in_window_for_seat(tmp_path):
    path = tmp_path / "audit.jsonl"
    # two in-window pushes for dev-4
    append_audit(path, {"seat_id": "dev-4", "decision": "allow", "pushed": True}, now=_at(_T0))
    append_audit(
        path, {"seat_id": "dev-4", "decision": "allow", "pushed": True}, now=_at(_T0 + timedelta(minutes=5))
    )
    # a denial (not a push) — ignored
    append_audit(path, {"seat_id": "dev-4", "decision": "deny", "pushed": False}, now=_at(_T0))
    # a different seat — ignored
    append_audit(path, {"seat_id": "dev-2", "decision": "allow", "pushed": True}, now=_at(_T0))
    # an out-of-window push (2h earlier) — ignored
    append_audit(
        path, {"seat_id": "dev-4", "decision": "allow", "pushed": True}, now=_at(_T0 - timedelta(hours=2))
    )

    n = count_recent_pushes(path, "dev-4", window_seconds=3600, now=_at(_T0 + timedelta(minutes=10)))
    assert n == 2


def test_count_recent_pushes_on_missing_file_is_zero(tmp_path):
    assert count_recent_pushes(tmp_path / "nope.jsonl", "dev-4", window_seconds=3600, now=_at(_T0)) == 0


def test_count_recent_pushes_tolerates_garbled_lines(tmp_path):
    path = tmp_path / "audit.jsonl"
    append_audit(path, {"seat_id": "dev-4", "decision": "allow", "pushed": True}, now=_at(_T0))
    with path.open("a") as fh:
        fh.write("{ not json\n")
    n = count_recent_pushes(path, "dev-4", window_seconds=3600, now=_at(_T0 + timedelta(minutes=1)))
    assert n == 1  # the garbled line is skipped, not fatal
