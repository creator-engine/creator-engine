from __future__ import annotations

import json
from pathlib import Path

from creator_engine_validator import ce_cli


def _claim(value: str) -> str:
    return json.dumps({"subject": "brain", "predicate": "mode", "object": value})


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
    assert json.loads(capsys.readouterr().out)["record"]["id"] == "brain-assertion-cli-0002"

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
