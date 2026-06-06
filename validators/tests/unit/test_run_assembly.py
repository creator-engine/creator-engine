"""Unit tests for the v3 G-3.6b offline composition root (``run_assembly``).

``make_run_driver(repo, root)`` returns a callable that drives one ratified,
audited agent-seat run end to end and PERSISTS its evidence — offline. It wires
the production ``token_minter`` (over ``forge.mint_scoped_token`` /
``forge.revoke_scoped_token`` -> the value-free ``MintedCredential``), the
minter->runner bridge (a closure cell sharing the one live ``ScopedToken`` from
the minter to the ``change_opener``'s authenticated ``gh`` runner via
``authenticated_gh_runner`` — so the change-opener authenticates with the SAME
minted token while the orchestrator stays value-free), the production
``change_opener`` (over ``forge.open_change(..., apply=False)``), and the G-3.5
``file_evidence_sink`` into one ``run_plan(...)`` drive.

These tests use a ``RunChangeSet``-yielding fake backend + a fake App-level
``gh_runner`` (mint/revoke) + a fake ``spawn`` (the authenticated change-opener
runner) + a fake ``write``, with ``subprocess`` / ``socket`` / ``Path.write_text``
monkeypatched to EXPLODE — ZERO live ``gh`` / network / subprocess / disk. They
assert the full pipeline, the persisted chain, the minter->runner bridge, secret
hygiene, and revocation.
"""

import json
import logging
import os
import socket
import subprocess
from pathlib import Path

import pytest
import yaml

from creator_engine_validator.forge.scoped_token import TokenRequest
from creator_engine_validator.run_assembly import make_run_driver
from creator_engine_validator.runner import (
    RunChangeSet,
    RunnerBackend,
    RunResult,
)
from creator_engine_validator.runner.noop_backend import LocalNoopBackend
from creator_engine_validator.runtime_evidence_spine import verify_chain
from creator_engine_validator.schema import validate_with_schema

_POLICY_SHA = "a" * 64
_IMAGE_SHA = "sha256:" + "b" * 64
_MINTED_SECRET = "ghs_TEST_MINTED_SECRET"
_SCHEMA = "schemas/runtime-evidence.schema.yaml"
_CONTRACT = "docs/contracts/runtime-evidence.md"
_REPO = "creator-engine/creator-engine"

_RUN_CHANGE_SET = RunChangeSet(
    branch="ce/run-1",
    base="main",
    manifest_paths=("validators/creator_engine_validator/run_assembly.py",),
    head_sha="d" * 40,
)


def valid_policy() -> dict:
    return {
        "kind": "runtime-policy-record",
        "record_type": "runtime_policy",
        "schema_version": "1",
        "policy_id": "gvisor-implementer-v1",
        "policy_sha": _POLICY_SHA,
        "role": "implementer",
        "isolation_backend": "gvisor-proxy",
        "image_ref": {"name": "registry.example/creator-engine/implementer", "sha": _IMAGE_SHA},
        "mount_manifest": [
            {"path": "/runtime/worktree", "mode": "rw", "write_justification": "allocated worktree"},
            {"path": "governance", "mode": "ro"},
        ],
        "egress_allowlist": [
            {"host": "model-provider.example", "protocol": "https", "assurance": ["l4"]},
        ],
        "secret_allowlist": ["model-provider-key"],
        "grant_extensible": False,
        "grant_authority": "controller",
    }


def approved(run_id: str = "run-1"):
    from creator_engine_validator.orchestrator import ApprovedPlan

    return ApprovedPlan(
        run_id=run_id, policy_sha=_POLICY_SHA, approved_by="operator", approval_ref="forge-issue#42"
    )


def _token_request(run_id: str = "run-1") -> TokenRequest:
    return TokenRequest(
        repo=_REPO,
        installation_id=42,
        run_id=run_id,
        policy_sha=_POLICY_SHA,
        permissions={"contents": "read", "pull_requests": "write"},
        secret_name="model-provider-key",
        requested_ttl_seconds=600,
    )


