"""Unit tests for the live herdr-ce subprocess/socket seam (ce-ops#217 U3)."""

from __future__ import annotations

import json
import hashlib
import subprocess
import threading
import time
from collections.abc import Callable, Mapping, Sequence
from pathlib import Path

import pytest

from creator_engine_validator.runner import herdr_session as hs


class FakeRunner:
    def __init__(
        self,
        *,
        read_outputs: Sequence[str] | None = None,
        foreground_returncode: int = 0,
        foreground_stderr: str = "",
        on_foreground: Callable[[list[str], dict[str, str]], None] | None = None,
    ) -> None:
        self.calls: list[tuple[list[str], dict[str, str]]] = []
        self.foreground_calls: list[tuple[list[str], dict[str, str]]] = []
        self.timeouts: list[float | None] = []
        self.read_outputs = list(read_outputs or [])
        self.foreground_returncode = foreground_returncode
        self.foreground_stderr = foreground_stderr
        self.on_foreground = on_foreground

    def run(
        self,
        argv: Sequence[str],
        *,
        env: Mapping[str, str] | None = None,
        timeout_s: float | None = None,
    ) -> subprocess.CompletedProcess[str]:
        args = list(argv)
        self.calls.append((args, dict(env or {})))
        self.timeouts.append(timeout_s)
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

    def run_foreground(
        self,
        argv: Sequence[str],
        *,
        env: Mapping[str, str] | None = None,
    ) -> subprocess.CompletedProcess[str]:
        args = list(argv)
        env_dict = dict(env or {})
        self.foreground_calls.append((args, env_dict))
        if self.on_foreground is not None:
            self.on_foreground(args, env_dict)
        return subprocess.CompletedProcess(
            args,
            self.foreground_returncode,
            "",
            self.foreground_stderr,
        )


@pytest.fixture(autouse=True)
def isolate_default_steer_lock_dir(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        hs,
        "_default_steer_lock_dir",
        lambda: tmp_path / "herdr-steer-locks",
    )


class MutableClock:
    def __init__(self, current: float = 0.0) -> None:
        self.current = current

    def __call__(self) -> float:
        return self.current


def advance_clock(clock: MutableClock) -> Callable[[float], None]:
    def sleep(seconds: float) -> None:
        clock.current += seconds

    return sleep


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


def test_unbounded_run_omits_timeout_kwarg_for_legacy_injected_runner() -> None:
    class LegacyRunner:
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
            return subprocess.CompletedProcess(args, 0, "legacy output", "")

    runner = LegacyRunner()
    session = hs.HerdrSession(
        socket_path="/run/ce/herdr/control.sock",
        herdr_binary="herdr",
        runner=runner,
    )
    pane = hs.HerdrPane(
        pane_id="pane-1",
        surface_ref="herdr-surface-918aa1506d296ee1a72da70227854392",
    )

    assert session.observe(pane, lines=5) == b"legacy output"
    assert runner.calls == [
        (
            [
                "herdr",
                "pane",
                "read",
                "pane-1",
                "--source",
                "recent",
                "--lines",
                "5",
                "--format",
                "text",
            ],
            {hs.HERDR_SOCKET_ENV: "/run/ce/herdr/control.sock"},
        )
    ]


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


def test_deliver_brief_verifies_agent_reaction_after_commit() -> None:
    body = "Wave-B brief\nDo the focused work."
    marker = f"==CE-BRIEF-SHA256:{hashlib.sha256(body.encode('utf-8')).hexdigest()}=="
    runner = FakeRunner(read_outputs=["Ready", "prompt cleared", "Working on it"])
    session = hs.HerdrSession(herdr_binary="/opt/herdr", runner=runner)
    pane = hs.HerdrPane(
        pane_id="pane-1",
        surface_ref="herdr-surface-918aa1506d296ee1a72da70227854392",
    )

    assert session.deliver_brief(
        pane,
        body,
        reaction_timeout_s=1,
        reaction_poll_interval_s=0,
        sleep=lambda _seconds: None,
    ) == marker

    send_text_call = next(
        call[0] for call in runner.calls if call[0][1:3] == ["pane", "send-text"]
    )
    assert send_text_call[:4] == ["/opt/herdr", "pane", "send-text", "pane-1"]
    assert send_text_call[4].endswith(f"\n{marker}")


