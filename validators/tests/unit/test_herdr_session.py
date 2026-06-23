"""Placeholder unit tests for the herdr-ce integration seam (ce-ops#217, U1).

U1 ships the CE-side adapter *scaffold* only — the interface and the boundary
documentation, with no live wiring. These tests pin the U1 contract: the
interface exists with the named surface (connect / spawn-pane / send / attach /
observe), and every method fails-closed with :class:`HerdrNotWired` until U3/U4
wire it live. The live behavioural coverage lands with U3 (socket drive) and U4
(attribution shim).
"""
from __future__ import annotations

import pytest

from creator_engine_validator.runner import herdr_session as hs


def test_terminal_kind_constant() -> None:
    assert hs.HERDR_TERMINAL_KIND == "herdr"


def test_pane_handle_shape() -> None:
    pane = hs.HerdrPane(pane_id="p0", surface_ref="/run/ce/herdr.sock", pid=4242)
    assert pane.pane_id == "p0"
    assert pane.surface_ref == "/run/ce/herdr.sock"
    assert pane.pid == 4242


def test_scaffold_exposes_the_named_interface() -> None:
    session = hs.HerdrSession(socket_path="/run/ce/herdr.sock")
    for name in ("connect", "spawn_pane", "send", "attach", "observe", "close"):
        assert callable(getattr(session, name)), name


def test_control_path_methods_fail_closed_until_wired() -> None:
    """U1 invariant: nothing is wired; the seam fails closed (HerdrNotWired)."""
    session = hs.HerdrSession()
    pane = hs.HerdrPane(pane_id="p0", surface_ref="/run/ce/herdr.sock")

    with pytest.raises(hs.HerdrNotWired):
        session.connect()
    with pytest.raises(hs.HerdrNotWired):
        session.spawn_pane(command=["true"])
    with pytest.raises(hs.HerdrNotWired):
        session.send(pane, b"steer")
    with pytest.raises(hs.HerdrNotWired):
        session.attach(pane)
    with pytest.raises(hs.HerdrNotWired):
        session.observe(pane)


def test_not_wired_is_a_notimplementederror() -> None:
    """HerdrNotWired is a NotImplementedError so callers can treat it uniformly."""
    assert issubclass(hs.HerdrNotWired, NotImplementedError)
    assert issubclass(hs.HerdrNotWired, hs.HerdrSessionError)


def test_close_is_idempotent_and_does_not_raise() -> None:
    session = hs.HerdrSession()
    session.close()
    session.close()
