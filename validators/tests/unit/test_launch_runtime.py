"""RV1-063 — ``ce launch`` / ``ce hud`` launcher runtime (strict TDD).

The launcher is the canonical deterministic Controller-seat launcher (DP-2 = B).
``ce hud`` is an alias/seam label for the *same* launcher — not a CE-native TUI.
tmux is replaced by a test double so dry-run planning, attach/resume, and the
hidden-continuation refusal can be exercised without a real tmux process or a
live provider login.
"""
from __future__ import annotations

import json
import shlex
from pathlib import Path

import pytest

from creator_engine_validator import launch_runtime
from creator_engine_validator.tmux_adapter import TmuxPane


def _inner_argv(result):
    """Recover the EXACT governed/bounded argv embedded in the ce-ops#26 wrapper.

    The pane command is now ``["/bin/sh", <wrapper>]``; the seat command runs
    FOREGROUND inside the wrapper (the line just before ``code=$?``).
    """
    wrapper = Path(result.events_ref).parent / "sentinel-wrapper.sh"
    lines = wrapper.read_text().splitlines()
    idx = next(i for i, line in enumerate(lines) if line == "code=$?")
    return shlex.split(lines[idx - 1])


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
    result = launch_runtime.launch(
        harness="claude",
        session="s",
        tmux_adapter=adapter,
        mcp_config_path=".hermes/s/mcp/ce-mcp.json",
    )
    (_sess, _win, cmd) = adapter.spawned[-1]
    # ce-ops#26: the pane runs the sentinel wrapper; the governed argv is INSIDE it.
    assert cmd == ["/bin/sh", str(Path(result.events_ref).parent / "sentinel-wrapper.sh")]
    inner = _inner_argv(result)
    assert inner[0] == "claude"
    assert "--setting-sources" in inner and "project" in inner and "--strict-mcp-config" in inner


def test_claude_launch_allows_skip_perms_with_confirmed_pack(monkeypatch):
    adapter = FakeAdapter()
    monkeypatch.setattr(launch_runtime, "_confirm_pack", lambda repo_root: True)
    result = launch_runtime.launch(
        harness="claude",
        session="s",
        extra_args=["--dangerously-skip-permissions"],
        tmux_adapter=adapter,
        mcp_config_path=".hermes/s/mcp/ce-mcp.json",
    )
    inner = _inner_argv(result)
    assert "--dangerously-skip-permissions" in inner
    assert "--setting-sources" in inner and "project" in inner


def test_non_claude_harness_command_unchanged(monkeypatch):
    # A non-Claude harness must not get the governed Claude command injected.
    adapter = FakeAdapter()
    result = launch_runtime.launch(harness="codex", session="s", extra_args=["--foo"], tmux_adapter=adapter)
    # ce-ops#26: non-claude commands pass through byte-identical INSIDE the wrapper.
    assert _inner_argv(result) == ["codex", "--foo"]


def test_seat_surface_dispatch_driven_seat_id_is_run_id(tmp_path):
    # ce-ops#26: --runtime-policy <state>/dispatches/<run_id>/runtime-policy.yaml ⇒
    # seat_id = run_id and events land NEXT TO dispatch.yaml.
    dispatch_dir = tmp_path / ".ce" / "state" / "dispatches" / "run-x-1"
    dispatch_dir.mkdir(parents=True)
    seat_dir, seat_id, run_id = launch_runtime._resolve_seat_surface(
        repo_root=tmp_path, session="s", window="w",
        runtime_policy=dispatch_dir / "runtime-policy.yaml",
    )
    assert (seat_dir, seat_id, run_id) == (dispatch_dir, "run-x-1", "run-x-1")


def test_seat_surface_bare_seat_id_is_session_window_slug(tmp_path):
    seat_dir, seat_id, run_id = launch_runtime._resolve_seat_surface(
        repo_root=tmp_path, session="Ctrl Seat", window="main", runtime_policy=None,
    )
    assert seat_id == "ctrl-seat--main"
    assert run_id is None
    assert seat_dir == tmp_path / ".ce" / "state" / "dispatches" / "ctrl-seat--main"


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


# ---------------------------------------------------------------------------
# v3.1-G1 defect-a — plain `ce launch` must provision the strict MCP config
# (claude was pinned at a path that was never created -> silent exit 1).
# ---------------------------------------------------------------------------


