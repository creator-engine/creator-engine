"""Daemon-free offline replay of the v3.5-A.2b-ii OpenShell live-run bundle.

These tests re-verify — with NO live gateway, NO subprocess, and NO socket — the
recorded evidence bundle a REAL governed run produced through
``AuditOverlayBackend(OpenShellBackend(SubprocessSandboxClient()))`` against a
connected OpenShell v0.0.57 gateway (recorded by ``examples/openshell_live_run.py``;
the curated pitch copy lives out-of-repo). The bundle is the offline ground truth
this CI test re-checks, so the cryptographic governance proof keeps passing without
any daemon.

The four properties asserted (mirrors the A.2b-ii mandate):

* **(a)** the attested hash-chained spine verifies clean — ``verify_chain(chain)``
  returns the EMPTY list (an empty list is PASS; a non-empty list is a tamper /
  integrity finding);
* **(b)** the recorded OCSF text maps correctly through the backend's
  ``parse_ocsf_textlog`` -> ``_map_ocsf_record`` / ``OpenShellBackend.collect`` path
  and surfaces BOTH a ``disposition: ALLOWED`` and a ``disposition: DENIED``;
* **(c)** the lifecycle order ``provision -> run -> collect -> teardown`` is
  attested, in order, in the chain;
* **(d)** the DENIED counterfactual (``example.com``) is present with its
  deny ``reason``.

Pure replay: load JSON, assert. It spawns no subprocess and opens no socket
(mirrors ``test_openshell_backend.py::test_no_network_during_lifecycle``).
"""

import json
import socket
import subprocess
from pathlib import Path

import pytest

from creator_engine_validator.runner import (
    CollectedEvidence,
    FakeSandboxClient,
    OpenShellBackend,
    ProvisionedHandle,
)
from creator_engine_validator.runner.openshell_backend import (
    _map_ocsf_record,
    parse_ocsf_textlog,
)
from creator_engine_validator.runtime_evidence_spine import (
    LIFECYCLE_PHASES,
    is_policy_sha,
    verify_chain,
)

#: The recorded live-run bundle (the A.2b-ii in-repo fixture).
_BUNDLE_PATH = Path(__file__).parent / "fixtures" / "openshell_live_bundle.json"
_BUNDLE = json.loads(_BUNDLE_PATH.read_text(encoding="utf-8"))


@pytest.fixture
def no_daemon(monkeypatch):
    """Make ANY socket or subprocess use explode — this replay must be fully offline."""

    def explode(*args, **kwargs):  # pragma: no cover - must never run
        raise AssertionError("the offline replay must not open a socket or spawn a subprocess")

    monkeypatch.setattr(socket, "socket", explode)
    monkeypatch.setattr(socket, "create_connection", explode)
    monkeypatch.setattr(subprocess, "run", explode)
    monkeypatch.setattr(subprocess, "Popen", explode)
    return monkeypatch


# ---------------------------------------------------------------------------
# Bundle shape / honesty
# ---------------------------------------------------------------------------
def test_bundle_is_a_real_live_recording():
    assert _BUNDLE["kind"] == "openshell-live-run-bundle"
    # Honesty marker: this bundle attests a REAL live run, not a labeled replay.
    assert _BUNDLE["recorded_mode"] == "live"
    assert _BUNDLE["openshell_version"] == "v0.0.57"
    # The image the live run provisioned is digest-pinned.
    assert "@sha256:" in _BUNDLE["image_ref"]


# ---------------------------------------------------------------------------
# (a) the hash-chained spine verifies clean — the cryptographic proof
# ---------------------------------------------------------------------------
def test_spine_chain_verifies_clean(no_daemon):
    chain = _BUNDLE["spine_chain"]
    # Empty list == PASS (verify_chain returns ChainFinding problems, never raises).
    assert verify_chain(chain) == []
    # Every record is bound to its runtime-policy (a 64-hex policy_sha).
    assert all(is_policy_sha(record["policy_sha"]) for record in chain)
    # One policy governs the whole run.
    assert len({record["policy_sha"] for record in chain}) == 1


def test_spine_chain_detects_tampering(no_daemon):
    # Sanity: mutating any attested field breaks the content address (the chain is
    # genuinely tamper-evident, not vacuously passing).
    tampered = [dict(record) for record in _BUNDLE["spine_chain"]]
    tampered[1] = dict(tampered[1])
    tampered[1]["classification"] = "denied"
    findings = verify_chain(tampered)
    assert findings != []
    assert any(f.kind == "content_address" and f.index == 1 for f in findings)


