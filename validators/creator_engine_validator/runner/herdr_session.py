"""CE-side integration seam to the herdr-ce multiplexer fork (ce-ops#217).

This module is the **CE-side adapter stub** that will drive the
``creator-engine/herdr-ce`` AGPL fork over its JSON Unix-socket API, replacing
both today's ``tmux send-keys`` pane-drive and the creator-engine#368
``seat_pty_session`` ``pty.fork`` byte-tap. herdr is a single Rust binary that
exposes ``workspace`` / ``tab`` / ``pane split`` / ``pane run`` / ``pane read``
/ ``wait agent-status`` over a local JSON Unix socket; CE Python drives that
socket at arm's length and **never links the Rust binary** — that arm's-length
boundary is also the AGPL §13 firewall (see
``docs/architecture/HERDR_GOVERNANCE_BOUNDARY.md``). The governance/validator
stack stays a separate process speaking over the socket; it is never compiled
or statically linked into the AGPL Rust binary, so the copyleft blast radius
covers only the multiplexer fork and CE's governance differentiator stays
proprietary.

Design-of-record: ``.ce/state/research/DESIGN_COCKPIT_ON_HERDR_20260623.md``
(§2 integration seam, §4 governed-interaction model). Build unit map: U1 = this
scaffold + the fork + license compliance; **U3** wires this live as a
``terminal_kind=herdr`` :class:`~creator_engine_validator.visibility_backend.VisibilityBackend`
and retires the ``pty.fork`` path behind the registry; **U4** adds the
attribution shim (``runtime_operator_steer`` spine-append-before-effect) that
makes this the *sole* control-path writer to the socket.

**Status — U3 LIVE BACKEND CLIENT.** This module is wired for
``terminal_kind=herdr`` through :mod:`creator_engine_validator.visibility_backend`.
CE drives the AGPL Rust binary only as a separate process speaking to the herdr
control socket; it never imports or links Rust code into Python, and herdr never
imports or links Python code into Rust.

Design invariants this seam will enforce (load-bearing, implemented in U3/U4):

* **Separate process, never linked.** CE issues ``herdr`` socket calls via a
  client connection; herdr never imports Python and Python never links Rust.
  This is the AGPL firewall *and* the right engineering boundary.
* **The socket is owned by the CE substrate/controller, not the governed seat.**
  The seat runs *inside* a herdr pane as a confined child and never receives a
  handle to the herdr control socket — so ``herdr pane run`` cannot become a
  §7 (``governed-seat-cannot-push``) bypass.
* **Every control-path steer is attributed before it executes (U4).** Operator
  steers are funneled through the CE attribution shim, which appends a
  ``runtime_operator_steer`` record to the evidence spine *before* the bytes
  reach the PTY (fail-closed on attribution).
"""

from __future__ import annotations

import json
import hashlib
import os
import shlex
import subprocess
import time
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

#: The ``terminal.kind`` key the herdr visibility backend will service (U3).
#: Parallels ``visibility_backend.TMUX_TERMINAL_KIND`` / ``HEADLESS_TERMINAL_KIND``.
HERDR_TERMINAL_KIND = "herdr"

#: The default per-host control-socket path herdr exposes. The concrete value is
#: substrate-owned and resolved by the containment wrapper (U2); recorded here as
#: the documented default, not bound by this scaffold.
DEFAULT_HERDR_SOCKET = "herdr.sock"

#: Environment carrier used by the herdr CLI client to find the substrate-owned
#: Unix control socket. The path is carried only in the CE controller process'
#: subprocess environment, never in the governed seat's pane environment.
HERDR_SOCKET_ENV = "HERDR_SOCKET_PATH"
LEGACY_HERDR_SOCKET_ENV = "HERDR_SOCKET"
FORBIDDEN_SEAT_ENV_NAMES = frozenset({HERDR_SOCKET_ENV, LEGACY_HERDR_SOCKET_ENV})
HERDR_SEND_SUBMIT_SETTLE_S = 1.0
HERDR_SEND_POLL_INTERVAL_S = 0.5
HERDR_SEND_SUBMIT_MAX_ATTEMPTS = 3
HERDR_SEND_PROMPT_TAIL_LINES = 8
HERDR_BRIEF_RENDER_TIMEOUT_S = 5.0
HERDR_BRIEF_RENDER_POLL_INTERVAL_S = 0.5
BRIEF_MARKER_PREFIX = "==CE-BRIEF-SHA256:"
BRIEF_MARKER_SUFFIX = "=="


