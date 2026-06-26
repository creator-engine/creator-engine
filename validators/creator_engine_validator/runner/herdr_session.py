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

import fcntl
import hashlib
import json
import logging
import os
import re
import shlex
import subprocess
import tempfile
import threading
import time
import uuid
from collections.abc import Callable, Mapping, Sequence
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, ContextManager, Iterator, Protocol

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
FORBIDDEN_REMOTE_ATTACH_PROGRAMS = frozenset(
    {"docker", "podman", "kubectl", "nerdctl", "ctr", "sudo", "nsenter"}
)
HERDR_SEND_SUBMIT_SETTLE_S = 1.0
HERDR_SEND_POLL_INTERVAL_S = 0.5
HERDR_SEND_SUBMIT_MAX_ATTEMPTS = 3
HERDR_BRIEF_REACTION_TIMEOUT_S = 5.0
HERDR_BRIEF_REACTION_POLL_INTERVAL_S = 0.5
HERDR_BRIEF_RENDER_TIMEOUT_S = HERDR_BRIEF_REACTION_TIMEOUT_S
HERDR_BRIEF_RENDER_POLL_INTERVAL_S = HERDR_BRIEF_REACTION_POLL_INTERVAL_S
HERDR_STEER_LOCK_TTL_S = 300.0
BRIEF_MARKER_PREFIX = "==CE-BRIEF-SHA256:"
BRIEF_MARKER_SUFFIX = "=="
DEFAULT_AGENT_REACTION_SIGNALS = (
    "working",
    "processing",
    "thinking",
    "codex session",
    "codex rollout",
    "session rollout",
)
CE_HERDR_AGENT_REACTION_SIGNALS_ENV = "CE_HERDR_AGENT_REACTION_SIGNALS"
_LOGGER = logging.getLogger(__name__)


def _default_steer_lock_dir() -> Path:
    return Path(tempfile.gettempdir()) / "creator-engine" / "herdr-steer-locks"


class HerdrSessionError(Exception):
    """A herdr-socket session could not be established or driven."""


class HerdrCommandError(HerdrSessionError):
    """The herdr CLI/socket command failed or returned malformed output."""


class HerdrNotWired(HerdrSessionError, NotImplementedError):
    """Raised by surfaces intentionally deferred past U3 (notably U4 steer)."""


class HerdrSteeringDeferred(HerdrCommandError):
    """Raised when autonomous dispatch is deferred behind operator steering."""


def _reaction_signal_pattern(signal: str) -> str:
    """Compile one literal reaction signal into a bounded, case-insensitive regex.

    Signal strings are literal words or phrases, not regex fragments. Matching is
    case-insensitive, requires non-word boundaries at both ends so partial words
    do not count, and treats whitespace inside phrases flexibly. This keeps the
    default heuristic extensible while avoiding an unreviewed regex injection
    surface in validator config.
    """
    if not isinstance(signal, str):
        raise HerdrCommandError("agent reaction signals must be strings")
    stripped = signal.strip()
    if not stripped:
        raise HerdrCommandError("agent reaction signals must not be empty")
    phrase = r"\s+".join(re.escape(part) for part in stripped.split())
    return rf"(?<![A-Za-z0-9_]){phrase}(?![A-Za-z0-9_])"


def _compile_agent_reaction_re(signals: Sequence[str]) -> re.Pattern[str]:
    """Return the reaction matcher for the configured literal signal set."""
    if not signals:
        raise HerdrCommandError(
            "agent reaction signals must be a non-empty sequence of literal strings"
        )
    patterns = [_reaction_signal_pattern(signal) for signal in signals]
    return re.compile("|".join(patterns), re.IGNORECASE)


def _agent_reaction_signals_from_env(value: str | None) -> tuple[str, ...]:
    if value is None or not value.strip():
        return ()
    return tuple(part for raw_part in value.split(",") if (part := raw_part.strip()))


AGENT_REACTION_RE = _compile_agent_reaction_re(DEFAULT_AGENT_REACTION_SIGNALS)


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
        timeout_s: float | None = None,
    ) -> subprocess.CompletedProcess[str]:
        """Run ``argv`` and return a completed process."""

    def run_foreground(
        self,
        argv: Sequence[str],
        *,
        env: Mapping[str, str] | None = None,
    ) -> subprocess.CompletedProcess[str]:
        """Run ``argv`` attached to the controller terminal until it exits."""


