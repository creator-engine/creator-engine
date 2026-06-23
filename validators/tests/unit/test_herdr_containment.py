"""Unit tests for the herdr-ce containment-launch spec (ce-ops#217, U2).

U2 ships the containment-launch SPEC + a thin wrapper STUB. These tests pin the
U2 contract:

* :func:`plan_herdr_containment` is a pure translation that records the
  substrate-owned socket and asserts the §7/AGPL invariants;
* the §7 keystone is fail-closed: a policy whose seat-writable mount overlaps the
  substrate-owned socket directory is REFUSED
  (:class:`HerdrContainmentInvariantViolation`);
* herdr adds no new egress (the plan egress equals the policy allowlist);
* the live :class:`HerdrContainmentLaunch` surface fails closed
  (:class:`HerdrContainmentNotWired`) until U3 wires it.

No live behaviour is exercised — no socket opens, no subprocess runs. The live
contained-launch coverage lands with U3.
"""

from __future__ import annotations

import os

import pytest

from creator_engine_validator.runner import herdr_containment as hc


def _policy(*, writable=("/runtime/worktree",), egress=()) -> dict:
    """A minimal runtime-policy-shaped record (only the fields U2 reads)."""
    return {
        "mount_manifest": [
            {"path": "/runtime/ro", "mode": "ro"},
            *({"path": p, "mode": "rw"} for p in writable),
        ],
        "egress_allowlist": [dict(e) for e in egress],
    }


def test_terminal_kind_constant() -> None:
    assert hc.HERDR_TERMINAL_KIND == "herdr"


def test_plan_is_substrate_owned_socket_outside_seat_writable() -> None:
    plan = hc.plan_herdr_containment(
        _policy(writable=("/runtime/worktree",)),
        run_id="run-1",
        seat_command=["claude", "--seat"],
    )
    assert plan.socket_owner == "substrate"
    assert plan.socket_dir == hc.DEFAULT_SUBSTRATE_SOCKET_DIR
    assert plan.socket_path.endswith(hc.DEFAULT_HERDR_SOCKET_NAME)
    # the §7 keystone properties
    assert plan.socket_reachable_by_seat is False
    assert plan.no_new_egress is True
    # socket dir is not in the seat's writable set
    assert plan.socket_dir not in plan.seat_writable_paths
    assert plan.seat_command == ("claude", "--seat")


def test_plan_carries_exactly_policy_egress_no_new_entries() -> None:
    plan = hc.plan_herdr_containment(
        _policy(egress=({"host": "api.anthropic.com", "port": 443}, {"host": "example.test"})),
        run_id="run-egress",
        seat_command=["true"],
    )
    assert plan.egress_allowlist == ("api.anthropic.com:443", "example.test")
    assert plan.no_new_egress is True


def test_empty_egress_stays_empty_deny_by_default() -> None:
    plan = hc.plan_herdr_containment(_policy(egress=()), run_id="r", seat_command=["true"])
    assert plan.egress_allowlist == ()


def test_section7_keystone_socket_dir_inside_seat_writable_is_refused() -> None:
    """A seat-writable mount that CONTAINS the substrate socket dir is fail-closed."""
    with pytest.raises(hc.HerdrContainmentInvariantViolation):
        hc.plan_herdr_containment(
            _policy(writable=("/run/ce",)),  # parent of /run/ce/herdr → overlap
            run_id="r",
            seat_command=["true"],
        )


def test_section7_keystone_seat_writable_equals_socket_dir_is_refused() -> None:
    with pytest.raises(hc.HerdrContainmentInvariantViolation):
        hc.plan_herdr_containment(
            _policy(writable=(hc.DEFAULT_SUBSTRATE_SOCKET_DIR,)),
            run_id="r",
            seat_command=["true"],
        )


def test_section7_keystone_seat_writable_under_socket_dir_is_refused() -> None:
    with pytest.raises(hc.HerdrContainmentInvariantViolation):
        hc.plan_herdr_containment(
            _policy(writable=(hc.DEFAULT_SUBSTRATE_SOCKET_DIR + "/nested",)),
            run_id="r",
            seat_command=["true"],
        )


def test_disjoint_socket_dir_is_allowed() -> None:
    # an explicitly disjoint substrate socket dir + a seat writable elsewhere is fine
    plan = hc.plan_herdr_containment(
        _policy(writable=("/runtime/worktree",)),
        run_id="r",
        seat_command=["true"],
        substrate_socket_dir="/var/run/ce-substrate",
    )
    assert plan.socket_dir == "/var/run/ce-substrate"


def test_asserted_invariants_recorded() -> None:
    plan = hc.plan_herdr_containment(_policy(), run_id="r", seat_command=["true"])
    joined = " ".join(plan.asserted_invariants)
    assert "socket_owner=substrate" in joined
    assert "§7 keystone" in joined
    assert "no_new_egress" in joined
    assert "AGPL firewall" in joined


