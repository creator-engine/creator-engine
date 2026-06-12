from __future__ import annotations

from pathlib import Path

from creator_engine_validator import codex_launch_spec as spec


def _result(argv, tmp_path):
    parsed = spec.parse_codex_argv(argv)
    return spec.evaluate_codex_launch(parsed, allowed_root=tmp_path, config_bypass_mode="config")


def test_refuses_headless_subcommands(tmp_path):
    for subcommand in ("exec", "review", "mcp-server", "exec-server", "app-server", "apply"):
        result = _result([subcommand], tmp_path)
        assert not result.ok
        assert {r.clause for r in result.refusals} == {spec.CLAUSE_HEADLESS}


def test_refuses_remote_ephemeral_and_posture_bypass_surfaces(tmp_path):
    result = _result(
        [
            "remote-control",
            "--remote",
            "--remote-token=x",
            "--ephemeral",
            "--ignore-user-config",
            "--ignore-rules",
            "--dangerously-bypass-hook-trust",
        ],
        tmp_path,
    )
    clauses = {r.clause for r in result.refusals}
    assert spec.CLAUSE_REMOTE in clauses
    assert spec.CLAUSE_TRANSCRIPT in clauses
    assert spec.CLAUSE_POSTURE_BYPASS in clauses


def test_refuses_add_dir_outside_allowed_root(tmp_path):
    result = _result(["--add-dir", "/outside"], tmp_path)
    assert not result.ok
    assert spec.CLAUSE_ADD_DIR in {r.clause for r in result.refusals}


def test_allows_add_dir_inside_allowed_root(tmp_path):
    inside = tmp_path / "subdir"
    inside.mkdir()
    result = _result(["--add-dir", str(inside)], tmp_path)
    assert result.ok


def test_requires_bypass_mode_config_or_argv(tmp_path):
    parsed = spec.parse_codex_argv([])
    result = spec.evaluate_codex_launch(parsed, allowed_root=tmp_path, config_bypass_mode=None)
    assert not result.ok
    assert spec.CLAUSE_BYPASS_MODE in {r.clause for r in result.refusals}

    argv_result = spec.evaluate_codex_launch(
        spec.parse_codex_argv([spec.BYPASS_FLAG]),
        allowed_root=tmp_path,
        config_bypass_mode=None,
    )
    assert argv_result.ok
    assert argv_result.bypass_mode == "argv"


def test_refuses_non_allowlisted_flags(tmp_path):
    result = _result(["--foo"], tmp_path)
    assert not result.ok
    assert spec.CLAUSE_ARG_ALLOWLIST in {r.clause for r in result.refusals}


def test_build_governed_command_scrubs_github_credentials():
    command = spec.build_governed_codex_command(["--model", "gpt-5"])
    assert command[:2] == ["env", "-u"]
    for name in spec.CREDENTIAL_ENV_UNSETS:
        assert ["-u", name] == command[command.index(name) - 1: command.index(name) + 1]
    assert command[-3:] == ["codex", "--model", "gpt-5"]


def test_detect_config_bypass_mode(tmp_path):
    cfg = tmp_path / "config.toml"
    cfg.write_text('approval_policy = "never"\nsandbox_mode = "danger-full-access"\n', encoding="utf-8")
    assert spec.detect_config_bypass_mode(cfg) == "config"
    cfg.write_text('approval_policy = "on-request"\nsandbox_mode = "danger-full-access"\n', encoding="utf-8")
    assert spec.detect_config_bypass_mode(cfg) is None
