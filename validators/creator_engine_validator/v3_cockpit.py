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

v3.5-B.6 adds two ADDITIVE surfaces:

* **Control-Room Violet** — the live site tokens VERBATIM (read from the
  design; the site files are never edited here): refusals render gate-red,
  verified chains spark-lime, pending/ESTIMATED amber, brand/authority
  violet. The semantic NAMES travel as L2 snapshot styling hints; this view
  only maps name → hex.
* **``--serve``** — the SAME app opened in a browser on demand (no daemon)
  via ``textual-serve`` (the mechanism is NOT in Textual core; ``textual-web``
  is explicitly rejected). Loopback-only bind, token gate (the Jupyter
  token-then-cookie model), and Host-header validation (anti-DNS-rebinding)
  are enforced by ONE aiohttp middleware over a PURE, testable config; the
  serve deps are lazy-imported ONLY on the serve path.

Read-only: observation + request + visible authority — never a new authority.
"""

from __future__ import annotations

import asyncio
import hmac
import secrets
from dataclasses import dataclass
from typing import Any, Callable, Sequence

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.widgets import DataTable, Footer, Header, Static, TabPane, TabbedContent

APP_TITLE = "◆ CE Cockpit"

# ---------------------------------------------------------------------------
# v3.5-B.6 — Control-Room Violet (the live site tokens, VERBATIM)
# ---------------------------------------------------------------------------
#: docs/index.html:35-41, hex-for-hex. READ from the design — the site lane is
#: separate and its files never appear in this gate's diff.
THEME = {
    "ink-900": "#08090F",
    "ink-850": "#0B0D15",
    "ink-800": "#0F1220",
    "fg": "#E9EAF5",
    "violet": "#A06BFF",
    "spark": "#9BE34F",
    "gate": "#FF4D6D",
    "amber": "#F4B740",
}

#: The semantic mapping over the L2 styling HINTS (palette names carried in
#: the snapshot): refused/blocked/hard-breach → gate · verified/allowed/go →
#: spark · pending/soft-breach/ESTIMATED → amber · governance/authority/brand
#: → violet. The view maps name → hex; it never re-derives semantics.
SEMANTIC_HEX = {
    "gate": THEME["gate"],
    "spark": THEME["spark"],
    "amber": THEME["amber"],
    "violet": THEME["violet"],
}

#: Honesty-tier badges (B.4) → hex: MEASURED is solid/go, ESTIMATED is the
#: labelled amber placeholder, UNAVAILABLE stays foreground (never a guess).
BADGE_HEX = {
    "MEASURED": THEME["spark"],
    "ESTIMATED": THEME["amber"],
    "UNAVAILABLE": THEME["fg"],
}

#: ``verify_chain`` badges (B.2) → hex: a verified chain is spark-lime, a
#: tampered chain is gate-red, an absent chain is amber (declared, not faked).
EVIDENCE_BADGE_HEX = {
    "clean": THEME["spark"],
    "findings": THEME["gate"],
    "no-chain": THEME["amber"],
}

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


def _dispatch_line(entry: dict[str, Any]) -> str:
    """Format ONE dispatch-feed entry (pure presentation)."""
    spend = entry.get("spend_envelope") or {}
    cap = spend.get("cap")
    unit = spend.get("unit") or ""
    window = spend.get("window") or "—"
    cap_text = f"{unit}{cap} {window}" if cap is not None else "—"
    return (
        f"{entry.get('run_id', '—')} · {entry.get('state', '—')} · "
        f"{entry.get('mutation_class', '—')} · cap {cap_text}"
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
    dispatches = snapshot.get("dispatches", {})
    dispatch_availability = availability.get("dispatches", "—")
    if dispatch_availability == "unavailable":
        lines += ["", "Dispatches (unavailable):", "—"]
    else:
        entries = dispatches.get("entries", [])
        lines += ["", f"Dispatches ({dispatches.get('count', len(entries))}):"]
        lines += [_dispatch_line(entry) for entry in entries] or ["—"]
    return "\n".join(lines)


def _refusal_lines(entry: dict[str, Any]) -> list[str]:
    """Format ONE refusal-feed entry (pure presentation; refusals = gate-red)."""
    gate = SEMANTIC_HEX["gate"]
    if entry.get("source") == "refusal-chain":
        clause = entry.get("deciding_clause") or "not covered by any envelope"
        return [
            f"[{gate}]⛔ {entry.get('recorded_at', '—')} · {entry.get('run_id', '—')}[/]",
            f"[{gate}]   {entry.get('tool', '—')} → {entry.get('target', '—')}[/]",
            f"[{gate}]   {entry.get('deny_kind', '—')} deny · {clause}[/]",
        ]
    return [
        f"·  {entry.get('recorded_at', '—')} · legacy {entry.get('event', '—')} (advisory)"
    ]


def _escalation_lines(entry: dict[str, Any]) -> list[str]:
    """Format ONE AWAITING-OPERATOR entry (pure presentation)."""
    gate = SEMANTIC_HEX["gate"]
    return [
        f"[{gate}]⚠ {entry.get('title', '—')}[/]",
        f"[{gate}]   decide: {entry.get('decision_needed', '—')}[/]",
        f"[{gate}]   recommend: {entry.get('recommendation', '—')}[/]",
        f"[{gate}]   source: {entry.get('source_ref') or '—'}[/]",
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
            hex_color = SEMANTIC_HEX.get(str(group.get("color")), THEME["fg"])
            lines.append(
                f"[{hex_color}]{group.get('first_at', '—')} "
                f"{group.get('tool', '—')} → {group.get('target', '—')} · "
                f"{group.get('classification', '—')}{retry}[/]"
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
    badge = str(evidence.get("badge", "—"))
    hex_color = EVIDENCE_BADGE_HEX.get(badge)
    badge_text = f"[{hex_color}]{badge}[/]" if hex_color else badge
    return (
        f"chain: {evidence.get('record_count', 0)} record(s) · "
        f"verify_chain: {badge_text}"
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

    def _badge(tile: dict[str, Any]) -> str:
        badge = str(tile.get("badge", "—"))
        hex_color = BADGE_HEX.get(badge)
        return f"[{hex_color}]{badge}[/]" if hex_color else badge

    segments = [
        f"spend {spend_text} {_badge(spend)}",
        f"rate {rate_text} {_badge(token)}",
        f"ctx {ctx_text} {_badge(context)}",
        f"headroom {headroom.get('placeholder', '—')} {_badge(headroom)}",
    ]
    lines = ["  │  ".join(segments)]
    banner_hex = {"soft": SEMANTIC_HEX["amber"], "hard": SEMANTIC_HEX["gate"]}
    for banner in meters.get("banners", []):
        tier = str(banner.get("tier", "—"))
        lines.append(
            f"[{banner_hex.get(tier, THEME['fg'])}]"
            f"⛔ {tier.upper()} BREACH · {banner.get('run_id', '—')} · "
            f"{banner.get('unit', '')}{banner.get('observed', '—')}/"
            f"{banner.get('unit', '')}{banner.get('limit', '—')} · "
            f"{banner.get('signal', '—')} → {banner.get('action', '—')}[/]"
        )
    return "\n".join(lines)


def _right_rail_text(snapshot: dict[str, Any]) -> str:
    """The Governance/Authority panel — binds the four L2 sections (B.3)."""
    governance = snapshot.get("governance", {})
    refusals = snapshot.get("refusals", {})
    escalations = snapshot.get("escalations", {})
    availability = snapshot.get("availability", {})
    lines = ["Governance / Authority", ""]

    escalation_status = availability.get("escalations", "—")
    open_count = escalations.get("open_count", 0)
    heading_hex = SEMANTIC_HEX["gate"] if open_count else SEMANTIC_HEX["amber"]
    lines.append(f"[{heading_hex}]⚠ AWAITING OPERATOR ({open_count})[/]")
    if escalation_status == "unavailable":
        lines.append(f"[{SEMANTIC_HEX['amber']}]  escalation source unavailable[/]")
    else:
        for entry in escalations.get("open", []):
            lines += _escalation_lines(entry)
        if not escalations.get("open"):
            lines.append("  —")
    lines.append("")

    lines.append(
        f"[{SEMANTIC_HEX['violet']}]★ REFUSED[/] · {refusals.get('source_label', '—')}"
    )
    chain_verified = refusals.get("chain_verified")
    if chain_verified is not None:
        verdict = (
            f"[{SEMANTIC_HEX['spark']}]clean[/]"
            if chain_verified
            else f"[{SEMANTIC_HEX['gate']}]FINDINGS[/]"
        )
        lines.append(f"  chain verifies: {verdict}")
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
    # Control-Room Violet (B.6): surfaces ink-900/850/800 · text fg · violet =
    # governance/authority/brand chrome · amber = the DEMO watermark. The
    # refusal/verified/pending colors ride the text markup (SEMANTIC_HEX).
    CSS = f"""
    Screen {{
        background: {THEME["ink-900"]};
        color: {THEME["fg"]};
    }}
    Header {{
        background: {THEME["ink-800"]};
        color: {THEME["violet"]};
    }}
    Footer {{
        background: {THEME["ink-800"]};
    }}
    #watermark {{
        dock: top;
        height: 1;
        text-align: center;
        text-style: bold;
        background: {THEME["amber"]};
        color: {THEME["ink-900"]};
    }}
    #left-rail {{
        width: 32;
        background: {THEME["ink-850"]};
        border-right: solid {THEME["violet"]};
        padding: 0 1;
    }}
    #center {{
        width: 1fr;
    }}
    #board {{
        height: 1fr;
        background: {THEME["ink-900"]};
    }}
    #detail {{
        height: 14;
        border-top: solid {THEME["violet"]};
    }}
    #right-rail {{
        width: 40;
        background: {THEME["ink-850"]};
        border-left: solid {THEME["violet"]};
        padding: 0 1;
    }}
    #meters {{
        dock: bottom;
        height: auto;
        max-height: 4;
        background: {THEME["ink-800"]};
        border-top: solid {THEME["violet"]};
        padding: 0 1;
    }}
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