class SubprocessHerdrCommandRunner:
    """Run herdr CLI commands as subprocesses; no Python/Rust linking occurs."""

    def __init__(self, *, timeout_seconds: float = 30.0) -> None:
        self._timeout_seconds = timeout_seconds

    @staticmethod
    def _merged_env(env: Mapping[str, str] | None) -> dict[str, str]:
        merged_env = dict(os.environ)
        if env:
            merged_env.update({str(k): str(v) for k, v in env.items()})
        return merged_env

    def run(
        self,
        argv: Sequence[str],
        *,
        env: Mapping[str, str] | None = None,
        timeout_s: float | None = None,
    ) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            list(argv),
            check=False,
            capture_output=True,
            text=True,
            timeout=self._timeout_seconds if timeout_s is None else timeout_s,
            env=self._merged_env(env),
        )

    def run_foreground(
        self,
        argv: Sequence[str],
        *,
        env: Mapping[str, str] | None = None,
    ) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            list(argv),
            check=False,
            env=self._merged_env(env),
        )


class SubprocessHerdrAttachRunner:
    """Run an interactive herdr remote attach without leaking local socket env."""

    def run(
        self,
        argv: Sequence[str],
        *,
        env: Mapping[str, str] | None = None,
    ) -> subprocess.CompletedProcess[str]:
        merged_env = {
            str(k): str(v)
            for k, v in os.environ.items()
            if k not in FORBIDDEN_SEAT_ENV_NAMES
        }
        for key, value in (env or {}).items():
            if key in FORBIDDEN_SEAT_ENV_NAMES:
                raise HerdrCommandError(
                    f"refusing to pass {key} into herdr remote attach"
                )
            merged_env[str(key)] = str(value)
        return subprocess.run(
            list(argv),
            check=False,
            text=True,
            env=merged_env,
        )