class _McpProbingAdapter(FakeAdapter):
    """FakeAdapter that records whether ``mcp_path`` existed at spawn time."""

    def __init__(self, mcp_path, **kw):
        super().__init__(**kw)
        self._mcp_path = mcp_path
        self.mcp_existed_at_spawn: bool | None = None

    def ensure_pane(self, *, session, window, command):
        self.mcp_existed_at_spawn = self._mcp_path.is_file()
        return super().ensure_pane(session=session, window=window, command=command)


def test_claude_launch_provisions_mcp_config_before_spawn(tmp_path, monkeypatch):
    # defect-a: a non-dry-run claude launch writes the strict MCP config into the
    # seat cwd (repo_root) BEFORE ensure_pane, so the governed seat can bind.
    monkeypatch.setattr(launch_runtime, "_confirm_pack", lambda repo_root: True)
    mcp_rel = ".hermes/launch/ce-controller/mcp/ce-mcp.json"
    mcp_abs = tmp_path / mcp_rel
    adapter = _McpProbingAdapter(mcp_abs)
    assert not mcp_abs.exists()
    launch_runtime.launch(
        harness="claude",
        session="ce-controller",
        tmux_adapter=adapter,
        repo_root=str(tmp_path),
    )
    assert adapter.spawned, "the governed seat must spawn"
    assert adapter.mcp_existed_at_spawn is True, "MCP config must exist before ensure_pane"
    assert mcp_abs.read_text(encoding="utf-8") == (
        json.dumps({"mcpServers": {}}, indent=2, sort_keys=True) + "\n"
    )


def test_claude_launch_does_not_overwrite_existing_mcp_config(tmp_path, monkeypatch):
    # An Operator/launcher-supplied MCP config is never clobbered by provisioning.
    monkeypatch.setattr(launch_runtime, "_confirm_pack", lambda repo_root: True)
    mcp_rel = ".hermes/launch/s/mcp/ce-mcp.json"
    mcp_abs = tmp_path / mcp_rel
    mcp_abs.parent.mkdir(parents=True)
    preexisting = '{"mcpServers": {"keep": {"command": "x"}}}\n'
    mcp_abs.write_text(preexisting, encoding="utf-8")
    launch_runtime.launch(
        harness="claude",
        session="s",
        tmux_adapter=FakeAdapter(),
        mcp_config_path=mcp_rel,
        repo_root=str(tmp_path),
    )
    assert mcp_abs.read_text(encoding="utf-8") == preexisting


def test_claude_launch_refuses_nonfile_mcp_target_before_spawn(tmp_path, monkeypatch):
    # A non-regular-file at the MCP target is a fail-closed LaunchRefused (no spawn).
    monkeypatch.setattr(launch_runtime, "_confirm_pack", lambda repo_root: True)
    mcp_rel = ".hermes/launch/s/mcp/ce-mcp.json"
    (tmp_path / mcp_rel).mkdir(parents=True)  # a DIRECTORY where the file must go
    adapter = FakeAdapter()
    with pytest.raises(launch_runtime.LaunchRefused):
        launch_runtime.launch(
            harness="claude",
            session="s",
            tmux_adapter=adapter,
            mcp_config_path=mcp_rel,
            repo_root=str(tmp_path),
        )
    assert adapter.spawned == []


# ---------------------------------------------------------------------------
# v3.1-G1 defect-b — CC-D-6 gates the bridge's unattended skip-permissions flag.
# The bridge passes `--claude-arg=--dangerously-skip-permissions`; the governance
# already exists (CC-D-6), so launch_runtime is the enforced boundary.
# ---------------------------------------------------------------------------


def test_unattended_skip_perms_refuses_when_hook_pack_unconfirmed(tmp_path, monkeypatch):
    # CC-D-6 fail-closed: an unattended (skip-perms) seat with an unconfirmed
    # hook-pack is refused before any side effect.
    monkeypatch.setattr(launch_runtime, "_confirm_pack", lambda repo_root: False)
    adapter = FakeAdapter()
    with pytest.raises(launch_runtime.LaunchRefused) as exc:
        launch_runtime.launch(
            harness="claude",
            session="drive-seat",
            extra_args=["--dangerously-skip-permissions"],
            tmux_adapter=adapter,
            repo_root=str(tmp_path),
        )
    assert "CC-D-6" in str(exc.value)
    assert adapter.spawned == []