def test_deliver_brief_baseline_read_is_bounded_by_reaction_timeout() -> None:
    clock = MutableClock()
    runner = FakeRunner(read_outputs=["Ready", "prompt cleared", "Working"])
    session = hs.HerdrSession(herdr_binary="/opt/herdr", runner=runner)
    pane = hs.HerdrPane(
        pane_id="pane-1",
        surface_ref="herdr-surface-918aa1506d296ee1a72da70227854392",
    )

    session.deliver_brief(
        pane,
        "brief body",
        reaction_timeout_s=2.5,
        reaction_poll_interval_s=0,
        sleep=lambda _seconds: None,
        clock=clock,
    )

    read_timeouts = [
        timeout
        for (call, _env), timeout in zip(runner.calls, runner.timeouts, strict=True)
        if call[1:3] == ["pane", "read"]
    ]
    assert read_timeouts[0] == 2.5


def test_deliver_brief_reaction_deadline_starts_before_baseline_read() -> None:
    clock = MutableClock(current=100.0)

    class BaselineConsumesTime(FakeRunner):
        def __init__(self) -> None:
            super().__init__(read_outputs=["Ready", "prompt cleared", "Working"])
            self._read_count = 0

        def run(self, argv, *, env=None, timeout_s=None):
            completed = super().run(argv, env=env, timeout_s=timeout_s)
            if list(argv)[1:3] == ["pane", "read"]:
                self._read_count += 1
                if self._read_count == 1:
                    clock.current += 2.0
            return completed

    runner = BaselineConsumesTime()
    session = hs.HerdrSession(herdr_binary="/opt/herdr", runner=runner)
    pane = hs.HerdrPane(
        pane_id="pane-1",
        surface_ref="herdr-surface-918aa1506d296ee1a72da70227854392",
    )

    session.deliver_brief(
        pane,
        "brief body",
        reaction_timeout_s=5.0,
        reaction_poll_interval_s=0,
        sleep=lambda _seconds: None,
        clock=clock,
    )

    read_timeouts = [
        timeout
        for (call, _env), timeout in zip(runner.calls, runner.timeouts, strict=True)
        if call[1:3] == ["pane", "read"]
    ]
    assert read_timeouts == [5.0, 3.0, 3.0]


def test_deliver_brief_fails_closed_when_agent_does_not_react() -> None:
    clock = MutableClock()
    runner = FakeRunner(read_outputs=["Ready", "prompt cleared", "Ready"])
    session = hs.HerdrSession(herdr_binary="/opt/herdr", runner=runner)
    pane = hs.HerdrPane(
        pane_id="pane-1",
        surface_ref="herdr-surface-918aa1506d296ee1a72da70227854392",
    )

    with pytest.raises(hs.HerdrCommandError, match="did not produce an agent reaction"):
        session.deliver_brief(
            pane,
            "brief body",
            reaction_timeout_s=3,
            reaction_poll_interval_s=1,
            sleep=advance_clock(clock),
            clock=clock,
        )
    read_timeouts = [
        timeout
        for (call, _env), timeout in zip(runner.calls, runner.timeouts, strict=True)
        if call[1:3] == ["pane", "read"]
    ]
    assert read_timeouts == [3, 1, 1]