class _ChangeSetBackend(RunnerBackend):
    """Fake backend whose run() reports a deterministic change-set (the agent's work as DATA)."""

    backend_key = "changeset"

    def __init__(self) -> None:
        self._inner = LocalNoopBackend()

    def provision(self, request):
        return self._inner.provision(request)

    def run(self, handle, request):
        return RunResult(
            exit_code=0, stdout="noop", stderr="", started_ref=handle.ref, change_set=_RUN_CHANGE_SET
        )

    def collect(self, handle):
        return self._inner.collect(handle)

    def teardown(self, handle):
        return self._inner.teardown(handle)


def _mint_gh_runner(calls: list):
    """A fake App-level gh runner for mint (POST a token) / revoke (DELETE the token)."""

    def gh_runner(argv, input_text=None):
        calls.append(list(argv))
        return subprocess.CompletedProcess(
            args=list(argv),
            returncode=0,
            stdout=json.dumps({"token": _MINTED_SECRET, "expires_at": "2026-06-05T11:00:00Z"}),
            stderr="",
        )

    return gh_runner


def _spawn(captured: list):
    """A fake spawn for the authenticated change-opener runner; canned empty PR list."""

    def spawn(argv, input_text, env):
        captured.append({"argv": list(argv), "input_text": input_text, "env": dict(env)})
        return subprocess.CompletedProcess(list(argv), 0, stdout="[]", stderr="")

    return spawn


def _explode(monkeypatch):
    def explode(*a, **k):  # pragma: no cover - must never run
        raise AssertionError("the composition root must use the injected fakes, not a live runtime")

    monkeypatch.setattr(subprocess, "run", explode)
    monkeypatch.setattr(subprocess, "Popen", explode)
    monkeypatch.setattr(socket, "socket", explode)
    monkeypatch.setattr(Path, "write_text", explode)


def test_offline_drive_persists_pr_opened_chain(monkeypatch):
    _explode(monkeypatch)
    mint_calls: list = []
    spawn_calls: list = []
    written: list = []

    driver = make_run_driver(
        _REPO,
        Path("/evidence"),
        spawn=_spawn(spawn_calls),
        write=lambda p, t: written.append((p, t)),
        backend=_ChangeSetBackend(),
        gh_runner=_mint_gh_runner(mint_calls),
    )
    evidence = driver(valid_policy(), "run-1", ("echo", "hi"), approved(), _token_request("run-1"))

    # Full pipeline: the lifecycle opens at provision and ends at collect (a per-run
    # credential was minted, so secret issuance/revocation events are attested in between),
    # then a TERMINAL pr_opened outcome record; the whole chain verifies clean.
    records = list(evidence.records)
    outcome = records[-1]
    assert records[0]["lifecycle_phase"] == "provision"
    assert records[-2]["lifecycle_phase"] == "collect"  # last lifecycle step before the outcome
    phases = [r.get("lifecycle_phase") for r in records[:-1]]
    assert "run" in phases and "collect" in phases
    assert outcome["record_type"] == "runtime_run_outcome"
    assert outcome["outcome"] == "pr_opened"
    assert "lifecycle_phase" not in outcome
    assert outcome["change_set"]["branch"] == "ce/run-1"
    assert verify_chain(records) == []

    # Persistence: exactly one write of a schema-valid, verify_chain-clean chain doc.
    assert len(written) == 1
    path, text = written[0]
    assert path == Path("/evidence/run-1.runtime-evidence.yaml")
    doc = yaml.safe_load(text)
    assert doc["kind"] == "runtime-evidence-chain"
    assert doc["records"][-1]["outcome"] == "pr_opened"
    assert verify_chain(doc["records"]) == []
    assert validate_with_schema(doc, _SCHEMA, str(path), code="x", contract=_CONTRACT) == []

    # Minter->runner bridge: the SAME minted secret reached the child gh env of open_change ONLY.
    assert spawn_calls, "the change-opener's authenticated runner must have been invoked"
    assert all(c["env"]["GH_TOKEN"] == _MINTED_SECRET for c in spawn_calls)

    # Secret hygiene: the live value is in NO record / argv / input / parent env.
    blob = yaml.safe_dump(doc) + json.dumps([str(r) for r in evidence.records])
    assert _MINTED_SECRET not in blob
    for c in spawn_calls:
        assert all(_MINTED_SECRET not in a for a in c["argv"])
        assert c["input_text"] is None or _MINTED_SECRET not in c["input_text"]
    assert os.environ.get("GH_TOKEN") != _MINTED_SECRET

    # Revocation (G-3.7.0a): the DELETE installation/token authenticates AS the token — it routes
    # through the token-authed runner (spawn), NOT the App-level mint runner (mint_calls).
    delete_spawns = [c for c in spawn_calls if any("DELETE" in a for a in c["argv"])]
    assert delete_spawns, "revoke must route through the token-authed runner (spawn), not mint_calls"
    assert all(c["env"]["GH_TOKEN"] == _MINTED_SECRET for c in delete_spawns)
    assert not any("DELETE" in a for a in mint_calls), "DELETE must NOT go through the App-level runner"


