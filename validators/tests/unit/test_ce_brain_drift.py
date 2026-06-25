from __future__ import annotations

import hashlib
from pathlib import Path

from creator_engine_validator import brain_probe
from creator_engine_validator import brain_runtime as rt
from creator_engine_validator.checks import ce_brain_drift


def _ledger_text(
    *,
    assertion_id: str = "brain-assertion-drift-0001",
    claim: dict | None = None,
    evidence_ref: str = "evidence.txt",
) -> str:
    captured: list[str] = []
    rt.assert_claim(
        assertion_id=assertion_id,
        claim=claim or {"subject": "artifact", "predicate": "exists", "object": "evidence"},
        scope="unit",
        evidence_ref=evidence_ref,
        records=[],
        write=lambda _path, text: captured.append(text),
    )
    return captured[-1]


def _write_ledger(tmp_path: Path, text: str) -> Path:
    path = tmp_path / ".ce" / "state" / "brain" / "assertions.yaml"
    path.parent.mkdir(parents=True)
    path.write_text(text, encoding="utf-8")
    return path


def _probe_result(verdict: brain_probe.Verdict) -> brain_probe.ProbeResult:
    return brain_probe.ProbeResult("unit_probe", verdict, {"source": "unit"})


def test_matching_probe_assertion_passes(tmp_path: Path):
    path = _write_ledger(
        tmp_path,
        _ledger_text(
            claim={
                "subject": "capability",
                "predicate": "probe-verdict",
                "object": "unit_probe",
                "verdict": "present",
            },
            evidence_ref="probe:unit_probe",
        ),
    )

    result = ce_brain_drift.validate_file(
        path,
        context=ce_brain_drift.DriftContext(
            repo_root=tmp_path,
            probe_context=brain_probe.ProbeContext(probes={"unit_probe": lambda _context: _probe_result("present")}),
        ),
    )

    assert result == []


def test_diverged_probe_assertion_reports_structured_drift(tmp_path: Path):
    path = _write_ledger(
        tmp_path,
        _ledger_text(
            claim={
                "subject": "capability",
                "predicate": "probe-verdict",
                "object": "unit_probe",
                "verdict": "present",
            },
            evidence_ref="probe:unit_probe",
        ),
    )

    errors = ce_brain_drift.validate_file(
        path,
        context=ce_brain_drift.DriftContext(
            repo_root=tmp_path,
            probe_context=brain_probe.ProbeContext(probes={"unit_probe": lambda _context: _probe_result("absent")}),
        ),
    )

    assert [error.code for error in errors] == [ce_brain_drift.CODE_DRIFT]
    message = errors[0].message
    assert "brain-assertion-drift-0001" in message
    assert "claimed verdict='present'" in message
    assert "observed verdict='absent'" in message
    assert errors[0].to_dict()["assertion_id"] == "brain-assertion-drift-0001"
    assert errors[0].to_dict()["claimed"] == "verdict=present"
    assert errors[0].to_dict()["observed"] == "verdict=absent"
    assert errors[0].to_dict()["evidence_ref"] == "probe:unit_probe"


def test_unknown_probe_observation_fails_closed(tmp_path: Path):
    path = _write_ledger(
        tmp_path,
        _ledger_text(
            claim={
                "subject": "capability",
                "predicate": "probe-verdict",
                "object": "unit_probe",
                "verdict": "present",
            },
            evidence_ref="probe:unit_probe",
        ),
    )

    errors = ce_brain_drift.validate_file(
        path,
        context=ce_brain_drift.DriftContext(
            repo_root=tmp_path,
            probe_context=brain_probe.ProbeContext(probes={"unit_probe": lambda _context: _probe_result("unknown")}),
        ),
    )

    assert [error.code for error in errors] == [ce_brain_drift.CODE_UNVERIFIABLE]
    assert "claimed verdict='present'" in errors[0].message
    assert "observed verdict='unknown'" in errors[0].message


