"""Gate 3 tmux adapter — the only seam that talks to the tmux binary.

The governed lane-launch primitive (`ce lane launch`) requires an
operator-visible tmux pane for visibility-required roles. This module spawns
or attaches a tmux pane/window and reports the concrete tmux identity
(`session_id`, `window_id`, `pane_id`, and best-effort `pane_tty`/`pane_pid`).

It runs a caller-supplied *local* command only. It NEVER launches a provider,
model, or credentialed surface, and it never prints secrets or environment
variables. The subprocess runner is injectable so tests can drive the adapter
without a real tmux process.

Prose contract: ``docs/operations/GOVERNED_LANE_LAUNCH_PROTOCOL.md``.
"""
from __future__ import annotations

import array
import os
import secrets
import socket
import subprocess
import sys
import tempfile
import threading
import time
from dataclasses import dataclass, replace
from typing import Callable, Mapping, Sequence

TMUX_BIN = "tmux"

# Tab-separated identity format expanded by tmux ``-F`` at creation. This carries
# *identity only*. ``pane_current_path`` is deliberately NOT taken from this
# creation-time snapshot: tmux honours ``-c`` but the pane's reported
# ``pane_current_path`` settles a moment after creation, so the snapshot can
# still read the server's cwd. The cwd is instead verified post-spawn by polling
# ``display-message`` (see ``_poll_pane_cwd``).
#
# NOTE on the delimiter: the format string carries a literal TAB, but some tmux
# builds *sanitize* whitespace in ``-F`` output, emitting an underscore (``_``)
# in place of the tab. This is build/environment dependent, NOT version
# dependent: tmux 3.4 on one Ubuntu 24.04 box converts ``\t`` -> ``_`` while tmux
# 3.4 on another box preserves the tab (ce-ops#332). ``_parse_identity`` is
# therefore tolerant of BOTH separators. The five identity fields are safe to
# normalise this way because none of them contains an underscore: ``session_id``
# is ``$N``, ``window_id`` ``@N``, ``pane_id`` ``%N``, ``pane_tty`` a
# ``/dev/...`` path, and ``pane_pid`` a decimal integer.
_IDENTITY_FORMAT = "#{session_id}\t#{window_id}\t#{pane_id}\t#{pane_tty}\t#{pane_pid}"

# Bounded poll for the pane to settle into its ``-c`` start directory.
_CWD_POLL_ATTEMPTS = 20
_CWD_POLL_INTERVAL = 0.25  # seconds; ~5s worst case
_FD_HANDOFF_TIMEOUT = 5.0
_FD_RECEIVER = (
    "import array, os, socket, sys; "
    "sock=socket.socket(socket.AF_UNIX, socket.SOCK_STREAM); "
    "sock.connect(sys.argv[1]); sock.sendall(sys.argv[2].encode('ascii')); "
    "_data, ancdata, _flags, _addr=sock.recvmsg(1, socket.CMSG_SPACE(array.array('i').itemsize)); "
    "fds=[fd for level, kind, data in ancdata if level == socket.SOL_SOCKET and kind == socket.SCM_RIGHTS "
    "for fd in array.array('i', data)]; "
    "fd=fds.pop() if len(fds) == 1 else None; "
    "fd is not None or (_ for _ in ()).throw(RuntimeError('missing directory descriptor')); "
    "os.fchdir(fd); os.close(fd); sock.sendall(b'R'); sock.close(); "
    "os.execvp(sys.argv[3], sys.argv[3:])"
)


class TmuxError(Exception):
    """Base class for tmux adapter errors."""


class TmuxUnavailable(TmuxError):
    """tmux is not available, so a visible lane cannot be launched."""


class TmuxCwdMismatch(TmuxError):
    """The spawned pane did not start in the requested working directory."""


class TmuxFdHandoffRefused(TmuxError):
    """The pane did not acknowledge descriptor ownership before execution."""


@dataclass(frozen=True)
class TmuxPane:
    """Concrete tmux pane identity for a launched lane."""

    session_id: str
    window_id: str
    pane_id: str
    pane_tty: str | None = None
    pane_pid: int | None = None
    pane_cwd: str | None = None


Runner = Callable[..., subprocess.CompletedProcess]


def _default_runner(argv: Sequence[str], check: bool = True) -> subprocess.CompletedProcess:
    return subprocess.run(list(argv), check=check, capture_output=True, text=True)


def is_proc_self_fd_path(cwd: str | os.PathLike[str] | None) -> bool:
    """Return whether ``cwd`` is the parent-process descriptor capability form."""
    if cwd is None:
        return False
    value = os.fspath(cwd)
    prefix = "/proc/self/fd/"
    suffix = value[len(prefix) :] if value.startswith(prefix) else ""
    return bool(suffix) and suffix.isdecimal() and str(int(suffix)) == suffix


