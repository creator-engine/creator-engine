"""CE-substrate containment-launch spec for the herdr-ce multiplexer (ce-ops#217, U2).

This module is the **U2 containment wrapper**: it defines how the CE substrate
launches the ``creator-engine/herdr-ce`` AGPL multiplexer binary under CE's
mandatory containment (bwrap/gVisor → OpenShell payload, ce-ops#115/#128) with
the load-bearing **§7 keystone invariant** front-and-centre:

    The herdr control socket is OWNED by the CE substrate/controller process and
    is NEVER handed to the governed seat. The seat runs *inside* a herdr pane as a
    confined child; it never gets a handle to the control socket — exactly as a
    seat today does not control its own tmux server. This is what stops
    ``herdr pane run`` from becoming a §7 (``governed-seat-cannot-push``) bypass.

Design-of-record: ``.ce/state/research/DESIGN_COCKPIT_ON_HERDR_20260623.md``
(§2 containment fit + the §7-boundary risk, §5 unit U2). Boundary doc:
``docs/architecture/HERDR_GOVERNANCE_BOUNDARY.md`` (the AGPL firewall + §7
corollary, landed by the U1 CE-side scaffold). The CE-side socket *client*
(``HerdrSession``) is the U1 scaffold; the live ``terminal_kind=herdr``
visibility backend is U3; the attribution shim (sole control-path writer) is U4.

**Status — U2 SPEC + STUB ONLY (no live agent sessions; that is U3).** This
slice ships:

* :func:`plan_herdr_containment` — a PURE translation (no I/O) of a runtime-policy
  record into a :class:`HerdrContainmentPlan`: the substrate-owned socket
  directory, the per-seat control-socket path, and the assertions that pin the
  invariants (no new egress beyond the policy's allowlist; the socket directory
  is substrate-owned and NOT in the seat's writable mount set);
* :class:`HerdrContainmentLaunch` — a thin wrapper STUB whose live ``launch`` /
  ``control_socket_path`` methods fail **closed**
  (:class:`HerdrContainmentNotWired`) until U3 wires them against a live
  ``RunnerBackend`` (gVisor/OpenShell). The pure plan + the invariant assertions
  are exercised now; nothing spawns a process or opens a socket on import.

The split mirrors the OpenShell/gVisor backends' translate-vs-execute boundary:
the pure plan is fully unit-tested; the only live surface (the actual contained
launch) is deferred behind a fail-closed stub so CI runs no subprocess and opens
no socket. Defensive only — this hardens CE's own agent runtime; never an
offensive capability.
"""

from __future__ import annotations

import os
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import PurePosixPath
from typing import Any

#: The ``terminal.kind`` this containment wrapper services — parallels
#: ``herdr_session.HERDR_TERMINAL_KIND`` (kept as a literal here so U2 does not
#: import the U1 scaffold module, which lands in a separate PR).
HERDR_TERMINAL_KIND = "herdr"

#: The substrate-owned directory the herdr control socket lives in. It is held by
#: the CE substrate/controller and is NEVER added to a governed seat's writable
#: mount set — the keystone of the §7 boundary. The concrete root is overlay /
#: deployment-time; this is the documented default the plan pins.
DEFAULT_SUBSTRATE_SOCKET_DIR = "/run/ce/herdr"

#: The control-socket filename inside the substrate-owned directory.
DEFAULT_HERDR_SOCKET_NAME = "control.sock"

#: The herdr binary the substrate launches under containment. Resolved from the
#: image / PATH at deploy time; recorded as the documented default.
DEFAULT_HERDR_BINARY = "herdr"


class HerdrContainmentError(Exception):
    """A herdr containment plan or launch could not be established."""


class HerdrContainmentInvariantViolation(HerdrContainmentError):
    """A containment plan would violate a load-bearing §7/AGPL boundary invariant.

    Raised by :func:`plan_herdr_containment` when the requested policy would, for
    example, place the substrate-owned socket directory inside the governed seat's
    writable mount set — i.e. hand the seat a path to the control socket. This is
    fail-closed: the plan refuses rather than silently weakening the boundary.
    """


class HerdrContainmentNotWired(HerdrContainmentError, NotImplementedError):
    """Raised by the U2 stub: the live contained launch is not wired yet (U3)."""


