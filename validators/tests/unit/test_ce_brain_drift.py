from __future__ import annotations

import hashlib
from pathlib import Path

import pytest
import yaml

from creator_engine_validator import brain_probe
from creator_engine_validator import brain_runtime as rt
from creator_engine_validator.checks import ce_brain_drift
from creator_engine_validator.runtime_evidence_spine import CONTENT_HASH_FIELD, canonical_content_hash


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


def _write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _write_authoritative_ledger(repo_root: Path, text: str) -> Path:
    path = repo_root / ".ce" / "brain" / "assertions.yaml"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def _write_authoritative_validate_workflow_ledger(repo: Path) -> Path:
    captured: list[tuple[Path, str]] = []
    rt.assert_claim(
        assertion_id="brain-assertion-validate-workflow-drift-gate",
        statement="validate workflow merge_group trigger includes checks_requested",
        assertion_type="capability",
        scope={"artifact": ".github/workflows/validate.yml", "gate": "drift-ci"},
        claim={
            "subject": "workflow",
            "predicate": "allows-merge-queue-validation",
            "object": "validate",
            "projection": {
                "type": "yaml-path",
                "path": ["on", "merge_group", "types"],
                "normalize": "string_set_contains",
                "expected": ["checks_requested"],
            },
        },
        evidence_ref=".github/workflows/validate.yml",
        verification_method={"type": "static", "evidence_ref": ".github/workflows/validate.yml"},
        state_root=repo / ".ce",
        records=[],
        write=lambda path, text: captured.append((path, text)),
    )
    path, text = captured[-1]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def _ledger_text_with_verification_method(
    *,
    verification_method,
    assertion_id: str = "brain-assertion-drift-0001",
    claim: dict | None = None,
    evidence_ref: str = "evidence.txt",
) -> str:
    data = yaml.safe_load(
        _ledger_text(assertion_id=assertion_id, claim=claim, evidence_ref=evidence_ref)
    )
    record = data["records"][0]
    record["verification_method"] = verification_method
    record[CONTENT_HASH_FIELD] = canonical_content_hash(record)
    return rt.serialize_ledger(data["records"])


def _probe_result(verdict: brain_probe.Verdict) -> brain_probe.ProbeResult:
    return brain_probe.ProbeResult("unit_probe", verdict, {"source": "unit"})


def _harness_fan_out_claim(verdict: brain_probe.Verdict = "present") -> dict:
    return {
        "subject": "capability",
        "predicate": "probe-verdict",
        "object": "harness_fan_out",
        "verdict": verdict,
    }


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


@pytest.mark.parametrize(
    "verification_method",
    [
        "manual-attested",
        {"type": "manual-attested", "evidence_ref": "missing.txt"},
    ],
)
def test_manual_attested_verification_method_skips_artifact_resolution(tmp_path: Path, verification_method):
    path = _write_ledger(
        tmp_path,
        _ledger_text_with_verification_method(
            verification_method=verification_method,
            evidence_ref="missing.txt",
        ),
    )

    errors = ce_brain_drift.validate_file(path, context=ce_brain_drift.DriftContext(repo_root=tmp_path))

    assert errors == []


@pytest.mark.parametrize(
    "verification_method",
    [
        "static",
        {"type": "static", "evidence_ref": "probe:harness_fan_out"},
    ],
)
def test_explicit_static_verification_method_uses_artifact_even_when_evidence_ref_looks_like_probe(
    tmp_path: Path, verification_method
):
    evidence = tmp_path / "probe:harness_fan_out"
    evidence.write_text("static evidence", encoding="utf-8")
    path = _write_ledger(
        tmp_path,
        _ledger_text_with_verification_method(
            verification_method=verification_method,
            claim={
                "subject": "artifact",
                "predicate": "value",
                "object": "probe-like evidence",
                "value": "static evidence",
            },
            evidence_ref="probe:harness_fan_out",
        ),
    )

    errors = ce_brain_drift.validate_file(
        path,
        context=ce_brain_drift.DriftContext(
            repo_root=tmp_path,
            probe_context=brain_probe.ProbeContext(env={"CE_HARNESS_FAN_OUT": "0"}),
        ),
    )

    assert errors == []


