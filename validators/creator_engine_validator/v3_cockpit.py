"""CE v3.5-B.1 — the Cockpit L3 Textual view. BINDS to L2 snapshots; computes nothing.

The principle-6 law (design §3.0.6, [[ce-cockpit-frontend-agnostic-core]]):
this module is the REPLACEABLE view layer. It receives the ONE
JSON-serializable L2 snapshot (produced by the L2 read-model module in
``runner/``, delivered by ``v3_cli``) plus an optional ``reload`` callable and renders it —
**no fold, no filter, no derivation, no direct spine/registry read happens
here** (a source-level test enforces it). Every number and label on screen is
already present in the snapshot; widget callbacks only re-bind. A future full
GUI (web / Tauri / Electron / native) replaces THIS file only.

Layout (design §3.1): left rail (fleet nav) · center (the ops board) · right
rail (the governance/authority panel — its content lands in B.3). The
persistent ``CE_DEMO`` watermark renders whenever the snapshot's source carries
one (Fork 4 — a pitch demo is never mistaken for live governance).

The live tail: ``watchfiles.awatch`` (lazily imported, only when watch paths
are provided) wakes the app when an L1 root changes; the app then calls the
injected ``reload`` (which runs the L2 fold) and re-binds. The tail lives here
in app wiring; the fold stays in L2.

This module imports ``textual`` at module level BY DESIGN — it is only ever
loaded on the TUI path (``v3_cli`` lazy-imports it inside the ``cockpit``
dispatch; ``--json`` and every non-cockpit subcommand never touch it).

Read-only: observation + request + visible authority — never a new authority.
"""

from __future__ import annotations

import asyncio
from typing import Any, Callable, Sequence

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, VerticalScroll
from textual.widgets import DataTable, Footer, Header, Static

APP_TITLE = "◆ CE Cockpit"

#: The board table's column headings (presentation labels over snapshot fields).
_BOARD_COLUMNS = ("Scope", "Stage", "State", "Change-type", "Ready", "Bet")

SnapshotLoader = Callable[[], dict[str, Any]]


def _mark(flag: Any) -> str:
    return "✓" if flag else "—"


def _board_row(card: dict[str, Any]) -> tuple[str, ...]:
    """Format ONE card dict into a display row (pure presentation, no derivation)."""
    return (
        str(card.get("scope_id", "—")),
        str(card.get("phase", "—")),
        str(card.get("state", "—")),
        str(card.get("mutation_class", "—")),
        _mark(card.get("ready")),
        _mark(card.get("ratified")),
    )


def _seat_line(seat: dict[str, Any]) -> str:
    """Format ONE seat dict into a rail line (pure presentation)."""
    return (
        f"{seat.get('controller_id', '—')} / {seat.get('lane_id', '—')}\n"
        f"  {seat.get('role', '—')} · {seat.get('status', '—')}"
    )


def _left_rail_text(snapshot: dict[str, Any]) -> str:
    """Assemble the fleet-nav rail text from snapshot fields (presentation only)."""
    board = snapshot.get("board", {})
    counts = board.get("phase_counts", {})
    header = " · ".join(f"{phase} {counts.get(phase, 0)}" for phase in board.get("columns", []))
    seats = snapshot.get("seats", [])
    availability = snapshot.get("availability", {})
    lines = [header or "—", "", f"Seats ({availability.get('seats', '—')}):"]
    lines += [_seat_line(seat) for seat in seats]
    return "\n".join(lines)


def _refusal_lines(entry: dict[str, Any]) -> list[str]:
    """Format ONE refusal-feed entry (pure presentation)."""
    if entry.get("source") == "refusal-chain":
        clause = entry.get("deciding_clause") or "not covered by any envelope"
        return [
            f"⛔ {entry.get('recorded_at', '—')} · {entry.get('run_id', '—')}",
            f"   {entry.get('tool', '—')} → {entry.get('target', '—')}",
            f"   {entry.get('deny_kind', '—')} deny · {clause}",
        ]
    return [
        f"·  {entry.get('recorded_at', '—')} · legacy {entry.get('event', '—')} (advisory)"
    ]


def _seat_governance_lines(lane_id: str, seat: dict[str, Any]) -> list[str]:
    """Format ONE seat's envelope/matrix section (pure presentation)."""
    lines = [f"{lane_id}:"]
    envelope = seat.get("envelope")
    if envelope:
        lines.append(
            f"  envelope {envelope.get('envelope_id', '—')} → "
            f"{envelope.get('mechanic', '—')} on PR {envelope.get('pr_number', '—')}"
        )
        lines.append(f"  ratified_prompt_sha {envelope.get('ratified_prompt_sha', '—')}")
        lines.append(
            f"  actor {envelope.get('actor', '—')} · {envelope.get('emitting_role', '—')}"
            f" · {envelope.get('operating_mode', '—')}"
        )
    elif seat.get("no_write_authority"):
        lines.append("  envelope: none (no write authority provisioned)")
    else:
        lines.append("  envelope: — (every mechanic withheld)")
    cells = " ".join(
        f"{mechanic}={cell}" for mechanic, cell in (seat.get("matrix") or {}).items()
    )
    lines.append(f"  matrix: {cells}")
    return lines