class HerdrSessionError(Exception):
    """A herdr-socket session could not be established or driven."""


class HerdrCommandError(HerdrSessionError):
    """The herdr CLI/socket command failed or returned malformed output."""


class HerdrNotWired(HerdrSessionError, NotImplementedError):
    """Raised by surfaces intentionally deferred past U3 (notably U4 steer)."""


@dataclass(frozen=True)
class HerdrPane:
    """A handle to a single herdr pane CE drives over the socket.

    Mirrors the shape the U3 :class:`VisibilityBackend` will stamp onto the Pane
    Registry ``terminal`` record (``{kind: herdr, surface_ref, pane_id, pid}``):
    ``surface_ref`` is an opaque controller-owned surface id, never the raw
    herdr control-socket path; ``pane_id`` is herdr's pane identifier; ``pid`` is
    the seat process herdr owns and the reaper terminates.
    """

    pane_id: str
    surface_ref: str
    pid: int | None = None
    workspace_id: str | None = None


@dataclass(frozen=True)
class HerdrWorkspace:
    """The workspace and root pane returned by ``herdr workspace create``."""

    workspace_id: str
    root_pane_id: str


class HerdrCommandRunner(Protocol):
    """A narrow subprocess seam for tests and live CLI execution."""

    def run(
        self,
        argv: Sequence[str],
        *,
        env: Mapping[str, str] | None = None,
    ) -> subprocess.CompletedProcess[str]:
        """Run ``argv`` and return a completed process."""


class SubprocessHerdrCommandRunner:
    """Run herdr CLI commands as subprocesses; no Python/Rust linking occurs."""

    def __init__(self, *, timeout_seconds: float = 30.0) -> None:
        self._timeout_seconds = timeout_seconds

    def run(
        self,
        argv: Sequence[str],
        *,
        env: Mapping[str, str] | None = None,
    ) -> subprocess.CompletedProcess[str]:
        merged_env = dict(os.environ)
        if env:
            merged_env.update({str(k): str(v) for k, v in env.items()})
        return subprocess.run(
            list(argv),
            check=False,
            capture_output=True,
            text=True,
            timeout=self._timeout_seconds,
            env=merged_env,
        )