def test_real_harness_fan_out_probe_assertion_passes_with_injected_env(tmp_path: Path):
    path = _write_ledger(
        tmp_path,
        _ledger_text(
            assertion_id="brain-assertion-drift-harness-fanout",
            claim=_harness_fan_out_claim("present"),
            evidence_ref="probe:harness_fan_out",
        ),
    )

    errors = ce_brain_drift.validate_file(
        path,
        context=ce_brain_drift.DriftContext(
            repo_root=tmp_path,
            probe_context=brain_probe.ProbeContext(env={"CE_HARNESS_FAN_OUT": "1"}),
        ),
    )

    assert errors == []


def test_real_harness_fan_out_probe_assertion_reports_planted_stale_verdict(tmp_path: Path):
    path = _write_ledger(
        tmp_path,
        _ledger_text(
            assertion_id="brain-assertion-drift-harness-fanout",
            claim=_harness_fan_out_claim("absent"),
            evidence_ref="probe:harness_fan_out",
        ),
    )

    errors = ce_brain_drift.validate_file(
        path,
        context=ce_brain_drift.DriftContext(
            repo_root=tmp_path,
            probe_context=brain_probe.ProbeContext(env={"CE_HARNESS_FAN_OUT": "1"}),
        ),
    )

    assert [error.code for error in errors] == [ce_brain_drift.CODE_DRIFT]
    assert "probe 'harness_fan_out' drifted" in errors[0].message
    assert "claimed verdict='absent'" in errors[0].message
    assert "observed verdict='present'" in errors[0].message


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


def test_workflow_raw_hash_anchor_fails_closed_as_unstable(tmp_path: Path):
    workflow = tmp_path / ".github" / "workflows" / "validate.yml"
    workflow.parent.mkdir(parents=True)
    workflow.write_text(
        "on:\n"
        "  merge_group:\n"
        "    types: [checks_requested]\n"
        "jobs:\n"
        "  validate:\n"
        "    runs-on: ubuntu-latest\n"
        "    steps: []\n",
        encoding="utf-8",
    )
    path = _write_ledger(
        tmp_path,
        _ledger_text(
            claim={
                "subject": "workflow",
                "predicate": "has-full-file-hash",
                "object": "validate",
                "sha256": hashlib.sha256(workflow.read_bytes()).hexdigest(),
            },
            evidence_ref=".github/workflows/validate.yml",
        ),
    )

    errors = ce_brain_drift.validate_file(path, context=ce_brain_drift.DriftContext(repo_root=tmp_path))

    assert [error.code for error in errors] == [ce_brain_drift.CODE_UNVERIFIABLE]
    assert "must not use full-artifact hash/value anchors" in errors[0].message
    assert "normalized projection" in errors[0].message


def test_workflow_normalized_projection_accepts_unrelated_variation(tmp_path: Path):
    workflow = tmp_path / ".github" / "workflows" / "validate.yml"
    workflow.parent.mkdir(parents=True)
    workflow.write_text(
        "name: renamed validation workflow\n"
        "on:\n"
        "  merge_group:\n"
        "    types: [checks_requested, checks_requested]\n"
        "  pull_request:\n"
        "jobs:\n"
        "  extra-docs-check:\n"
        "    runs-on: ubuntu-latest\n"
        "    steps: []\n"
        "  validate:\n"
        "    runs-on: ubuntu-latest\n"
        "    steps: []\n",
        encoding="utf-8",
    )
    path = _write_ledger(
        tmp_path,
        _ledger_text(
            claim={
                "subject": "workflow",
                "predicate": "allows-merge-queue",
                "object": "validate",
                "projection": {
                    "type": "yaml-path",
                    "path": ["on", "merge_group", "types"],
                    "normalize": "string_set_contains",
                    "expected": ["checks_requested"],
                },
            },
            evidence_ref=".github/workflows/validate.yml",
        ),
    )

    errors = ce_brain_drift.validate_file(path, context=ce_brain_drift.DriftContext(repo_root=tmp_path))

    assert errors == []