@pytest.mark.parametrize("reaction_timeout_s", [0, -0.1])
def test_deliver_brief_rejects_non_positive_reaction_timeout(
    reaction_timeout_s: float,
) -> None:
    session = hs.HerdrSession(herdr_binary="/opt/herdr", runner=FakeRunner())
    pane = hs.HerdrPane(
        pane_id="pane-1",
        surface_ref="herdr-surface-918aa1506d296ee1a72da70227854392",
    )

    with pytest.raises(hs.HerdrCommandError, match="reaction timeout must be positive"):
        session.deliver_brief(
            pane,
            "brief body",
            reaction_timeout_s=reaction_timeout_s,
            reaction_poll_interval_s=0,
            sleep=lambda _seconds: None,
        )


def test_deliver_brief_does_not_accept_marker_echo_without_agent_reaction() -> None:
    clock = MutableClock()
    body = "brief body"
    marker = f"==CE-BRIEF-SHA256:{hashlib.sha256(body.encode('utf-8')).hexdigest()}=="
    runner = FakeRunner(read_outputs=["Ready", "prompt cleared", f"rendered\n{marker}"])
    session = hs.HerdrSession(herdr_binary="/opt/herdr", runner=runner)
    pane = hs.HerdrPane(
        pane_id="pane-1",
        surface_ref="herdr-surface-918aa1506d296ee1a72da70227854392",
    )

    with pytest.raises(hs.HerdrCommandError, match="did not produce an agent reaction"):
        session.deliver_brief(
            pane,
            body,
            reaction_timeout_s=3,
            reaction_poll_interval_s=1,
            sleep=advance_clock(clock),
            clock=clock,
        )


def test_deliver_brief_does_not_accept_echoed_brief_reaction_words() -> None:
    clock = MutableClock()
    body = "Please start working and processing this brief."
    marker = f"==CE-BRIEF-SHA256:{hashlib.sha256(body.encode('utf-8')).hexdigest()}=="
    runner = FakeRunner(read_outputs=["Ready", "prompt cleared", f"{body}\n{marker}"])
    session = hs.HerdrSession(herdr_binary="/opt/herdr", runner=runner)
    pane = hs.HerdrPane(
        pane_id="pane-1",
        surface_ref="herdr-surface-918aa1506d296ee1a72da70227854392",
    )

    with pytest.raises(hs.HerdrCommandError, match="did not produce an agent reaction"):
        session.deliver_brief(
            pane,
            body,
            reaction_timeout_s=3,
            reaction_poll_interval_s=1,
            sleep=advance_clock(clock),
            clock=clock,
        )


def test_deliver_brief_multi_poll_ignores_echo_then_accepts_agent_reaction() -> None:
    body = "Please start working and processing this brief."
    marker = f"==CE-BRIEF-SHA256:{hashlib.sha256(body.encode('utf-8')).hexdigest()}=="
    runner = FakeRunner(
        read_outputs=[
            "Ready",
            "prompt cleared",
            f"{body}\n{marker}",
            "Codex session rollout started",
        ]
    )
    session = hs.HerdrSession(herdr_binary="/opt/herdr", runner=runner)
    pane = hs.HerdrPane(
        pane_id="pane-1",
        surface_ref="herdr-surface-918aa1506d296ee1a72da70227854392",
    )

    assert session.deliver_brief(
        pane,
        body,
        reaction_timeout_s=1,
        reaction_poll_interval_s=0,
        sleep=lambda _seconds: None,
    ) == marker

    read_calls = [call[0] for call in runner.calls if call[0][1:3] == ["pane", "read"]]
    assert len(read_calls) == 4


def test_deliver_brief_preserves_genuine_reaction_with_brief_line_prefix() -> None:
    body = "Working"
    marker = f"==CE-BRIEF-SHA256:{hashlib.sha256(body.encode('utf-8')).hexdigest()}=="
    runner = FakeRunner(
        read_outputs=[
            "Ready",
            "prompt cleared",
            f"{body}\n{marker}",
            "Working on it",
        ]
    )
    session = hs.HerdrSession(herdr_binary="/opt/herdr", runner=runner)
    pane = hs.HerdrPane(
        pane_id="pane-1",
        surface_ref="herdr-surface-918aa1506d296ee1a72da70227854392",
    )

    assert session.deliver_brief(
        pane,
        body,
        reaction_timeout_s=1,
        reaction_poll_interval_s=0,
        sleep=lambda _seconds: None,
    ) == marker