def _right_rail_text(snapshot: dict[str, Any]) -> str:
    """The Governance/Authority panel — binds the four L2 sections (B.3)."""
    governance = snapshot.get("governance", {})
    refusals = snapshot.get("refusals", {})
    lines = ["Governance / Authority", ""]

    lines.append(f"★ REFUSED [{refusals.get('source_label', '—')}]")
    chain_verified = refusals.get("chain_verified")
    if chain_verified is not None:
        lines.append(f"  chain verifies: {'clean' if chain_verified else 'FINDINGS'}")
    for entry in refusals.get("entries", []):
        lines += _refusal_lines(entry)
    lines.append("")

    lines.append("Envelope (granted authority):")
    for lane_id, seat in (governance.get("seats") or {}).items():
        lines += _seat_governance_lines(str(lane_id), seat)
    lines.append("")

    lines.append("Ratified by / standing facts:")
    for fact in governance.get("standing_facts", []):
        lines.append(f"  • {fact}")
    lines.append("")

    posture = governance.get("posture", {})
    lines.append("Posture:")
    for hard in posture.get("hard_denies", []):
        lines.append(f"  hard: {hard}")
    for advisory in posture.get("advisory", []):
        lines.append(f"  advisory: {advisory}")
    return "\n".join(lines)


class CockpitApp(App[None]):
    """The read-only Cockpit TUI — one view bound to one L2 snapshot."""

    TITLE = APP_TITLE
    BINDINGS = [
        Binding("q", "quit", "Quit"),
        Binding("r", "refresh_snapshot", "Refresh"),
    ]
    CSS = """
    #watermark {
        dock: top;
        height: 1;
        text-align: center;
        text-style: bold;
        background: $warning;
        color: $text;
    }
    #left-rail {
        width: 32;
        border-right: solid $primary;
        padding: 0 1;
    }
    #board {
        width: 1fr;
    }
    #right-rail {
        width: 40;
        border-left: solid $primary;
        padding: 0 1;
    }
    """

    def __init__(
        self,
        snapshot: dict[str, Any],
        *,
        reload: SnapshotLoader | None = None,
        watch_paths: Sequence[str] = (),
    ) -> None:
        super().__init__()
        self._snapshot = snapshot
        self._reload = reload
        self._watch_paths = list(watch_paths)
        self._watch_task: asyncio.Task[None] | None = None

    # -- compose / bind -------------------------------------------------------
    def compose(self) -> ComposeResult:
        yield Header()
        watermark = (self._snapshot.get("source") or {}).get("watermark")
        if watermark:
            yield Static(str(watermark), id="watermark")
        with Horizontal(id="body"):
            yield VerticalScroll(Static("", id="left-rail-text"), id="left-rail")
            yield DataTable(id="board")
            yield VerticalScroll(Static("", id="right-rail-text"), id="right-rail")
        yield Footer()

    def on_mount(self) -> None:
        table = self.query_one("#board", DataTable)
        table.add_columns(*_BOARD_COLUMNS)
        self._bind_snapshot()
        if self._watch_paths and self._reload is not None:
            self._watch_task = asyncio.create_task(self._watch_loop())

    def _bind_snapshot(self) -> None:
        """Re-bind every widget to the CURRENT snapshot (no computation)."""
        table = self.query_one("#board", DataTable)
        table.clear()
        for card in self._snapshot.get("board", {}).get("cards", []):
            table.add_row(*_board_row(card))
        self.query_one("#left-rail-text", Static).update(_left_rail_text(self._snapshot))
        self.query_one("#right-rail-text", Static).update(_right_rail_text(self._snapshot))

    # -- refresh / live tail --------------------------------------------------
    def action_refresh_snapshot(self) -> None:
        if self._reload is not None:
            self._snapshot = self._reload()
            self._bind_snapshot()

    async def _watch_loop(self) -> None:
        """Tail the L1 roots and re-bind on change (the fold runs in L2 via reload)."""
        from watchfiles import awatch  # lazy: only the live-tail path needs it

        assert self._reload is not None
        async for _changes in awatch(*self._watch_paths):
            self._snapshot = self._reload()
            self._bind_snapshot()


def run_app(
    snapshot: dict[str, Any],
    *,
    reload: SnapshotLoader | None = None,
    watch_paths: Sequence[str] = (),
) -> int:
    """Run the Cockpit TUI over a prepared L2 snapshot; return a CLI exit code."""
    CockpitApp(snapshot, reload=reload, watch_paths=watch_paths).run()
    return 0
