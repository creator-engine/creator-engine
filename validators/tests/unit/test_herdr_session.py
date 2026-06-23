"""Unit tests for the live herdr-ce subprocess/socket seam (ce-ops#217 U3)."""

from __future__ import annotations

import json
import subprocess
from collections.abc import Mapping, Sequence

import pytest

from creator_engine_validator.runner import herdr_session as hs


class FakeRunner:
    def __init__(self) -> None:
        self.calls: list[tuple[list[str], dict[str, str]]] = []

    def run(
        self,
        argv: Sequence[str],
        *,
        env: Mapping[str, str] | None = None,
    ) -> subprocess.CompletedProcess[str]:
        args = list(argv)
        self.calls.append((args, dict(env or {})))
        if args[1:3] == ["workspace", "create"]:
            payload = {"workspace_id": "workspace-1"}
        elif args[1:3] == ["pane", "split"]:
            payload = {"pane_id": "pane-1"}
        elif args[1:3] == ["pane", "run"]:
            payload = {"pid": 4242}
        elif args[1:3] == ["pane", "read"]:
            payload = {"output": "recent output"}
        elif args[1:3] == ["wait", "agent-status"]:
            payload = {"status": "ready", "pane_id": "pane-1"}
        else:  # pragma: no cover - protects test fixtures if the command map drifts
            return subprocess.CompletedProcess(args, 2, "", "unexpected command")
        return subprocess.CompletedProcess(args, 0, json.dumps(payload), "")


def test_terminal_kind_constant() -> None:
    assert hs.HERDR_TERMINAL_KIND == "herdr"


def test_pane_handle_shape() -> None:
    pane = hs.HerdrPane(
        pane_id="p0",
        surface_ref="/run/ce/herdr.sock",
        pid=4242,
        workspace_id="w0",
    )
    assert pane.pane_id == "p0"
    assert pane.surface_ref == "/run/ce/herdr.sock"
    assert pane.pid == 4242
    assert pane.workspace_id == "w0"


def test_spawn_pane_drives_workspace_split_and_run_over_socket_env() -> None:
    runner = FakeRunner()
    session = hs.HerdrSession(
        socket_path="/run/ce/herdr/control.sock",
        herdr_binary="/opt/herdr",
        runner=runner,
    )

    pane = session.spawn_pane(
        command=["/bin/sh", "wrapper.sh"],
        cwd="/worktree",
        env={"CE_LEDGER_ROOT": "/ledger"},
        label="gate3-lane",
    )

    assert pane == hs.HerdrPane(
        pane_id="pane-1",
        surface_ref="/run/ce/herdr/control.sock",
        pid=4242,
        workspace_id="workspace-1",
    )
    assert [call[0] for call in runner.calls] == [
        [
            "/opt/herdr",
            "workspace",
            "create",
            "--cwd",
            "/worktree",
            "--label",
            "gate3-lane",
            "--json",
        ],
        ["/opt/herdr", "pane", "split", "--workspace", "workspace-1", "--json"],
        [
            "/opt/herdr",
            "pane",
            "run",
            "pane-1",
            "--cwd",
            "/worktree",
            "--env",
            "CE_LEDGER_ROOT=/ledger",
            "--json",
            "--",
            "/bin/sh",
            "wrapper.sh",
        ],
    ]
    assert all(
        env == {hs.HERDR_SOCKET_ENV: "/run/ce/herdr/control.sock"}
        for _, env in runner.calls
    )


def test_observe_and_wait_agent_status_use_controller_socket() -> None:
    runner = FakeRunner()
    session = hs.HerdrSession(
        socket_path="/run/ce/herdr/control.sock",
        herdr_binary="herdr",
        runner=runner,
    )
    pane = hs.HerdrPane(pane_id="pane-1", surface_ref="/run/ce/herdr/control.sock")

    assert session.observe(pane) == b"recent output"
    assert session.wait_agent_status(pane) == {"status": "ready", "pane_id": "pane-1"}

    assert runner.calls[0][0] == [
        "herdr",
        "pane",
        "read",
        "pane-1",
        "--source",
        "recent-unwrapped",
        "--json",
    ]
    assert runner.calls[1][0] == [
        "herdr",
        "wait",
        "agent-status",
        "--pane",
        "pane-1",
        "--status",
        "ready",
        "--json",
    ]
    assert all(
        env == {hs.HERDR_SOCKET_ENV: "/run/ce/herdr/control.sock"}
        for _, env in runner.calls
    )


def test_socket_env_is_never_passed_into_governed_seat() -> None:
    session = hs.HerdrSession(runner=FakeRunner())
    with pytest.raises(hs.HerdrCommandError):
        session.run_pane(
            pane_id="pane-1",
            command=["true"],
            env={hs.HERDR_SOCKET_ENV: "/run/ce/herdr/control.sock"},
        )


def test_command_failure_is_reported() -> None:
    class Boom(FakeRunner):
        def run(self, argv, *, env=None):
            return subprocess.CompletedProcess(list(argv), 7, "", "boom")

    session = hs.HerdrSession(runner=Boom())
    with pytest.raises(hs.HerdrCommandError):
        session.create_workspace(cwd="/worktree", label="lane")


def test_send_remains_fail_closed_until_u4_attribution() -> None:
    session = hs.HerdrSession()
    pane = hs.HerdrPane(pane_id="p0", surface_ref="/run/ce/herdr.sock")
    with pytest.raises(hs.HerdrNotWired):
        session.send(pane, b"steer")


def test_not_wired_is_a_notimplementederror() -> None:
    assert issubclass(hs.HerdrNotWired, NotImplementedError)
    assert issubclass(hs.HerdrNotWired, hs.HerdrSessionError)


def test_close_is_idempotent_and_does_not_raise() -> None:
    session = hs.HerdrSession()
    session.close()
    session.close()
