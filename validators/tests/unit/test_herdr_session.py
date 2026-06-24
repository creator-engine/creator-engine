"""Unit tests for the live herdr-ce subprocess/socket seam (ce-ops#217 U3)."""

from __future__ import annotations

import json
import hashlib
import subprocess
from collections.abc import Mapping, Sequence

import pytest

from creator_engine_validator.runner import herdr_session as hs


class FakeRunner:
    def __init__(self, *, read_outputs: Sequence[str] | None = None) -> None:
        self.calls: list[tuple[list[str], dict[str, str]]] = []
        self.read_outputs = list(read_outputs or [])

    def run(
        self,
        argv: Sequence[str],
        *,
        env: Mapping[str, str] | None = None,
    ) -> subprocess.CompletedProcess[str]:
        args = list(argv)
        self.calls.append((args, dict(env or {})))
        if args[1:3] == ["workspace", "create"]:
            payload = {
                "result": {
                    "type": "workspace_created",
                    "workspace": {"workspace_id": "workspace-1"},
                    "root_pane": {"pane_id": "pane-1"},
                }
            }
        elif args[1:3] == ["pane", "split"]:
            payload = {"pane_id": "pane-1"}
        elif args[1:3] == ["pane", "run"]:
            return subprocess.CompletedProcess(args, 0, "", "")
        elif args[1:3] == ["pane", "read"]:
            stdout = self.read_outputs.pop(0) if self.read_outputs else "recent output"
            return subprocess.CompletedProcess(args, 0, stdout, "")
        elif args[1:3] == ["pane", "send-text"]:
            return subprocess.CompletedProcess(args, 0, "", "")
        elif args[1:3] == ["pane", "send-keys"]:
            return subprocess.CompletedProcess(args, 0, "", "")
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
        surface_ref="herdr-surface-78e9ef9dba13817d88584fe75af1bffe",
        pid=4242,
        workspace_id="w0",
    )
    assert pane.pane_id == "p0"
    assert pane.surface_ref == "herdr-surface-78e9ef9dba13817d88584fe75af1bffe"
    assert pane.pid == 4242
    assert pane.workspace_id == "w0"


def test_spawn_pane_drives_workspace_create_root_pane_and_run_over_socket_env() -> None:
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
        surface_ref="herdr-surface-918aa1506d296ee1a72da70227854392",
        pid=None,
        workspace_id="workspace-1",
    )
    assert "/run/ce/herdr/control.sock" not in pane.surface_ref
    assert [call[0] for call in runner.calls] == [
        [
            "/opt/herdr",
            "workspace",
            "create",
            "--cwd",
            "/worktree",
            "--label",
            "gate3-lane",
            "--env",
            "CE_LEDGER_ROOT=/ledger",
        ],
        ["/opt/herdr", "pane", "run", "pane-1", "/bin/sh wrapper.sh"],
    ]
    assert all(
        env == {hs.HERDR_SOCKET_ENV: "/run/ce/herdr/control.sock"}
        for _, env in runner.calls
    )


def test_dispatcher_run_and_send_target_workspace_root_pane() -> None:
    runner = FakeRunner()
    session = hs.HerdrSession(
        socket_path="/run/ce/herdr/control.sock",
        herdr_binary="/opt/herdr",
        runner=runner,
    )

    pane = session.spawn_pane(command=["/bin/sh", "wrapper.sh"], cwd="/worktree")
    session.send(pane, "printf ready\\n", submit_settle_s=0, submit_poll_interval_s=0)

    run_call = runner.calls[1][0]
    send_call = runner.calls[2][0]

    assert pane.pane_id == "pane-1"
    assert run_call == ["/opt/herdr", "pane", "run", "pane-1", "/bin/sh wrapper.sh"]
    assert send_call == ["/opt/herdr", "pane", "send-text", "pane-1", "printf ready\\n"]
    assert run_call[3] == pane.pane_id
    assert send_call[3] == pane.pane_id