@dataclass(frozen=True)
class HerdrContainmentPlan:
    """A pure, value-free plan for launching herdr under CE containment (U2).

    Carries POINTERS only — no live handles, no opened socket. Produced by
    :func:`plan_herdr_containment` and consumed by the U3 live launch.

    Invariants pinned on this plan (asserted at construction in the planner):

    * ``socket_dir`` (substrate-owned) does NOT overlap any ``seat_writable_paths``
      entry — the governed seat cannot reach the control socket (the §7 keystone).
    * ``egress_allowlist`` is exactly the policy's allowlist — herdr adds NO new
      egress (it is local-first: local PTYs + a local Unix socket).
    * ``socket_owner == "substrate"`` always — never ``"seat"``.
    """

    backend_key: str
    run_id: str
    herdr_binary: str
    #: The substrate-owned directory holding the control socket (NOT seat-writable).
    socket_dir: str
    #: The per-seat control-socket path inside ``socket_dir``.
    socket_path: str
    #: Who owns the control socket. Structurally always ``"substrate"`` (the
    #: keystone); a ``"seat"`` value is rejected by the planner.
    socket_owner: str
    #: The seat command herdr runs inside a pane (sentinel-wrapped upstream).
    seat_command: tuple[str, ...]
    #: The seat's writable mount paths — the socket_dir must NOT overlap these.
    seat_writable_paths: tuple[str, ...]
    #: The egress allowlist (host[:port]) — equals the policy's; herdr adds none.
    egress_allowlist: tuple[str, ...]
    #: Invariant assertions recorded for the evidence spine / audit.
    asserted_invariants: tuple[str, ...] = field(default_factory=tuple)

    @property
    def no_new_egress(self) -> bool:
        """True — herdr is local-first; the plan never widens the policy egress."""
        return True

    @property
    def socket_reachable_by_seat(self) -> bool:
        """False by construction — the §7 keystone (planner rejects otherwise)."""
        return False


def _writable_paths(runtime_policy: Mapping[str, Any]) -> tuple[str, ...]:
    """Extract the seat's read-write mount paths from a runtime-policy record."""
    paths: list[str] = []
    for entry in runtime_policy.get("mount_manifest") or []:
        if isinstance(entry, dict) and entry.get("mode") == "rw":
            path = entry.get("path")
            if isinstance(path, str) and path:
                paths.append(path)
    return tuple(paths)


def _egress_allowlist(runtime_policy: Mapping[str, Any]) -> tuple[str, ...]:
    """Extract host[:port] egress entries from a runtime-policy record (deny-by-default)."""
    out: list[str] = []
    for entry in runtime_policy.get("egress_allowlist") or []:
        if not isinstance(entry, dict):
            continue
        host = entry.get("host")
        if not isinstance(host, str) or not host:
            continue
        port = entry.get("port")
        out.append(f"{host}:{port}" if isinstance(port, int) else host)
    return tuple(out)


def _normalize(path: str) -> PurePosixPath:
    """Lexically normalize a POSIX container path — PURE, no filesystem access.

    Uses pure-string normalization (``os.path.normpath`` semantics via
    ``PurePosixPath``-of-``os.path.normpath``): collapses ``.``/``..``/duplicate
    separators WITHOUT touching the host filesystem or resolving symlinks. This
    keeps the §7 overlap check deterministic regardless of host fs/symlink state
    (the planner is a PURE runtime-policy → containment-plan translation).
    """
    # os.path.normpath is pure string normalization (no fs/symlink access);
    # PurePosixPath then gives structural parent/equality comparison.
    return PurePosixPath(os.path.normpath(path))


def _is_within(child: str, parent: str) -> bool:
    """True when ``child`` is ``parent`` or nested under it (lexical path-prefix).

    PURE: compares lexically-normalized paths with NO filesystem access — the
    result depends only on the input strings, never on host fs/symlink state.
    """
    cp = _normalize(child)
    pp = _normalize(parent)
    return cp == pp or pp in cp.parents


def _overlaps(a: str, b: str) -> bool:
    """True when paths ``a`` and ``b`` are equal or one contains the other."""
    return a == b or _is_within(a, b) or _is_within(b, a)