# ---------------------------------------------------------------------------
# (c) the lifecycle order provision -> run -> collect -> teardown is attested
# ---------------------------------------------------------------------------
def test_lifecycle_order_attested(no_daemon):
    phases = [record["lifecycle_phase"] for record in _BUNDLE["spine_chain"]]
    # First provision, last teardown; collect immediately precedes teardown.
    assert phases[0] == "provision"
    assert phases[-1] == "teardown"
    assert phases[-2] == "collect"
    # The de-duplicated order matches the canonical lifecycle (>=1 run between).
    ordered_unique: list[str] = []
    for phase in phases:
        if phase not in ordered_unique:
            ordered_unique.append(phase)
    assert tuple(ordered_unique) == LIFECYCLE_PHASES  # provision, run, collect, teardown
    assert phases.count("run") >= 1
    # The sequence numbers are contiguous from 0 (also covered by verify_chain).
    assert [record["sequence"] for record in _BUNDLE["spine_chain"]] == list(range(len(phases)))


# ---------------------------------------------------------------------------
# (b) the OCSF text maps through the backend collect path -> ALLOWED + DENIED
# ---------------------------------------------------------------------------
def test_ocsf_maps_through_backend_collect_path(no_daemon):
    # Re-parse the recorded OCSF text and drive it through the REAL backend collect
    # path (FakeSandboxClient -> OpenShellBackend.collect -> _map_ocsf_record).
    parsed = parse_ocsf_textlog(_BUNDLE["ocsf_textlog"])
    backend = OpenShellBackend(client=FakeSandboxClient(ocsf_records=parsed))
    handle = ProvisionedHandle(
        backend_key="openshell", run_id="replay", policy_sha="a" * 64, ref="openshell:replay"
    )
    evidence = backend.collect(handle)
    assert isinstance(evidence, CollectedEvidence)

    dispositions = [r["disposition"] for r in evidence.records if "disposition" in r]
    assert "ALLOWED" in dispositions
    assert "DENIED" in dispositions

    # The bundle's stored ocsf_records ARE exactly what the backend collect produces.
    assert list(evidence.records) == _BUNDLE["ocsf_records"]
    # And they agree with the bundle's own disposition summary.
    assert dispositions == _BUNDLE["ocsf_dispositions"]


def test_ocsf_records_map_via_map_ocsf_record(no_daemon):
    # The same mapping through the lower-level _map_ocsf_record entry point.
    remapped = [_map_ocsf_record(r) for r in parse_ocsf_textlog(_BUNDLE["ocsf_textlog"])]
    assert remapped == _BUNDLE["ocsf_records"]
    dispositions = [r["disposition"] for r in remapped if "disposition" in r]
    assert dispositions.count("ALLOWED") >= 1
    assert dispositions.count("DENIED") >= 1


# ---------------------------------------------------------------------------
# (d) the DENIED counterfactual is present with its deny reason
# ---------------------------------------------------------------------------
def test_denied_counterfactual_present_with_reason(no_daemon):
    denied = [r for r in _BUNDLE["ocsf_records"] if r.get("disposition") == "DENIED"]
    assert len(denied) >= 1
    record = denied[0]
    assert record["target"] == "example.com:443"
    assert record["reason"] == "endpoint example.com:443 is not allowed by any policy"
    # The full original log line is preserved under raw for evidence-spine fidelity.
    assert record["raw"]["disposition"] == "DENIED"
    assert "example.com:443" in record["raw"]["raw"]


def test_allowed_decision_carries_the_ce_translated_policy_name(no_daemon):
    # The ALLOWED egress decision cites the CE-translated network-rule name — proof
    # the CE runtime-policy flowed end-to-end into OpenShell's OPA engine.
    allowed = [
        r
        for r in _BUNDLE["ocsf_records"]
        if r.get("disposition") == "ALLOWED" and r.get("target") == "api.github.com:443"
    ]
    assert allowed, "expected an ALLOWED api.github.com:443 egress decision"
    assert allowed[0]["policy"] == "api_github_com_443"
    assert allowed[0]["engine"] == "opa"