@dataclass(frozen=True)
class HerdrRemoteAttachPlan:
    """A value-only plan for operator reach via ``herdr --remote``.

    ``argv`` is the exact command vector to execute. It intentionally contains no
    container-runtime program, no ``sudo``, and no local ``HERDR_SOCKET_PATH``:
    the operator reaches the contained seat through herdr's authenticated remote
    client/server path, not through host-root or container-runtime attach.
    """

    remote_target: str
    session: str | None
    pane_id: str | None
    herdr_binary: str
    argv: tuple[str, ...]
    reach_plane: str = "herdr-remote"
    avoids_runtime_attach: tuple[str, ...] = (
        "docker exec",
        "podman exec",
        "kubectl exec",
        "sudo",
        "host-root container runtime attach",
    )

    def to_dict(self) -> dict[str, Any]:
        return {
            "remote_target": self.remote_target,
            "session": self.session,
            "pane_id": self.pane_id,
            "herdr_binary": self.herdr_binary,
            "argv": list(self.argv),
            "reach_plane": self.reach_plane,
            "avoids_runtime_attach": list(self.avoids_runtime_attach),
        }


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
        steer_lock_dir: str | Path | None = None,
        steer_lock_ttl_s: float = HERDR_STEER_LOCK_TTL_S,
        steer_lock_heartbeat_interval_s: float | None = None,
        clock: Callable[[], float] = time.time,
        agent_reaction_signals: Sequence[str] | None = None,
        extra_agent_reaction_signals: Sequence[str] | None = None,
    ) -> None:
        """Create a controller-side herdr session.

        ``agent_reaction_signals`` is a non-empty sequence of literal signal
        strings used by :meth:`deliver_brief` to detect post-dispatch agent
        activity. The configured sequence replaces the default set entirely;
        pass ``None`` to use :data:`DEFAULT_AGENT_REACTION_SIGNALS`.

        ``extra_agent_reaction_signals`` and comma-separated literals from
        :envvar:`CE_HERDR_AGENT_REACTION_SIGNALS` are appended to whichever base
        set is selected, letting harness operators extend detection without
        code changes.
        """
        #: The substrate-owned herdr control socket. Held by the CE
        #: substrate/controller, never handed to a governed seat (§2/§7).
        self._socket_path = Path(socket_path)
        self._herdr_binary = str(herdr_binary)
        self._runner = runner if runner is not None else SubprocessHerdrCommandRunner()
        base_reaction_signals = (
            DEFAULT_AGENT_REACTION_SIGNALS
            if agent_reaction_signals is None
            else agent_reaction_signals
        )
        if not base_reaction_signals:
            raise HerdrCommandError(
                "agent reaction signals must be a non-empty sequence of literal strings"
            )
        reaction_signals = (
            *base_reaction_signals,
            *_agent_reaction_signals_from_env(
                os.environ.get(CE_HERDR_AGENT_REACTION_SIGNALS_ENV)
            ),
            *(extra_agent_reaction_signals or ()),
        )
        self._agent_reaction_re = _compile_agent_reaction_re(
            reaction_signals
        )
        self._connected = False
        self._steer_lock_dir = (
            Path(steer_lock_dir)
            if steer_lock_dir is not None
            else _default_steer_lock_dir()
        )
        self._steer_lock_ttl_s = steer_lock_ttl_s
        self._steer_lock_heartbeat_interval_s = steer_lock_heartbeat_interval_s
        self._clock = clock

    @property
    def socket_path(self) -> Path:
        """The substrate-owned control socket path (controller-only)."""
        return self._socket_path

    def _socket_env(self) -> dict[str, str]:
        return {HERDR_SOCKET_ENV: str(self._socket_path)}

    @staticmethod
    def _atomic_write_text(path: Path, content: str) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.parent / f"{path.name}.tmp.{os.getpid()}.{uuid.uuid4().hex[:8]}"
        tmp.write_text(content, encoding="utf-8")
        tmp.rename(path)

    @staticmethod
    def _iso_utc(epoch_seconds: float) -> str:
        return datetime.fromtimestamp(epoch_seconds, UTC).strftime("%Y-%m-%dT%H:%M:%SZ")

    @staticmethod
    def _parse_iso_utc(value: Any) -> float | None:
        if not isinstance(value, str) or not value:
            return None
        text = value[:-1] + "+00:00" if value.endswith("Z") else value
        try:
            parsed = datetime.fromisoformat(text)
        except ValueError:
            return None
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=UTC)
        return parsed.astimezone(UTC).timestamp()

    def _steer_lock_key(self, pane: HerdrPane) -> str:
        socket_identity = os.path.realpath(str(self._socket_path))
        digest = hashlib.sha256(
            f"{socket_identity}\0{pane.surface_ref}\0{pane.pane_id}".encode("utf-8")
        ).hexdigest()
        return f"herdr-pane-{digest[:32]}"

    def _steer_lock_paths(self, pane: HerdrPane) -> tuple[Path, Path]:
        key = self._steer_lock_key(pane)
        return self._steer_lock_dir / f"{key}.lock", self._steer_lock_dir / f"{key}.json"

    @contextmanager
    def _steer_lock_file(self, pane: HerdrPane) -> Iterator[Path]:
        lock_path, lease_path = self._steer_lock_paths(pane)
        lock_path.parent.mkdir(parents=True, exist_ok=True)
        with open(lock_path, "w") as lock_file:
            fcntl.flock(lock_file, fcntl.LOCK_EX)
            try:
                yield lease_path
            finally:
                fcntl.flock(lock_file, fcntl.LOCK_UN)

    def _read_steer_lease(self, lease_path: Path) -> dict[str, Any] | None:
        if not lease_path.is_file():
            return None
        try:
            data = json.loads(lease_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return None
        return data if isinstance(data, dict) else None

    def _lease_is_live(self, lease: Mapping[str, Any], *, now: float) -> bool:
        expires_at = self._parse_iso_utc(lease.get("expires_at"))
        return expires_at is None or now < expires_at

    def _lease_expires_at(self, now: float) -> float:
        return now + max(self._steer_lock_ttl_s, 0.0)

    def _heartbeat_interval_s(self) -> float:
        if self._steer_lock_heartbeat_interval_s is not None:
            return max(self._steer_lock_heartbeat_interval_s, 0.001)
        if self._steer_lock_ttl_s <= 0:
            return 1.0
        return max(min(self._steer_lock_ttl_s / 3.0, 30.0), 0.1)

    def _refresh_steer_lease(self, pane: HerdrPane, *, lease_id: str) -> bool:
        with self._steer_lock_file(pane) as lease_path:
            current = self._read_steer_lease(lease_path)
            if not current or current.get("lease_id") != lease_id:
                return False
            now = self._clock()
            current["refreshed_at"] = self._iso_utc(now)
            current["expires_at"] = self._iso_utc(self._lease_expires_at(now))
            self._atomic_write_text(
                lease_path,
                json.dumps(current, sort_keys=True, indent=2),
            )
            return True

    def _start_steer_lease_heartbeat(
        self,
        pane: HerdrPane,
        *,
        lease_id: str,
    ) -> tuple[threading.Event, threading.Thread]:
        stop = threading.Event()

        def refresh_until_stopped() -> None:
            while not stop.wait(self._heartbeat_interval_s()):
                if not self._refresh_steer_lease(pane, lease_id=lease_id):
                    return

        thread = threading.Thread(
            target=refresh_until_stopped,
            name=f"herdr-steer-lock-{pane.pane_id}",
            daemon=True,
        )
        thread.start()
        return stop, thread

    @contextmanager
    def _pane_steer_lease(
        self,
        pane: HerdrPane,
        *,
        owner: str,
        heartbeat: bool = False,
    ) -> Iterator[None]:
        if owner not in {"dispatch", "operator"}:
            raise HerdrCommandError(f"invalid herdr steer lock owner: {owner!r}")
        lease_id = f"{owner}-{uuid.uuid4().hex}"
        with self._steer_lock_file(pane) as lease_path:
            now = self._clock()
            existing = self._read_steer_lease(lease_path)
            if existing and not self._lease_is_live(existing, now=now):
                try:
                    lease_path.unlink()
                except FileNotFoundError:
                    pass
                existing = None
            if existing:
                existing_owner = str(existing.get("owner") or "unknown")
                if owner == "dispatch" and existing_owner == "operator":
                    reason = "operator steering"
                    message = f"deferred: operator steering pane {pane.pane_id}"
                    _LOGGER.warning(
                        message,
                        extra={
                            "action": "herdr_dispatch",
                            "status": "deferred",
                            "reason": reason,
                            "pane_id": pane.pane_id,
                            "surface_ref": pane.surface_ref,
                        },
                    )
                    raise HerdrSteeringDeferred(
                        f"{message}: surface_ref={pane.surface_ref}"
                    )
                raise HerdrCommandError(
                    f"herdr pane {pane.pane_id} is already held by {existing_owner} "
                    f"steering lease"
                )
            expires_at = self._lease_expires_at(now)
            record = {
                "kind": "herdr-steer-lock",
                "version": 1,
                "lease_id": lease_id,
                "owner": owner,
                "pane_id": pane.pane_id,
                "surface_ref": pane.surface_ref,
                "socket_key": self._steer_lock_key(pane),
                "status": "active",
                "reason": (
                    "operator steering" if owner == "operator" else "autonomous dispatch"
                ),
                "acquired_at": self._iso_utc(now),
                "refreshed_at": self._iso_utc(now),
                "expires_at": self._iso_utc(expires_at),
            }
            self._atomic_write_text(
                lease_path,
                json.dumps(record, sort_keys=True, indent=2),
            )
        heartbeat_stop: threading.Event | None = None
        heartbeat_thread: threading.Thread | None = None
        if heartbeat:
            heartbeat_stop, heartbeat_thread = self._start_steer_lease_heartbeat(
                pane,
                lease_id=lease_id,
            )
        try:
            yield
        finally:
            if heartbeat_stop is not None:
                heartbeat_stop.set()
            if heartbeat_thread is not None:
                heartbeat_thread.join(timeout=max(self._heartbeat_interval_s() * 2, 0.1))
            with self._steer_lock_file(pane) as lease_path:
                current = self._read_steer_lease(lease_path)
                if current and current.get("lease_id") == lease_id:
                    try:
                        lease_path.unlink()
                    except FileNotFoundError:
                        pass

    def _operator_steer_lease(
        self,
        pane: HerdrPane,
        *,
        heartbeat: bool = False,
    ) -> ContextManager[None]:
        return self._pane_steer_lease(pane, owner="operator", heartbeat=heartbeat)

    def _dispatch_steer_lease(self, pane: HerdrPane) -> ContextManager[None]:
        return self._pane_steer_lease(pane, owner="dispatch")

    def _run(
        self,
        args: Sequence[str],
        *,
        timeout_s: float | None = None,
    ) -> subprocess.CompletedProcess[str]:
        argv = [self._herdr_binary, *args]
        try:
            kwargs: dict[str, Any] = {"env": self._socket_env()}
            if timeout_s is not None:
                kwargs["timeout_s"] = timeout_s
            completed = self._runner.run(argv, **kwargs)
        except subprocess.TimeoutExpired as exc:
            raise HerdrCommandError(f"herdr command timed out: {argv!r}") from exc
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

    def _run_foreground_ok(self, args: Sequence[str]) -> None:
        argv = [self._herdr_binary, *args]
        try:
            completed = self._runner.run_foreground(argv, env=self._socket_env())
        except (OSError, subprocess.SubprocessError) as exc:
            raise HerdrCommandError(f"herdr command failed to start: {argv!r}: {exc}") from exc
        if completed.returncode != 0:
            stderr = (completed.stderr or "").strip()
            raise HerdrCommandError(
                f"herdr command exited {completed.returncode}: {argv!r}"
                + (f": {stderr}" if stderr else "")
            )

    def _run_text(
        self,
        args: Sequence[str],
        *,
        timeout_s: float | None = None,
    ) -> str:
        completed = self._run(args, timeout_s=timeout_s)
        return completed.stdout or ""

    def _read_recent_unwrapped_text(
        self,
        pane: HerdrPane,
        *,
        timeout_s: float | None = None,
    ) -> str:
        return self._run_text(
            [
                "pane",
                "read",
                pane.pane_id,
                "--source",
                "recent-unwrapped",
                "--format",
                "text",
            ],
            timeout_s=timeout_s,
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

    @staticmethod
    def _active_input_region(pane_text: str) -> str:
        normalized = pane_text.replace("\r\n", "\n").replace("\r", "\n")
        return normalized.split("\n")[-1]

    @classmethod
    def _input_line_pending(cls, pane_text: str, submitted_text: str) -> bool:
        needle = cls._pending_input_needle(submitted_text)
        if not needle:
            return False
        return needle in cls._active_input_region(pane_text)

    @staticmethod
    def _brief_marker(brief_body: str) -> str:
        digest = hashlib.sha256(brief_body.encode("utf-8")).hexdigest()
        return f"{BRIEF_MARKER_PREFIX}{digest}{BRIEF_MARKER_SUFFIX}"

    @classmethod
    def _brief_payload(cls, brief_body: str) -> tuple[str, str]:
        marker = cls._brief_marker(brief_body)
        separator = "" if brief_body.endswith("\n") else "\n"
        return f"{brief_body}{separator}{marker}", marker

    @staticmethod
    def _agent_reaction_score(
        pane_text: str,
        *,
        reaction_re: re.Pattern[str] = AGENT_REACTION_RE,
    ) -> int:
        return len(reaction_re.findall(pane_text))

    @staticmethod
    def _without_dispatched_payload(pane_text: str, dispatched_payload: str) -> str:
        normalized = pane_text.replace("\r\n", "\n").replace("\r", "\n")
        payload = dispatched_payload.replace("\r\n", "\n").replace("\r", "\n")
        if not payload:
            return normalized
        redacted = normalized.replace(payload, "")
        payload_lines = {line.strip() for line in payload.splitlines() if line.strip()}
        return "\n".join(
            line for line in redacted.splitlines() if line.strip() not in payload_lines
        )

    @classmethod
    def _agent_reaction_observed(
        cls,
        pane_text: str,
        *,
        baseline_text: str,
        dispatched_payload: str,
        reaction_re: re.Pattern[str] = AGENT_REACTION_RE,
    ) -> bool:
        redacted_pane_text = cls._without_dispatched_payload(pane_text, dispatched_payload)
        redacted_baseline_text = cls._without_dispatched_payload(
            baseline_text,
            dispatched_payload,
        )
        return cls._agent_reaction_score(
            redacted_pane_text,
            reaction_re=reaction_re,
        ) > cls._agent_reaction_score(redacted_baseline_text, reaction_re=reaction_re)

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
        commit_read_timeout_s: Callable[[], float] | None = None,
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
        with self._dispatch_steer_lease(pane):
            self._run_ok(["pane", "send-text", pane.pane_id, text])
            sleep(submit_settle_s)
            submitted = False
            for _attempt in range(submit_max_attempts):
                self._run_ok(["pane", "send-keys", pane.pane_id, "Enter"])
                sleep(submit_poll_interval_s)
                pane_text = self._read_recent_unwrapped_text(
                    pane,
                    timeout_s=(
                        commit_read_timeout_s() if commit_read_timeout_s is not None else None
                    ),
                )
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
        reaction_timeout_s: float = HERDR_BRIEF_REACTION_TIMEOUT_S,
        reaction_poll_interval_s: float = HERDR_BRIEF_REACTION_POLL_INTERVAL_S,
        render_timeout_s: float | None = None,
        render_poll_interval_s: float | None = None,
        sleep: Callable[[float], None] = time.sleep,
        clock: Callable[[], float] = time.monotonic,
    ) -> str:
        """Deliver a marked brief and fail closed unless the agent reacts.

        Reaction detection is a bounded pane-read delta heuristic over
        configurable literal signals. ``herdr wait agent-status`` is still
        lifecycle-oriented ("ready", etc.) rather than a structured
        per-dispatch acknowledgement, so it cannot yet prove that this exact
        brief was received and acted on. Until herdr exposes that primitive,
        brief delivery uses the keyword delta and fails closed on timeout.
        """
        if render_timeout_s is not None:
            reaction_timeout_s = render_timeout_s
        if render_poll_interval_s is not None:
            reaction_poll_interval_s = render_poll_interval_s
        if reaction_timeout_s <= 0:
            raise HerdrCommandError("herdr brief reaction timeout must be positive")
        if reaction_poll_interval_s < 0:
            raise HerdrCommandError(
                "herdr brief reaction poll interval must be non-negative"
            )
        payload, marker = self._brief_payload(brief_body)
        deadline = clock() + reaction_timeout_s

        def remaining_budget_s() -> float:
            return deadline - clock()

        def bounded_remaining_budget_s(*, context: str) -> float:
            remaining = remaining_budget_s()
            if remaining <= 0:
                raise HerdrCommandError(
                    "herdr brief reaction timeout expired before "
                    f"{context} on pane {pane.pane_id}: {marker}"
                )
            return remaining

        baseline_text = self._read_recent_unwrapped_text(
            pane,
            timeout_s=bounded_remaining_budget_s(context="baseline read"),
        )
        self.send(
            pane,
            payload,
            submit_settle_s=HERDR_SEND_SUBMIT_SETTLE_S,
            submit_poll_interval_s=reaction_poll_interval_s,
            submit_max_attempts=HERDR_SEND_SUBMIT_MAX_ATTEMPTS,
            commit_read_timeout_s=lambda: bounded_remaining_budget_s(
                context="dispatch commit verification"
            ),
            sleep=sleep,
        )
        while True:
            remaining = remaining_budget_s()
            if remaining <= 0:
                raise HerdrCommandError(
                    "herdr brief dispatch did not produce an agent reaction "
                    f"on pane {pane.pane_id}: {marker}"
                )
            pane_text = self._read_recent_unwrapped_text(
                pane,
                timeout_s=remaining,
            )
            if self._agent_reaction_observed(
                pane_text,
                baseline_text=baseline_text,
                dispatched_payload=payload,
                reaction_re=self._agent_reaction_re,
            ):
                return marker
            if clock() >= deadline:
                raise HerdrCommandError(
                    "herdr brief dispatch did not produce an agent reaction "
                    f"on pane {pane.pane_id}: {marker}"
                )
            sleep(min(reaction_poll_interval_s, max(0.0, remaining_budget_s())))

    # -- attach -----------------------------------------------------------
    def attach(self, pane: HerdrPane) -> None:
        """Attach an operator-visible live view of ``pane`` (detach-survivable).

        U3/U8: herdr is daemon-by-shape — panes survive the terminal closing and
        support detach/reattach. Attach is the live interactive surface (U8's
        A/B/C: multi-session, resizable stream, interactive steer). Steering
        through an attached view holds the same per-pane lease as :meth:`send`.
        """
        with self._operator_steer_lease(pane, heartbeat=True):
            self._run_foreground_ok(["pane", "attach", pane.pane_id])

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


def _clean_remote_attach_value(value: str | Path, *, field: str) -> str:
    text = str(value).strip()
    if not text:
        raise HerdrCommandError(f"herdr remote attach requires a non-empty {field}")
    if text.startswith("-"):
        raise HerdrCommandError(
            f"herdr remote attach {field} must not start with '-': {text!r}"
        )
    return text


def _program_name(value: str) -> str:
    return Path(value).name.lower()


def _assert_no_runtime_attach(argv: Sequence[str]) -> None:
    programs = {_program_name(part) for part in argv}
    forbidden = programs & FORBIDDEN_REMOTE_ATTACH_PROGRAMS
    if forbidden:
        raise HerdrCommandError(
            "herdr remote attach must use herdr as the reach plane; refusing "
            f"runtime/privileged attach token(s): {', '.join(sorted(forbidden))}"
        )


def build_remote_attach_command(
    remote_target: str,
    *,
    session: str | None = None,
    herdr_binary: str | Path = "herdr",
) -> tuple[str, ...]:
    """Build the authenticated herdr reach-plane command vector.

    The supported remote attach API is ``herdr --remote <ssh-target>
    [--session <name>]``. This builder deliberately does not compose
    ``docker exec``, ``sudo``, or any host-root/container-runtime attach path.
    """
    binary = _clean_remote_attach_value(herdr_binary, field="herdr binary")
    target = _clean_remote_attach_value(remote_target, field="remote target")
    argv: list[str] = [binary, "--remote", target]
    if session is not None:
        session_text = _clean_remote_attach_value(session, field="session")
        argv.extend(["--session", session_text])
    _assert_no_runtime_attach(argv)
    return tuple(argv)


def plan_remote_attach(
    *,
    remote_target: str,
    session: str | None = None,
    pane: HerdrPane | None = None,
    pane_id: str | None = None,
    herdr_binary: str | Path = "herdr",
) -> HerdrRemoteAttachPlan:
    """Return a pure remote attach plan for a contained herdr seat surface."""
    resolved_pane_id = pane.pane_id if pane is not None else pane_id
    if resolved_pane_id is not None:
        resolved_pane_id = _clean_remote_attach_value(resolved_pane_id, field="pane id")
    argv = build_remote_attach_command(
        remote_target,
        session=session,
        herdr_binary=herdr_binary,
    )
    return HerdrRemoteAttachPlan(
        remote_target=str(remote_target).strip(),
        session=str(session).strip() if session is not None else None,
        pane_id=resolved_pane_id,
        herdr_binary=str(herdr_binary),
        argv=argv,
    )


def remote_attach(
    *,
    remote_target: str,
    session: str | None = None,
    pane: HerdrPane | None = None,
    pane_id: str | None = None,
    herdr_binary: str | Path = "herdr",
    runner: HerdrCommandRunner | None = None,
) -> subprocess.CompletedProcess[str]:
    """Execute ``herdr --remote`` through an injectable runner.

    The helper is intentionally runner-injectable for offline tests and for live
    callers that need a PTY-aware runner. It passes an empty environment overlay
    so tests can assert that no controller-held socket path is supplied to the
    remote reach path.
    """
    plan = plan_remote_attach(
        remote_target=remote_target,
        session=session,
        pane=pane,
        pane_id=pane_id,
        herdr_binary=herdr_binary,
    )
    command_runner = runner if runner is not None else SubprocessHerdrAttachRunner()
    try:
        completed = command_runner.run(plan.argv, env={})
    except (OSError, subprocess.SubprocessError) as exc:
        raise HerdrCommandError(
            f"herdr remote attach failed to start: {plan.argv!r}: {exc}"
        ) from exc
    if completed.returncode != 0:
        stderr = (completed.stderr or "").strip()
        raise HerdrCommandError(
            f"herdr remote attach exited {completed.returncode}: {plan.argv!r}"
            + (f": {stderr}" if stderr else "")
        )
    return completed
