"""Unit tests for the v3 G-3.5 evidence persistence sink.

The sink serializes a run's ``CollectedEvidence`` (the ``AuditOverlayBackend``
hash-chain) into a durable ``runtime-evidence-chain`` file matching
``schemas/runtime-evidence.schema.yaml`` — persisting iff the chain verifies
AND validates, else refusing value-free. These tests perform ZERO live
filesystem write (a fake ``write`` is the sole transport), no network, no
subprocess. The producer chain is built with the real overlay over the inert
``LocalNoopBackend`` (mirroring ``test_audit_overlay.py``).
"""

import socket
import subprocess
from pathlib import Path

import yaml

from creator_engine_validator.checks import registered_checks
from creator_engine_validator.evidence_sink import (
    EvidencePersistRefused,
    PersistedEvidence,
    file_evidence_sink,
)
from creator_engine_validator.runner import available_backends
from creator_engine_validator.runner.audit_overlay import (
    AuditOverlayBackend,
    CounterClock,
    LifecycleEvent,
)
from creator_engine_validator.runner.backend import (
    CollectedEvidence,
    ProvisionRequest,
    RunRequest,
)
from creator_engine_validator.runner.noop_backend import LocalNoopBackend
from creator_engine_validator.runtime_evidence_spine import (
    CHAIN_KIND,
    CONTENT_HASH_FIELD,
    verify_chain,
)
from creator_engine_validator.schema import validate_with_schema

_SCHEMA = "schemas/runtime-evidence.schema.yaml"
_CONTRACT = "docs/contracts/runtime-evidence.md"
_POLICY_SHA = "a" * 64
_IMAGE_SHA = "sha256:" + "b" * 64


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
        "mount_manifest": [{"path": "governance", "mode": "ro"}],
        "egress_allowlist": [],
        "secret_allowlist": ["model-provider-key"],
        "grant_extensible": False,
        "grant_authority": "controller",
    }


def _collected(run_id: str = "run-1") -> CollectedEvidence:
    """A real, schema-valid provision/run/collect chain via the overlay."""
    overlay = AuditOverlayBackend(LocalNoopBackend(), clock=CounterClock())
    handle = overlay.provision(ProvisionRequest(runtime_policy=valid_policy(), run_id=run_id))
    overlay.run(handle, RunRequest(command=("echo", "hi")))
    evidence = overlay.collect(handle)
    overlay.teardown(handle)
    return evidence


def _change_opened(run_id: str = "run-1") -> CollectedEvidence:
    """A real chain whose terminal record is the G-3.1 ``change-opened`` phase.

    The chain is hash-intact (``verify_chain == []``) but the ``change-opened``
    ``lifecycle_phase`` is NOT in the schema enum, so the sink must refuse it.
    """
    overlay = AuditOverlayBackend(LocalNoopBackend(), clock=CounterClock())
    handle = overlay.provision(ProvisionRequest(runtime_policy=valid_policy(), run_id=run_id))
    overlay.run(handle, RunRequest(command=("echo", "hi")))
    evidence = overlay.collect(handle)
    opened = overlay.observe(handle, LifecycleEvent(phase="change-opened"))
    return CollectedEvidence(
        handle_ref=evidence.handle_ref,
        records=tuple(evidence.records) + (opened,),
        note=evidence.note,
    )


def _capturing_sink(root: str = "/evidence"):
    captured: list[tuple[Path, str]] = []

    def fake_write(path: Path, text: str) -> None:
        captured.append((path, text))

    return file_evidence_sink(Path(root), write=fake_write), captured


# ---------------------------------------------------------------------------
# Happy path + fidelity
# ---------------------------------------------------------------------------
def test_happy_path_writes_schema_valid_chain_and_returns_receipt():
    sink, captured = _capturing_sink()
    evidence = _collected("run-1")
    receipt = sink(evidence)

    assert len(captured) == 1
    path, text = captured[0]
    assert path == Path("/evidence/run-1.runtime-evidence.yaml")
    doc = yaml.safe_load(text)
    assert doc["kind"] == CHAIN_KIND
    assert doc["record_type"] == "runtime_evidence_chain"
    assert doc["schema_version"] == "1"
    assert [r["lifecycle_phase"] for r in doc["records"]] == ["provision", "run", "collect"]

    assert isinstance(receipt, PersistedEvidence)
    assert receipt.path == path
    assert receipt.run_id == "run-1"
    assert receipt.record_count == 3
    assert receipt.tip_content_hash == evidence.records[-1][CONTENT_HASH_FIELD]


