"""RV1-063 — ``ce launch`` / ``ce hud`` launcher runtime (strict TDD).

The launcher is the canonical deterministic Controller-seat launcher (DP-2 = B).
``ce hud`` is an alias/seam label for the *same* launcher — not a CE-native TUI.
tmux is replaced by a test double so dry-run planning, attach/resume, and the
hidden-continuation refusal can be exercised without a real tmux process or a
live provider login.
"""
from __future__ import annotations

import pytest

from creator_engine_validator import launch_runtime
from creator_engine_validator.tmux_adapter import TmuxPane


class FakeAdapter:
    kind = "tmux"

    def __init__(self, *, available: bool = True, sessions: set[str] | None = None):
        self._available = available
        self._sessions = set(sessions or set())
        self.spawned: list[tuple[str, str, list[str]]] = []

    def is_available(self) -> bool:
        return self._available

    def session_exists(self, session: str) -> bool:
        return session in self._sessions

    def ensure_pane(self, *, session, window, command):
        self.spawned.append((session, window, list(command)))
        self._sessions.add(session)
        return TmuxPane(session_id="$1", window_id="@2", pane_id="%3", pane_tty="/dev/pts/7", pane_pid=999)


# ---------------------------------------------------------------------------
# Deterministic planning + hud alias
# ---------------------------------------------------------------------------


def test_plan_launch_is_deterministic_and_visible():
    plan = launch_runtime.plan_launch(harness="claude")
    assert plan.mode == "launch"
    assert plan.visibility == "operator_visible"
    assert plan.harness == "claude"
    assert plan.command[0] == "claude"


def test_hud_is_an_alias_of_launch_not_a_native_tui():
    launch_plan = launch_runtime.plan_launch(harness="claude", session="s", window="w")
    hud_plan = launch_runtime.plan_launch(harness="claude", session="s", window="w", invoked_as="hud")
    assert hud_plan.invoked_as == "hud"
    assert hud_plan.alias_of == "launch"
    # Same launcher: identical session/window/command/visibility.
    assert hud_plan.session == launch_plan.session
    assert hud_plan.command == launch_plan.command
    assert hud_plan.visibility == "operator_visible"


# ---------------------------------------------------------------------------
# Dry-run: no side effects, proves alias without a provider login
# ---------------------------------------------------------------------------


def test_dry_run_does_not_spawn():
    adapter = FakeAdapter()
    result = launch_runtime.launch(harness="claude", dry_run=True, tmux_adapter=adapter)
    assert result.plan.dry_run is True
    assert result.spawned is False
    assert adapter.spawned == []


def test_dry_run_works_without_tmux_available():
    # Planning must not require a live tmux (or provider) — dry-run is pure.
    adapter = FakeAdapter(available=False)
    result = launch_runtime.launch(harness="claude", dry_run=True, tmux_adapter=adapter)
    assert result.plan.dry_run is True
    assert adapter.spawned == []


# ---------------------------------------------------------------------------
# Hidden-continuation refusal (no hidden fallback)
# ---------------------------------------------------------------------------


def test_launch_refuses_hidden_continuation():
    adapter = FakeAdapter()
    with pytest.raises(launch_runtime.HiddenContinuationRefused):
        launch_runtime.launch(harness="claude", allow_hidden=True, tmux_adapter=adapter)
    assert adapter.spawned == []


def test_launch_refuses_non_visible_terminal():
    adapter = FakeAdapter()
    with pytest.raises(launch_runtime.HiddenContinuationRefused):
        launch_runtime.launch(harness="claude", visible=False, tmux_adapter=adapter)
    assert adapter.spawned == []


# ---------------------------------------------------------------------------
# tmux availability + resume semantics
# ---------------------------------------------------------------------------


def test_launch_refuses_when_tmux_unavailable():
    adapter = FakeAdapter(available=False)
    with pytest.raises(launch_runtime.TmuxUnavailableError):
        launch_runtime.launch(harness="claude", tmux_adapter=adapter)
    assert adapter.spawned == []


def test_resume_refuses_missing_session():
    adapter = FakeAdapter(sessions=set())  # nothing to resume
    with pytest.raises(launch_runtime.ResumeTargetMissing):
        launch_runtime.launch(harness="claude", session="ce-controller", resume=True, tmux_adapter=adapter)
    assert adapter.spawned == []


def test_resume_attaches_existing_session():
    adapter = FakeAdapter(sessions={"ce-controller"})
    result = launch_runtime.launch(
        harness="claude", session="ce-controller", resume=True, tmux_adapter=adapter
    )
    assert result.plan.mode == "resume"
    assert result.attached is True


