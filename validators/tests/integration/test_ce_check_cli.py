"""RV1-060 — integration tests for ``ce check`` over bundled examples.

Confirms the ``ce check`` umbrella faithfully wraps the retained
``creator-engine-validator`` conformance surface end-to-end (well-formed pass /
malformed fail) without reimplementing it.
"""
from __future__ import annotations

import json
from pathlib import Path

from creator_engine_validator import ce_cli, cli as validator_cli


def test_ce_check_passes_wellformed_examples(repo_root: Path, capsys):
    example = repo_root / "examples" / "well-formed" / "state-version-record"
    ret = ce_cli.main(["check", str(example), "--json"])
    assert ret == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["ok"] is True


def test_ce_check_fails_malformed_example_like_validator(repo_root: Path, capsys):
    malformed = repo_root / "examples" / "malformed" / "state-version-record" / "stale-version.yaml"
    ce_ret = ce_cli.main(["check", str(malformed), "--json"])
    capsys.readouterr()
    validator_ret = validator_cli.main(["--json", "check", str(malformed)])
    capsys.readouterr()
    assert ce_ret == validator_ret != 0


def test_ce_check_list_checks(capsys):
    ret = ce_cli.main(["check", "--list-checks", "--json"])
    assert ret == 0
    payload = json.loads(capsys.readouterr().out)
    assert "checks" in payload
