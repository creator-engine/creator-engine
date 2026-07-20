from __future__ import annotations

import hashlib
import json
from pathlib import Path

from creator_engine_validator import brain_probe
from creator_engine_validator import brain_runtime as rt
from creator_engine_validator import ce_cli
from creator_engine_validator.checks import ce_brain_drift
import pytest

pytestmark = pytest.mark.slow



def _claim(value: str) -> str:
    return json.dumps({"subject": "brain", "predicate": "mode", "object": value})


def _probe_claim(verdict: str) -> str:
    return json.dumps(
        {
            "subject": "capability",
            "predicate": "probe-verdict",
            "object": "missing-capability",
            "verdict": verdict,
        }
    )


def _artifact_hash_claim(digest: str) -> str:
    return json.dumps(
        {
            "subject": "artifact",
            "predicate": "sha256",
            "object": "evidence.txt",
            "sha256": digest,
        }
    )


def _write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def test_ce_brain_reconcile_requires_plan_acceptance_and_writes(tmp_path: Path, capsys):
    evidence = tmp_path / "evidence.txt"
    evidence.write_text("current", encoding="utf-8")
    captured: list[tuple[Path, str]] = []
    rt.assert_claim(
        assertion_id="brain-assertion-reconcile-cli-0001",
        claim={"subject": "artifact", "predicate": "hash", "object": "evidence.txt", "sha256": hashlib.sha256(b"old").hexdigest()},
        scope="integration", evidence_ref="evidence.txt",
        verification_method={"type": "static", "evidence_ref": "evidence.txt"},
        state_root=tmp_path / ".ce", records=[], write=lambda path, text: captured.append((path, text)),
    )
    path, text = captured[-1]
    _write_text(path, text)
    argv = ["brain", "reconcile", "--repo-root", str(tmp_path), "--id", "brain-assertion-reconcile-cli-0001", "--json"]
    assert ce_cli.main(argv) == 0
    planned = json.loads(capsys.readouterr().out)
    assert planned["written"] is False and planned["plan"]["write_required"] is True
    assert ce_cli.main([*argv[:-1], "--apply", "--accept-plan-sha", planned["plan"]["plan_sha256"], "--json"]) == 0
    applied = json.loads(capsys.readouterr().out)
    assert applied["written"] is True


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
    _write_text(path, text)
    return path


def _write_brain_assertion(state_root: Path, *, assertion_id: str, value: str) -> Path:
    result = rt.assert_claim(
        assertion_id=assertion_id,
        claim={"subject": "brain", "predicate": "sync-state", "object": value},
        scope="integration",
        evidence_ref="manual-sync-test",
        state_root=state_root,
    )
    return result.ledger_path


def test_ce_brain_assert_check_correct_verify_roundtrip(tmp_path: Path, capsys):
    state_root = tmp_path / ".ce" / "state"

    assert ce_cli.main(
        [
            "brain",
            "assert",
            "--state-root",
            str(state_root),
            "--id",
            "brain-assertion-cli-0001",
            "--scope",
            "integration",
            "--statement",
            "The brain assertion ledger is the doctrine-preserving SSOT for corrections.",
            "--claim-json",
            _claim("ssot"),
            "--evidence-ref",
            "validators/tests/integration/test_ce_brain_cli.py#assert",
            "--json",
        ]
    ) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["id"] == "brain-assertion-cli-0001"

    assert ce_cli.main(
        [
            "brain",
            "check",
            "--state-root",
            str(state_root),
            "--scope",
            "integration",
            "--claim-json",
            _claim("ssot"),
            "--json",
        ]
    ) == 0
    checked = json.loads(capsys.readouterr().out)
    assert checked["status"] == "active"

    assert ce_cli.main(
        [
            "brain",
            "correct",
            "--state-root",
            str(state_root),
            "--id",
            "brain-assertion-cli-0001",
            "--new-id",
            "brain-assertion-cli-0002",
            "--claim-json",
            _claim("deterministic-ssot"),
            "--evidence-ref",
            "validators/tests/integration/test_ce_brain_cli.py#correct",
            "--json",
        ]
    ) == 0
    corrected = json.loads(capsys.readouterr().out)
    assert corrected["superseded_status"] == "superseded"
    assert corrected["status"] == "active"

    assert ce_cli.main(
        [
            "brain",
            "check",
            "--state-root",
            str(state_root),
            "--scope",
            "integration",
            "--claim-json",
            _claim("ssot"),
            "--json",
        ]
    ) == 0
    assert json.loads(capsys.readouterr().out)["status"] == "unknown"

    assert ce_cli.main(
        [
            "brain",
            "check",
            "--state-root",
            str(state_root),
            "--scope",
            "integration",
            "--claim-json",
            _claim("deterministic-ssot"),
            "--json",
        ]
    ) == 0
    active = json.loads(capsys.readouterr().out)["record"]
    assert active["id"] == "brain-assertion-cli-0002"
    assert active["statement"] == "The brain assertion ledger is the doctrine-preserving SSOT for corrections."

    assert ce_cli.main(["brain", "verify", "--state-root", str(state_root), "--json"]) == 0
    verified = json.loads(capsys.readouterr().out)
    assert verified["record_count"] == 3
    assert verified["active_count"] == 1


