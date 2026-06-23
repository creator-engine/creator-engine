"""Retired CE-owned PTY session substrate (ce-ops#207 W2′ → ce-ops#217 U3).

.. note::

The #368 hand-rolled PTY byte tap is superseded by the herdr-ce Posture A
backend. U3 keeps this module only as a compatibility shell for older imports and
for the ``surface_ref`` helper concept, which now maps to an opaque herdr
surface id. No production path in this module forks, opens, or owns a PTY;
callers must use ``terminal_kind=herdr`` through the visibility-backend registry.
"""
from __future__ import annotations

import os
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path


class SeatPtySessionError(Exception):
    """A CE-owned PTY session could not be established."""


class SeatPtySessionRetired(SeatPtySessionError, NotImplementedError):
    """The #368 PTY byte-tap path has been retired; use herdr instead."""


@dataclass(frozen=True)
class SeatPtySession:
    """Legacy data shape for the retired CE-owned PTY session.

    Kept so historical tests/imports can name the old shape while U3 removes the
    live spawn path. New live records use ``HerdrPane`` and ``terminal.kind=herdr``.
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
    """Return the retired #368 attach-socket path under the seat dir.

    Historical helper only. In the live U3 path, Pane Registry ``surface_ref`` is
    an opaque herdr surface id; the raw herdr socket path stays controller-private.
    """
    return Path(seat_dir) / "attach.sock"


def spawn_pty_session(
    *,
    command: Sequence[str],
    seat_dir: str | Path,
    cwd: str | None = None,
    env: Mapping[str, str] | None = None,
) -> SeatPtySession:
    """Fail closed: the live #368 PTY byte-tap path is retired."""
    raise SeatPtySessionRetired(
        "spawn_pty_session is retired by ce-ops#217 U3; use terminal_kind='herdr' "
        "so CE drives the substrate-owned herdr socket instead"
    )
