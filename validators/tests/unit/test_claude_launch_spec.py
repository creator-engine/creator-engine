"""CC-G-D Ring 0 — unit tests for ``claude_launch_spec`` (strict TDD).

This is the pure, offline launch-spec evaluator for the Ring 0 Claude
launcher/kernel. It parses a requested ``claude`` argv, returns fail-closed
refusal clauses for every prohibited surface (seat contract §5), and builds a
governed command that pins ``--setting-sources project`` + strict MCP. No
process is spawned, no file is read, no network call is made.
"""
from __future__ import annotations

import pytest

from creator_engine_validator import claude_launch_spec as cls


# ---------------------------------------------------------------------------
# Task 1 — argv parser
# ---------------------------------------------------------------------------


def test_parse_extracts_setting_sources_and_skip_perms():
    spec = cls.parse_claude_argv(
        ["--setting-sources", "project,local", "--dangerously-skip-permissions"]
    )
    assert spec.setting_sources == ("project", "local")
    assert spec.skip_permissions is True


def test_parse_extracts_mcp_config_and_strict():
    spec = cls.parse_claude_argv(
        ["--strict-mcp-config", "--mcp-config", ".hermes/x/mcp/ce-mcp.json"]
    )
    assert spec.strict_mcp is True
    assert spec.mcp_config_path == ".hermes/x/mcp/ce-mcp.json"


def test_parse_handles_equals_form():
    spec = cls.parse_claude_argv(
        ["--setting-sources=project", "--mcp-config=.hermes/y/mcp/ce-mcp.json"]
    )
    assert spec.setting_sources == ("project",)
    assert spec.mcp_config_path == ".hermes/y/mcp/ce-mcp.json"


def test_parse_defaults_are_none_or_false():
    spec = cls.parse_claude_argv([])
    assert spec.setting_sources is None
    assert spec.mcp_config_path is None
    assert spec.strict_mcp is False
    assert spec.skip_permissions is False
    assert spec.argv == ()


# ---------------------------------------------------------------------------
# Task 2 — always-prohibited surfaces (seat contract §5)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "argv,clause,surface",
    [
        (["--bare"], cls.CLAUSE_BARE, "--bare"),
        (["agents"], cls.CLAUSE_AGENTS, "agents"),
        (["--agents"], cls.CLAUSE_AGENTS, "--agents"),
        (["--remote-control"], cls.CLAUSE_REMOTE_CONTROL, "--remote-control"),
        (["--remote-control-at-startup"], cls.CLAUSE_REMOTE_CONTROL, "--remote-control-at-startup"),
        (["--setting-sources", "user,local"], cls.CLAUSE_LOCAL_SETTINGS, "--setting-sources"),
        (["--setting-sources", "user"], cls.CLAUSE_LOCAL_SETTINGS, "--setting-sources"),
    ],
)
def test_evaluate_refuses_prohibited_surface(argv, clause, surface):
    spec = cls.parse_claude_argv(argv)
    result = cls.evaluate_claude_launch(spec, hook_pack_confirmed=True)
    assert not result.ok
    assert clause in {r.clause for r in result.refusals}
    assert surface in {r.surface for r in result.refusals}


def test_evaluate_allows_clean_governed_argv():
    spec = cls.parse_claude_argv(["--setting-sources", "project"])
    assert cls.evaluate_claude_launch(spec, hook_pack_confirmed=True).ok


def test_evaluate_allows_empty_argv():
    # No requested surfaces -> nothing to refuse (the builder will pin posture).
    assert cls.evaluate_claude_launch(cls.parse_claude_argv([]), hook_pack_confirmed=True).ok


# ---------------------------------------------------------------------------
# Task 3 — --print refusal (governed authoring lane) + skip-permissions gate
# ---------------------------------------------------------------------------


def test_print_refused_for_governed_authoring_lane():
    for argv in (["-p"], ["--print"]):
        spec = cls.parse_claude_argv(argv)
        r = cls.evaluate_claude_launch(spec, hook_pack_confirmed=True, governed_authoring_lane=True)
        assert cls.CLAUSE_PRINT in {x.clause for x in r.refusals}


def test_print_allowed_when_not_a_governed_authoring_lane():
    # Read-only scripted ce checks may use --print; not a governed authoring lane.
    spec = cls.parse_claude_argv(["--print", "--setting-sources", "project"])
    r = cls.evaluate_claude_launch(spec, hook_pack_confirmed=True, governed_authoring_lane=False)
    assert cls.CLAUSE_PRINT not in {x.clause for x in r.refusals}