# ---------------------------------------------------------------------------
# v3.5-B.6 — `ce cockpit --serve`: the SAME app, in a browser, on demand
# ---------------------------------------------------------------------------
#: Binds the wrapper accepts — loopback ONLY; anything else is refused loudly
#: at config-build time, before any socket exists.
_LOOPBACK_BINDS = frozenset({"127.0.0.1", "localhost", "::1"})

#: Host-header spellings a loopback browser legitimately sends.
_LOOPBACK_HOST_NAMES = ("127.0.0.1", "localhost", "[::1]")

#: ``secrets.token_urlsafe(32)`` emits 43 chars; the floor rejects anything a
#: caller could plausibly hand-shorten into a guessable gate.
_MIN_TOKEN_LENGTH = 32

#: The session cookie the token gate mints (the Jupyter token-then-cookie model).
TOKEN_COOKIE = "ce_cockpit_token"


def generate_token() -> str:
    """Mint an unguessable URL-safe session token (printed once at launch)."""
    return secrets.token_urlsafe(32)


@dataclass(frozen=True)
class ServeConfig:
    """The PURE serve configuration — every security decision derives from it."""

    command: str
    host: str
    port: int
    token: str
    allowed_hosts: tuple[str, ...]


@dataclass(frozen=True)
class ServeDecision:
    """One request's PURE allow/deny decision (the testable security core)."""

    allowed: bool
    reason: str
    set_cookie: bool = False


