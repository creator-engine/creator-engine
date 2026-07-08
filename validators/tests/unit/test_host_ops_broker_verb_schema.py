from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
HOST_OPS_ROOT = ROOT / "tools" / "host-ops-broker"
if str(HOST_OPS_ROOT) not in sys.path:
    sys.path.insert(0, str(HOST_OPS_ROOT))

from host_ops_broker.verb_schema import COMMAND_LIKE_FIELDS, VERBS, VerbSchemaError, validate_params

DIGEST = "registry.example/ce/tool@sha256:" + "a" * 64

VALID_PARAMS = {
    "status": {"include": ["daemons", "systemd"], "target": "agent", "detail": "diagnostic"},
    "restart-daemon": {"daemon": "agent", "mode": "try-restart", "wait_ready_seconds": 0},
    "prepare-owned-state-root": {"root_name": "controller", "purpose": "controller", "mode": "0750"},
    "rotate-attempt-log": {"subsystem": "attempts", "log_kind": "attempt", "max_bytes": 10, "keep": 1},
    "repair-systemd-unit": {"unit": "ce-agent.service", "action": "restart-only", "wait_ready_seconds": 10},
    "run-ephemeral-container": {"task": "verify", "image": DIGEST, "args": ["dry-run"], "network": "none"},
    "prune-stopped-owned-containers": {"namespace": "ce", "older_than_seconds": 3600, "max_remove": 1},
    "snapshot-openbao": {"profile": "daily", "destination": "local", "label": "operator-safe"},
    "restore-drill-openbao": {"profile": "daily", "snapshot_ref": "snap-001", "mode": "metadata-verify"},
}

INVALID_PARAMS = {
    "status": {"include": ["raw-sockets"]},
    "restart-daemon": {"daemon": "agent", "wait_ready_seconds": 121},
    "prepare-owned-state-root": {"root_name": "controller", "purpose": "unknown"},
    "rotate-attempt-log": {"subsystem": "attempts", "log_kind": "other"},
    "repair-systemd-unit": {"unit": "ce-agent.service", "wait_ready_seconds": -1},
    "run-ephemeral-container": {"task": "verify", "image": "registry.example/ce/tool:latest"},
    "prune-stopped-owned-containers": {"namespace": "ce", "max_remove": 0},
    "snapshot-openbao": {"profile": "daily"},
    "restore-drill-openbao": {"profile": "daily", "snapshot_ref": "snap-001", "mode": "live-restore"},
}


def test_schema_matrix_names_all_nine_verbs():
    assert tuple(VALID_PARAMS) == VERBS


@pytest.mark.parametrize("verb", VERBS)
def test_valid_params_are_accepted_for_every_verb(verb):
    normalized = validate_params(verb, VALID_PARAMS[verb])
    assert normalized


@pytest.mark.parametrize("verb", VERBS)
def test_invalid_params_are_rejected_for_every_verb(verb):
    with pytest.raises(VerbSchemaError):
        validate_params(verb, INVALID_PARAMS[verb])


@pytest.mark.parametrize("verb", VERBS)
def test_extra_params_are_rejected_for_every_verb(verb):
    raw = dict(VALID_PARAMS[verb])
    raw["extra"] = "nope"
    with pytest.raises(VerbSchemaError):
        validate_params(verb, raw)


def test_restart_daemon_name_with_space_is_rejected_by_schema():
    raw = dict(VALID_PARAMS["restart-daemon"])
    raw["daemon"] = "ce agent"

    with pytest.raises(VerbSchemaError, match="daemon contains unsupported characters"):
        validate_params("restart-daemon", raw)


@pytest.mark.parametrize("verb", VERBS)
@pytest.mark.parametrize("field", sorted(COMMAND_LIKE_FIELDS))
def test_command_like_params_are_rejected_for_every_verb(verb, field):
    raw = dict(VALID_PARAMS[verb])
    raw[field] = "nope"
    with pytest.raises(VerbSchemaError):
        validate_params(verb, raw)