class _BoomBackend(_ChangeSetBackend):
    def run(self, handle, request):
        raise RuntimeError("boom mid-run")


def _revoke_failing_spawn(captured: list):
    """A fake spawn that FAILS the revoke DELETE (rc=1) but serves the open-change read (rc=0)."""

    def spawn(argv, input_text, env):
        captured.append({"argv": list(argv), "input_text": input_text, "env": dict(env)})
        rc = 1 if any("DELETE" in a for a in argv) else 0
        return subprocess.CompletedProcess(list(argv), rc, stdout="[]", stderr="boom-revoke")

    return spawn


def test_revokes_even_when_the_run_raises(monkeypatch):
    _explode(monkeypatch)
    mint_calls: list = []
    spawn_calls: list = []

    driver = make_run_driver(
        _REPO,
        Path("/evidence"),
        spawn=_spawn(spawn_calls),
        write=lambda p, t: None,
        backend=_BoomBackend(),
        gh_runner=_mint_gh_runner(mint_calls),
    )
    with pytest.raises(RuntimeError, match="boom"):
        driver(valid_policy(), "run-1", ("echo", "hi"), approved(), _token_request("run-1"))
    # The credential is revoked even on a failed run (the finally fires) — token-authed (spawn),
    # not the App-level mint runner.
    delete_spawns = [c for c in spawn_calls if any("DELETE" in a for a in c["argv"])]
    assert delete_spawns, "revoke (token-authed) must fire even when the run raises"
    assert all(c["env"]["GH_TOKEN"] == _MINTED_SECRET for c in delete_spawns)
    assert not any("DELETE" in a for a in mint_calls)


def test_revoke_transport_failure_is_best_effort_and_alertable(monkeypatch, caplog):
    _explode(monkeypatch)
    mint_calls: list = []
    spawn_calls: list = []

    driver = make_run_driver(
        _REPO,
        Path("/evidence"),
        spawn=_revoke_failing_spawn(spawn_calls),
        write=lambda p, t: None,
        backend=_ChangeSetBackend(),
        gh_runner=_mint_gh_runner(mint_calls),
    )
    with caplog.at_level(logging.WARNING):
        evidence = driver(valid_policy(), "run-1", ("echo", "hi"), approved(), _token_request("run-1"))
    # Success path preserved: a failed revoke transport is swallowed (not raised), the drive
    # still returns its evidence and the run succeeds.
    assert evidence.records[-1]["outcome"] == "pr_opened"
    assert any("DELETE" in a for c in spawn_calls for a in c["argv"]), "revoke was attempted"
    # Alertable + value-free: a WARNING names the run/token_ref but NEVER the secret value.
    warnings = [r for r in caplog.records if r.levelno == logging.WARNING]
    assert any("revoke" in r.getMessage().lower() for r in warnings)
    assert all(_MINTED_SECRET not in r.getMessage() for r in caplog.records)


def test_revoke_failure_does_not_mask_the_run_exception(monkeypatch):
    _explode(monkeypatch)
    # Both the run AND the revoke transport fail; the ORIGINAL run exception must propagate,
    # never the revoke ForgeConfigError.
    driver = make_run_driver(
        _REPO,
        Path("/evidence"),
        spawn=_revoke_failing_spawn([]),
        write=lambda p, t: None,
        backend=_BoomBackend(),
        gh_runner=_mint_gh_runner([]),
    )
    with pytest.raises(RuntimeError, match="boom"):
        driver(valid_policy(), "run-1", ("echo", "hi"), approved(), _token_request("run-1"))