def test_create_workspace_returns_nested_workspace_and_root_pane_ids() -> None:
    runner = FakeRunner()
    session = hs.HerdrSession(
        socket_path="/run/ce/herdr/control.sock",
        herdr_binary="/opt/herdr",
        runner=runner,
    )

    workspace = session.create_workspace(
        cwd="/worktree",
        label="gate3-lane",
        env={"B": "2", "A": "1"},
    )

    assert workspace == hs.HerdrWorkspace(
        workspace_id="workspace-1",
        root_pane_id="pane-1",
    )
    assert runner.calls == [
        (
            [
                "/opt/herdr",
                "workspace",
                "create",
                "--cwd",
                "/worktree",
                "--label",
                "gate3-lane",
                "--env",
                "A=1",
                "--env",
                "B=2",
            ],
            {hs.HERDR_SOCKET_ENV: "/run/ce/herdr/control.sock"},
        )
    ]


def test_observe_uses_pane_read_recent_text_stdout_and_wait_uses_controller_socket() -> None:
    runner = FakeRunner()
    session = hs.HerdrSession(
        socket_path="/run/ce/herdr/control.sock",
        herdr_binary="herdr",
        runner=runner,
    )
    pane = hs.HerdrPane(
        pane_id="pane-1",
        surface_ref="herdr-surface-918aa1506d296ee1a72da70227854392",
    )

    assert session.observe(pane, lines=40, output_format="ansi") == b"recent output"
    assert session.wait_agent_status(pane) == {"status": "ready", "pane_id": "pane-1"}

    assert runner.calls[0][0] == [
        "herdr",
        "pane",
        "read",
        "pane-1",
        "--source",
        "recent",
        "--lines",
        "40",
        "--format",
        "ansi",
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


def test_send_text_uses_controller_socket_and_does_not_expose_socket_to_seat_env_or_terminal() -> None:
    runner = FakeRunner()
    session = hs.HerdrSession(
        socket_path="/run/ce/herdr/control.sock",
        herdr_binary="/opt/herdr",
        runner=runner,
    )
    pane = hs.HerdrPane(
        pane_id="pane-1",
        surface_ref="herdr-surface-918aa1506d296ee1a72da70227854392",
    )
    terminal = {
        "kind": hs.HERDR_TERMINAL_KIND,
        "surface_ref": pane.surface_ref,
        "pane_id": pane.pane_id,
    }

    session.send(pane, b"printf hello\\n", submit_settle_s=0, submit_poll_interval_s=0)

    assert runner.calls == [
        (
            ["/opt/herdr", "pane", "send-text", "pane-1", "printf hello\\n"],
            {hs.HERDR_SOCKET_ENV: "/run/ce/herdr/control.sock"},
        ),
        (
            ["/opt/herdr", "pane", "send-keys", "pane-1", "Enter"],
            {hs.HERDR_SOCKET_ENV: "/run/ce/herdr/control.sock"},
        ),
        (
            [
                "/opt/herdr",
                "pane",
                "read",
                "pane-1",
                "--source",
                "recent-unwrapped",
                "--format",
                "text",
            ],
            {hs.HERDR_SOCKET_ENV: "/run/ce/herdr/control.sock"},
        ),
    ]
    assert "/run/ce/herdr/control.sock" not in repr(terminal)
    assert hs.HERDR_SOCKET_ENV not in terminal


def test_send_treats_submitted_text_in_scrollback_with_empty_input_as_committed() -> None:
    runner = FakeRunner(read_outputs=["printf ready\n"])
    session = hs.HerdrSession(
        socket_path="/run/ce/herdr/control.sock",
        herdr_binary="/opt/herdr",
        runner=runner,
    )
    pane = hs.HerdrPane(
        pane_id="pane-1",
        surface_ref="herdr-surface-918aa1506d296ee1a72da70227854392",
    )

    session.send(pane, "printf ready", submit_settle_s=0, submit_poll_interval_s=0)

    assert [call[0] for call in runner.calls] == [
        ["/opt/herdr", "pane", "send-text", "pane-1", "printf ready"],
        ["/opt/herdr", "pane", "send-keys", "pane-1", "Enter"],
        [
            "/opt/herdr",
            "pane",
            "read",
            "pane-1",
            "--source",
            "recent-unwrapped",
            "--format",
            "text",
        ],
    ]


def test_send_fails_closed_when_submitted_text_remains_on_active_input_line() -> None:
    runner = FakeRunner(
        read_outputs=[
            "scrollback\nprintf ready",
            "scrollback\nprintf ready",
            "scrollback\nprintf ready",
        ]
    )
    session = hs.HerdrSession(herdr_binary="/opt/herdr", runner=runner)
    pane = hs.HerdrPane(
        pane_id="pane-1",
        surface_ref="herdr-surface-918aa1506d296ee1a72da70227854392",
    )

    with pytest.raises(hs.HerdrCommandError, match="did not commit"):
        session.send(pane, "printf ready", submit_settle_s=0, submit_poll_interval_s=0)

    assert [call[0] for call in runner.calls].count(
        ["/opt/herdr", "pane", "send-keys", "pane-1", "Enter"]
    ) == hs.HERDR_SEND_SUBMIT_MAX_ATTEMPTS


def test_deliver_brief_verifies_marker_rendered_after_commit() -> None:
    body = "Wave-B brief\nDo the focused work."
    marker = f"==CE-BRIEF-SHA256:{hashlib.sha256(body.encode('utf-8')).hexdigest()}=="
    runner = FakeRunner(read_outputs=["prompt cleared", f"rendered\n{marker}"])
    session = hs.HerdrSession(herdr_binary="/opt/herdr", runner=runner)
    pane = hs.HerdrPane(
        pane_id="pane-1",
        surface_ref="herdr-surface-918aa1506d296ee1a72da70227854392",
    )

    assert session.deliver_brief(
        pane,
        body,
        render_timeout_s=0,
        render_poll_interval_s=0,
        sleep=lambda _seconds: None,
    ) == marker

    send_text_call = runner.calls[0][0]
    assert send_text_call[:4] == ["/opt/herdr", "pane", "send-text", "pane-1"]
    assert send_text_call[4].endswith(f"\n{marker}")


def test_deliver_brief_fails_closed_when_marker_does_not_render() -> None:
    runner = FakeRunner(read_outputs=["prompt cleared", "rendered without marker"])
    session = hs.HerdrSession(herdr_binary="/opt/herdr", runner=runner)
    pane = hs.HerdrPane(
        pane_id="pane-1",
        surface_ref="herdr-surface-918aa1506d296ee1a72da70227854392",
    )

    with pytest.raises(hs.HerdrCommandError, match="brief marker did not render"):
        session.deliver_brief(
            pane,
            "brief body",
            render_timeout_s=0,
            render_poll_interval_s=0,
            sleep=lambda _seconds: None,
        )


def test_deliver_brief_marker_hash_matches_brief_body_before_marker() -> None:
    body = "line one\nline two\n"
    runner = FakeRunner(read_outputs=["prompt cleared", "rendered"])
    session = hs.HerdrSession(herdr_binary="/opt/herdr", runner=runner)
    pane = hs.HerdrPane(
        pane_id="pane-1",
        surface_ref="herdr-surface-918aa1506d296ee1a72da70227854392",
    )
    marker = f"==CE-BRIEF-SHA256:{hashlib.sha256(body.encode('utf-8')).hexdigest()}=="
    runner.read_outputs[1] = f"rendered\n{marker}"

    session.deliver_brief(
        pane,
        body,
        render_timeout_s=0,
        render_poll_interval_s=0,
        sleep=lambda _seconds: None,
    )

    payload = runner.calls[0][0][4]
    assert payload == f"{body}{marker}"


def test_send_non_utf8_bytes_remain_fail_closed() -> None:
    session = hs.HerdrSession(runner=FakeRunner())
    pane = hs.HerdrPane(
        pane_id="p0",
        surface_ref="herdr-surface-78e9ef9dba13817d88584fe75af1bffe",
    )
    with pytest.raises(hs.HerdrCommandError, match="only accepts UTF-8 text"):
        session.send(pane, b"\xff")


def test_socket_env_names_are_never_passed_into_governed_workspace() -> None:
    session = hs.HerdrSession(runner=FakeRunner())
    for env_name in (hs.HERDR_SOCKET_ENV, hs.LEGACY_HERDR_SOCKET_ENV):
        with pytest.raises(hs.HerdrCommandError, match=env_name):
            session.create_workspace(
                cwd="/worktree",
                label="lane",
                env={env_name: "/run/ce/herdr/control.sock"},
            )
        with pytest.raises(hs.HerdrCommandError, match=env_name):
            session.spawn_pane(
                command=["true"],
                cwd="/worktree",
                env={env_name: "/run/ce/herdr/control.sock"},
                label="lane",
            )


def test_socket_env_names_are_never_passed_into_governed_seat_pane() -> None:
    session = hs.HerdrSession(runner=FakeRunner())
    for env_name in (hs.HERDR_SOCKET_ENV, hs.LEGACY_HERDR_SOCKET_ENV):
        with pytest.raises(hs.HerdrCommandError, match=env_name):
            session.run_pane(
                pane_id="pane-1",
                command=["true"],
                env={env_name: "/run/ce/herdr/control.sock"},
            )
        with pytest.raises(hs.HerdrCommandError, match=env_name):
            session.split_pane(
                pane_id="pane-1",
                env={env_name: "/run/ce/herdr/control.sock"},
            )


def test_run_pane_uses_real_command_shape_and_rejects_unsupported_cwd_env() -> None:
    runner = FakeRunner()
    session = hs.HerdrSession(
        socket_path="/run/ce/herdr/control.sock",
        herdr_binary="/opt/herdr",
        runner=runner,
    )

    assert session.run_pane(pane_id="pane-1", command=["/bin/sh", "wrapper.sh"]) is None

    assert runner.calls == [
        (
            ["/opt/herdr", "pane", "run", "pane-1", "/bin/sh wrapper.sh"],
            {hs.HERDR_SOCKET_ENV: "/run/ce/herdr/control.sock"},
        )
    ]
    with pytest.raises(hs.HerdrCommandError, match="does not accept cwd"):
        session.run_pane(pane_id="pane-1", command=["true"], cwd="/worktree")
    with pytest.raises(hs.HerdrCommandError, match="does not accept env"):
        session.run_pane(pane_id="pane-1", command=["true"], env={"CE_LEDGER_ROOT": "/ledger"})


def test_run_pane_shell_quotes_command_sequence_as_one_command_string() -> None:
    runner = FakeRunner()
    session = hs.HerdrSession(herdr_binary="/opt/herdr", runner=runner)

    session.run_pane(pane_id="pane-1", command=["sh", "-c", "printf ce-herdr-live"])

    assert runner.calls[0][0] == [
        "/opt/herdr",
        "pane",
        "run",
        "pane-1",
        "sh -c 'printf ce-herdr-live'",
    ]


def test_malformed_json_raises_command_error_not_name_error() -> None:
    class BadJson(FakeRunner):
        def run(self, argv, *, env=None):
            return subprocess.CompletedProcess(list(argv), 0, "not-json", "")

    session = hs.HerdrSession(runner=BadJson())
    with pytest.raises(hs.HerdrCommandError, match="non-JSON output"):
        session.create_workspace(cwd="/worktree", label="lane")


def test_command_failure_is_reported() -> None:
    class Boom(FakeRunner):
        def run(self, argv, *, env=None):
            return subprocess.CompletedProcess(list(argv), 7, "", "boom")

    session = hs.HerdrSession(runner=Boom())
    with pytest.raises(hs.HerdrCommandError):
        session.create_workspace(cwd="/worktree", label="lane")


def test_not_wired_is_a_notimplementederror() -> None:
    assert issubclass(hs.HerdrNotWired, NotImplementedError)
    assert issubclass(hs.HerdrNotWired, hs.HerdrSessionError)


def test_close_is_idempotent_and_does_not_raise() -> None:
    session = hs.HerdrSession()
    session.close()
    session.close()
