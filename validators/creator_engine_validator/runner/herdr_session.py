"""CE-side integration seam to the herdr-ce multiplexer fork (ce-ops#217, U1).

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

**Status — U1 SCAFFOLD ONLY.** Nothing here is wired live. The methods raise
:class:`NotImplementedError`; no socket is opened, no ``herdr`` binary is
invoked, nothing is registered against the visibility-backend registry. The
module exists so U3/U4 have a stable interface to implement against and so the
seam boundary is documented in code now, before any live wiring exists.

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

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path

#: The ``terminal.kind`` key the herdr visibility backend will service (U3).
#: Parallels ``visibility_backend.TMUX_TERMINAL_KIND`` / ``HEADLESS_TERMINAL_KIND``.
HERDR_TERMINAL_KIND = "herdr"

#: The default per-host control-socket path herdr exposes. The concrete value is
#: substrate-owned and resolved by the containment wrapper (U2); recorded here as
#: the documented default, not bound by this scaffold.
DEFAULT_HERDR_SOCKET = "herdr.sock"


class HerdrSessionError(Exception):
    """A herdr-socket session could not be established or driven."""


class HerdrNotWired(HerdrSessionError, NotImplementedError):
    """Raised by the U1 scaffold: the herdr seam is not yet wired live (U3/U4)."""


@dataclass(frozen=True)
class HerdrPane:
    """A handle to a single herdr pane CE drives over the socket.

    Mirrors the shape the U3 :class:`VisibilityBackend` will stamp onto the Pane
    Registry ``terminal`` record (``{kind: herdr, surface_ref, pane_id, pid}``):
    ``surface_ref`` becomes the herdr control-socket ref (the productized form of
    #368's reserved ``attach.sock`` ``surface_ref``); ``pane_id`` is herdr's pane
    identifier; ``pid`` is the seat process herdr owns and the reaper terminates.
    """

    pane_id: str
    surface_ref: str
    pid: int | None = None


class HerdrSession:
    """CE-side client that drives the herdr-ce fork over its JSON Unix socket.

    **U1 scaffold:** the interface (connect / spawn-pane / send / attach /
    observe) is defined and documented; every method raises :class:`HerdrNotWired`.
    U3 implements ``connect``/``spawn_pane``/``observe`` against the live socket
    and wires this behind ``terminal_kind=herdr`` in the visibility-backend
    registry; U4 implements ``send`` through the attribution shim so it is the
    sole control-path writer (spine-append-before-effect, fail-closed).
    """

    def __init__(
        self,
        *,
        socket_path: str | Path = DEFAULT_HERDR_SOCKET,
    ) -> None:
        #: The substrate-owned herdr control socket. Held by the CE
        #: substrate/controller, never handed to a governed seat (§2/§7).
        self._socket_path = Path(socket_path)
        self._connected = False

    # -- connect ----------------------------------------------------------
    def connect(self) -> None:
        """Open the client connection to the substrate-owned herdr socket.

        U3: dial ``self._socket_path`` and negotiate the JSON protocol. The
        socket must already be owned by the CE substrate/controller process (U2
        containment wrapper); this client never *creates* the seat-reachable
        socket — it connects to the control socket the substrate holds.
        """
        raise HerdrNotWired("HerdrSession.connect is a U1 scaffold; wired in U3")

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

        U3: maps to ``herdr workspace create`` / ``herdr pane split`` /
        ``herdr pane run`` over the socket and returns a :class:`HerdrPane`. The
        sentinel wrapper stays OUTERMOST (the #368 contract) so ``events.jsonl``
        lifecycle events are produced identically; the substrate change is *which
        surface owns the PTY*, not the wrapper contract.
        """
        raise HerdrNotWired("HerdrSession.spawn_pane is a U1 scaffold; wired in U3")

    # -- send (steer) -----------------------------------------------------
    def send(self, pane: HerdrPane, data: bytes) -> None:
        """Inject input/keystrokes into ``pane`` — the governed control path.

        U4 (NOT U3): this is the steer path and is the §7-boundary keystone. It
        MUST route through the CE attribution shim, which appends a
        ``runtime_operator_steer`` record (actor / target_lane / bytes_digest /
        ts) to the evidence spine BEFORE the bytes reach the PTY, and fail
        CLOSED if the spine append fails (the steer does not execute). This
        :class:`HerdrSession` is the *only* control-path writer to the socket;
        the governed seat never holds the socket, so ``herdr pane run`` cannot
        become a §7 bypass. No-new-authority holds: a steer injects input, it
        cannot widen the seat's envelope — the seat's own tool-calls still pass
        its Ring-1 hook and the §7 hard-denies still fire.
        """
        raise HerdrNotWired(
            "HerdrSession.send is a U1 scaffold; the attribution shim is wired in U4"
        )

    # -- attach -----------------------------------------------------------
    def attach(self, pane: HerdrPane) -> None:
        """Attach an operator-visible live view of ``pane`` (detach-survivable).

        U3/U8: herdr is daemon-by-shape — panes survive the terminal closing and
        support detach/reattach. Attach is the live interactive surface (U8's
        A/B/C: multi-session, resizable stream, interactive steer). Steering
        through an attached view still funnels writes through :meth:`send`.
        """
        raise HerdrNotWired("HerdrSession.attach is a U1 scaffold; wired in U3/U8")

    # -- observe ----------------------------------------------------------
    def observe(self, pane: HerdrPane) -> bytes:
        """Read recent pane output for the evidence spine (witnessability).

        U3: maps to ``herdr pane read <id> --source recent-unwrapped`` and feeds
        the Pane Registry ``events.jsonl`` lifecycle / read-model fold. Observe
        is the read path; it never widens authority.
        """
        raise HerdrNotWired("HerdrSession.observe is a U1 scaffold; wired in U3")

    def close(self) -> None:
        """Release the client connection. Idempotent; never reaps a seat (reaper owns that)."""
        self._connected = False