def test_deliver_brief_marker_hash_matches_brief_body_before_marker() -> None:
    body = "line one\nline two\n"
    runner = FakeRunner(read_outputs=["Ready", "prompt cleared", "Working"])
    session = hs.HerdrSession(herdr_binary="/opt/herdr", runner=runner)
    pane = hs.HerdrPane(
        pane_id="pane-1",
        surface_ref="herdr-surface-918aa1506d296ee1a72da70227854392",
    )
    marker = f"==CE-BRIEF-SHA256:{hashlib.sha256(body.encode('utf-8')).hexdigest()}=="

    session.deliver_brief(
        pane,
        body,
        reaction_timeout_s=1,
        reaction_poll_interval_s=0,
        sleep=lambda _seconds: None,
    )

    send_text_call = next(
        call[0] for call in runner.calls if call[0][1:3] == ["pane", "send-text"]
    )
    payload = send_text_call[4]
    assert payload == f"{body}{marker}"


@pytest.mark.parametrize(
    ("pane_text", "payload", "expected"),
    [
        ("", "", ""),
        ("before\npayload\npayload-tail\nafter", "", "before\npayload\npayload-tail\nafter"),
        ("before\npayload\nafter", "payload", "before\n\nafter"),
        ("before\r\nline one\r\nline two\r\nafter", "line one\nline two", "before\n\nafter"),
        ("brief: working\nagent: Working on it", "working", "brief: \nagent: Working on it"),
    ],
)
def test_without_dispatched_payload_handles_empty_multiline_and_partial_lines(
    pane_text: str,
    payload: str,
    expected: str,
) -> None:
    assert hs.HerdrSession._without_dispatched_payload(pane_text, payload) == expected


@pytest.mark.parametrize(
    ("pane_text", "expected"),
    [
        ("", 0),
        ("Working\nPROCESSING\nthinking", 3),
        ("preworking processingness thinking", 1),
        ("Codex    session rollout\nsession rollout", 2),
    ],
)
def test_agent_reaction_score_handles_empty_multiline_partial_words_and_case(
    pane_text: str,
    expected: int,
) -> None:
    assert hs.HerdrSession._agent_reaction_score(pane_text) == expected


def test_deliver_brief_accepts_injected_reaction_signal_set() -> None:
    runner = FakeRunner(read_outputs=["Ready", "prompt cleared", "Acknowledged"])
    session = hs.HerdrSession(
        herdr_binary="/opt/herdr",
        runner=runner,
        agent_reaction_signals=("acknowledged",),
    )
    pane = hs.HerdrPane(
        pane_id="pane-1",
        surface_ref="herdr-surface-918aa1506d296ee1a72da70227854392",
    )

    assert session.deliver_brief(
        pane,
        "brief body",
        reaction_timeout_s=1,
        reaction_poll_interval_s=0,
        sleep=lambda _seconds: None,
    ) == hs.HerdrSession._brief_marker("brief body")


def test_agent_reaction_signals_replace_defaults_and_reject_empty_sequence() -> None:
    with pytest.raises(hs.HerdrCommandError, match="non-empty sequence"):
        hs.HerdrSession(
            herdr_binary="/opt/herdr",
            runner=FakeRunner(),
            agent_reaction_signals=(),
        )

    clock = MutableClock()
    runner = FakeRunner(read_outputs=["Ready", "prompt cleared", "Working"])
    session = hs.HerdrSession(
        herdr_binary="/opt/herdr",
        runner=runner,
        agent_reaction_signals=("acknowledged",),
    )
    pane = hs.HerdrPane(
        pane_id="pane-1",
        surface_ref="herdr-surface-918aa1506d296ee1a72da70227854392",
    )

    with pytest.raises(hs.HerdrCommandError, match="did not produce an agent reaction"):
        session.deliver_brief(
            pane,
            "brief body",
            reaction_timeout_s=3,
            reaction_poll_interval_s=1,
            sleep=advance_clock(clock),
            clock=clock,
        )


