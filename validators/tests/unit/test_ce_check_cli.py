"""RV1-060/061 — unit tests for the ``ce check`` umbrella surface.

``ce check`` is the first-class ``ce`` wrapper over the retained
``creator-engine-validator`` conformance checks (DP-1 = A: ``ce`` wraps the
existing validator subcommands; the distribution is not renamed and the
``creator-engine-validator`` entrypoint is retained).
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from creator_engine_validator import ce_cli, cli as validator_cli


def test_check_help_is_reachable():
    with pytest.raises(SystemExit) as exc:
        ce_cli.main(["check", "--help"])
    assert exc.value.code == 0


def test_ce_check_wraps_validator_check_json(repo_root: Path, capsys):
    example = repo_root / "examples" / "well-formed" / "side-effect-ledger"
    ret = ce_cli.main(["check", str(example), "--json"])
    assert ret == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["ok"] is True
    assert "results" in payload


def test_ce_check_matches_validator_exit_code_on_malformed(repo_root: Path, capsys):
    malformed = repo_root / "examples" / "malformed" / "side-effect-ledger" / "secret-payload.yaml"
    ce_ret = ce_cli.main(["check", str(malformed), "--json"])
    capsys.readouterr()
    validator_ret = validator_cli.main(["--json", "check", str(malformed)])
    capsys.readouterr()
    assert ce_ret == validator_ret != 0


def test_ce_check_defaults_to_dot_path(monkeypatch, repo_root: Path, tmp_path: Path, capsys):
    # Omitting paths must default to ".": `ce check` and `ce check .` must
    # produce the same exit code (faithful wrap, not a reimplementation).
    mini_repo = tmp_path / "mini-repo"
    mini_repo.mkdir()
    (mini_repo / "schemas").symlink_to(repo_root / "schemas", target_is_directory=True)
    (mini_repo / "docs").symlink_to(repo_root / "docs", target_is_directory=True)
    example_dir = mini_repo / "examples" / "well-formed"
    example_dir.mkdir(parents=True)
    for storage_dir in ("attestations", "ratifications", "redactions"):
        (example_dir / storage_dir).mkdir()
    (example_dir / "identity-record.yml").write_text(
        (repo_root / "examples" / "well-formed" / "identity-record.yml").read_text(
            encoding="utf-8"
        ),
        encoding="utf-8",
    )

    monkeypatch.chdir(mini_repo)
    default_ret = ce_cli.main(["check", "--json"])
    capsys.readouterr()
    explicit_ret = ce_cli.main(["check", ".", "--json"])
    capsys.readouterr()
    assert default_ret == explicit_ret


def test_creator_engine_validator_entrypoint_is_retained():
    # DP-1 = A: the legacy console-script function must remain importable/callable.
    assert callable(validator_cli.main)