class HerdrSession:
    """CE-side client that drives the herdr-ce fork over its JSON Unix socket.

    The client shells out to the herdr binary and passes the substrate-owned
    socket path in a private subprocess environment. This gives CE the required
    socket/process boundary without binding to the Rust crate.
    """

    def __init__(
        self,
        *,
        socket_path: str | Path = DEFAULT_HERDR_SOCKET,
        herdr_binary: str | Path = "herdr",
        runner: HerdrCommandRunner | None = None,
    ) -> None:
        #: The substrate-owned herdr control socket. Held by the CE
        #: substrate/controller, never handed to a governed seat (§2/§7).
        self._socket_path = Path(socket_path)
        self._herdr_binary = str(herdr_binary)
        self._runner = runner if runner is not None else SubprocessHerdrCommandRunner()
        self._connected = False

    @property
    def socket_path(self) -> Path:
        """The substrate-owned control socket path (controller-only)."""
        return self._socket_path

    def _socket_env(self) -> dict[str, str]:
        return {HERDR_SOCKET_ENV: str(self._socket_path)}

    def _run(self, args: Sequence[str]) -> subprocess.CompletedProcess[str]:
        argv = [self._herdr_binary, *args]
        try:
            completed = self._runner.run(argv, env=self._socket_env())
        except (OSError, subprocess.SubprocessError) as exc:
            raise HerdrCommandError(f"herdr command failed to start: {argv!r}: {exc}") from exc
        if completed.returncode != 0:
            stderr = (completed.stderr or "").strip()
            raise HerdrCommandError(
                f"herdr command exited {completed.returncode}: {argv!r}"
                + (f": {stderr}" if stderr else "")
            )
        return completed

    def _run_ok(self, args: Sequence[str]) -> None:
        self._run(args)

    def _run_text(self, args: Sequence[str]) -> str:
        completed = self._run(args)
        return completed.stdout or ""

    def _read_recent_unwrapped_text(self, pane: HerdrPane) -> str:
        return self._run_text(
            [
                "pane",
                "read",
                pane.pane_id,
                "--source",
                "recent-unwrapped",
                "--format",
                "text",
            ]
        )

    def _run_json(self, args: Sequence[str]) -> dict[str, Any]:
        completed = self._run(args)
        argv = [self._herdr_binary, *args]
        stdout = (completed.stdout or "").strip()
        if not stdout:
            return {}
        try:
            data = json.loads(stdout)
        except json.JSONDecodeError as exc:
            raise HerdrCommandError(
                f"herdr command returned non-JSON output: {argv!r}: {stdout[:200]!r}"
            ) from exc
        if not isinstance(data, dict):
            raise HerdrCommandError(
                f"herdr command returned a non-object JSON payload: {argv!r}"
            )
        return data

    @staticmethod
    def _env_args(env: Mapping[str, str] | None, *, context: str) -> list[str]:
        args: list[str] = []
        for key, value in sorted((env or {}).items()):
            key_text = str(key)
            if key_text in FORBIDDEN_SEAT_ENV_NAMES:
                raise HerdrCommandError(
                    f"refusing to pass {key_text} into a governed {context}"
                )
            if not key_text or "=" in key_text:
                raise HerdrCommandError(
                    f"refusing unsafe herdr env assignment name for governed {context}: "
                    f"{key_text!r}"
                )
            args.extend(["--env", f"{key_text}={value}"])
        return args

    @staticmethod
    def _first_str(data: Mapping[str, Any], *keys: str) -> str | None:
        for key in keys:
            value = data.get(key)
            if isinstance(value, str) and value:
                return value
        return None

    @staticmethod
    def _first_pid(data: Mapping[str, Any]) -> int | None:
        for key in ("pid", "process_id", "pane_pid"):
            value = data.get(key)
            if isinstance(value, int) and value > 0:
                return value
            if isinstance(value, str) and value.isdigit() and int(value) > 0:
                return int(value)
        return None

    @staticmethod
    def _surface_ref(*, workspace_id: str, pane_id: str) -> str:
        """Return a ledger-safe opaque handle for a herdr pane surface.

        The controller keeps the raw herdr socket path in ``HerdrSession`` and in
        the private subprocess environment only. Ledger-visible pane records may
        be read by governed seats, so they carry this opaque id instead.
        """
        digest = hashlib.sha256(f"{workspace_id}\0{pane_id}".encode("utf-8")).hexdigest()
        return f"herdr-surface-{digest[:32]}"

    @staticmethod
    def _pending_input_needle(text: str) -> str:
        for line in reversed(text.splitlines()):
            needle = line.strip()
            if needle:
                return needle
        return text.strip()

    @classmethod
    def _input_line_pending(cls, pane_text: str, submitted_text: str) -> bool:
        needle = cls._pending_input_needle(submitted_text)
        if not needle:
            return False
        tail = pane_text.splitlines()[-HERDR_SEND_PROMPT_TAIL_LINES:]
        return any(needle in row for row in tail)

    @staticmethod
    def _brief_marker(brief_body: str) -> str:
        digest = hashlib.sha256(brief_body.encode("utf-8")).hexdigest()
        return f"{BRIEF_MARKER_PREFIX}{digest}{BRIEF_MARKER_SUFFIX}"

    @classmethod
    def _brief_payload(cls, brief_body: str) -> tuple[str, str]:
        marker = cls._brief_marker(brief_body)
        separator = "" if brief_body.endswith("\n") else "\n"
        return f"{brief_body}{separator}{marker}", marker

    # -- connect ----------------------------------------------------------
    def connect(self) -> None:
        """Open the client connection to the substrate-owned herdr socket.

        The herdr CLI is the socket client; this method records that subsequent
        CLI calls must carry ``HERDR_SOCKET_PATH``. It intentionally does not
        expose the socket path to the governed seat's command or environment.
        """
        self._connected = True

    def create_workspace(
        self,
        *,
        cwd: str | None = None,
        label: str | None = None,
        env: Mapping[str, str] | None = None,
    ) -> HerdrWorkspace:
        """Create a workspace over the herdr socket and return workspace/root pane ids."""
        args = ["workspace", "create"]
        if cwd:
            args.extend(["--cwd", cwd])
        if label:
            args.extend(["--label", label])
        args.extend(self._env_args(env, context="workspace"))
        data = self._run_json(args)
        result = data.get("result")
        if not isinstance(result, Mapping):
            raise HerdrCommandError("herdr workspace create did not return a result object")
        if result.get("type") != "workspace_created":
            raise HerdrCommandError(
                "herdr workspace create did not return a workspace_created result"
            )
        workspace = result.get("workspace")
        root_pane = result.get("root_pane")
        if not isinstance(workspace, Mapping) or not isinstance(root_pane, Mapping):
            raise HerdrCommandError(
                "herdr workspace create did not return workspace/root_pane objects"
            )
        workspace_id = self._first_str(workspace, "workspace_id")
        root_pane_id = self._first_str(root_pane, "pane_id")
        if workspace_id is None or root_pane_id is None:
            raise HerdrCommandError(
                "herdr workspace create did not return workspace_id/root pane_id"
            )
        return HerdrWorkspace(workspace_id=workspace_id, root_pane_id=root_pane_id)

    def split_pane(
        self,
        *,
        pane_id: str,
        direction: str = "right",
        cwd: str | None = None,
        env: Mapping[str, str] | None = None,
    ) -> str:
        """Split ``pane_id`` in ``direction`` and return the created pane id."""
        if direction not in {"right", "down"}:
            raise HerdrCommandError("herdr pane split direction must be 'right' or 'down'")
        args = ["pane", "split", pane_id, "--direction", direction]
        if cwd:
            args.extend(["--cwd", cwd])
        args.extend(self._env_args(env, context="seat pane"))
        data = self._run_json(args)
        pane_id = self._first_str(data, "pane_id", "pane", "id")
        if pane_id is None:
            raise HerdrCommandError("herdr pane split did not return a pane id")
        return pane_id

    def run_pane(
        self,
        *,
        pane_id: str,
        command: Sequence[str],
        cwd: str | None = None,
        env: Mapping[str, str] | None = None,
    ) -> int | None:
        """Run the sentinel-wrapped seat command inside an existing herdr pane."""
        self._env_args(env, context="seat pane")
        if env:
            raise HerdrCommandError(
                "herdr pane run does not accept env; pass env to create_workspace"
            )
        if cwd is not None:
            raise HerdrCommandError(
                "herdr pane run does not accept cwd; pass cwd to create_workspace"
            )
        command_text = shlex.join(str(part) for part in command)
        if not command_text:
            raise HerdrCommandError("herdr pane run requires a command")
        self._run_ok(["pane", "run", pane_id, command_text])
        return None

    def wait_agent_status(
        self,
        pane: HerdrPane,
        *,
        status: str = "ready",
    ) -> dict[str, Any]:
        """Wait for herdr's agent-status signal for ``pane``."""
        return self._run_json(
            ["wait", "agent-status", "--pane", pane.pane_id, "--status", status, "--json"]
        )

    # -- spawn-pane -------------------------------------------------------
    def spawn_pane(
        self,
        *,
        command: Sequence[str],
        cwd: str | None = None,
        env: Mapping[str, str] | None = None,
        label: str | None = None,
    ) -> HerdrPane:
        """Create a herdr pane running the sentinel-wrapped seat ``command``.

        Maps to ``herdr workspace create`` / ``herdr pane run`` over the socket
        and returns a :class:`HerdrPane` for the workspace root pane. The sentinel
        wrapper stays OUTERMOST (the #368 contract) so ``events.jsonl`` lifecycle
        events are produced identically; the substrate change is *which surface
        owns the PTY*, not the wrapper contract.
        """
        if not self._connected:
            self.connect()
        workspace = self.create_workspace(cwd=cwd, label=label, env=env)
        pid = self.run_pane(pane_id=workspace.root_pane_id, command=command)
        return HerdrPane(
            pane_id=workspace.root_pane_id,
            surface_ref=self._surface_ref(
                workspace_id=workspace.workspace_id,
                pane_id=workspace.root_pane_id,
            ),
            pid=pid,
            workspace_id=workspace.workspace_id,
        )

    # -- send (steer) -----------------------------------------------------
    def send(
        self,
        pane: HerdrPane,
        data: bytes | str,
        *,
        submit_settle_s: float = HERDR_SEND_SUBMIT_SETTLE_S,
        submit_poll_interval_s: float = HERDR_SEND_POLL_INTERVAL_S,
        submit_max_attempts: int = HERDR_SEND_SUBMIT_MAX_ATTEMPTS,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        """Inject input/keystrokes into ``pane`` — the governed control path.

        U3 wires ordinary text input through ``herdr pane send-text``. The CLI
        only accepts text, so non-UTF-8 bytes remain fail-closed until a later
        narrow key/control helper is explicitly backed by the herdr source.
        After the text is placed in the input box, CE commits it with a bounded
        ``herdr pane send-keys <pane_id> Enter`` loop and confirms via
        ``recent-unwrapped`` reads that the pending input line left the prompt.
        This :class:`HerdrSession` is the *only* control-path writer to the
        socket; the governed seat never holds the socket, so ``herdr pane run``
        cannot become a §7 bypass. U4 layers attribution ahead of this write.
        """
        if isinstance(data, str):
            text = data
        else:
            try:
                text = data.decode("utf-8")
            except UnicodeDecodeError as exc:
                raise HerdrCommandError(
                    "herdr pane send-text only accepts UTF-8 text; "
                    "non-text/control input remains fail-closed"
                ) from exc
        self._run_ok(["pane", "send-text", pane.pane_id, text])
        sleep(submit_settle_s)
        submitted = False
        for _attempt in range(submit_max_attempts):
            self._run_ok(["pane", "send-keys", pane.pane_id, "Enter"])
            sleep(submit_poll_interval_s)
            pane_text = self._read_recent_unwrapped_text(pane)
            if not self._input_line_pending(pane_text, text):
                submitted = True
                break
        if not submitted:
            raise HerdrCommandError(
                f"herdr pane send did not commit after {submit_max_attempts} "
                f"Enter attempt(s): pane {pane.pane_id} still shows pending input"
            )

    def deliver_brief(
        self,
        pane: HerdrPane,
        brief_body: str,
        *,
        render_timeout_s: float = HERDR_BRIEF_RENDER_TIMEOUT_S,
        render_poll_interval_s: float = HERDR_BRIEF_RENDER_POLL_INTERVAL_S,
        sleep: Callable[[float], None] = time.sleep,
        clock: Callable[[], float] = time.monotonic,
    ) -> str:
        """Deliver a brief with a SHA-256 render marker and fail closed if absent."""
        payload, marker = self._brief_payload(brief_body)
        self.send(
            pane,
            payload,
            submit_settle_s=HERDR_SEND_SUBMIT_SETTLE_S,
            submit_poll_interval_s=render_poll_interval_s,
            submit_max_attempts=HERDR_SEND_SUBMIT_MAX_ATTEMPTS,
            sleep=sleep,
        )
        deadline = clock() + render_timeout_s
        while True:
            if marker in self._read_recent_unwrapped_text(pane):
                return marker
            if clock() >= deadline:
                raise HerdrCommandError(
                    f"herdr brief marker did not render on pane {pane.pane_id}: {marker}"
                )
            sleep(render_poll_interval_s)

    # -- attach -----------------------------------------------------------
    def attach(self, pane: HerdrPane) -> None:
        """Attach an operator-visible live view of ``pane`` (detach-survivable).

        U3/U8: herdr is daemon-by-shape — panes survive the terminal closing and
        support detach/reattach. Attach is the live interactive surface (U8's
        A/B/C: multi-session, resizable stream, interactive steer). Steering
        through an attached view still funnels writes through :meth:`send`.
        """
        raise HerdrNotWired("HerdrSession.attach is a U1 scaffold; wired in U3/U8")

    # -- observe ----------------------------------------------------------
    def observe(
        self,
        pane: HerdrPane,
        *,
        lines: int = 200,
        output_format: str = "text",
    ) -> bytes:
        """Read recent pane output for the evidence spine (witnessability).

        Maps to ``herdr pane read <id> --source recent --lines N --format ...``
        and feeds the Pane Registry ``events.jsonl`` lifecycle / read-model
        fold. ``pane read`` prints text/ANSI directly to stdout; it is not a
        JSON command. Observe is the read path; it never widens authority.
        """
        if lines <= 0:
            raise HerdrCommandError("herdr pane read lines must be positive")
        if output_format not in {"text", "ansi"}:
            raise HerdrCommandError("herdr pane read format must be 'text' or 'ansi'")
        text = self._run_text(
            [
                "pane",
                "read",
                pane.pane_id,
                "--source",
                "recent",
                "--lines",
                str(lines),
                "--format",
                output_format,
            ]
        )
        return text.encode("utf-8")

    def close(self) -> None:
        """Release the client connection. Idempotent; never reaps a seat (reaper owns that)."""
        self._connected = False