def test_send_non_utf8_bytes_remain_fail_closed() -> None:
    session = hs.HerdrSession(runner=FakeRunner())
    pane = hs.HerdrPane(
        pane_id="p0",
        surface_ref="herdr-surface-78e9ef9dba13817d88584fe75af1bffe",
    )
    with pytest.raises(hs.HerdrCommandError, match="only accepts UTF-8 text"):
        session.send(pane, b"\xff")


def test_send_defers_before_write_when_operator_is_steering(
    tmp_path: Path,
    caplog: pytest.LogCaptureFixture,
) -> None:
    runner = FakeRunner()
    session = hs.HerdrSession(
        herdr_binary="/opt/herdr",
        runner=runner,
        steer_lock_dir=tmp_path,
    )
    pane = hs.HerdrPane(
        pane_id="pane-1",
        surface_ref="herdr-surface-918aa1506d296ee1a72da70227854392",
    )

    with session._operator_steer_lease(pane):
        with caplog.at_level("WARNING", logger=hs.__name__):
            with pytest.raises(
                hs.HerdrSteeringDeferred,
                match="deferred: operator steering pane pane-1",
            ):
                session.send(pane, "printf ready", submit_settle_s=0)

    assert runner.calls == []
    assert "deferred: operator steering pane pane-1" in caplog.text
    assert caplog.records[-1].action == "herdr_dispatch"
    assert caplog.records[-1].status == "deferred"
    assert caplog.records[-1].reason == "operator steering"
    assert caplog.records[-1].pane_id == "pane-1"
    assert caplog.records[-1].surface_ref == pane.surface_ref


def test_steer_lock_is_per_pane_not_global(tmp_path: Path) -> None:
    runner = FakeRunner(read_outputs=["committed"])
    session = hs.HerdrSession(
        herdr_binary="/opt/herdr",
        runner=runner,
        steer_lock_dir=tmp_path,
    )
    pane_1 = hs.HerdrPane(
        pane_id="pane-1",
        surface_ref="herdr-surface-918aa1506d296ee1a72da70227854392",
    )
    pane_2 = hs.HerdrPane(
        pane_id="pane-2",
        surface_ref="herdr-surface-3d1a629a76f24962a4df6437bd6ab140",
    )

    with session._operator_steer_lease(pane_1):
        session.send(pane_2, "printf ready", submit_settle_s=0, submit_poll_interval_s=0)

    assert runner.calls[0][0] == [
        "/opt/herdr",
        "pane",
        "send-text",
        "pane-2",
        "printf ready",
    ]


def test_observe_is_not_blocked_by_operator_steering(tmp_path: Path) -> None:
    runner = FakeRunner(read_outputs=["read-only output"])
    session = hs.HerdrSession(
        herdr_binary="/opt/herdr",
        runner=runner,
        steer_lock_dir=tmp_path,
    )
    pane = hs.HerdrPane(
        pane_id="pane-1",
        surface_ref="herdr-surface-918aa1506d296ee1a72da70227854392",
    )

    with session._operator_steer_lease(pane):
        assert session.observe(pane, lines=5) == b"read-only output"

    assert runner.calls == [
        (
            [
                "/opt/herdr",
                "pane",
                "read",
                "pane-1",
                "--source",
                "recent",
                "--lines",
                "5",
                "--format",
                "text",
            ],
            {hs.HERDR_SOCKET_ENV: "herdr.sock"},
        )
    ]


