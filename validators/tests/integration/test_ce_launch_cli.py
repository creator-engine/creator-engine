"""RV1-063 — integration tests for ``ce launch`` / ``ce hud``.

These use the real tmux adapter but only via side-effect-free paths: the
deterministic ``--dry-run`` plan, the hidden-continuation refusal, and the
resume-missing-session refusal. No real Controller seat / provider is spawned.
"""
from __future__ import annotations

import json
from pathlib import Path

from creator_engine_validator import ce_cli
import pytest

pytestmark = pytest.mark.slow



def _fake_codex(tmp_path: Path, monkeypatch) -> Path:
    codex = tmp_path / "bin" / "codex"
    codex.parent.mkdir()
    codex.write_text("#!/bin/sh\n", encoding="utf-8")
    codex.chmod(0o755)
    monkeypatch.setenv(ce_cli.launch_runtime.codex_launch_spec.CODEX_HARNESS_ENV, str(codex))
    return codex


def test_dry_run_plan_is_deterministic(capsys):
    ce_cli.main(["launch", "--dry-run", "--json"])
    first = json.loads(capsys.readouterr().out)
    ce_cli.main(["launch", "--dry-run", "--json"])
    second = json.loads(capsys.readouterr().out)
    assert first == second
    assert first["plan"]["visibility"] == "operator_visible"


def test_hud_alias_matches_launch_dry_run(capsys):
    ce_cli.main(["launch", "--dry-run", "--json"])
    launch = json.loads(capsys.readouterr().out)["plan"]
    ce_cli.main(["hud", "--dry-run", "--json"])
    hud = json.loads(capsys.readouterr().out)["plan"]
    assert hud["alias_of"] == "launch"
    assert hud["command"] == launch["command"]
    assert hud["session"] == launch["session"]


def test_launch_no_tmux_is_refused(capsys):
    ret = ce_cli.main(["launch", "--no-tmux"])
    assert ret != 0


def test_resume_missing_session_is_refused(capsys):
    # A session name that does not exist must refuse rather than spawn hidden.
    ret = ce_cli.main(["launch", "--resume", "--session", "ce-controller-nonexistent-xyz", "--json"])
    assert ret != 0


def test_codex_dry_run_is_pure_and_governed(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(
        ce_cli.launch_runtime.codex_launch_spec, "detect_config_bypass_mode", lambda: "config"
    )
    monkeypatch.setattr(
        ce_cli.launch_runtime, "_confirm_codex_managed_pack", lambda repo_root: True
    )
    codex = _fake_codex(tmp_path, monkeypatch)
    ret = ce_cli.main([
        "launch", "--harness", "codex", "--codex-arg=--model", "--codex-arg", "gpt-5",
        "--dry-run", "--json",
    ])
    assert ret == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["spawned"] is False
    assert payload["plan"]["command"][-3:] == [str(codex), "--model", "gpt-5"]
    assert payload["plan"]["codex_bypass_mode"] == "config"