def test_skip_permissions_refused_without_confirmed_pack():
    spec = cls.parse_claude_argv(["--dangerously-skip-permissions"])
    r = cls.evaluate_claude_launch(spec, hook_pack_confirmed=False)
    assert cls.CLAUSE_SKIP_PERMS in {x.clause for x in r.refusals}


def test_skip_permissions_allowed_with_confirmed_pack():
    spec = cls.parse_claude_argv(["--dangerously-skip-permissions", "--setting-sources", "project"])
    r = cls.evaluate_claude_launch(spec, hook_pack_confirmed=True)
    assert cls.CLAUSE_SKIP_PERMS not in {x.clause for x in r.refusals}


# ---------------------------------------------------------------------------
# Task 4 — strict MCP posture + governed-command builder
# ---------------------------------------------------------------------------


def test_mcp_refused_when_not_strict():
    spec = cls.parse_claude_argv(["--mcp-config", ".hermes/x/mcp/ce-mcp.json"])
    r = cls.evaluate_claude_launch(spec, hook_pack_confirmed=True)
    assert cls.CLAUSE_MCP in {x.clause for x in r.refusals}


def test_mcp_refused_when_uncontrolled_global_path():
    spec = cls.parse_claude_argv(["--strict-mcp-config", "--mcp-config", "/etc/global/mcp.json"])
    r = cls.evaluate_claude_launch(spec, hook_pack_confirmed=True)
    assert cls.CLAUSE_MCP in {x.clause for x in r.refusals}


def test_mcp_allowed_when_strict_and_ce_owned():
    spec = cls.parse_claude_argv(["--strict-mcp-config", "--mcp-config", ".hermes/x/mcp/ce-mcp.json"])
    r = cls.evaluate_claude_launch(spec, hook_pack_confirmed=True)
    assert cls.CLAUSE_MCP not in {x.clause for x in r.refusals}
    assert r.ok


def test_build_governed_command_pins_settings_strict_mcp():
    cmd = cls.build_governed_claude_command(
        base_argv=None,
        mcp_config_path=".hermes/lane-x/mcp/ce-mcp.json",
        closeout_file=None,
        completion_report_ref=None,
    )
    assert cmd[0] == "claude"
    assert "--setting-sources" in cmd and "project" in cmd
    assert "--strict-mcp-config" in cmd
    assert "--mcp-config" in cmd
    # The built command must itself pass evaluation.
    built = cls.parse_claude_argv(cmd[1:])
    assert cls.evaluate_claude_launch(built, hook_pack_confirmed=True).ok


def test_build_governed_command_does_not_emit_closeout_as_flags():
    # Closeout pointers ride the lane environment, never as claude flags.
    cmd = cls.build_governed_claude_command(
        base_argv=["--model", "claude-opus-4-7"],
        mcp_config_path=".hermes/lane-x/mcp/ce-mcp.json",
        closeout_file=".hermes/lane-x/closeout.md",
        completion_report_ref="reports/cc-g-d.yaml",
    )
    joined = " ".join(cmd)
    assert "closeout" not in joined
    assert "reports/cc-g-d.yaml" not in joined
    # Operator base args are preserved.
    assert "--model" in cmd and "claude-opus-4-7" in cmd


def test_build_governed_command_is_idempotent_on_clean_setting_sources():
    cmd = cls.build_governed_claude_command(
        base_argv=["--setting-sources", "project"],
        mcp_config_path=".hermes/lane-x/mcp/ce-mcp.json",
        closeout_file=None,
        completion_report_ref=None,
    )
    # Exactly one --setting-sources, pinned to project.
    assert cmd.count("--setting-sources") == 1
    built = cls.parse_claude_argv(cmd[1:])
    assert built.setting_sources == ("project",)
    assert cls.evaluate_claude_launch(built, hook_pack_confirmed=True).ok


def test_build_governed_command_refuses_conflicting_setting_sources():
    with pytest.raises(cls.GovernedCommandError):
        cls.build_governed_claude_command(
            base_argv=["--setting-sources", "user,local"],
            mcp_config_path=".hermes/lane-x/mcp/ce-mcp.json",
            closeout_file=None,
            completion_report_ref=None,
        )