class _FdHandoff:
    """One-shot SCM_RIGHTS handoff from launcher to the pane bootstrap."""

    def __init__(self, cwd: str | os.PathLike[str], timeout: float):
        try:
            self._fd = os.open(os.fspath(cwd), os.O_RDONLY | os.O_DIRECTORY)
        except OSError as exc:
            raise TmuxFdHandoffRefused("cannot duplicate pinned launch directory") from exc
        self._timeout = timeout
        self._token = secrets.token_hex(32)
        self._directory = tempfile.mkdtemp(prefix="ce-tmux-fd-", dir="/tmp")
        self.path = os.path.join(self._directory, "handoff.sock")
        self._socket = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self._socket.bind(self.path)
        os.chmod(self.path, 0o600)
        self._socket.listen(1)
        self._done = threading.Event()
        self._error: str | None = None
        self._thread = threading.Thread(target=self._serve, daemon=True)
        self._thread.start()

    def wrapped_command(self, command: Sequence[str]) -> list[str]:
        return [sys.executable, "-c", _FD_RECEIVER, self.path, self._token, *command]

    def _serve(self) -> None:
        try:
            self._socket.settimeout(self._timeout)
            conn, _ = self._socket.accept()
            with conn:
                conn.settimeout(self._timeout)
                if conn.recv(128) != self._token.encode("ascii"):
                    self._error = "pane descriptor handoff authentication failed"
                    return
                rights = array.array("i", [self._fd]).tobytes()
                conn.sendmsg(
                    [b"F"],
                    [(socket.SOL_SOCKET, socket.SCM_RIGHTS, rights)],
                )
                if conn.recv(1) != b"R":
                    self._error = "pane did not acknowledge fchdir"
        except (OSError, ValueError) as exc:
            self._error = f"pane descriptor handoff failed: {exc}"
        finally:
            self._done.set()

    def require_completion(self) -> None:
        if not self._done.wait(self._timeout):
            raise TmuxFdHandoffRefused(
                "pane did not inherit the pinned directory descriptor before execution"
            )
        if self._error is not None:
            raise TmuxFdHandoffRefused(self._error)

    def close(self) -> None:
        try:
            self._socket.close()
        finally:
            self._thread.join(timeout=self._timeout)
            os.close(self._fd)
            try:
                os.unlink(self.path)
            except FileNotFoundError:
                pass
            os.rmdir(self._directory)


