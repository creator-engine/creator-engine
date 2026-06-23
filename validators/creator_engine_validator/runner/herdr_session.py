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
import os
import subprocess
from collections.abc import Mapping, Sequence
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
HERDR_SOCKET_ENV = "HERDR_SOCKET"


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
    ``surface_ref`` becomes the herdr control-socket ref (the productized form of
    #368's reserved ``attach.sock`` ``surface_ref``); ``pane_id`` is herdr's pane
    identifier; ``pid`` is the seat process herdr owns and the reaper terminates.
    """

    pane_id: str
    surface_ref: str
    pid: int | None = None
    workspace_id: str | None = None


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

    def _run_json(self, args: Sequence[str]) -> dict[str, Any]:
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

    # -- connect ----------------------------------------------------------
    def connect(self) -> None:
        """Open the client connection to the substrate-owned herdr socket.

        The herdr CLI is the socket client; this method records that subsequent
        CLI calls must carry ``HERDR_SOCKET``. It intentionally does not expose
        the socket path to the governed seat's command or environment.
        """
        self._connected = True

    def create_workspace(self, *, cwd: str | None = None, label: str | None = None) -> str:
        """Create a workspace over the herdr socket and return its id."""
        args = ["workspace", "create"]
        if cwd:
            args.extend(["--cwd", cwd])
        if label:
            args.extend(["--label", label])
        args.append("--json")
        data = self._run_json(args)
        workspace_id = self._first_str(data, "workspace_id", "workspace", "id")
        if workspace_id is None:
            raise HerdrCommandError("herdr workspace create did not return a workspace id")
        return workspace_id

    def split_pane(self, *, workspace_id: str) -> str:
        """Split/create a pane in ``workspace_id`` and return its id."""
        data = self._run_json(["pane", "split", "--workspace", workspace_id, "--json"])
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
        argv = ["pane", "run", pane_id]
        if cwd:
            argv.extend(["--cwd", cwd])
        for key, value in sorted((env or {}).items()):
            if key == HERDR_SOCKET_ENV:
                raise HerdrCommandError(
                    f"refusing to pass {HERDR_SOCKET_ENV} into a governed seat pane"
                )
            argv.extend(["--env", f"{key}={value}"])
        argv.extend(["--json", "--", *list(command)])
        data = self._run_json(argv)
        return self._first_pid(data)

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

        Maps to ``herdr workspace create`` / ``herdr pane split`` /
        ``herdr pane run`` over the socket and returns a :class:`HerdrPane`. The
        sentinel wrapper stays OUTERMOST (the #368 contract) so ``events.jsonl``
        lifecycle events are produced identically; the substrate change is *which
        surface owns the PTY*, not the wrapper contract.
        """
        if not self._connected:
            self.connect()
        workspace_id = self.create_workspace(cwd=cwd, label=label)
        pane_id = self.split_pane(workspace_id=workspace_id)
        pid = self.run_pane(pane_id=pane_id, command=command, cwd=cwd, env=env)
        return HerdrPane(
            pane_id=pane_id,
            surface_ref=str(self._socket_path),
            pid=pid,
            workspace_id=workspace_id,
        )

    # -- send (steer) -----------------------------------------------------
    def send(self, pane: HerdrPane, data: bytes) -> None:
        """Inject input/keystrokes into ``pane`` — the governed control path.

        U4 (NOT U3): this is the steer path and is the §7-boundary keystone. It
        MUST route through the CE attribution shim, which appends a
        ``runtime_operator_steer`` record (actor / target_lane / bytes_digest /
        ts) to the evidence spine BEFORE the bytes reach the PTY, and fail
        CLOSED if the spine append fails (the steer does not execute). This
        :class:`HerdrSession` is the *only* control-path writer to the socket;
        the governed seat never holds the socket, so ``herdr pane run`` cannot
        become a §7 bypass. No-new-authority holds: a steer injects input, it
        cannot widen the seat's envelope — the seat's own tool-calls still pass
        its Ring-1 hook and the §7 hard-denies still fire.
        """
        raise HerdrNotWired(
            "HerdrSession.send is a U1 scaffold; the attribution shim is wired in U4"
        )

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
    def observe(self, pane: HerdrPane) -> bytes:
        """Read recent pane output for the evidence spine (witnessability).

        Maps to ``herdr pane read <id> --source recent-unwrapped`` and feeds
        the Pane Registry ``events.jsonl`` lifecycle / read-model fold. Observe
        is the read path; it never widens authority.
        """
        data = self._run_json(
            ["pane", "read", pane.pane_id, "--source", "recent-unwrapped", "--json"]
        )
        text = self._first_str(data, "output", "text", "data", "content")
        return (text or "").encode()

    def close(self) -> None:
        """Release the client connection. Idempotent; never reaps a seat (reaper owns that)."""
        self._connected = False