def build_serve_config(
    *,
    command: str,
    token: str,
    host: str = "127.0.0.1",
    port: int = 8000,
) -> ServeConfig:
    """Build + validate the serve config (PURE; raises ``ValueError`` loudly).

    The three B.6 security requirements are enforced here, not in the web
    layer: loopback-only bind (``0.0.0.0`` and any non-loopback host are
    refused), a required unguessable token, and the allowed Host-header set
    the middleware validates against (anti-DNS-rebinding).
    """
    if host not in _LOOPBACK_BINDS:
        raise ValueError(
            f"refusing to bind {host!r}: `ce cockpit --serve` is loopback-ONLY "
            f"(allowed binds: {', '.join(sorted(_LOOPBACK_BINDS))}). The Cockpit "
            "is a local Operator surface, never a network service — exposing it "
            "would hand the board to the network, and that line never moves."
        )
    if len(token) < _MIN_TOKEN_LENGTH:
        raise ValueError(
            f"serve token too short ({len(token)} < {_MIN_TOKEN_LENGTH} chars): "
            "the token gate is mandatory and must be unguessable "
            "(use generate_token())."
        )
    allowed_hosts = _LOOPBACK_HOST_NAMES + tuple(
        f"{name}:{port}" for name in _LOOPBACK_HOST_NAMES
    )
    return ServeConfig(
        command=command, host=host, port=port, token=token, allowed_hosts=allowed_hosts
    )