def test_round_trip_verifies_and_validates_clean():
    sink, captured = _capturing_sink()
    evidence = _collected("run-7")
    sink(evidence)
    _, text = captured[0]
    doc = yaml.safe_load(text)

    # chain integrity round-trips
    assert verify_chain(doc["records"]) == []
    # schema validity round-trips (the same contract ce_runtime_evidence enforces)
    assert validate_with_schema(doc, _SCHEMA, "round-trip", code="x", contract=_CONTRACT) == []
    # byte-faithful: the producer's content_hash values are preserved verbatim
    assert [r[CONTENT_HASH_FIELD] for r in doc["records"]] == [
        r[CONTENT_HASH_FIELD] for r in evidence.records
    ]


def test_serialization_is_deterministic():
    s1, c1 = _capturing_sink()
    s2, c2 = _capturing_sink()
    evidence = _collected("run-1")
    s1(evidence)
    s2(evidence)
    assert c1[0][1] == c2[0][1]


# ---------------------------------------------------------------------------
# Refusals (nothing written)
# ---------------------------------------------------------------------------
def test_refuse_empty_records():
    sink, captured = _capturing_sink()
    empty = CollectedEvidence(handle_ref="h", records=(), note="")
    try:
        sink(empty)
        assert False, "expected EvidencePersistRefused"
    except EvidencePersistRefused:
        pass
    assert captured == []


def test_refuse_nonuniform_run_id():
    sink, captured = _capturing_sink()
    evidence = _collected("run-1")
    records = [dict(r) for r in evidence.records]
    records[1]["run_id"] = "run-OTHER"
    bad = CollectedEvidence(handle_ref=evidence.handle_ref, records=tuple(records), note=evidence.note)
    try:
        sink(bad)
        assert False, "expected EvidencePersistRefused"
    except EvidencePersistRefused:
        pass
    assert captured == []


def test_refuse_tampered_content_hash():
    sink, captured = _capturing_sink()
    evidence = _collected("run-1")
    records = [dict(r) for r in evidence.records]
    records[0][CONTENT_HASH_FIELD] = "f" * 64  # well-formed hex, wrong value
    bad = CollectedEvidence(handle_ref=evidence.handle_ref, records=tuple(records), note=evidence.note)
    assert verify_chain(list(bad.records)) != []  # the integrity gate catches it
    try:
        sink(bad)
        assert False, "expected EvidencePersistRefused"
    except EvidencePersistRefused:
        pass
    assert captured == []


def test_refuse_change_opened_phase_not_in_schema_enum():
    """The §1 run-outcome gap, proven as an intentional, tested refusal."""
    sink, captured = _capturing_sink()
    bad = _change_opened("run-1")
    assert verify_chain(list(bad.records)) == []  # hash-intact; only the schema vocabulary rejects it
    try:
        sink(bad)
        assert False, "expected EvidencePersistRefused"
    except EvidencePersistRefused:
        pass
    assert captured == []


def test_refusal_message_is_value_free():
    sink, _ = _capturing_sink()
    evidence = _collected("run-1")
    records = [dict(r) for r in evidence.records]
    records[0][CONTENT_HASH_FIELD] = "f" * 64
    bad = CollectedEvidence(handle_ref=evidence.handle_ref, records=tuple(records), note=evidence.note)
    try:
        sink(bad)
        assert False, "expected EvidencePersistRefused"
    except EvidencePersistRefused as exc:
        message = str(exc)
        assert _POLICY_SHA not in message
        assert "f" * 64 not in message


# ---------------------------------------------------------------------------
# Zero-live transport + purity
# ---------------------------------------------------------------------------
def test_zero_live_filesystem_write(monkeypatch):
    def explode(*args, **kwargs):  # pragma: no cover - must never run
        raise AssertionError("the sink must not touch the live filesystem in CI")

    monkeypatch.setattr(Path, "write_text", explode)
    monkeypatch.setattr(subprocess, "run", explode)
    monkeypatch.setattr(socket, "socket", explode)

    sink, captured = _capturing_sink()
    sink(_collected("run-1"))
    assert len(captured) == 1  # the injected fake write is the sole transport


def test_purity_unchanged():
    assert len(registered_checks()) == 43
    assert available_backends() == ("gvisor-proxy", "local-noop")
