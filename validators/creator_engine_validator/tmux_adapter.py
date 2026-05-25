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

import subprocess
from dataclasses import dataclass
from typing import Callable, Sequence

TMUX_BIN = "tmux"

# Tab-separated identity format expanded by tmux ``-F``.
_IDENTITY_FORMAT = "#{session_id}\t#{window_id}\t#{pane_id}\t#{pane_tty}\t#{pane_pid}"


class TmuxError(Exception):
    """Base class for tmux adapter errors."""


class TmuxUnavailable(TmuxError):
    """tmux is not available, so a visible lane cannot be launched."""


@dataclass(frozen=True)
class TmuxPane:
    """Concrete tmux pane identity for a launched lane."""

    session_id: str
    window_id: str
    pane_id: str
    pane_tty: str | None = None
    pane_pid: int | None = None


Runner = Callable[..., subprocess.CompletedProcess]


def _default_runner(argv: Sequence[str], check: bool = True) -> subprocess.CompletedProcess:
    return subprocess.run(list(argv), check=check, capture_output=True, text=True)


class TmuxAdapter:
    """Adapter over the tmux binary with an injectable subprocess runner."""

    kind = "tmux"

    def __init__(self, *, runner: Runner | None = None, tmux_bin: str = TMUX_BIN):
        self._runner = runner or _default_runner
        self._tmux_bin = tmux_bin

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

    def ensure_pane(self, *, session: str, window: str, command: Sequence[str]) -> TmuxPane:
        """Spawn or attach a tmux pane/window running ``command``; return its identity.

        Creates ``session`` with the requested window when it does not exist,
        otherwise adds a new window to the live session. ``command`` is a local
        command vector; no provider/model is launched.
        """
        if not self.is_available():
            raise TmuxUnavailable(
                "tmux is unavailable; a visibility-required lane cannot be launched"
            )

        command = list(command)
        if self._session_exists(session):
            argv = [
                self._tmux_bin, "new-window", "-d",
                "-t", session, "-n", window,
                "-P", "-F", _IDENTITY_FORMAT,
                *command,
            ]
        else:
            argv = [
                self._tmux_bin, "new-session", "-d",
                "-s", session, "-n", window,
                "-P", "-F", _IDENTITY_FORMAT,
                *command,
            ]
        proc = self._runner(argv)
        return self._parse_identity(proc.stdout)

    @staticmethod
    def _parse_identity(stdout: str) -> TmuxPane:
        line = (stdout or "").strip().splitlines()
        fields = (line[0].split("\t") if line else [])
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
