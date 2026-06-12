"""RV1-063 — unit tests for ``ce launch`` / ``ce hud`` CLI surfaces.

Drives ``creator_engine_validator.ce_cli.main`` directly with the tmux adapter
replaced by a test double, so the deterministic dry-run, hud alias, and the
hidden-continuation / resume refusals are exercised without a real tmux process
or a live provider login.
"""
from __future__ import annotations

import json

import pytest

from creator_engine_validator import ce_cli
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
        return TmuxPane(session_id="$1", window_id="@2", pane_id="%3")


@pytest.fixture()
def use_fake_tmux(monkeypatch):
    adapter = FakeAdapter()

    def _install(a: FakeAdapter):
        monkeypatch.setattr(ce_cli, "_make_tmux_adapter", lambda: a)

    _install(adapter)
    return _install


@pytest.mark.parametrize("argv", [["launch", "--help"], ["hud", "--help"]])
def test_launch_and_hud_help_reachable(argv):
    with pytest.raises(SystemExit) as exc:
        ce_cli.main(argv)
    assert exc.value.code == 0


def test_launch_dry_run_json(use_fake_tmux, capsys):
    ret = ce_cli.main(["launch", "--dry-run", "--json"])
    assert ret == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["plan"]["mode"] == "launch"
    assert payload["plan"]["invoked_as"] == "launch"
    assert payload["plan"]["visibility"] == "operator_visible"
    assert payload["spawned"] is False


def test_hud_dry_run_json_is_alias_of_launch(use_fake_tmux, capsys):
    ce_cli.main(["launch", "--dry-run", "--json", "--session", "s", "--window", "w"])
    launch_payload = json.loads(capsys.readouterr().out)
    ce_cli.main(["hud", "--dry-run", "--json", "--session", "s", "--window", "w"])
    hud_payload = json.loads(capsys.readouterr().out)
    assert hud_payload["plan"]["invoked_as"] == "hud"
    assert hud_payload["plan"]["alias_of"] == "launch"
    assert hud_payload["plan"]["command"] == launch_payload["plan"]["command"]


def test_launch_refuses_no_tmux_flag(use_fake_tmux, capsys):
    adapter = FakeAdapter()
    use_fake_tmux(adapter)
    ret = ce_cli.main(["launch", "--no-tmux"])
    assert ret != 0
    assert adapter.spawned == []


def test_launch_spawns_visible_seat(use_fake_tmux):
    adapter = FakeAdapter()
    use_fake_tmux(adapter)
    ret = ce_cli.main(["launch", "--session", "ce-controller"])
    assert ret == 0
    assert adapter.spawned


def test_launch_resume_refuses_missing_session(use_fake_tmux):
    adapter = FakeAdapter(sessions=set())
    use_fake_tmux(adapter)
    ret = ce_cli.main(["launch", "--resume", "--session", "ce-controller"])
    assert ret != 0
    assert adapter.spawned == []


def test_launch_resume_attaches_existing(use_fake_tmux, capsys):
    adapter = FakeAdapter(sessions={"ce-controller"})
    use_fake_tmux(adapter)
    ret = ce_cli.main(["launch", "--resume", "--session", "ce-controller", "--json"])
    assert ret == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["plan"]["mode"] == "resume"
    assert payload["attached"] is True


# ---------------------------------------------------------------------------
# CC-G-D — Ring 0 governed Claude surfaces via the CLI
# ---------------------------------------------------------------------------


def test_cli_launch_refuses_claude_bare(use_fake_tmux, monkeypatch, capsys):
    adapter = FakeAdapter()
    use_fake_tmux(adapter)
    monkeypatch.setattr(ce_cli.launch_runtime, "_confirm_pack", lambda r: True)
    ret = ce_cli.main(["launch", "--harness", "claude", "--claude-arg=--bare"])
    assert ret != 0
    assert adapter.spawned == []
    err = capsys.readouterr().err
    assert "G6-LAUNCH-CLAUDE-REFUSED" in err
    assert "CC-D-1" in err


def test_cli_launch_refuses_claude_skip_perms_without_pack(use_fake_tmux, monkeypatch, capsys):
    adapter = FakeAdapter()
    use_fake_tmux(adapter)
    monkeypatch.setattr(ce_cli.launch_runtime, "_confirm_pack", lambda r: False)
    ret = ce_cli.main(
        ["launch", "--harness", "claude", "--claude-arg=--dangerously-skip-permissions"]
    )
    assert ret != 0
    assert adapter.spawned == []
    assert "CC-D-6" in capsys.readouterr().err


def test_cli_launch_pins_governed_command(use_fake_tmux, monkeypatch):
    adapter = FakeAdapter()
    use_fake_tmux(adapter)
    monkeypatch.setattr(ce_cli.launch_runtime, "_confirm_pack", lambda r: True)
    ret = ce_cli.main(
        ["launch", "--harness", "claude", "--mcp-config", ".hermes/s/mcp/ce-mcp.json"]
    )
    assert ret == 0
    (_sess, _win, cmd) = adapter.spawned[-1]
    # ce-ops#26: the pane runs the sentinel wrapper; the governed argv is INSIDE it.
    import shlex
    from pathlib import Path

    assert cmd[0] == "/bin/sh"
    lines = Path(cmd[1]).read_text().splitlines()
    idx = next(i for i, line in enumerate(lines) if line == "code=$?")
    inner = shlex.split(lines[idx - 1])
    assert "--setting-sources" in inner and "project" in inner and "--strict-mcp-config" in inner


def test_cli_launch_dry_run_still_pure(use_fake_tmux):
    adapter = FakeAdapter()
    use_fake_tmux(adapter)
    assert ce_cli.main(["launch", "--harness", "claude", "--dry-run", "--json"]) == 0
    assert adapter.spawned == []


def test_cli_codex_dry_run_json_uses_governed_command(use_fake_tmux, monkeypatch, capsys):
    adapter = FakeAdapter()
    use_fake_tmux(adapter)
    monkeypatch.setattr(
        ce_cli.launch_runtime.codex_launch_spec, "detect_config_bypass_mode", lambda: "config"
    )
    ret = ce_cli.main([
        "launch", "--harness", "codex", "--codex-arg=--model", "--codex-arg", "gpt-5",
        "--claude-arg=--bare", "--dry-run", "--json",
    ])
    assert ret == 0
    payload = json.loads(capsys.readouterr().out)
    command = payload["plan"]["command"]
    assert command[:2] == ["env", "-u"]
    assert command[-3:] == ["codex", "--model", "gpt-5"]
    assert "--bare" not in command
    assert payload["plan"]["codex_bypass_mode"] == "config"


def test_cli_codex_refuses_non_allowlisted_arg(use_fake_tmux, monkeypatch, capsys):
    adapter = FakeAdapter()
    use_fake_tmux(adapter)
    monkeypatch.setattr(
        ce_cli.launch_runtime.codex_launch_spec, "detect_config_bypass_mode", lambda: "config"
    )
    ret = ce_cli.main(["launch", "--harness", "codex", "--codex-arg=--foo"])
    assert ret != 0
    assert adapter.spawned == []
    assert "CDX-D-7" in capsys.readouterr().err