class TmuxAdapter:
    """Adapter over the tmux binary with an injectable subprocess runner."""

    kind = "tmux"

    def __init__(
        self,
        *,
        runner: Runner | None = None,
        tmux_bin: str = TMUX_BIN,
        cwd_poll_attempts: int = _CWD_POLL_ATTEMPTS,
        cwd_poll_interval: float = _CWD_POLL_INTERVAL,
        fd_handoff_timeout: float = _FD_HANDOFF_TIMEOUT,
        sleeper: Callable[[float], None] | None = None,
    ):
        self._runner = runner or _default_runner
        self._tmux_bin = tmux_bin
        self._cwd_poll_attempts = max(1, int(cwd_poll_attempts))
        self._cwd_poll_interval = cwd_poll_interval
        self._fd_handoff_timeout = max(0.01, float(fd_handoff_timeout))
        self._sleeper = sleeper or time.sleep

    def is_available(self) -> bool:
        """Return True when the tmux binary responds to ``-V``."""
        try:
            self._runner([self._tmux_bin, "-V"])
        except (FileNotFoundError, OSError, subprocess.SubprocessError):
            return False
        return True

    def _session_exists(self, session: str) -> bool:
        proc = self._runner([self._tmux_bin, "has-session", "-t", session], check=False)
        return proc.returncode == 0

    def ensure_pane(
        self,
        *,
        session: str,
        window: str,
        command: Sequence[str],
        cwd: str | os.PathLike[str] | None = None,
        env: Mapping[str, str] | None = None,
    ) -> TmuxPane:
        """Spawn or attach a tmux pane/window running ``command``; return its identity.

        Creates ``session`` with the requested window when it does not exist,
        otherwise adds a new window to the live session. ``command`` is a local
        command vector; no provider/model is launched.

        When ``cwd`` is given, the pane's start directory is *enforced* via tmux
        ``-c <cwd>`` and then *verified* against the pane's reported
        ``pane_current_path``; a mismatch raises :class:`TmuxCwdMismatch` so a
        lane can never silently run outside its allocated worktree.

        When ``env`` is given, each ``KEY: VALUE`` pair is pinned into the new
        session/window environment via tmux ``-e KEY=VALUE`` (emitted before the
        pane command). This is the launch-pinned carrier the in-band hook reads;
        the values are passed to tmux only and are never printed.
        """
        if not self.is_available():
            raise TmuxUnavailable(
                "tmux is unavailable; a visibility-required lane cannot be launched"
            )

        command = list(command)
        handoff = _FdHandoff(cwd, self._fd_handoff_timeout) if is_proc_self_fd_path(cwd) else None
        if handoff is not None:
            command = handoff.wrapped_command(command)
        cwd_args = ["-c", str(cwd)] if cwd is not None and handoff is None else []
        env_args: list[str] = []
        if env:
            for key, value in env.items():
                env_args += ["-e", f"{key}={value}"]
        if self._session_exists(session):
            argv = [
                self._tmux_bin, "new-window", "-d",
                "-t", session, "-n", window,
                *cwd_args,
                *env_args,
                "-P", "-F", _IDENTITY_FORMAT,
                *command,
            ]
        else:
            argv = [
                self._tmux_bin, "new-session", "-d",
                "-s", session, "-n", window,
                *cwd_args,
                *env_args,
                "-P", "-F", _IDENTITY_FORMAT,
                *command,
            ]
        pane: TmuxPane | None = None
        try:
            proc = self._runner(argv)
            pane = self._parse_identity(proc.stdout)
            if handoff is not None:
                try:
                    handoff.require_completion()
                except TmuxFdHandoffRefused:
                    self._kill_pane(pane.pane_id)
                    raise

            # When a cwd is requested, tmux enforces it via ``-c`` but the pane's
        # ``pane_current_path`` settles a moment after creation. Poll
        # ``display-message`` (bounded) until it reports the requested cwd; refuse
        # with :class:`TmuxCwdMismatch` if it never does — BEFORE the caller writes
        # any Pane Registry record or injects a prompt — so a lane can never run
        # outside its allocated worktree. The just-spawned pane is killed on
        # refusal to avoid an orphaned pane in the wrong directory.
            if cwd is not None and handoff is None:
                want = os.path.realpath(str(cwd))
                observed = self._poll_pane_cwd(pane.pane_id, want)
                if observed is None:
                    self._kill_pane(pane.pane_id)
                    raise TmuxCwdMismatch(
                        f"pane {pane.pane_id} never reported the requested cwd {str(cwd)!r} "
                        f"(resolved {want!r}) within "
                        f"{self._cwd_poll_attempts} polls; refusing before pane-registry "
                        "write / prompt injection"
                    )
                pane = replace(pane, pane_cwd=observed)
            return pane
        finally:
            if handoff is not None:
                handoff.close()

    def _poll_pane_cwd(self, pane_id: str, want_realpath: str) -> str | None:
        """Poll ``display-message`` for the pane's settled cwd; return it on match.

        Returns the observed (raw) ``pane_current_path`` once its realpath equals
        ``want_realpath``, or ``None`` if it never matches within the bounded poll.
        """
        last: str | None = None
        for attempt in range(self._cwd_poll_attempts):
            proc = self._runner(
                [self._tmux_bin, "display-message", "-p", "-t", pane_id,
                 "#{pane_current_path}"],
                check=False,
            )
            last = (proc.stdout or "").strip()
            if last and os.path.realpath(last) == want_realpath:
                return last
            if attempt < self._cwd_poll_attempts - 1:
                self._sleeper(self._cwd_poll_interval)
        return None

    def _kill_pane(self, pane_id: str) -> None:
        """Best-effort kill of a just-spawned pane (used when cwd verification fails)."""
        try:
            self._runner([self._tmux_bin, "kill-pane", "-t", pane_id], check=False)
        except (FileNotFoundError, OSError, subprocess.SubprocessError):
            pass

    @staticmethod
    def _parse_identity(stdout: str) -> TmuxPane:
        line = (stdout or "").strip().splitlines()
        # Some tmux builds sanitize the literal TAB delimiter in ``-F`` output to
        # an underscore (ce-ops#332), so normalise the separator before splitting.
        # Both ``\t`` and ``_`` are treated as field separators; the five identity
        # fields never contain an underscore themselves, so splitting on ``_``
        # after the swap recovers exactly the intended fields under either build.
        raw = line[0] if line else ""
        fields = raw.replace("\t", "_").split("_") if raw else []
        fields = [f.strip() for f in fields]

        def get(idx: int) -> str | None:
            return fields[idx] if idx < len(fields) and fields[idx] else None

        session_id = get(0) or ""
        window_id = get(1) or ""
        pane_id = get(2) or ""
        if not (session_id and window_id and pane_id):
            raise TmuxError(f"could not parse tmux identity from output: {stdout!r}")
        pane_tty = get(3)
        pane_pid_raw = get(4)
        pane_pid = int(pane_pid_raw) if pane_pid_raw and pane_pid_raw.isdigit() else None
        return TmuxPane(
            session_id=session_id,
            window_id=window_id,
            pane_id=pane_id,
            pane_tty=pane_tty,
            pane_pid=pane_pid,
        )