def test_expired_operator_steer_lock_self_releases_for_dispatch(tmp_path: Path) -> None:
    now = 1_800_000_000.0
    runner = FakeRunner(read_outputs=["committed"])
    session = hs.HerdrSession(
        herdr_binary="/opt/herdr",
        runner=runner,
        steer_lock_dir=tmp_path,
        clock=lambda: now,
    )
    pane = hs.HerdrPane(
        pane_id="pane-1",
        surface_ref="herdr-surface-918aa1506d296ee1a72da70227854392",
    )
    _lock_path, lease_path = session._steer_lock_paths(pane)
    session._atomic_write_text(
        lease_path,
        json.dumps(
            {
                "kind": "herdr-steer-lock",
                "version": 1,
                "lease_id": "operator-expired",
                "owner": "operator",
                "pane_id": pane.pane_id,
                "surface_ref": pane.surface_ref,
                "status": "active",
                "reason": "operator steering",
                "acquired_at": session._iso_utc(now - 20),
                "refreshed_at": session._iso_utc(now - 20),
                "expires_at": session._iso_utc(now - 10),
            },
            sort_keys=True,
        ),
    )

    session.send(pane, "printf ready", submit_settle_s=0, submit_poll_interval_s=0)

    assert runner.calls[0][0] == [
        "/opt/herdr",
        "pane",
        "send-text",
        "pane-1",
        "printf ready",
    ]
    assert not lease_path.exists()


def test_attach_runs_foreground_pane_attach_with_operator_lease(tmp_path: Path) -> None:
    pane = hs.HerdrPane(
        pane_id="pane-1",
        surface_ref="herdr-surface-918aa1506d296ee1a72da70227854392",
    )
    lease_seen_during_attach: list[dict[str, object]] = []

    def inspect_lease(_args: list[str], _env: dict[str, str]) -> None:
        _lock_path, lease_path = session._steer_lock_paths(pane)
        lease_seen_during_attach.append(json.loads(lease_path.read_text(encoding="utf-8")))

    runner = FakeRunner(on_foreground=inspect_lease)
    session = hs.HerdrSession(
        socket_path="/run/ce/herdr/control.sock",
        herdr_binary="/opt/herdr",
        runner=runner,
        steer_lock_dir=tmp_path,
    )
    _lock_path, lease_path = session._steer_lock_paths(pane)

    session.attach(pane)

    assert runner.calls == []
    assert runner.foreground_calls == [
        (
            ["/opt/herdr", "pane", "attach", "pane-1"],
            {hs.HERDR_SOCKET_ENV: "/run/ce/herdr/control.sock"},
        )
    ]
    assert lease_seen_during_attach[0]["owner"] == "operator"
    assert lease_seen_during_attach[0]["pane_id"] == "pane-1"
    assert lease_seen_during_attach[0]["reason"] == "operator steering"
    assert (
        lease_seen_during_attach[0]["refreshed_at"]
        == lease_seen_during_attach[0]["acquired_at"]
    )
    assert not lease_path.exists()