def test_resolvable_artifact_without_hash_or_value_claim_fails_closed(tmp_path: Path):
    evidence = tmp_path / "evidence.txt"
    evidence.write_text("current\n", encoding="utf-8")
    path = _write_ledger(tmp_path, _ledger_text(evidence_ref="evidence.txt#section"))

    errors = ce_brain_drift.validate_file(
        path,
        context=ce_brain_drift.DriftContext(
            repo_root=tmp_path,
            read_bytes=lambda p: p.read_bytes(),
        ),
    )

    assert [error.code for error in errors] == [ce_brain_drift.CODE_UNVERIFIABLE]
    assert "evidence file existence alone is not verification" in errors[0].message


def test_matching_artifact_hash_passes(tmp_path: Path):
    evidence = tmp_path / "evidence.txt"
    evidence.write_text("current\n", encoding="utf-8")
    observed = hashlib.sha256(b"current\n").hexdigest()
    path = _write_ledger(
        tmp_path,
        _ledger_text(
            claim={
                "subject": "artifact",
                "predicate": "sha256",
                "object": "evidence",
                "sha256": observed,
            },
            evidence_ref="evidence.txt",
        ),
    )

    errors = ce_brain_drift.validate_file(path, context=ce_brain_drift.DriftContext(repo_root=tmp_path))

    assert errors == []


def test_malformed_artifact_hash_claim_fails_closed(tmp_path: Path):
    evidence = tmp_path / "evidence.txt"
    evidence.write_text("current\n", encoding="utf-8")
    path = _write_ledger(
        tmp_path,
        _ledger_text(
            claim={
                "subject": "artifact",
                "predicate": "sha256",
                "object": "evidence",
                "sha256": "not-a-sha",
            },
            evidence_ref="evidence.txt",
        ),
    )

    errors = ce_brain_drift.validate_file(path, context=ce_brain_drift.DriftContext(repo_root=tmp_path))

    assert [error.code for error in errors] == [ce_brain_drift.CODE_UNVERIFIABLE]
    assert "claim.sha256 must be a sha256 hex string" in errors[0].message


def test_unsupported_artifact_hash_claim_key_fails_closed(tmp_path: Path):
    evidence = tmp_path / "evidence.txt"
    evidence.write_text("current\n", encoding="utf-8")
    path = _write_ledger(
        tmp_path,
        _ledger_text(
            claim={
                "subject": "artifact",
                "predicate": "sha256",
                "object": "evidence",
                "hash": hashlib.sha256(b"current\n").hexdigest(),
            },
            evidence_ref="evidence.txt",
        ),
    )

    errors = ce_brain_drift.validate_file(path, context=ce_brain_drift.DriftContext(repo_root=tmp_path))

    assert [error.code for error in errors] == [ce_brain_drift.CODE_UNVERIFIABLE]
    assert "claim.hash is not a supported drift comparison key" in errors[0].message


def test_malformed_artifact_value_claim_fails_closed(tmp_path: Path):
    evidence = tmp_path / "evidence.txt"
    evidence.write_text("current\n", encoding="utf-8")
    path = _write_ledger(
        tmp_path,
        _ledger_text(
            claim={
                "subject": "artifact",
                "predicate": "value",
                "object": "evidence",
                "value": ["not", "a", "string"],
            },
            evidence_ref="evidence.txt",
        ),
    )

    errors = ce_brain_drift.validate_file(path, context=ce_brain_drift.DriftContext(repo_root=tmp_path))

    assert [error.code for error in errors] == [ce_brain_drift.CODE_UNVERIFIABLE]
    assert "claim.value must be a string value" in errors[0].message


def test_artifact_hash_drift_reports_claimed_and_observed(tmp_path: Path):
    evidence = tmp_path / "evidence.txt"
    evidence.write_text("current\n", encoding="utf-8")
    path = _write_ledger(
        tmp_path,
        _ledger_text(
            claim={
                "subject": "artifact",
                "predicate": "sha256",
                "object": "evidence",
                "sha256": "a" * 64,
            },
            evidence_ref="evidence.txt",
        ),
    )

    errors = ce_brain_drift.validate_file(
        path,
        context=ce_brain_drift.DriftContext(repo_root=tmp_path),
    )

    observed = hashlib.sha256(b"current\n").hexdigest()
    assert [error.code for error in errors] == [ce_brain_drift.CODE_DRIFT]
    assert "claimed sha256=" + ("a" * 64) in errors[0].message
    assert f"observed sha256={observed}" in errors[0].message
    assert errors[0].to_dict()["assertion_id"] == "brain-assertion-drift-0001"
    assert errors[0].to_dict()["claimed"] == "sha256=" + ("a" * 64)
    assert errors[0].to_dict()["observed"] == f"sha256={observed}"
    assert errors[0].to_dict()["evidence_ref"] == "evidence.txt"