def test_unattended_skip_perms_carries_flag_when_hook_pack_confirmed(tmp_path, monkeypatch):
    # CC-D-6 confirmed: the governed argv carries --dangerously-skip-permissions.
    monkeypatch.setattr(launch_runtime, "_confirm_pack", lambda repo_root: True)
    adapter = FakeAdapter()
    result = launch_runtime.launch(
        harness="claude",
        session="drive-seat",
        extra_args=["--dangerously-skip-permissions"],
        tmux_adapter=adapter,
        repo_root=str(tmp_path),
    )
    inner = _inner_argv(result)
    assert "--dangerously-skip-permissions" in inner
    assert "--setting-sources" in inner and "project" in inner


def test_claude_dry_run_does_not_confirm_pack_when_no_skip_perms(monkeypatch):
    # Dry-run with no skip-perms must not invoke the (possibly impure) pack probe.
    adapter = FakeAdapter()

    def _boom(repo_root):
        raise AssertionError("_confirm_pack must not be called without skip-permissions")

    monkeypatch.setattr(launch_runtime, "_confirm_pack", _boom)
    result = launch_runtime.launch(harness="claude", dry_run=True, tmux_adapter=adapter)
    assert result.plan.dry_run is True
    assert adapter.spawned == []


# --- CE Ring 0 Hermes harness governance (round: Hermes governance TDD) ---


def test_hermes_dry_run_emits_governed_profile_pinned_command():
    result = launch_runtime.launch(harness="hermes", dry_run=True)
    # no longer a bare ["hermes"]; profile is pinned and visible in the plan
    assert result.plan.command == ["hermes", "--profile", "creator-engine"]
    assert result.plan.dry_run is True


def test_hermes_launch_refuses_yolo_before_side_effect():
    adapter = FakeAdapter(available=True)
    with pytest.raises(launch_runtime.LaunchRefused):
        launch_runtime.launch(harness="hermes", extra_args=["--yolo"], tmux_adapter=adapter)


def test_hermes_launch_refuses_profile_override_before_side_effect():
    adapter = FakeAdapter(available=True)
    with pytest.raises(launch_runtime.LaunchRefused):
        launch_runtime.launch(
            harness="hermes", extra_args=["--profile", "mythos"], tmux_adapter=adapter
        )


def test_hermes_launch_refuses_resume_continue_before_side_effect():
    adapter = FakeAdapter(available=True)
    for argv in (["--resume", "s"], ["-c"]):
        with pytest.raises(launch_runtime.LaunchRefused):
            launch_runtime.launch(harness="hermes", extra_args=argv, tmux_adapter=adapter)


def test_claude_governance_not_regressed_by_hermes_branch():
    # the Claude harness still pins --setting-sources project + --strict-mcp-config
    result = launch_runtime.launch(harness="claude", dry_run=True)
    cmd = result.plan.command
    assert cmd[0] == "claude"
    assert "--setting-sources" in cmd and "project" in cmd
    assert "--strict-mcp-config" in cmd


class _SpawnTrackingAdapter:
    kind = "tmux"
    def __init__(self): self.spawned = []
    def is_available(self): return True
    def ensure_pane(self, *, session, window, command, cwd=None):
        self.spawned.append((session, window, list(command), cwd))
        return TmuxPane(session_id="$1", window_id="@2", pane_id="%3")


@pytest.mark.parametrize("argv", [["--res"], ["-rabc"], ["--cont"], ["-cabc"], ["--yol"], ["--acc"], ["--ignore-r"], ["--prof", "mythos"]])
def test_hermes_refuses_abbreviated_bypass_with_no_spawn(argv):
    adapter = _SpawnTrackingAdapter()
    with pytest.raises(launch_runtime.LaunchRefused):
        launch_runtime.launch(harness="hermes", extra_args=argv, tmux_adapter=adapter)
    assert adapter.spawned == []


def test_hermes_refusal_uses_hermes_code_not_claude():
    adapter = _SpawnTrackingAdapter()
    try:
        launch_runtime.launch(harness="hermes", extra_args=["--yolo"], tmux_adapter=adapter)
        assert False, "expected refusal"
    except launch_runtime.LaunchRefused as exc:
        assert getattr(exc, "code", "") == "G6-LAUNCH-HERMES-REFUSED"
    assert adapter.spawned == []