def test_workflow_normalized_projection_reports_semantic_drift(tmp_path: Path):
    workflow = tmp_path / ".github" / "workflows" / "validate.yml"
    workflow.parent.mkdir(parents=True)
    workflow.write_text(
        "on:\n"
        "  merge_group:\n"
        "    types: [other_event]\n",
        encoding="utf-8",
    )
    path = _write_ledger(
        tmp_path,
        _ledger_text(
            claim={
                "subject": "workflow",
                "predicate": "allows-merge-queue",
                "object": "validate",
                "projection": {
                    "type": "yaml-path",
                    "path": "on.merge_group.types",
                    "normalize": "string_set_contains",
                    "expected": ["checks_requested"],
                },
            },
            evidence_ref=".github/workflows/validate.yml",
        ),
    )

    errors = ce_brain_drift.validate_file(path, context=ce_brain_drift.DriftContext(repo_root=tmp_path))

    assert [error.code for error in errors] == [ce_brain_drift.CODE_DRIFT]
    assert "artifact projection drifted" in errors[0].message
    assert errors[0].to_dict()["claimed"] == 'contains=["checks_requested"]'
    assert errors[0].to_dict()["observed"] == 'strings=["other_event"]'


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


def test_run_ignores_stale_loaded_ledger_when_authoritative_exists(tmp_path: Path):
    repo = tmp_path / "repo"
    repo.mkdir()
    authoritative = _ledger_text(
        assertion_id="brain-assertion-drift-auth01",
        claim={
            "subject": "artifact",
            "predicate": "value",
            "object": "evidence",
            "value": "current",
        },
    )
    stale = _ledger_text(
        assertion_id="brain-assertion-drift-stale1",
        claim={
            "subject": "artifact",
            "predicate": "value",
            "object": "evidence",
            "value": "current",
        },
    )
    (repo / "evidence.txt").write_text("current", encoding="utf-8")
    _write_authoritative_ledger(repo, authoritative)
    _write_ledger(repo, stale)

    result = ce_brain_drift.run([repo, repo / ".ce" / "state"])

    assert result.ok
    assert result.errors == ()


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


def test_verify_state_root_ignores_stale_loaded_ledger_when_authoritative_exists(tmp_path: Path):
    repo = tmp_path / "repo"
    repo.mkdir()
    authoritative = _ledger_text(
        assertion_id="brain-assertion-drift-auth01",
        claim={
            "subject": "artifact",
            "predicate": "value",
            "object": "evidence",
            "value": "current",
        },
    )
    stale = _ledger_text(
        assertion_id="brain-assertion-drift-stale1",
        claim={
            "subject": "artifact",
            "predicate": "value",
            "object": "evidence",
            "value": "current",
        },
    )
    (repo / "evidence.txt").write_text("current", encoding="utf-8")
    _write_authoritative_ledger(repo, authoritative)
    _write_ledger(repo, stale)

    drift = ce_brain_drift.verify_state_root(repo / ".ce" / "state")

    assert drift.ok
    assert drift.ledger_path == repo / ".ce" / "brain" / "assertions.yaml"
    assert drift.record_count == 1
    assert drift.active_count == 1
    assert drift.findings == ()


def test_verify_state_root_missing_runtime_copy_does_not_fail_fresh_checkout(tmp_path: Path):
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "evidence.txt").write_text("current", encoding="utf-8")
    _write_authoritative_ledger(
        repo,
        _ledger_text(
            claim={
                "subject": "artifact",
                "predicate": "value",
                "object": "evidence",
                "value": "current",
            },
        ),
    )

    drift = ce_brain_drift.verify_state_root(repo / ".ce" / "state")

    assert drift.ok
    assert drift.record_count == 1
    assert drift.active_count == 1
    assert drift.findings == ()