def evaluate_request(
    config: ServeConfig,
    *,
    host_header: str | None,
    query_token: str | None,
    cookie_token: str | None,
) -> ServeDecision:
    """Decide ONE request (PURE): Host validation first, then token-then-cookie.

    A forged or absent ``Host`` header is rejected even when the token is
    valid (anti-DNS-rebinding). A valid ``?token=`` mints the session cookie;
    a valid cookie carries every subsequent request (websocket included —
    same-origin browsers send it on the WS upgrade).
    """
    host = (host_header or "").strip().lower()
    if host not in config.allowed_hosts:
        return ServeDecision(
            False, "Host header rejected (anti-DNS-rebinding): not a loopback origin"
        )
    if query_token is not None and hmac.compare_digest(query_token, config.token):
        return ServeDecision(True, "token accepted", set_cookie=True)
    if cookie_token is not None and hmac.compare_digest(cookie_token, config.token):
        return ServeDecision(True, "cookie session accepted")
    return ServeDecision(
        False, "token required (use the tokened URL printed at launch)"
    )


def tokened_url(config: ServeConfig) -> str:
    """The one-line launch URL carrying the session token (PURE)."""
    return f"http://{config.host}:{config.port}/?token={config.token}"


def _build_server(config: ServeConfig):
    """Build the governed ``textual-serve`` server (the serve-extra I/O edge).

    The serve mechanism ships in ``textual-serve`` — NOT Textual core — so its
    deps are lazy-imported HERE only; ``textual-web`` (public tunnel) is
    explicitly rejected by the ratified design and never used. The governed
    wrapper subclasses the library's public ``Server`` and appends ONE aiohttp
    middleware that runs ``evaluate_request`` over EVERY route (index,
    websocket, static, download); the library source is never patched.
    """
    from aiohttp import web
    from textual_serve.server import Server

    @web.middleware
    async def _governed_gate(request, handler):
        decision = evaluate_request(
            config,
            host_header=request.headers.get("Host"),
            query_token=request.query.get("token"),
            cookie_token=request.cookies.get(TOKEN_COOKIE),
        )
        if not decision.allowed:
            raise web.HTTPForbidden(text=f"CE Cockpit: {decision.reason}")
        response = await handler(request)
        if decision.set_cookie and not response.prepared:
            response.set_cookie(
                TOKEN_COOKIE, config.token, httponly=True, samesite="Strict"
            )
        return response

    class _GovernedCockpitServer(Server):
        async def _make_app(self) -> web.Application:
            app = await super()._make_app()
            app.middlewares.append(_governed_gate)
            return app

    return _GovernedCockpitServer(
        config.command, host=config.host, port=config.port, title=APP_TITLE
    )


def run_serve(config: ServeConfig) -> int:
    """Serve the SAME Cockpit app in a browser, on demand (no daemon).

    Foreground lifecycle: the web process exits with the command (Ctrl+C);
    each browser session spawns the app subprocess on demand and reaps it
    when the session closes.
    """
    server = _build_server(config)
    print(
        f"CE Cockpit --serve: {tokened_url(config)}\n"
        f"  bind {config.host}:{config.port} (loopback-only) · token-gated · "
        "Host-validated · Ctrl+C to quit",
        flush=True,
    )
    server.serve()
    return 0