def test_attach_heartbeat_keeps_operator_lease_live_past_original_ttl(
    tmp_path: Path,
) -> None:
    now = [1_800_000_000.0]
    pane = hs.HerdrPane(
        pane_id="pane-1",
        surface_ref="herdr-surface-918aa1506d296ee1a72da70227854392",
    )
    attach_started = threading.Event()
    lease_refreshed = threading.Event()
    release_attach = threading.Event()
    attach_errors: list[BaseException] = []
    original_expires_at: list[str] = []

    def inspect_long_running_attach(_args: list[str], _env: dict[str, str]) -> None:
        _lock_path, lease_path = session._steer_lock_paths(pane)
        initial = json.loads(lease_path.read_text(encoding="utf-8"))
        original_expires_at.append(str(initial["expires_at"]))
        now[0] += 20.0
        attach_started.set()
        deadline = time.monotonic() + 2.0
        while time.monotonic() < deadline:
            refreshed = json.loads(lease_path.read_text(encoding="utf-8"))
            refreshed_expiry = hs.HerdrSession._parse_iso_utc(refreshed["expires_at"])
            if (
                refreshed["refreshed_at"] != initial["refreshed_at"]
                and refreshed["expires_at"] != original_expires_at[0]
                and refreshed_expiry is not None
                and now[0] < refreshed_expiry
            ):
                lease_refreshed.set()
                break
            time.sleep(0.01)
        release_attach.wait(timeout=2.0)

    runner = FakeRunner(on_foreground=inspect_long_running_attach)
    session = hs.HerdrSession(
        herdr_binary="/opt/herdr",
        runner=runner,
        steer_lock_dir=tmp_path,
        steer_lock_ttl_s=10.0,
        steer_lock_heartbeat_interval_s=0.01,
        clock=lambda: now[0],
    )

    def run_attach() -> None:
        try:
            session.attach(pane)
        except BaseException as exc:  # pragma: no cover - asserted after join
            attach_errors.append(exc)

    attach_thread = threading.Thread(target=run_attach)
    attach_thread.start()
    assert attach_started.wait(timeout=2.0)
    assert lease_refreshed.wait(timeout=2.0)

    with pytest.raises(
        hs.HerdrSteeringDeferred,
        match="deferred: operator steering pane pane-1",
    ):
        session.send(pane, "printf ready", submit_settle_s=0)

    release_attach.set()
    attach_thread.join(timeout=2.0)
    assert not attach_thread.is_alive()
    assert attach_errors == []
    _lock_path, lease_path = session._steer_lock_paths(pane)
    assert not lease_path.exists()


def test_attach_operator_lease_releases_on_foreground_failure(tmp_path: Path) -> None:
    runner = FakeRunner(foreground_returncode=7, foreground_stderr="attach failed")
    session = hs.HerdrSession(
        herdr_binary="/opt/herdr",
        runner=runner,
        steer_lock_dir=tmp_path,
    )
    pane = hs.HerdrPane(
        pane_id="pane-1",
        surface_ref="herdr-surface-918aa1506d296ee1a72da70227854392",
    )
    _lock_path, lease_path = session._steer_lock_paths(pane)

    with pytest.raises(hs.HerdrCommandError, match="attach failed"):
        session.attach(pane)

    assert runner.foreground_calls == [
        (
            ["/opt/herdr", "pane", "attach", "pane-1"],
            {hs.HERDR_SOCKET_ENV: "herdr.sock"},
        )
    ]
    assert not lease_path.exists()


def test_attach_is_deferred_while_dispatch_lease_is_live(tmp_path: Path) -> None:
    now = 1_800_000_000.0
    session = hs.HerdrSession(
        runner=FakeRunner(),
        steer_lock_dir=tmp_path,
        clock=lambda: now,
    )
    pane = hs.HerdrPane(
        pane_id="pane-1",
        surface_ref="herdr-surface-918aa1506d296ee1a72da70227854392",
    )
    _lock_path, lease_path = session._steer_lock_paths(pane)
    session._atomic_write_text(
        lease_path,
        json.dumps(
            {
                "kind": "herdr-steer-lock",
                "version": 1,
                "lease_id": "dispatch-live",
                "owner": "dispatch",
                "pane_id": pane.pane_id,
                "surface_ref": pane.surface_ref,
                "status": "active",
                "reason": "autonomous dispatch",
                "acquired_at": session._iso_utc(now),
                "expires_at": session._iso_utc(now + 10),
            },
            sort_keys=True,
        ),
    )

    with pytest.raises(hs.HerdrCommandError, match="held by dispatch steering lease"):
        session.attach(pane)

    assert lease_path.exists()


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


def test_remote_attach_command_uses_herdr_remote_session_shape() -> None:
    argv = hs.build_remote_attach_command(
        "ce-vps-1",
        session="ce-vps-codex",
        herdr_binary="/usr/local/bin/herdr",
    )

    assert argv == (
        "/usr/local/bin/herdr",
        "--remote",
        "ce-vps-1",
        "--session",
        "ce-vps-codex",
    )
    rendered = " ".join(argv)
    assert "docker exec" not in rendered
    assert "sudo" not in rendered