def test_launch_spawns_visible_controller_seat():
    adapter = FakeAdapter()
    result = launch_runtime.launch(harness="claude", session="ce-controller", tmux_adapter=adapter)
    assert result.spawned is True
    assert adapter.spawned, "controller seat should be spawned in a visible tmux pane"
    assert result.plan.visibility == "operator_visible"


def test_launch_result_to_dict_is_json_safe():
    import json

    adapter = FakeAdapter()
    result = launch_runtime.launch(harness="claude", dry_run=True, tmux_adapter=adapter)
    json.dumps(result.to_dict())
    assert result.to_dict()["plan"]["mode"] == "launch"


# ---------------------------------------------------------------------------
# CC-G-D — Ring 0 Claude launch refusal + governed command in `ce launch`
# ---------------------------------------------------------------------------


def test_claude_launch_refuses_bare_before_side_effects(monkeypatch):
    adapter = FakeAdapter()
    monkeypatch.setattr(launch_runtime, "_confirm_pack", lambda repo_root: True)
    with pytest.raises(launch_runtime.LaunchRefused) as exc:
        launch_runtime.launch(harness="claude", extra_args=["--bare"], tmux_adapter=adapter)
    assert exc.value.code == "G6-LAUNCH-CLAUDE-REFUSED"
    assert "CC-D-1" in str(exc.value)
    assert adapter.spawned == []


def test_claude_launch_refuses_skip_perms_without_confirmed_pack(monkeypatch):
    adapter = FakeAdapter()
    monkeypatch.setattr(launch_runtime, "_confirm_pack", lambda repo_root: False)
    with pytest.raises(launch_runtime.LaunchRefused) as exc:
        launch_runtime.launch(
            harness="claude",
            extra_args=["--dangerously-skip-permissions"],
            tmux_adapter=adapter,
        )
    assert "CC-D-6" in str(exc.value)
    assert adapter.spawned == []


def test_claude_launch_pins_setting_sources_and_strict_mcp(monkeypatch):
    adapter = FakeAdapter()
    monkeypatch.setattr(launch_runtime, "_confirm_pack", lambda repo_root: True)
    launch_runtime.launch(
        harness="claude",
        session="s",
        tmux_adapter=adapter,
        mcp_config_path=".hermes/s/mcp/ce-mcp.json",
    )
    (_sess, _win, cmd) = adapter.spawned[-1]
    assert cmd[0] == "claude"
    assert "--setting-sources" in cmd and "project" in cmd and "--strict-mcp-config" in cmd


def test_claude_launch_allows_skip_perms_with_confirmed_pack(monkeypatch):
    adapter = FakeAdapter()
    monkeypatch.setattr(launch_runtime, "_confirm_pack", lambda repo_root: True)
    launch_runtime.launch(
        harness="claude",
        session="s",
        extra_args=["--dangerously-skip-permissions"],
        tmux_adapter=adapter,
        mcp_config_path=".hermes/s/mcp/ce-mcp.json",
    )
    (_sess, _win, cmd) = adapter.spawned[-1]
    assert "--dangerously-skip-permissions" in cmd
    assert "--setting-sources" in cmd and "project" in cmd


def test_non_claude_harness_command_unchanged(monkeypatch):
    # A non-Claude harness must not get the governed Claude command injected.
    adapter = FakeAdapter()
    launch_runtime.launch(harness="codex", session="s", extra_args=["--foo"], tmux_adapter=adapter)
    (_sess, _win, cmd) = adapter.spawned[-1]
    assert cmd == ["codex", "--foo"]


def test_claude_launch_refuses_uncontrolled_mcp_config_flag(monkeypatch):
    # An operator-supplied --mcp-config outside the governed roots must refuse
    # (LaunchRefused), never crash with a raw GovernedCommandError.
    adapter = FakeAdapter()
    monkeypatch.setattr(launch_runtime, "_confirm_pack", lambda repo_root: True)
    with pytest.raises(launch_runtime.LaunchRefused) as exc:
        launch_runtime.launch(
            harness="claude",
            session="s",
            tmux_adapter=adapter,
            mcp_config_path="/etc/global/mcp.json",
        )
    assert "CC-D-7" in str(exc.value)
    assert adapter.spawned == []


def test_claude_dry_run_does_not_confirm_pack_when_no_skip_perms(monkeypatch):
    # Dry-run with no skip-perms must not invoke the (possibly impure) pack probe.
    adapter = FakeAdapter()

    def _boom(repo_root):
        raise AssertionError("_confirm_pack must not be called without skip-permissions")

    monkeypatch.setattr(launch_runtime, "_confirm_pack", _boom)
    result = launch_runtime.launch(harness="claude", dry_run=True, tmux_adapter=adapter)
    assert result.plan.dry_run is True
    assert adapter.spawned == []