def test_ce_brain_check_unknown_on_missing_ledger(tmp_path: Path, capsys):
    rc = ce_cli.main(
        [
            "brain",
            "check",
            "--state-root",
            str(tmp_path / ".ce" / "state"),
            "--scope",
            "integration",
            "--claim-json",
            _claim("missing"),
            "--json",
        ]
    )

    assert rc == 0
    assert json.loads(capsys.readouterr().out) == {"record": None, "status": "unknown"}


def test_ce_brain_hydrate_json_empty_ledger_contract(tmp_path: Path, capsys):
    state_root = tmp_path / ".ce" / "state"

    rc = ce_cli.main(["brain", "hydrate", "--state-root", str(state_root), "--json"])

    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["kind"] == "ce-brain-hydration-contract"
    assert payload["active_decisions"] == []
    assert payload["active_lessons"] == []
    assert payload["newest_resume_state"] is None


def test_ce_brain_verify_catches_tamper(tmp_path: Path, capsys):
    state_root = tmp_path / ".ce" / "state"
    assert ce_cli.main(
        [
            "brain",
            "assert",
            "--state-root",
            str(state_root),
            "--id",
            "brain-assertion-cli-0003",
            "--scope",
            "integration",
            "--claim-json",
            _claim("tamper"),
            "--evidence-ref",
            "validators/tests/integration/test_ce_brain_cli.py#tamper",
        ]
    ) == 0
    capsys.readouterr()
    path = state_root / "brain" / "assertions.yaml"
    text = path.read_text(encoding="utf-8").replace("tamper", "mutated")
    path.write_text(text, encoding="utf-8")

    rc = ce_cli.main(["brain", "verify", "--state-root", str(state_root)])

    assert rc == 1
    assert "brain_assertion_content_address" in capsys.readouterr().err


def test_ce_brain_verify_reprobes_probe_backed_assertions(tmp_path: Path, capsys):
    state_root = tmp_path / ".ce" / "state"
    assert ce_cli.main(
        [
            "brain",
            "assert",
            "--state-root",
            str(state_root),
            "--id",
            "brain-assertion-cli-0004",
            "--scope",
            "capability-probes",
            "--claim-json",
            _probe_claim("present"),
            "--evidence-ref",
            "probe:missing-capability",
        ]
    ) == 0
    capsys.readouterr()

    rc = ce_cli.main(["brain", "verify", "--state-root", str(state_root), "--json"])

    assert rc == 1
    payload = json.loads(capsys.readouterr().out)
    assert any("brain_assertion_probe_disagreement" in error for error in payload["errors"])


def test_ce_brain_verify_drift_missing_ledger_is_zero_active_assertions(tmp_path: Path, capsys):
    state_root = tmp_path / ".ce" / "state"

    rc = ce_cli.main(["brain", "verify", "--drift", "--state-root", str(state_root), "--json"])

    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["record_count"] == 0
    assert payload["active_count"] == 0
    assert payload["errors"] == []
    assert payload["drift"]["ok"] is True
    assert payload["drift"]["findings"] == []