def plan_herdr_containment(
    runtime_policy: Mapping[str, Any],
    *,
    run_id: str,
    seat_command: Sequence[str],
    backend_key: str = "openshell",
    herdr_binary: str = DEFAULT_HERDR_BINARY,
    substrate_socket_dir: str = DEFAULT_SUBSTRATE_SOCKET_DIR,
    socket_name: str = DEFAULT_HERDR_SOCKET_NAME,
) -> HerdrContainmentPlan:
    """Translate a runtime-policy record into a herdr containment plan (PURE, no I/O).

    The plan launches the herdr-ce binary under the chosen isolation backend with
    the substrate owning the control socket. It asserts the load-bearing §7/AGPL
    invariants and raises :class:`HerdrContainmentInvariantViolation` (fail-closed)
    if any would be violated:

    * **Socket ownership (the §7 keystone).** The substrate-owned ``socket_dir``
      MUST NOT overlap any seat read-write mount path (equal, nested under, or a
      parent of) — otherwise the governed seat could reach the control socket and
      turn ``herdr pane run`` into a §7 bypass. Violation → refuse.
    * **No new egress.** herdr is local-first (local PTYs + a local Unix socket);
      the plan carries exactly the policy's ``egress_allowlist`` and never adds an
      entry. (deny-by-default is preserved upstream by the backend translation.)

    No container is allocated, no socket is opened, no subprocess is run — that is
    the U3 live launch (:meth:`HerdrContainmentLaunch.launch`).
    """
    socket_dir = substrate_socket_dir
    socket_path = str(PurePosixPath(socket_dir) / socket_name)
    seat_writable = _writable_paths(runtime_policy)

    # §7 keystone: the substrate-owned socket dir must not overlap any
    # seat-writable path. Fail closed otherwise.
    for writable in seat_writable:
        if _overlaps(socket_dir, writable):
            raise HerdrContainmentInvariantViolation(
                "the substrate-owned herdr socket directory "
                f"{socket_dir!r} overlaps the governed seat's writable mount "
                f"{writable!r}; the seat would reach the control socket "
                "(a §7 bypass). The socket directory must be substrate-owned and "
                "outside every seat-writable mount."
            )

    egress = _egress_allowlist(runtime_policy)

    invariants = (
        "socket_owner=substrate (the control socket is never handed to the seat)",
        "socket_dir is outside every seat read-write mount (§7 keystone)",
        "no_new_egress (herdr is local-first; egress == policy allowlist)",
        "the seat's own tool-calls still pass its Ring-1 hook; §7 hard-denies fire",
        "CE Python drives the socket as a separate process; never linked into the "
        "AGPL Rust binary (the AGPL firewall)",
    )

    return HerdrContainmentPlan(
        backend_key=backend_key,
        run_id=run_id,
        herdr_binary=herdr_binary,
        socket_dir=socket_dir,
        socket_path=socket_path,
        socket_owner="substrate",
        seat_command=tuple(seat_command),
        seat_writable_paths=seat_writable,
        egress_allowlist=egress,
        asserted_invariants=invariants,
    )


class HerdrContainmentLaunch:
    """Thin wrapper that launches herdr under CE containment (U2 STUB; live in U3).

    Holds a :class:`HerdrContainmentPlan` and, in U3, will drive a live
    :class:`~creator_engine_validator.runner.backend.RunnerBackend` (gVisor or
    OpenShell) to start the contained herdr binary, then expose the
    substrate-owned control socket to the CE controller (and ONLY the controller).

    **U2 stub:** :meth:`launch` and :meth:`control_socket_path` fail closed with
    :class:`HerdrContainmentNotWired`. The plan and its invariants are available
    now (``self.plan``); nothing here opens a socket or spawns a process.
    """

    def __init__(self, plan: HerdrContainmentPlan) -> None:
        if plan.socket_owner != "substrate":
            # Defense-in-depth: a plan must never reach launch with a seat-owned
            # socket. The planner already guarantees this; re-assert at the seam.
            raise HerdrContainmentInvariantViolation(
                "refusing a containment launch whose control socket is not "
                f"substrate-owned (socket_owner={plan.socket_owner!r})"
            )
        self.plan = plan

    def launch(self) -> None:
        """Start the contained herdr binary under the backend (U3).

        U3: provision the isolation backend from the runtime policy, start the
        herdr binary inside it with the substrate-owned socket bound in the
        substrate's namespace (NOT the seat's), and return a handle the CE
        controller uses to drive the socket. The seat runs as a confined child
        inside a herdr pane and never receives the control socket.
        """
        raise HerdrContainmentNotWired(
            "HerdrContainmentLaunch.launch is a U2 stub; the live contained "
            "launch is wired in U3"
        )

    def control_socket_path(self) -> str:
        """Return the substrate-owned control-socket path (U3, controller-only).

        U3: returns the live socket path ONLY to the CE substrate/controller; it
        is never exposed to the governed seat. The stub fails closed so no caller
        can mistake the planned path for a live, controller-held socket.
        """
        raise HerdrContainmentNotWired(
            "HerdrContainmentLaunch.control_socket_path is a U2 stub; the live "
            "controller-held socket is exposed in U3"
        )
