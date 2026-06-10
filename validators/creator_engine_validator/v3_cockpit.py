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
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.widgets import DataTable, Footer, Header, Static, TabPane, TabbedContent

APP_TITLE = "◆ CE Cockpit"

#: The board table's column headings (presentation labels over snapshot fields).
_BOARD_COLUMNS = (
    "Scope", "Stage", "State", "Seat", "Role", "Status",
    "Harness/Model", "Envelope", "Outcome", "Why blocked",
)

#: The crabfleet filter triad — keys bind to the L2-precomputed id lists.
_FILTER_KEYS = ("all", "mine", "live")

SnapshotLoader = Callable[[], dict[str, Any]]


def _mark(flag: Any) -> str:
    return "✓" if flag else "—"


def _board_row(card: dict[str, Any]) -> tuple[str, ...]:
    """Format ONE card dict into a display row (pure presentation, no derivation)."""
    seat = card.get("seat") or {}
    harness_model = f"{seat.get('harness') or '—'}/{seat.get('model') or '—'}"
    return (
        str(card.get("scope_id", "—")),
        str(card.get("phase", "—")),
        str(card.get("state", "—")),
        str(seat.get("controller_id") or "—"),
        str(card.get("role_badge") or "—"),
        str(card.get("status_chip", "—")),
        harness_model,
        str(card.get("envelope_badge") or "—"),
        str(card.get("outcome_chip") or "—"),
        str(card.get("blocked_reason") or "—"),
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


def _stream_text(detail: dict[str, Any]) -> str:
    """Format the Stream tab — collapsed event-group spans (pure presentation)."""
    lines = []
    for group in (detail.get("stream") or {}).get("groups", []):
        if group.get("kind") == "actions":
            retry = f" ×{group['count']} RETRY" if group.get("retry") else ""
            lines.append(
                f"[{group.get('color', '—')}] {group.get('first_at', '—')} "
                f"{group.get('tool', '—')} → {group.get('target', '—')} · "
                f"{group.get('classification', '—')}{retry}"
            )
        else:
            lines.append(f"·  {group.get('recorded_at', '—')} {group.get('kind', '—')}")
    return "\n".join(lines) or "—"


def _diffs_text(detail: dict[str, Any]) -> str:
    diffs = detail.get("diffs") or {}
    lines = [f"source: {diffs.get('source', '—')}"]
    lines += [f"  {f.get('path', '—')}  ({f.get('writes', 0)} write(s))" for f in diffs.get("files", [])]
    return "\n".join(lines)


def _evidence_text(detail: dict[str, Any]) -> str:
    evidence = detail.get("evidence") or {}
    return (
        f"chain: {evidence.get('record_count', 0)} record(s) · "
        f"verify_chain: {evidence.get('badge', '—')}"
    )


def _waterfall_text(detail: dict[str, Any]) -> str:
    lines = []
    for stage in (detail.get("waterfall") or {}).get("stages", []):
        duration = stage.get("duration_seconds")
        duration_text = f"{duration:.0f}s" if duration is not None else "—"
        lines.append(f"{stage.get('stage', '—'):>10}  {duration_text:>8}  ({stage.get('started_at', '—')})")
    return "\n".join(lines) or "—"


def _outcome_text(detail: dict[str, Any]) -> str:
    outcome = detail.get("outcome") or {}
    lines = [f"outcome: {outcome.get('outcome') or '—'}"]
    change_set = outcome.get("change_set")
    if change_set:
        lines.append(
            f"change: {change_set.get('branch', '—')} → {change_set.get('base', '—')} "
            f"(PR {change_set.get('pr_number', '—')} · head {change_set.get('head_sha', '—')})"
        )
    ratification = outcome.get("ratification")
    if ratification:
        lines.append(f"ratified_prompt_sha: {ratification.get('ratified_prompt_sha', '—')}")
        lines.append(f"approver_ref: {ratification.get('approver_ref', '—')}")
    else:
        lines.append("ratification: —")
    return "\n".join(lines)


def _meter_strip_text(snapshot: dict[str, Any]) -> str:
    """Format the unified meter strip — every tile shows its honesty badge (B.4)."""
    meters = snapshot.get("meters", {})
    spend = meters.get("spend", {})
    token = meters.get("token_rate", {})
    context = meters.get("context", {})
    headroom = meters.get("subscription_headroom", {})

    spend_value = spend.get("spend")
    spend_text = f"${spend_value:.2f}" if spend_value is not None else "—"
    rate = token.get("tokens_per_hour")
    rate_text = f"{rate:,.0f} tok/hr" if rate is not None else "—"
    pct = context.get("pct")
    ctx_text = f"{pct:.0f}% {context.get('state', '—')}" if pct is not None else "—"

    segments = [
        f"spend {spend_text} [{spend.get('badge', '—')}]",
        f"rate {rate_text} [{token.get('badge', '—')}]",
        f"ctx {ctx_text} [{context.get('badge', '—')}]",
        f"headroom {headroom.get('placeholder', '—')} [{headroom.get('badge', '—')}]",
    ]
    lines = ["  │  ".join(segments)]
    for banner in meters.get("banners", []):
        lines.append(
            f"⛔ {str(banner.get('tier', '—')).upper()} BREACH · {banner.get('run_id', '—')} · "
            f"{banner.get('unit', '')}{banner.get('observed', '—')}/"
            f"{banner.get('unit', '')}{banner.get('limit', '—')} · "
            f"{banner.get('signal', '—')} → {banner.get('action', '—')}"
        )
    return "\n".join(lines)


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
        Binding("a", "filter('all')", "All"),
        Binding("m", "filter('mine')", "Mine"),
        Binding("l", "filter('live')", "Live"),
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
    #center {
        width: 1fr;
    }
    #board {
        height: 1fr;
    }
    #detail {
        height: 14;
        border-top: solid $primary;
    }
    #right-rail {
        width: 40;
        border-left: solid $primary;
        padding: 0 1;
    }
    #meters {
        dock: bottom;
        height: auto;
        max-height: 4;
        border-top: solid $primary;
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
        self._active_filter = "all"
        self._row_lanes: list[str | None] = []

    # -- compose / bind -------------------------------------------------------
    def compose(self) -> ComposeResult:
        yield Header()
        watermark = (self._snapshot.get("source") or {}).get("watermark")
        if watermark:
            yield Static(str(watermark), id="watermark")
        with Horizontal(id="body"):
            yield VerticalScroll(Static("", id="left-rail-text"), id="left-rail")
            with Vertical(id="center"):
                yield DataTable(id="board")
                with TabbedContent(id="detail"):
                    with TabPane("Stream", id="tab-stream"):
                        yield Static("", id="detail-stream")
                    with TabPane("Diffs", id="tab-diffs"):
                        yield Static("", id="detail-diffs")
                    with TabPane("Evidence trail", id="tab-evidence"):
                        yield Static("", id="detail-evidence")
                    with TabPane("Waterfall", id="tab-waterfall"):
                        yield Static("", id="detail-waterfall")
                    with TabPane("Outcome", id="tab-outcome"):
                        yield Static("", id="detail-outcome")
            yield VerticalScroll(Static("", id="right-rail-text"), id="right-rail")
        yield Static("", id="meters")
        yield Footer()

    def on_mount(self) -> None:
        table = self.query_one("#board", DataTable)
        table.add_columns(*_BOARD_COLUMNS)
        table.cursor_type = "row"
        self._bind_snapshot()
        if self._watch_paths and self._reload is not None:
            self._watch_task = asyncio.create_task(self._watch_loop())

    def _bind_snapshot(self) -> None:
        """Re-bind every widget to the CURRENT snapshot (no computation).

        The active filter only selects which of the L2-precomputed id lists
        (``board.filters``) drives row inclusion — the fold happened in L2.
        """
        board = self._snapshot.get("board", {})
        included = set(
            (board.get("filters") or {}).get(self._active_filter, [])
            if self._active_filter != "all"
            else [c.get("scope_id") for c in board.get("cards", [])]
        )
        table = self.query_one("#board", DataTable)
        table.clear()
        self._row_lanes = []
        for card in board.get("cards", []):
            if card.get("scope_id") not in included:
                continue
            table.add_row(*_board_row(card))
            self._row_lanes.append((card.get("seat") or {}).get("lane_id"))
        self.query_one("#left-rail-text", Static).update(_left_rail_text(self._snapshot))
        self.query_one("#right-rail-text", Static).update(_right_rail_text(self._snapshot))
        self.query_one("#meters", Static).update(_meter_strip_text(self._snapshot))
        self._bind_detail(self._row_lanes[0] if self._row_lanes else None)

    def _bind_detail(self, lane_id: str | None) -> None:
        """Bind the seat-detail tabs to ONE seat's L2-folded detail structures."""
        detail = (self._snapshot.get("seat_detail") or {}).get(str(lane_id)) or {}
        self.query_one("#detail-stream", Static).update(_stream_text(detail))
        self.query_one("#detail-diffs", Static).update(_diffs_text(detail))
        self.query_one("#detail-evidence", Static).update(_evidence_text(detail))
        self.query_one("#detail-waterfall", Static).update(_waterfall_text(detail))
        self.query_one("#detail-outcome", Static).update(_outcome_text(detail))

    def on_data_table_row_highlighted(self, event: DataTable.RowHighlighted) -> None:
        index = event.cursor_row
        if 0 <= index < len(self._row_lanes):
            self._bind_detail(self._row_lanes[index])

    # -- refresh / filters / live tail ----------------------------------------
    def action_refresh_snapshot(self) -> None:
        if self._reload is not None:
            self._snapshot = self._reload()
            self._bind_snapshot()

    def action_filter(self, name: str) -> None:
        if name in _FILTER_KEYS:
            self._active_filter = name
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
