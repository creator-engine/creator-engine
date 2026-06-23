"""CE-owned attachable PTY session substrate (ce-ops#207, W2′).

.. note::

   **SUPERSEDED-IN-PRINCIPLE by the herdr-ce fork (ce-ops#217, Posture A).** The
   ``pty.fork`` byte-tap below is the hand-rolled precursor to herdr's productized
   pane/socket model; the design-of-record
   (``.ce/state/research/DESIGN_COCKPIT_ON_HERDR_20260623.md`` §2) routes the
   forward backend through ``runner/herdr_session.HerdrSession`` over the herdr
   JSON socket. U3 implements ``terminal_kind=herdr`` against that seam and
   RETIRES this ``pty.fork`` path behind the visibility-backend registry. This
   module is **kept live until U3 retires it** (do not delete here); the
   ``surface_ref`` control-socket concept it reserves becomes the herdr socket ref.
   TODO(ce-ops#217 U3): retire the ``pty.fork`` backend; keep the registry seam.

The headless visibility backend must hand CE — **not tmux** — ownership of the
seat process *and its PTY*. This module is that substrate: it spawns the
sentinel-wrapped seat argv under a PTY whose **master fd CE holds**, so the live
byte stream of the seat exists on CE's governance spine regardless of any
renderer. It is the structural fix for the witnessability gap where today the
work-stream lives only in the tmux pane buffer and dies with tmux.

Design invariants (deliberate, load-bearing):

* **CE owns the PTY master.** ``pty.fork`` wires the child to a fresh PTY slave as
  its controlling tty (so the seat sees an interactive tty exactly as under tmux)
  and hands the parent the master fd. CE is the process owner — there is no tmux
  server in the loop.
* **The master tap EXISTS but raw bytes are NOT streamed out here.** Owning the
  master fd is what makes attach *possible*, but raw-byte streaming OUT — and the
  redaction gate that any raw surface needs — is the separate W2-sec / T1 lane.
  This module hands the master fd to the substrate (so W2-sec/T1 can build on it)
  and **does not write the bytes to any new surface**: stdout/stderr are not
  redirected to a log, not echoed, not persisted. Value-bearing bytes never leave
  CE's process here.
* **The sentinel wrapper stays OUTERMOST.** The caller wraps the (already
  governed, already resource-bounded) argv in the seat-sentinel POSIX-sh
  supervisor and hands *that* argv here, so ``events.jsonl`` lifecycle events are
  produced identically to the tmux path — the substrate change is *which surface
  owns the PTY*, not the wrapper contract.
* **Detach-survivable.** The seat keeps running with no client attached (the
  master fd is held by this substrate, not a client). A control-socket *ref* is
  recorded for the future attach RPC (T1); this module does not implement the
  socket server — it only reserves the path the Pane Registry record points at.
* **v1 classification.** This is the v1 launcher's PTY-owning surface seam,
  consumed only by ``visibility_backend`` (v1) → ``lane_runtime`` (v1). It imports
  only stdlib; no v3 crossing.
"""
from __future__ import annotations

import os
import pty
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path


class SeatPtySessionError(Exception):
    """A CE-owned PTY session could not be established."""


@dataclass(frozen=True)
class SeatPtySession:
    """A live, CE-owned PTY session wrapping a seat process.

    ``master_fd`` is the single byte tap CE holds (the seat's stdout/stderr +
    interactive input route through it). It is the substrate the future attach
    RPC reads/writes; this unit does **not** stream it anywhere. ``surface_ref``
    is the per-session control-socket path the Pane Registry record points at
    (reserved for T1's attach server — not bound here). ``pid`` is the seat
    process id CE owns and the reaper (W4) terminates.
    """

    pid: int
    master_fd: int
    surface_ref: str

    def close_master(self) -> None:
        """Release the master fd. Idempotent; never reaps the child (W4 owns that)."""
        try:
            os.close(self.master_fd)
        except OSError:
            pass


def socket_ref_for(seat_dir: str | Path) -> Path:
    """Return the per-session control-socket path under the seat dir.

    The path is *reserved* (recorded in the Pane Registry ``surface_ref``) for the
    future attach server (T1). This unit does not bind the socket — owning the
    PTY master is what makes attach possible; the socket server is a later lane.
    """
    return Path(seat_dir) / "attach.sock"


# Injection seam for tests: production uses ``pty.fork`` (forks + wires the child
# to a PTY slave as its controlling tty, returns ``(pid, master_fd)`` in the
# parent and ``(0, slave_fd)`` in the child).
ForkPty = Callable[[], "tuple[int, int]"]


def spawn_pty_session(
    *,
    command: Sequence[str],
    seat_dir: str | Path,
    cwd: str | None = None,
    env: Mapping[str, str] | None = None,
    _forkpty: ForkPty | None = None,
) -> SeatPtySession:
    """Spawn ``command`` under a CE-owned PTY; return the live :class:`SeatPtySession`.

    The child execs ``command`` with a PTY slave as its controlling tty and the
    caller-supplied ``cwd``/``env`` applied; the parent keeps the master fd. The
    seat-pinned env (``CE_LEDGER_ROOT`` / reviewer-authority ref) is set on the
    child exactly as the tmux backend pins it via ``tmux -e`` — never echoed,
    never on argv.

    ``_forkpty`` is an injection seam for tests; production never passes it.
    """
    argv = list(command)
    if not argv:
        raise SeatPtySessionError("refusing to spawn an empty PTY command")

    seat_dir = Path(seat_dir)
    surface_ref = str(socket_ref_for(seat_dir))

    forkpty = _forkpty if _forkpty is not None else pty.fork
    pid, master_fd = forkpty()
    if pid == 0:
        # --- child: exec the seat under the PTY slave (now our controlling tty) ---
        try:
            if cwd:
                os.chdir(cwd)
            child_env = dict(os.environ)
            if env:
                child_env.update({str(k): str(v) for k, v in env.items()})
            os.execvpe(argv[0], argv, child_env)
        except BaseException:
            # exec failed in the child: exit non-zero so the sentinel wrapper's
            # ``exited`` event still fires (silence≠success). Never fall through
            # into the parent's code path.
            os._exit(127)
    # --- parent: CE owns the master fd (the byte tap) and the seat pid ---
    return SeatPtySession(pid=pid, master_fd=master_fd, surface_ref=surface_ref)
