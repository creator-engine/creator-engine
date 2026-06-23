"""Regression tests for retiring the #368 PTY byte-tap path (ce-ops#217 U3)."""

from __future__ import annotations

import inspect

import pytest

from creator_engine_validator import seat_pty_session as sps


def test_spawn_pty_session_is_retired_fail_closed(tmp_path):
    with pytest.raises(sps.SeatPtySessionRetired):
        sps.spawn_pty_session(command=["true"], seat_dir=str(tmp_path))


def test_spawn_pty_session_no_longer_exposes_fork_injection_seam() -> None:
    signature = inspect.signature(sps.spawn_pty_session)
    assert "_forkpty" not in signature.parameters


def test_module_no_longer_imports_pty_module() -> None:
    assert "pty" not in vars(sps)


def test_socket_ref_for_legacy_records_stays_under_seat_dir(tmp_path):
    assert sps.socket_ref_for(tmp_path) == tmp_path / "attach.sock"
