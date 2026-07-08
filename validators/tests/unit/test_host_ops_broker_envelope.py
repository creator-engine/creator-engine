from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
HOST_OPS_ROOT = ROOT / "tools" / "host-ops-broker"
if str(HOST_OPS_ROOT) not in sys.path:
    sys.path.insert(0, str(HOST_OPS_ROOT))

from host_ops_broker.envelope import EnvelopeError, RESULTS, response_envelope, validate_request


def _request(**overrides):
    raw = {
        "schema": "ce.host_ops.request.v1",
        "verb": "status",
        "request_id": "hostops-1",
        "caller": {"identity": "controller:dev", "role": "controller"},
        "params": {},
        "created_at": "2026-07-08T12:00:00Z",
    }
    raw.update(overrides)
    return raw


def test_accepts_v1_request_envelope():
    env = validate_request(_request())
    assert env.schema == "ce.host_ops.request.v1"
    assert env.verb == "status"
    assert env.params["detail"] == "summary"


@pytest.mark.parametrize(
    "patch",
    [
        {"unexpected": True},
        {"command": "systemctl restart nope"},
        {"caller": {"identity": "controller:dev", "role": "controller", "argv": []}},
    ],
)
def test_rejects_unknown_extra_or_command_like_fields(patch):
    raw = _request()
    raw.update(patch)
    with pytest.raises((EnvelopeError, ValueError)):
        validate_request(raw)


@pytest.mark.parametrize(
    "created_at",
    ["2026-07-08T12:00:00+00:00", "2026-07-08T12:00:00", "not-a-date"],
)
def test_created_at_requires_rfc3339_utc_z(created_at):
    with pytest.raises(EnvelopeError):
        validate_request(_request(created_at=created_at))


@pytest.mark.parametrize("field", ["schema", "verb", "request_id", "caller", "params", "created_at"])
def test_missing_required_fields_are_rejected(field):
    raw = _request()
    raw.pop(field)
    with pytest.raises(EnvelopeError):
        validate_request(raw)


def test_mutating_verb_requires_reason():
    with pytest.raises(EnvelopeError):
        validate_request(_request(verb="restart-daemon", params={"daemon": "agent"}))


def test_response_envelope_covers_all_result_classes():
    for result in RESULTS:
        resp = response_envelope("hostops-1", "status", result, details={"class": result})
        assert resp["schema"] == "ce.host_ops.response.v1"
        assert resp["result"] == result