def test_remote_attach_plan_carries_contained_pane_metadata_without_runtime_attach() -> None:
    pane = hs.HerdrPane(
        pane_id="pane-1",
        surface_ref="herdr-surface-918aa1506d296ee1a72da70227854392",
    )

    plan = hs.plan_remote_attach(
        remote_target="operator@ce-vps-1",
        session="ce-vps-codex",
        pane=pane,
    )

    assert plan.argv == ("herdr", "--remote", "operator@ce-vps-1", "--session", "ce-vps-codex")
    assert plan.pane_id == "pane-1"
    assert plan.reach_plane == "herdr-remote"
    assert "docker exec" in plan.avoids_runtime_attach
    assert "host-root container runtime attach" in plan.avoids_runtime_attach


def test_remote_attach_executes_through_injectable_runner_without_socket_env() -> None:
    class RemoteRunner:
        def __init__(self) -> None:
            self.calls: list[tuple[list[str], dict[str, str]]] = []

        def run(self, argv, *, env=None):
            self.calls.append((list(argv), dict(env or {})))
            return subprocess.CompletedProcess(list(argv), 0, "", "")

    runner = RemoteRunner()

    hs.remote_attach(
        remote_target="ce-vps-1",
        session="ce-vps-codex",
        pane_id="pane-1",
        runner=runner,
    )

    assert runner.calls == [
        (
            ["herdr", "--remote", "ce-vps-1", "--session", "ce-vps-codex"],
            {},
        )
    ]
    assert hs.HERDR_SOCKET_ENV not in runner.calls[0][1]
    assert hs.LEGACY_HERDR_SOCKET_ENV not in runner.calls[0][1]


def test_remote_attach_refuses_privileged_or_container_runtime_programs() -> None:
    with pytest.raises(hs.HerdrCommandError, match="sudo"):
        hs.build_remote_attach_command("ce-vps-1", herdr_binary="sudo")
    with pytest.raises(hs.HerdrCommandError, match="docker"):
        hs.build_remote_attach_command("ce-vps-1", herdr_binary="/usr/bin/docker")


def test_subprocess_remote_attach_runner_scrubs_local_socket_env(monkeypatch) -> None:
    captured: dict[str, object] = {}

    def fake_run(argv, *, check, text, env):
        captured["argv"] = list(argv)
        captured["check"] = check
        captured["text"] = text
        captured["env"] = dict(env)
        return subprocess.CompletedProcess(list(argv), 0, "", "")

    monkeypatch.setenv(hs.HERDR_SOCKET_ENV, "/run/ce/herdr/control.sock")
    monkeypatch.setenv(hs.LEGACY_HERDR_SOCKET_ENV, "/run/ce/herdr/legacy.sock")
    monkeypatch.setattr(hs.subprocess, "run", fake_run)

    runner = hs.SubprocessHerdrAttachRunner()
    runner.run(["herdr", "--remote", "ce-vps-1"], env={})

    env = captured["env"]
    assert isinstance(env, dict)
    assert hs.HERDR_SOCKET_ENV not in env
    assert hs.LEGACY_HERDR_SOCKET_ENV not in env


def test_malformed_json_raises_command_error_not_name_error() -> None:
    class BadJson(FakeRunner):
        def run(self, argv, *, env=None, timeout_s=None):
            return subprocess.CompletedProcess(list(argv), 0, "not-json", "")

    session = hs.HerdrSession(runner=BadJson())
    with pytest.raises(hs.HerdrCommandError, match="non-JSON output"):
        session.create_workspace(cwd="/worktree", label="lane")


def test_command_failure_is_reported() -> None:
    class Boom(FakeRunner):
        def run(self, argv, *, env=None, timeout_s=None):
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