def test_ce_brain_sync_idempotently_reconciles_instance_local_state(tmp_path: Path, capsys):
    state_root = tmp_path / ".ce" / "state"
    authoritative = _write_brain_assertion(
        tmp_path / ".ce",
        assertion_id="brain-assertion-sync-auth01",
        value="canonical",
    )
    local = _write_brain_assertion(
        state_root,
        assertion_id="brain-assertion-sync-local1",
        value="stale-local",
    )
    assert local.read_text(encoding="utf-8") != authoritative.read_text(encoding="utf-8")

    rc = ce_cli.main(["brain", "sync", "--state-root", str(state_root)])

    assert rc == 0
    first = capsys.readouterr().out
    assert "ce brain sync: reconciled" in first
    assert "source:" in first
    assert "target:" in first
    assert local.read_text(encoding="utf-8") == authoritative.read_text(encoding="utf-8")

    rc = ce_cli.main(["brain", "sync", "--state-root", str(state_root)])

    assert rc == 0
    second = capsys.readouterr().out
    assert "ce brain sync: already in sync" in second
    assert local.read_text(encoding="utf-8") == authoritative.read_text(encoding="utf-8")


def test_ce_brain_verify_drift_passes_matching_artifact_hash(tmp_path: Path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    state_root = tmp_path / ".ce" / "state"
    evidence = tmp_path / "evidence.txt"
    evidence.write_text("current\n", encoding="utf-8")
    digest = hashlib.sha256(b"current\n").hexdigest()

    assert ce_cli.main(
        [
            "brain",
            "assert",
            "--state-root",
            str(state_root),
            "--id",
            "brain-assertion-cli-0005",
            "--scope",
            "integration",
            "--claim-json",
            _artifact_hash_claim(digest),
            "--evidence-ref",
            "evidence.txt",
        ]
    ) == 0
    capsys.readouterr()

    rc = ce_cli.main(["brain", "verify", "--drift", "--state-root", str(state_root), "--json"])

    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["drift"]["ok"] is True
    assert payload["drift"]["active_count"] == 1
    assert payload["drift"]["findings"] == []


def test_ce_brain_verify_drift_returns_nonzero_on_artifact_drift(tmp_path: Path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    state_root = tmp_path / ".ce" / "state"
    evidence = tmp_path / "evidence.txt"
    evidence.write_text("observed\n", encoding="utf-8")

    assert ce_cli.main(
        [
            "brain",
            "assert",
            "--state-root",
            str(state_root),
            "--id",
            "brain-assertion-cli-0006",
            "--scope",
            "integration",
            "--claim-json",
            _artifact_hash_claim("a" * 64),
            "--evidence-ref",
            "evidence.txt",
        ]
    ) == 0
    capsys.readouterr()

    rc = ce_cli.main(["brain", "verify", "--drift", "--state-root", str(state_root), "--json"])

    assert rc == 1
    payload = json.loads(capsys.readouterr().out)
    assert payload["drift"]["ok"] is False
    assert [finding["code"] for finding in payload["drift"]["findings"]] == [ce_brain_drift.CODE_DRIFT]
    assert any("brain-assertion-cli-0006" in error for error in payload["errors"])


def test_ce_brain_verify_drift_non_json_failure_message_is_actionable(tmp_path: Path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    state_root = tmp_path / ".ce" / "state"
    evidence = tmp_path / "evidence.txt"
    evidence.write_text("observed\n", encoding="utf-8")

    assert ce_cli.main(
        [
            "brain",
            "assert",
            "--state-root",
            str(state_root),
            "--id",
            "brain-assertion-cli-0007",
            "--scope",
            "integration",
            "--claim-json",
            _artifact_hash_claim("a" * 64),
            "--evidence-ref",
            "evidence.txt",
        ]
    ) == 0
    capsys.readouterr()

    rc = ce_cli.main(["brain", "verify", "--drift", "--state-root", str(state_root)])

    assert rc == 1
    captured = capsys.readouterr()
    assert "ce brain verify --drift: FAIL" in captured.out
    assert "run `ce brain sync`" in captured.err
    assert "instance-local .ce/state/brain drift" in captured.err
    assert "CI is unaffected by ignored instance-local runtime state" in captured.err


def test_ce_brain_verify_drift_falls_back_to_authoritative_ledger_and_fails_on_semantic_drift(
    tmp_path: Path, monkeypatch, capsys
):
    monkeypatch.chdir(tmp_path)
    state_root = tmp_path / ".ce" / "state"
    authoritative = _write_authoritative_validate_workflow_ledger(tmp_path)
    _write_text(
        tmp_path / ".github" / "workflows" / "validate.yml",
        "on:\n"
        "  merge_group:\n"
        "    types: [other_event]\n",
    )

    rc = ce_cli.main(["brain", "verify", "--drift", "--state-root", str(state_root), "--json"])

    assert not state_root.exists()
    assert rc == 1
    payload = json.loads(capsys.readouterr().out)
    assert payload["drift"]["ledger_path"] == str(authoritative)
    assert payload["drift"]["record_count"] == 1
    assert payload["drift"]["active_count"] == 1
    assert [finding["code"] for finding in payload["drift"]["findings"]] == [ce_brain_drift.CODE_DRIFT]
    assert "artifact projection drifted" in payload["errors"][0]


def test_ce_brain_probe_unknown_capability_returns_unknown(capsys):
    rc = ce_cli.main(["brain", "probe", "missing-capability", "--json"])

    assert rc == 0
    assert json.loads(capsys.readouterr().out) == {
        "evidence": {"reason": "unknown_probe"},
        "name": "missing-capability",
        "verdict": "unknown",
    }


def test_ce_brain_probe_all_json_is_sorted(monkeypatch, capsys):
    monkeypatch.setattr(
        brain_probe,
        "probe_all",
        lambda context=None: [
            brain_probe.ProbeResult("wheelhouse_matches_source", "present", {"source": "unit"}),
            brain_probe.ProbeResult("gh_authenticated", "unknown", {"source": "unit"}),
        ],
    )

    rc = ce_cli.main(["brain", "probe", "--all", "--json"])

    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert [item["name"] for item in payload["probes"]] == [
        "gh_authenticated",
        "wheelhouse_matches_source",
    ]


def test_ce_brain_probe_requires_name_or_all(capsys):
    rc = ce_cli.main(["brain", "probe"])

    assert rc == 2
    captured = capsys.readouterr()
    assert captured.out == ""
    assert "specify exactly one of <name> or --all" in captured.err


def test_ce_brain_probe_rejects_name_and_all(capsys):
    rc = ce_cli.main(["brain", "probe", "gh_authenticated", "--all"])

    assert rc == 2
    captured = capsys.readouterr()
    assert captured.out == ""
    assert "specify exactly one of <name> or --all" in captured.err


def test_ce_brain_bootstrap_surfaces_scope_relevant_assertions(tmp_path: Path, capsys):
    state_root = tmp_path / ".ce" / "state"
    assert ce_cli.main(
        [
            "brain",
            "assert",
            "--state-root",
            str(state_root),
            "--id",
            "brain-assertion-cli-0005",
            "--scope",
            "global",
            "--claim-json",
            _claim("global"),
            "--evidence-ref",
            "validators/tests/integration/test_ce_brain_cli.py#global",
        ]
    ) == 0
    capsys.readouterr()
    assert ce_cli.main(
        [
            "brain",
            "assert",
            "--state-root",
            str(state_root),
            "--id",
            "brain-assertion-cli-0006",
            "--scope-json",
            json.dumps({"project": "creator-engine", "role": "controller", "seat_class": "foreman"}),
            "--claim-json",
            _claim("controller"),
            "--evidence-ref",
            "validators/tests/integration/test_ce_brain_cli.py#controller",
        ]
    ) == 0
    capsys.readouterr()

    rc = ce_cli.main(
        [
            "brain",
            "bootstrap",
            "--state-root",
            str(state_root),
            "--scope-json",
            json.dumps({"project": "creator-engine", "role": "controller"}),
            "--json",
        ]
    )

    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["kind"] == "brain-bootstrap-context"
    assert payload["context"]["scope"]["seat_class"] == "foreman"
    assert [item["id"] for item in payload["knowledge_ssot"]["assertions"]] == [
        "brain-assertion-cli-0005",
        "brain-assertion-cli-0006",
    ]


def test_ce_brain_bootstrap_refuses_tampered_ledger(tmp_path: Path, capsys):
    state_root = tmp_path / ".ce" / "state"
    assert ce_cli.main(
        [
            "brain",
            "assert",
            "--state-root",
            str(state_root),
            "--id",
            "brain-assertion-cli-0006",
            "--scope",
            "global",
            "--claim-json",
            _claim("tamper-bootstrap"),
            "--evidence-ref",
            "validators/tests/integration/test_ce_brain_cli.py#tamper-bootstrap",
        ]
    ) == 0
    capsys.readouterr()
    path = state_root / "brain" / "assertions.yaml"
    path.write_text(path.read_text(encoding="utf-8").replace("tamper-bootstrap", "mutated-bootstrap"), encoding="utf-8")

    rc = ce_cli.main(["brain", "bootstrap", "--state-root", str(state_root), "--json"])

    assert rc == 1
    captured = capsys.readouterr()
    assert captured.out == ""
    assert "brain_assertion_content_address" in captured.err