def test_artifact_value_drift_reports_drift(tmp_path: Path):
    evidence = tmp_path / "evidence.txt"
    evidence.write_text("observed", encoding="utf-8")
    path = _write_ledger(
        tmp_path,
        _ledger_text(
            claim={
                "subject": "artifact",
                "predicate": "value",
                "object": "evidence",
                "value": "claimed",
            },
            evidence_ref="evidence.txt",
        ),
    )

    errors = ce_brain_drift.validate_file(path, context=ce_brain_drift.DriftContext(repo_root=tmp_path))

    assert [error.code for error in errors] == [ce_brain_drift.CODE_DRIFT]
    assert "claimed value='claimed'" in errors[0].message
    assert "observed value='observed'" in errors[0].message


def test_unverifiable_artifact_fails_closed(tmp_path: Path):
    path = _write_ledger(tmp_path, _ledger_text(evidence_ref="missing.txt"))

    errors = ce_brain_drift.validate_file(path, context=ce_brain_drift.DriftContext(repo_root=tmp_path))

    assert [error.code for error in errors] == [ce_brain_drift.CODE_UNVERIFIABLE]
    assert "brain-assertion-drift-0001" in errors[0].message
    assert "not a resolvable local file" in errors[0].message


def test_drift_output_is_deterministic_with_injected_evidence(tmp_path: Path):
    evidence = tmp_path / "evidence.txt"
    evidence.write_text("current\n", encoding="utf-8")
    path = _write_ledger(
        tmp_path,
        _ledger_text(
            claim={
                "subject": "artifact",
                "predicate": "sha256",
                "object": "evidence",
                "sha256": "a" * 64,
            },
            evidence_ref="evidence.txt",
        ),
    )
    context = ce_brain_drift.DriftContext(
        repo_root=tmp_path,
        read_bytes=lambda _path: b"current\n",
    )

    first = ce_brain_drift.validate_file(path, context=context)
    second = ce_brain_drift.validate_file(path, context=context)

    assert [error.to_dict() for error in first] == [error.to_dict() for error in second]


def test_run_registers_drift_check_and_discovers_brain_ledger(tmp_path: Path):
    _write_ledger(tmp_path, _ledger_text(evidence_ref="missing.txt"))

    result = ce_brain_drift.run([tmp_path])

    assert result.name == ce_brain_drift.CHECK_NAME
    assert not result.ok
    assert any(error.code == ce_brain_drift.CODE_UNVERIFIABLE for error in result.errors)


def test_verify_state_root_resolves_artifacts_from_repo_root(tmp_path: Path, monkeypatch):
    repo = tmp_path / "repo"
    repo.mkdir()
    evidence = repo / "evidence.txt"
    evidence.write_text("current\n", encoding="utf-8")
    observed = hashlib.sha256(b"current\n").hexdigest()
    _write_ledger(
        repo,
        _ledger_text(
            claim={
                "subject": "artifact",
                "predicate": "sha256",
                "object": "evidence",
                "sha256": observed,
            },
            evidence_ref="evidence.txt",
        ),
    )
    away = tmp_path / "away"
    away.mkdir()
    monkeypatch.chdir(away)

    drift = ce_brain_drift.verify_state_root(repo / ".ce" / "state")

    assert drift.ok
    assert drift.record_count == 1
    assert drift.active_count == 1
    assert drift.findings == ()


def test_missing_state_root_is_zero_active_assertions_for_cli_and_registered_check(tmp_path: Path):
    state_root = tmp_path / ".ce" / "state"

    drift = ce_brain_drift.verify_state_root(state_root)
    registered = ce_brain_drift.run([state_root])

    assert drift.ok
    assert drift.record_count == 0
    assert drift.active_count == 0
    assert drift.findings == ()
    assert registered.ok
    assert registered.errors == ()
