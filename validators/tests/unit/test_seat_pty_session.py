"""Unit tests for the CE-owned PTY session substrate (ce-ops#207 W2′).

These exercise the real ``pty.fork`` path (not a double) to prove CE actually
owns a live PTY master fd over the seat process — the structural fix for the
witnessability gap where the work-stream lived only in the tmux pane buffer.
"""
from __future__ import annotations

import os

import pytest

from creator_engine_validator import seat_pty_session as sps


def _drain_and_reap(session: sps.SeatPtySession) -> int:
    """Read the master fd to EOF, then reap the child; return its exit status."""
    try:
        while True:
            try:
                chunk = os.read(session.master_fd, 1024)
            except OSError:
                break
            if not chunk:
                break
    finally:
        session.close_master()
    _, status = os.waitpid(session.pid, 0)
    return status


def test_spawn_owns_a_live_pty_master_over_the_seat(tmp_path):
    # The seat writes a marker to its (PTY) stdout; CE reads it off the master fd
    # it owns — proving the live byte tap exists on CE's side, no tmux involved.
    session = sps.spawn_pty_session(
        command=["/bin/sh", "-c", "printf CE_OWNS_PTY"],
        seat_dir=str(tmp_path),
    )
    assert session.pid > 0
    assert session.master_fd >= 0
    # surface_ref is the reserved control-socket path under the seat dir.
    assert session.surface_ref == str(tmp_path / "attach.sock")

    data = b""
    try:
        while True:
            try:
                chunk = os.read(session.master_fd, 1024)
            except OSError:
                break
            if not chunk:
                break
            data += chunk
    finally:
        session.close_master()
    os.waitpid(session.pid, 0)
    assert b"CE_OWNS_PTY" in data


def test_spawn_applies_seat_env_to_the_child(tmp_path):
    # The seat-pinned env reaches the child's environment (the launch-pinned
    # CE_LEDGER_ROOT carrier) — set in the env, never echoed onto argv.
    session = sps.spawn_pty_session(
        command=["/bin/sh", "-c", 'printf "%s" "$CE_TEST_PIN"'],
        seat_dir=str(tmp_path),
        env={"CE_TEST_PIN": "pinned-value"},
    )
    data = b""
    while True:
        try:
            chunk = os.read(session.master_fd, 1024)
        except OSError:
            break
        if not chunk:
            break
        data += chunk
    session.close_master()
    os.waitpid(session.pid, 0)
    assert b"pinned-value" in data


def test_spawn_runs_in_the_requested_cwd(tmp_path):
    workdir = tmp_path / "worktree"
    workdir.mkdir()
    session = sps.spawn_pty_session(
        command=["/bin/sh", "-c", "pwd"],
        seat_dir=str(tmp_path),
        cwd=str(workdir),
    )
    data = b""
    while True:
        try:
            chunk = os.read(session.master_fd, 1024)
        except OSError:
            break
        if not chunk:
            break
        data += chunk
    session.close_master()
    os.waitpid(session.pid, 0)
    assert os.path.realpath(str(workdir)).encode() in data


def test_spawn_refuses_empty_command(tmp_path):
    with pytest.raises(sps.SeatPtySessionError):
        sps.spawn_pty_session(command=[], seat_dir=str(tmp_path))


def test_failed_exec_in_child_exits_nonzero(tmp_path):
    # A non-existent binary: the child's exec fails and it exits 127 (so the
    # sentinel wrapper's `exited` event still fires — silence != success).
    session = sps.spawn_pty_session(
        command=["this-binary-does-not-exist-ce207"],
        seat_dir=str(tmp_path),
    )
    status = _drain_and_reap(session)
    assert os.WIFEXITED(status)
    assert os.WEXITSTATUS(status) == 127


def test_close_master_is_idempotent(tmp_path):
    session = sps.spawn_pty_session(
        command=["/bin/sh", "-c", "true"], seat_dir=str(tmp_path)
    )
    os.waitpid(session.pid, 0)
    session.close_master()
    session.close_master()  # second close must not raise


def test_socket_ref_for_is_under_seat_dir(tmp_path):
    assert sps.socket_ref_for(tmp_path) == tmp_path / "attach.sock"
