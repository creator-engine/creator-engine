"""Unit tests for CE Ring 0 Hermes harness governance (`hermes_launch_spec`).

Parallels `claude_launch_spec`: parse Hermes argv, refuse prohibited surfaces before
any side effect, and build a governed command that pins the Creator-Engine profile.
Hermes has no `--strict-mcp-config` equivalent, so none is invented here.
"""
from __future__ import annotations

import pytest

from creator_engine_validator import hermes_launch_spec as hls


def _refusal_clauses(spec_result) -> set[str]:
    return {r.clause for r in spec_result.refusals}


# --- governed command builds with the profile pinned ---


def test_build_governed_pins_creator_engine_profile():
    assert hls.build_governed_hermes_command(base_argv=[]) == [
        "hermes",
        "--profile",
        "creator-engine",
    ]


def test_build_governed_preserves_safe_args_after_profile_pin():
    cmd = hls.build_governed_hermes_command(base_argv=["--worktree"])
    assert cmd[:3] == ["hermes", "--profile", "creator-engine"]
    assert "--worktree" in cmd[3:]


def test_build_governed_is_idempotent_for_matching_profile():
    # a redundant, matching --profile creator-engine is collapsed, not duplicated
    cmd = hls.build_governed_hermes_command(base_argv=["--profile", "creator-engine"])
    assert cmd == ["hermes", "--profile", "creator-engine"]
    assert cmd.count("--profile") == 1


# --- prohibited-surface refusals (before any side effect) ---


def test_refuses_profile_override():
    result = hls.evaluate_hermes_launch(hls.parse_hermes_argv(["--profile", "mythos"]))
    assert not result.ok
    assert hls.CLAUSE_PROFILE_OVERRIDE in _refusal_clauses(result)


def test_refuses_profile_subcommand_override():
    result = hls.evaluate_hermes_launch(hls.parse_hermes_argv(["profile", "use", "mythos"]))
    assert not result.ok
    assert hls.CLAUSE_PROFILE_OVERRIDE in _refusal_clauses(result)


def test_refuses_yolo():
    result = hls.evaluate_hermes_launch(hls.parse_hermes_argv(["--yolo"]))
    assert not result.ok
    assert hls.CLAUSE_YOLO in _refusal_clauses(result)


@pytest.mark.parametrize("argv", [["--resume", "sess"], ["-r", "sess"]])
def test_refuses_resume(argv):
    result = hls.evaluate_hermes_launch(hls.parse_hermes_argv(argv))
    assert not result.ok
    assert hls.CLAUSE_RESUME in _refusal_clauses(result)


@pytest.mark.parametrize("argv", [["--continue"], ["-c"], ["--continue", "name"]])
def test_refuses_continue(argv):
    result = hls.evaluate_hermes_launch(hls.parse_hermes_argv(argv))
    assert not result.ok
    assert hls.CLAUSE_CONTINUE in _refusal_clauses(result)


def test_refuses_accept_hooks():
    result = hls.evaluate_hermes_launch(hls.parse_hermes_argv(["--accept-hooks"]))
    assert not result.ok
    assert hls.CLAUSE_ACCEPT_HOOKS in _refusal_clauses(result)


@pytest.mark.parametrize("flag", ["--ignore-user-config", "--ignore-rules"])
def test_refuses_ignore_config(flag):
    result = hls.evaluate_hermes_launch(hls.parse_hermes_argv([flag]))
    assert not result.ok
    assert hls.CLAUSE_IGNORE_CONFIG in _refusal_clauses(result)


# --- safe argv is accepted ---


@pytest.mark.parametrize("argv", [[], ["--worktree"], ["--profile", "creator-engine"]])
def test_safe_argv_accepted(argv):
    result = hls.evaluate_hermes_launch(hls.parse_hermes_argv(argv))
    assert result.ok, [r.clause for r in result.refusals]


# --- Round 2 blocker: argparse prefix-abbreviation + concatenated-short bypasses ---


@pytest.mark.parametrize(
    "argv,clause",
    [
        (["--res"], hls.CLAUSE_RESUME),
        (["--resu", "s"], hls.CLAUSE_RESUME),
        (["-rabc"], hls.CLAUSE_RESUME),
        (["--cont"], hls.CLAUSE_CONTINUE),
        (["-cabc"], hls.CLAUSE_CONTINUE),
        (["--yol"], hls.CLAUSE_YOLO),
        (["--acc"], hls.CLAUSE_ACCEPT_HOOKS),
        (["--accept"], hls.CLAUSE_ACCEPT_HOOKS),
        (["--ignore-user"], hls.CLAUSE_IGNORE_CONFIG),
        (["--ignore-r"], hls.CLAUSE_IGNORE_CONFIG),
        (["--prof", "mythos"], hls.CLAUSE_PROFILE_OVERRIDE),
    ],
)
def test_refuses_abbreviated_and_concatenated_unsafe_surfaces(argv, clause):
    result = hls.evaluate_hermes_launch(hls.parse_hermes_argv(argv))
    assert not result.ok, f"expected refusal for {argv!r}"
    assert clause in _refusal_clauses(result)


def test_safe_abbrev_prefix_of_safe_option_still_accepted():
    # `--prof creator-engine` (abbrev of --profile with the canonical value) is fine;
    # safe options that are NOT prefixes of unsafe options remain accepted.
    assert hls.evaluate_hermes_launch(hls.parse_hermes_argv(["--prof", "creator-engine"])).ok
    assert hls.evaluate_hermes_launch(hls.parse_hermes_argv(["--worktree"])).ok