def test_launch_stub_fails_closed_until_u3() -> None:
    plan = hc.plan_herdr_containment(_policy(), run_id="r", seat_command=["true"])
    launch = hc.HerdrContainmentLaunch(plan)
    with pytest.raises(hc.HerdrContainmentNotWired):
        launch.launch()
    with pytest.raises(hc.HerdrContainmentNotWired):
        launch.control_socket_path()


def test_not_wired_is_a_notimplementederror() -> None:
    assert issubclass(hc.HerdrContainmentNotWired, NotImplementedError)
    assert issubclass(hc.HerdrContainmentNotWired, hc.HerdrContainmentError)
    assert issubclass(hc.HerdrContainmentInvariantViolation, hc.HerdrContainmentError)


def test_overlap_check_is_host_state_independent_no_filesystem_access(monkeypatch) -> None:
    """The §7 overlap check is PURE: same result whether or not paths exist on
    the host, and it must never touch the filesystem (no resolve/stat/symlink).

    We forbid any filesystem access in the overlap path by poisoning the
    fs-touching primitives the old ``Path(...).resolve()`` would have used; the
    planner must still produce the identical refusal/acceptance from the input
    strings alone.
    """

    def _boom(*_a, **_k):  # pragma: no cover - only fires on regression
        raise AssertionError("planner overlap check touched the filesystem (not pure)")

    # Poison the host-fs entry points a non-pure implementation would reach.
    monkeypatch.setattr(os.path, "realpath", _boom)
    monkeypatch.setattr(os, "stat", _boom)
    monkeypatch.setattr(os, "lstat", _boom)
    monkeypatch.setattr(os, "readlink", _boom)
    monkeypatch.setattr(os, "getcwd", _boom)

    # Overlapping (parent of socket dir) is still refused — purely from strings.
    with pytest.raises(hc.HerdrContainmentInvariantViolation):
        hc.plan_herdr_containment(
            _policy(writable=("/run/ce",)),
            run_id="r",
            seat_command=["true"],
        )
    # Disjoint is still accepted — purely from strings.
    plan = hc.plan_herdr_containment(
        _policy(writable=("/runtime/worktree",)),
        run_id="r",
        seat_command=["true"],
    )
    assert plan.socket_dir == hc.DEFAULT_SUBSTRATE_SOCKET_DIR


def test_overlap_check_is_lexical_not_symlink_resolving(tmp_path) -> None:
    """Symlink-shaped / non-existent inputs are compared LEXICALLY, never resolved.

    A pure planner must NOT follow symlinks: a seat-writable path that is a
    symlink whose target lives inside the socket dir must NOT be treated as
    overlapping, because the planner never consults the host fs. This pins the
    fix away from ``Path.resolve()``, which WOULD have followed the link and
    produced a host-state-dependent answer.
    """
    real_socket = tmp_path / "real-socket-dir"
    real_socket.mkdir()
    # A symlink whose *target* is inside the socket dir, but whose lexical path
    # is disjoint. resolve() would collapse it INTO the socket dir (overlap);
    # lexical normalization keeps it disjoint (no overlap).
    link = tmp_path / "seat-writable-link"
    link.symlink_to(real_socket / "nested")

    plan = hc.plan_herdr_containment(
        _policy(writable=(str(link),)),
        run_id="r",
        seat_command=["true"],
        substrate_socket_dir=str(real_socket),
    )
    # Lexically disjoint → allowed (host-state-independent); resolve() would have
    # raised the §7 violation here, proving the check no longer follows symlinks.
    assert plan.socket_dir == str(real_socket)


def test_overlap_helper_pure_on_nonexistent_and_normalized_paths() -> None:
    """``_overlaps`` returns identically on non-existent paths and normalizes
    lexically (``.``/``..``/dup-separators) with NO filesystem access."""
    # Non-existent paths: child nested under parent → overlap.
    assert hc._overlaps("/run/ce/herdr", "/run/ce") is True
    # Disjoint → no overlap.
    assert hc._overlaps("/run/ce/herdr", "/totally/other") is False
    # Not a raw string-prefix false positive: /run/ce-other is NOT under /run/ce.
    assert hc._overlaps("/run/ce-other", "/run/ce") is False
    # Lexical normalization: ``.``/``..``/duplicate separators collapse to equal.
    assert hc._overlaps("/run/ce/./herdr/../herdr", "/run/ce/herdr") is True
    assert hc._overlaps("/run//ce/herdr", "/run/ce") is True


def test_launch_refuses_non_substrate_owned_plan() -> None:
    """Defense-in-depth: a (hand-forged) seat-owned plan is refused at the seam."""
    bad = hc.HerdrContainmentPlan(
        backend_key="openshell",
        run_id="r",
        herdr_binary="herdr",
        socket_dir="/run/ce/herdr",
        socket_path="/run/ce/herdr/control.sock",
        socket_owner="seat",  # forbidden
        seat_command=("true",),
        seat_writable_paths=(),
        egress_allowlist=(),
    )
    with pytest.raises(hc.HerdrContainmentInvariantViolation):
        hc.HerdrContainmentLaunch(bad)