def test_verify_state_root_falls_back_to_authoritative_ledger_and_reports_drift(tmp_path: Path):
    repo = tmp_path / "repo"
    repo.mkdir()
    _write_text(
        repo / ".github" / "workflows" / "validate.yml",
        "on:\n"
        "  merge_group:\n"
        "    types: [other_event]\n",
    )
    authoritative = _write_authoritative_validate_workflow_ledger(repo)

    drift = ce_brain_drift.verify_state_root(repo / ".ce" / "state")

    assert not (repo / ".ce" / "state").exists()
    assert drift.ledger_path == authoritative
    assert drift.record_count == 1
    assert drift.active_count == 1
    assert not drift.ok
    assert [finding.code for finding in drift.findings] == [ce_brain_drift.CODE_DRIFT]
    assert "artifact projection drifted" in drift.findings[0].message


def test_verify_state_root_reports_authoritative_drift_with_stale_loaded_ledger_present(tmp_path: Path):
    repo = tmp_path / "repo"
    repo.mkdir()
    _write_text(
        repo / ".github" / "workflows" / "validate.yml",
        "on:\n"
        "  merge_group:\n"
        "    types: [other_event]\n",
    )
    authoritative = _write_authoritative_validate_workflow_ledger(repo)
    _write_ledger(
        repo,
        _ledger_text(
            assertion_id="brain-assertion-drift-stale1",
            claim={
                "subject": "artifact",
                "predicate": "value",
                "object": "evidence",
                "value": "stale local state",
            },
        ),
    )

    drift = ce_brain_drift.verify_state_root(repo / ".ce" / "state")

    assert drift.ledger_path == authoritative
    assert not drift.ok
    assert [finding.code for finding in drift.findings] == [ce_brain_drift.CODE_DRIFT]
    assert ".ce/state/brain/assertions.yaml" not in str(drift.findings[0].path)
    assert "artifact projection drifted" in drift.findings[0].message


def test_registered_run_discovers_authoritative_brain_ledger(tmp_path: Path):
    repo = tmp_path / "repo"
    repo.mkdir()
    _write_text(
        repo / ".github" / "workflows" / "validate.yml",
        "on:\n"
        "  merge_group:\n"
        "    types: [other_event]\n",
    )
    _write_authoritative_validate_workflow_ledger(repo)

    result = ce_brain_drift.run([repo])

    assert result.name == ce_brain_drift.CHECK_NAME
    assert not result.ok
    assert [error.code for error in result.errors] == [ce_brain_drift.CODE_DRIFT]


def test_authoritative_migrated_assertions_validate_and_probe():
    root = Path(__file__).resolve().parents[3]
    path = rt.authoritative_ledger_path(root)

    errors = ce_brain_drift.validate_file(
        path,
        context=ce_brain_drift.DriftContext(
            repo_root=root,
            probe_context=brain_probe.ProbeContext(repo_root=root, env={}),
        ),
    )

    assert errors == []
    records = rt.load_records_from_path(path)
    active = [record for record in records if record["status"] == "active"]
    assert len(active) == 88
    assert {
        brain_probe.record_probe_name(record)
        for record in active
        if brain_probe.record_probe_name(record) is not None
    } == {
        "codex_fan_out_surfaces",
        "codex_pretooluse_hook",
        "harness_fan_out",
        "integrator_belt_approval_current_head_required",
        "integrator_belt_approval_green_triggers_queue",
        "integrator_belt_merge_queue_conflict_gate",
        "pr_preflight_ci_parity",
        "pr_preflight_clean_tree_guard",
        "pr_preflight_scrubs_credential_env",
        "self_identity",
        "worker_spawn_runtime_support",
    }
    assert any(record["id"] == "brain-assertion-validate-workflow-drift-gate" for record in active)
    assert any(
        record["id"] == "brain-assertion-fleet-self-identity-live"
        and record["scope"] == {"seat": "ce-dev-1"}
        for record in active
    )
    # The deterministic-citations design gotcha: a static, artifact-backed
    # (non-probe) Knowledge-SSOT assertion grounded in a tracked design note.
    assert any(
        record["type"] == "gotcha"
        and record["claim"].get("object") == "deterministic_citations_via_docs_as_skills"
        and record["evidence_ref"] == ".ce/brain/notes/deterministic-citations.md"
        for record in active
    )


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
