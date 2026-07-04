"""Parity checks for the ``ce`` to v3 subprocess forwarding shims."""
from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
from pathlib import Path

import pytest

from creator_engine_validator import ce_cli

_REPO_ROOT = Path(__file__).resolve().parents[3]
_VALIDATORS = _REPO_ROOT / "validators"
_CEV3_DEPRECATION_NOTICE = "WARNING: cev3 is deprecated; use ce instead.\n"


def _env() -> dict[str, str]:
    env = os.environ.copy()
    env.pop(ce_cli._V3_FORWARDED_ENV, None)
    prior = env.get("PYTHONPATH")
    env["PYTHONPATH"] = str(_VALIDATORS) if not prior else f"{_VALIDATORS}{os.pathsep}{prior}"
    return env


def _run_module(module: str, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", module, *args],
        cwd=_REPO_ROOT,
        env=_env(),
        check=False,
        capture_output=True,
        text=True,
    )


@pytest.mark.parametrize(
    "command",
    ["install", "dispatch", "scope", "ratify", "drive", "report", "session", "queue-daemon"],
)
def test_ce_v3_shim_help_matches_v3_help(command: str) -> None:
    v3_command = ce_cli.V3_FORWARDING_SHIMS[command][1]

    via_ce = _run_module("creator_engine_validator.ce_cli", command, "--help")
    direct = _run_module("creator_engine_validator.v3_cli", v3_command, "--help")

    assert via_ce.returncode == direct.returncode == 0
    assert via_ce.stdout == direct.stdout
    assert direct.stderr == _CEV3_DEPRECATION_NOTICE + via_ce.stderr


@pytest.mark.parametrize(
    "command",
    ["install", "dispatch", "scope", "ratify", "drive", "report", "session", "queue-daemon"],
)
def test_ce_v3_shim_propagates_bad_arg_return_code(command: str) -> None:
    v3_command = ce_cli.V3_FORWARDING_SHIMS[command][1]

    via_ce = _run_module("creator_engine_validator.ce_cli", command, "--definitely-not-a-real-arg")
    direct = _run_module("creator_engine_validator.v3_cli", v3_command, "--definitely-not-a-real-arg")

    assert via_ce.returncode == direct.returncode
    assert via_ce.returncode != 0


def test_v3_shim_inventory_matches_v3_help_without_importing_v3() -> None:
    direct = _run_module("creator_engine_validator.v3_cli", "--help")
    assert direct.returncode == 0
    match = re.search(r"\{(?P<commands>[^}]+)\}", direct.stdout, re.DOTALL)
    assert match, direct.stdout
    v3_commands = {
        part.strip()
        for part in match.group("commands").replace("\n", "").split(",")
        if part.strip()
    }

    # "onboard" is a one-release-cycle legacy alias on the v3 "install"
    # subparser (the release-signed installer still invokes it); it must not
    # get its own first-class `ce` forwarding shim.
    assert set(ce_cli.V3_FORWARDING_SHIMS) == v3_commands - {"playbook", "onboard"}
    assert "install" in ce_cli.V3_FORWARDING_SHIMS
    assert "onboard" not in ce_cli.V3_FORWARDING_SHIMS


def test_v3_forwarding_shims_do_not_overlap_internal_command_groups() -> None:
    overlap = set(ce_cli.V3_FORWARDING_SHIMS) & ce_cli.INTERNAL_COMMAND_GROUPS
    assert overlap == set()


def test_cev3_deprecation_notice_is_direct_only_and_public() -> None:
    direct = _run_module("creator_engine_validator.v3_cli", "--help")
    via_ce = _run_module("creator_engine_validator.ce_cli", "session", "--help")

    assert direct.returncode == via_ce.returncode == 0
    assert direct.stderr == _CEV3_DEPRECATION_NOTICE
    assert _CEV3_DEPRECATION_NOTICE not in via_ce.stderr
    for command_group in ce_cli.INTERNAL_COMMAND_GROUPS:
        assert command_group not in direct.stderr


def test_v3_forwarder_uses_subprocess_and_propagates_return_code(monkeypatch) -> None:
    calls: list[list[str]] = []
    forwarded_envs: list[dict[str, str]] = []

    def fake_run(argv, *, check, env):
        calls.append(list(argv))
        forwarded_envs.append(dict(env))
        assert check is False
        return subprocess.CompletedProcess(argv, 17)

    monkeypatch.setattr(ce_cli.subprocess, "run", fake_run)

    rc = ce_cli.main(["install", "--spec", "spec.yaml", "--plan"])

    assert rc == 17
    assert calls == [
        [
            sys.executable,
            "-m",
            "creator_engine_validator.v3_cli",
            "install",
            "--spec",
            "spec.yaml",
            "--plan",
        ]
    ]
    assert forwarded_envs[0][ce_cli._V3_FORWARDED_ENV] == "1"


def test_dequeue_forwarder_sets_v3_sentinel_and_keeps_stderr_quiet(monkeypatch, capsys) -> None:
    calls: list[list[str]] = []
    forwarded_envs: list[dict[str, str]] = []

    def fake_run(argv, *, check, env):
        calls.append(list(argv))
        forwarded_envs.append(dict(env))
        assert check is False
        return subprocess.CompletedProcess(argv, 23)

    monkeypatch.setattr(ce_cli.subprocess, "run", fake_run)

    rc = ce_cli.main(
        [
            "dequeue",
            "782",
            "--repo",
            "creator-engine/creator-engine",
            "--token-env",
            "TEST_TOKEN",
            "--convert-to-draft",
            "--json",
        ]
    )
    captured = capsys.readouterr()

    assert rc == 23
    assert calls == [
        [
            sys.executable,
            "-m",
            "creator_engine_validator.v3_cli",
            "queue-dequeue",
            "782",
            "--repo",
            "creator-engine/creator-engine",
            "--token-env",
            "TEST_TOKEN",
            "--convert-to-draft",
            "--json",
        ]
    ]
    assert forwarded_envs[0][ce_cli._V3_FORWARDED_ENV] == "1"
    assert _CEV3_DEPRECATION_NOTICE not in captured.err


def test_bare_ce_keeps_usage_exit_2() -> None:
    parser = ce_cli._build_parser()
    action = next(a for a in parser._actions if isinstance(a, argparse._SubParsersAction))
    assert "session" in action.choices

    via_ce = _run_module("creator_engine_validator.ce_cli")

    assert via_ce.returncode == 2
    assert via_ce.stdout == ""
    assert "usage: ce" in via_ce.stderr
