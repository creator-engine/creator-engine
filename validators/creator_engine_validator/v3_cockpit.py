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
from textual.screen import ModalScreen, Screen
from textual.widgets import DataTable, Footer, Header, Static, TabPane, TabbedContent

APP_TITLE = "◆ CE Cockpit"

# ---------------------------------------------------------------------------
# v8 "The Factory Floor" — the live site tokens, VERBATIM
# ---------------------------------------------------------------------------
#: docs/index.html :root, hex-for-hex. READ from the design — the site lane is
#: separate and its files never appear in this gate's diff. Re-pinned from
#: Control-Room Violet to the v8 warm-factory palette when the site shipped v8.
THEME = {
    "ink-900": "#0C0B0A",
    "ink-850": "#16140F",
    "ink-800": "#191712",
    "fg": "#FAF8F1",
    "violet": "#A06BFF",
    "spark": "#7FB069",
    "gate": "#E0605C",
    "amber": "#E08B4C",
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

#: v3.1-B.7 — the cost rail shows the top-N per-scope rows by measured $; the
#: remainder is SUMMARIZED on a declared truncation line (never a silent cap).
_COST_TOP_N = 6

SnapshotLoader = Callable[[], dict[str, Any]]

#: The two cockpit faces (ce-ops#45): ``ceo`` is the solo-founder journey (the
#: DEFAULT face), ``dev`` is the expert ops board. Mirrored here as plain literals
#: so the view imports no loader — the canonical definitions, normalization, and
#: persistence live in ``runner.cockpit_prefs``; the composition root resolves the
#: persona and injects it (plus an ``on_persona_change`` callback) into the App.
_PERSONA_CEO = "ceo"
_PERSONA_DEV = "dev"
_PERSONAS = (_PERSONA_CEO, _PERSONA_DEV)
_DEFAULT_PERSONA = _PERSONA_CEO


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


def _cost_scope_line(row: dict[str, Any]) -> str:
    """Format ONE per-scope cost row — render-only, NEVER a $0 for an unpriced run."""
    scope_id = str(row.get("scope_id", "—"))
    tier = str(row.get("tier", "—"))
    if tier == "MEASURED":
        spend = row.get("spend")
        spend_text = f"${spend:.2f}" if spend is not None else "—"
        models = row.get("models") or []
        model_text = f" [{', '.join(models)}]" if models else ""
        badge = f"[{BADGE_HEX['MEASURED']}]MEASURED[/]"
        return f"  {scope_id} {spend_text} {badge}{model_text}"
    if tier == "UNPRICED":
        turns = row.get("unpriced_turns")
        turn_text = f" · {turns} turns" if turns is not None else ""
        badge = f"[{SEMANTIC_HEX['amber']}]UNPRICED[/]"
        # The honesty heart: an unpriced (subscription) run is NEVER shown as $0.
        return f"  {scope_id} unpriced (subscription){turn_text} {badge}"
    badge = f"[{BADGE_HEX['UNAVAILABLE']}]UNAVAILABLE[/]"
    return f"  {scope_id} — (no chain) {badge}"


def _cost_rail_lines(cost: dict[str, Any]) -> list[str]:
    """Format the B.7 cost rail: the fleet line + a top-N per-scope list (render-only)."""
    fleet = cost.get("fleet") or {}
    badge_name = str(cost.get("badge", "—"))
    badge_hex = BADGE_HEX.get(badge_name)
    badge = f"[{badge_hex}]{badge_name}[/]" if badge_hex else badge_name
    measured = fleet.get("measured_spend")
    measured_text = f"${measured:.2f}" if measured is not None else "—"
    unpriced_n = fleet.get("unpriced_run_count") or 0
    lines = [
        f"cost {measured_text} MEASURED · {unpriced_n} unpriced (subscription)  {badge}"
    ]
    note = cost.get("headroom_note")
    if note:
        lines.append(f"  [{SEMANTIC_HEX['amber']}]{note}[/]")

    rows = list(cost.get("scopes") or [])
    # Rank: highest measured $ first, then unpriced, then unavailable — so the
    # most expensive scopes are never the ones dropped by the top-N truncation.
    _tier_rank = {"MEASURED": 0, "UNPRICED": 1, "UNAVAILABLE": 2}
    rows.sort(
        key=lambda r: (
            _tier_rank.get(str(r.get("tier")), 9),
            -(r.get("spend") or 0.0),
            str(r.get("scope_id")),
        )
    )
    for row in rows[:_COST_TOP_N]:
        lines.append(_cost_scope_line(row))
    if len(rows) > _COST_TOP_N:
        dropped = rows[_COST_TOP_N:]
        dropped_measured = sum(r.get("spend") or 0.0 for r in dropped if r.get("tier") == "MEASURED")
        dropped_unpriced = len([r for r in dropped if r.get("tier") == "UNPRICED"])
        # Declare the truncation — never a silent cap (B.7 §A.3).
        lines.append(
            f"  … +{len(dropped)} more scopes truncated (top {_COST_TOP_N} by $ shown; "
            f"${dropped_measured:.2f} measured + {dropped_unpriced} unpriced hidden)"
        )
    return lines


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
    # v3.1-B.7 — the per-scope fleet cost rail under the strip (render-only).
    cost = meters.get("cost")
    if cost:
        lines.extend(_cost_rail_lines(cost))
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
    lines.append("")

    # ce-ops#38 work-claim locks — the ops-board "locks" band (render-only; binds
    # the precomputed L2 ``snapshot["claims"]`` — no governance computation here).
    lines += _claims_band_lines(snapshot)
    return "\n".join(lines)


def _claims_band_lines(snapshot: dict[str, Any]) -> list[str]:
    """The work-claim locks band — bound from the precomputed ``snapshot["claims"]``."""
    claims = snapshot.get("claims", {})
    availability = (snapshot.get("availability", {}) or {}).get("claims", "—")
    active = claims.get("active_count", 0)
    heading_hex = SEMANTIC_HEX["gate"] if claims.get("foreign_count") else SEMANTIC_HEX["violet"]
    lines = [f"[{heading_hex}]🔒 WORK CLAIMS ({active} active)[/]"]
    if availability == "unavailable":
        lines.append(f"[{SEMANTIC_HEX['amber']}]  claim cache unavailable[/]")
        return lines
    stale = claims.get("stale_count", 0)
    invalid = claims.get("invalid_count", 0)
    fetched = claims.get("cache_fetched_at") or "—"
    lines.append(f"  fetched {fetched} · stale {stale} · invalid {invalid}")
    for entry in claims.get("entries", []):
        if entry.get("status") not in ("active", "conflict"):
            continue
        flag = ""
        if entry.get("stale"):
            flag += f" [{SEMANTIC_HEX['amber']}]STALE[/]"
        if entry.get("status") == "conflict":
            flag += f" [{SEMANTIC_HEX['gate']}]CONFLICT[/]"
        lines.append(
            f"  • {entry.get('holder', '—')}@{entry.get('host', '—')} "
            f"({entry.get('claim_id', '—')}){flag}"
        )
    if not any(e.get("status") in ("active", "conflict") for e in claims.get("entries", [])):
        lines.append("  —")
    return lines


# ---------------------------------------------------------------------------
# ce-ops#45 — the CEO-mode JOURNEY view (L3, render-only). THE DEFAULT FACE.
#
# The journey is the solo-founder's DEFAULT cockpit face; the expert ops board is
# demoted to the Dev face you switch to (``CockpitApp`` installs the persona's
# screen, persisting the choice through an injected callback — the view performs
# no I/O). This face shows the FULL visual development-arc / roadmap (a one-screen
# picture of the CE process, a visual "where you are", and the project's work
# flowing through the five stages) plus the first-class decision-inbox ("what
# needs you"). Every string is read straight from ``snapshot["journey"]``; this
# view parses nothing, derives nothing, classifies nothing, and calls no loader.
# The detail comes only from the precomputed
# ``snapshot["journey"]["need_details"][detail_ref]``.
# ---------------------------------------------------------------------------

#: The journey needs-attention table columns (presentation labels over the
#: precomputed L2 item fields).
_JOURNEY_NEEDS_COLUMNS = ("#", "What needs you", "Your decision", "Suggested next step")


def _journey_arc_text(journey: dict[str, Any]) -> str:
    """Render the compact five-stage progress strip with the 'you are here' marker.

    Render-only: the stages, counts, current marker, and step position are all
    precomputed in ``snapshot["journey"]["arc"]``.
    """
    arc = journey.get("arc") or {}
    now = journey.get("now") or {}
    stages = list(arc.get("stages") or [])
    counts = arc.get("stage_counts") or {}
    here = now.get("stage")
    if (arc.get("availability") or "ok") == "unavailable":
        return "I cannot show the work stages right now."
    cells = []
    for stage in stages:
        marker = "▶ " if stage == here else "  "
        count = counts.get(stage, 0)
        hex_color = SEMANTIC_HEX["violet"] if stage == here else THEME["fg"]
        cells.append(f"[{hex_color}]{marker}{stage} ({count})[/]")
    strip = "   ".join(cells)
    position = arc.get("position") or {}
    index = position.get("index")
    total = position.get("total")
    if index is not None and total:
        # A plain "Step 3 of 5" so a non-engineer reads the progress at a glance.
        strip += f"      [{SEMANTIC_HEX['violet']}]Step {index + 1} of {total}[/]"
    return strip


def _journey_lane_scope_line(scope: dict[str, Any]) -> str:
    """Render ONE scope inside a roadmap lane (plain Goal · Ready, render-only)."""
    ready = "ready" if scope.get("ready") else "in progress"
    attention = ""
    if scope.get("needs_attention"):
        attention = f" [{SEMANTIC_HEX['gate']}]· needs you[/]"
    return f"  • {scope.get('goal', '—')} [{THEME['fg']}]· {ready}[/]{attention}"


def _journey_roadmap_text(journey: dict[str, Any]) -> str:
    """Render the FULL visual development-arc — one lane per canon stage (render-only).

    The one-screen picture of the CE process: each of the five stages is a lane
    carrying its plain description and the project's work currently sitting in it
    (the "project arc"); the current stage is marked. Binds ``arc["lanes"]`` only
    — it derives no stage and classifies no scope.
    """
    arc = journey.get("arc") or {}
    if (arc.get("availability") or "ok") == "unavailable":
        return "I cannot show where the work stands right now."
    blocks: list[str] = []
    for lane in arc.get("lanes") or []:
        current = lane.get("is_current")
        marker = "▶ " if current else "  "
        head_hex = SEMANTIC_HEX["violet"] if current else THEME["fg"]
        heading = (
            f"[{head_hex}]{marker}{lane.get('stage', '—')} "
            f"— {lane.get('label', '—')} ({lane.get('count', 0)})[/]"
        )
        lines = [heading, f"    [{THEME['fg']}]{lane.get('description', '')}[/]"]
        lane_scopes = lane.get("scopes") or []
        if lane_scopes:
            lines += [_journey_lane_scope_line(scope) for scope in lane_scopes]
        else:
            lines.append(f"  [{THEME['fg']}]—[/]")
        blocks.append("\n".join(lines))
    return "\n\n".join(blocks)


def _journey_now_text(journey: dict[str, Any]) -> str:
    """Render the plain 'where am I now' line (render-only — label is precomputed)."""
    now = journey.get("now") or {}
    lines = [f"[{SEMANTIC_HEX['violet']}]You are here:[/] {now.get('label', '—')}"]
    stage = now.get("stage")
    if stage:
        lines.append(f"  stage: {stage}")
    note = now.get("active_note")
    if note:
        lines.append(f"  [{SEMANTIC_HEX['amber']}]{note}[/]")
    return "\n".join(lines)


def _journey_needs_header_text(journey: dict[str, Any]) -> str:
    """Render the needs-attention header — honest empty vs unavailable (render-only)."""
    needs = journey.get("needs_attention") or {}
    open_count = needs.get("open_count", 0)
    heading_hex = SEMANTIC_HEX["gate"] if open_count else SEMANTIC_HEX["spark"]
    lines = [f"[{heading_hex}]What needs you ({open_count})[/]"]
    message = needs.get("message")
    if message:
        lines.append(f"  {message}")
    return "\n".join(lines)


def _journey_need_row(item: dict[str, Any]) -> tuple[str, ...]:
    """Format ONE needs-attention item into a display row (render-only)."""
    return (
        str(item.get("age_rank", "—")),
        str(item.get("headline", "—")),
        str(item.get("plain_ask", "—")),
        str(item.get("recommended_next_step", "—")),
    )


def _journey_detail_text(detail: dict[str, Any]) -> str:
    """Render ONE precomputed plain detail record (render-only — no derivation).

    Reads ONLY the precomputed ``need_details[detail_ref]`` fields; it parses no
    source ref, classifies nothing, and calls no loader.
    """
    if not detail:
        return "No detail available for this item."
    violet = SEMANTIC_HEX["violet"]
    lines = [
        f"[{violet}]{detail.get('title', '—')}[/]",
        "",
        f"[{violet}]What this means[/]",
        f"  {detail.get('what_this_means', '—')}",
        "",
        f"[{violet}]Why CE paused[/]",
        f"  {detail.get('why_ce_paused', '—')}",
        "",
        f"[{violet}]If you continue[/]",
        f"  {detail.get('if_you_continue', '—')}",
        "",
        f"[{violet}]If you decline or change direction[/]",
        f"  {detail.get('if_you_decline', '—')}",
        "",
        f"[{violet}]What CE will not do by itself[/]",
        f"  {detail.get('ce_will_not', '—')}",
        "",
        f"[{SEMANTIC_HEX['spark']}]Suggested next step[/]",
        f"  {detail.get('recommendation', '—')}",
    ]
    technical = detail.get("technical_source")
    if technical:
        # The OPTIONAL technical-source footer — never the explanation.
        lines += ["", f"[{THEME['fg']}]technical source: {technical}[/]"]
    return "\n".join(lines)


def _journey_resolve_form_text(detail: dict[str, Any]) -> str:
    """Render the FORM-ECHO shown before the binding act (ce-ops#45 Slice 2).

    The form-echo is a *fidelity affordance*, not the authority gate
    ([[ce-authority-attaches-to-form]]): it echoes, in plain language, the
    decision being recorded so the founder confirms the canonical FORM — the
    binding act then actuates the canonical resolve gate (which schema-validates
    the form). Render-only: reads the precomputed detail fields; writes nothing.
    """
    violet = SEMANTIC_HEX["violet"]
    spark = SEMANTIC_HEX["spark"]
    gate = SEMANTIC_HEX["gate"]
    return "\n".join(
        [
            f"[{violet}]Record your decision[/]",
            "",
            f"[{violet}]What you are deciding[/]",
            f"  {detail.get('title', '—')}",
            "",
            f"[{spark}]Recommended next step[/]",
            f"  {detail.get('recommendation', '—')}",
            "",
            f"[{gate}]If you confirm[/], this is marked decided and clears from your inbox.",
            "  CE records only that you made this call — it changes nothing else by itself.",
            "",
            f"[{violet}]Confirm (y)[/]    ·    Cancel (esc)",
        ]
    )


class JourneyDetailScreen(ModalScreen[None]):
    """A modal that shows ONE precomputed plain detail record (render-only).

    ce-ops#45 Slice 2: when a resolve seam is wired (live mode), pressing ``r``
    opens the form-echo confirmation and — only on confirm — actuates the
    canonical escalation-resolve gate through the App's injected callback. This
    view still writes nothing itself.
    """

    BINDINGS = [
        Binding("r", "record_decision", "Record my decision"),
        Binding("escape", "dismiss", "Close"),
        Binding("q", "dismiss", "Close"),
    ]
    CSS = f"""
    JourneyDetailScreen {{
        align: center middle;
    }}
    #journey-detail-box {{
        width: 80%;
        max-width: 100;
        height: auto;
        max-height: 80%;
        background: {THEME["ink-850"]};
        border: solid {THEME["violet"]};
        padding: 1 2;
    }}
    #journey-detail-hint {{
        height: auto;
        color: {THEME["fg"]};
        margin-top: 1;
    }}
    """

    def __init__(self, detail: dict[str, Any]) -> None:
        super().__init__()
        self._detail = detail or {}

    def compose(self) -> ComposeResult:
        with VerticalScroll(id="journey-detail-box"):
            yield Static(_journey_detail_text(self._detail), id="journey-detail-text")
            yield Static("", id="journey-detail-hint")

    def on_mount(self) -> None:
        can_resolve = bool(getattr(self.app, "resolve_enabled", False)) and bool(
            self._detail.get("need_id")
        )
        hint = (
            "Press r to record your decision    ·    esc to close"
            if can_resolve
            else "Press esc to close"
        )
        self.query_one("#journey-detail-hint", Static).update(hint)

    def check_action(self, action: str, parameters: tuple[object, ...]) -> bool | None:
        if action == "record_decision":
            # Only offer the binding act when a resolve seam is wired AND this
            # item carries the machine id the canonical gate needs.
            return bool(getattr(self.app, "resolve_enabled", False)) and bool(
                self._detail.get("need_id")
            )
        return True

    def action_record_decision(self) -> None:
        if not getattr(self.app, "resolve_enabled", False):
            return
        need_id = self._detail.get("need_id")
        if not need_id:
            return

        def _after_confirm(confirmed: bool | None) -> None:
            if confirmed:
                # The binding act: actuate the canonical gate via the injected
                # callback, then close this detail so the founder lands back on
                # the (now-updated) inbox.
                self.app.action_resolve_need(str(need_id))
                self.dismiss(None)

        self.app.push_screen(ResolveConfirmScreen(self._detail), _after_confirm)

    def action_dismiss(self, result: None = None) -> None:
        self.dismiss(None)


class ResolveConfirmScreen(ModalScreen[bool]):
    """The FORM-ECHO confirmation before the binding act (ce-ops#45 Slice 2).

    A fidelity affordance, NOT the authority gate ([[ce-authority-attaches-to-form]]):
    it echoes the plain form of the decision being recorded and requires a
    deliberate ``y`` confirm. The binding act itself actuates the canonical
    escalation-resolve gate (which schema-validates the form) via the App's
    injected callback — this view writes nothing. Returns ``True`` on confirm,
    ``False`` on cancel.
    """

    BINDINGS = [
        Binding("y", "confirm", "Confirm"),
        Binding("n", "cancel", "Cancel"),
        Binding("escape", "cancel", "Cancel"),
    ]
    CSS = f"""
    ResolveConfirmScreen {{
        align: center middle;
    }}
    #journey-resolve-box {{
        width: 70%;
        max-width: 90;
        height: auto;
        max-height: 70%;
        background: {THEME["ink-850"]};
        border: round {THEME["gate"]};
        padding: 1 2;
    }}
    """

    def __init__(self, detail: dict[str, Any]) -> None:
        super().__init__()
        self._detail = detail or {}

    def compose(self) -> ComposeResult:
        with VerticalScroll(id="journey-resolve-box"):
            yield Static(_journey_resolve_form_text(self._detail), id="journey-resolve-text")

    def action_confirm(self) -> None:
        self.dismiss(True)

    def action_cancel(self) -> None:
        self.dismiss(False)


class JourneyScreen(Screen[None]):
    """The CEO-mode journey — the DEFAULT cockpit face (render-only).

    The solo-founder's one-screen picture: a five-stage progress strip, the FULL
    visual development-arc / roadmap (a lane per stage with its plain description
    and the project's work flowing through it), an honest "you are here" line, and
    the first-class decision-inbox ("what needs you"). Binds the precomputed
    ``snapshot["journey"]`` structures only; selecting a needs-attention row opens
    the precomputed detail (``need_details[detail_ref]``) — no parsing, no
    classification, no loader. Press ``d`` to switch to the expert Dev board.
    """

    BINDINGS = [
        Binding("d", "switch_persona('dev')", "Developer view"),
    ]
    CSS = f"""
    JourneyScreen {{
        background: {THEME["ink-900"]};
        color: {THEME["fg"]};
    }}
    #journey-arc {{
        height: auto;
        background: {THEME["ink-800"]};
        border-bottom: solid {THEME["violet"]};
        padding: 1 1;
    }}
    #journey-now {{
        height: auto;
        padding: 1 1 0 1;
    }}
    #journey-roadmap {{
        height: 1fr;
        padding: 0 1;
        border-top: solid {THEME["violet"]};
    }}
    #journey-inbox {{
        dock: bottom;
        height: 14;
        margin: 0 1 0 1;
        border: round {THEME["violet"]};
        background: {THEME["ink-850"]};
        padding: 0 1;
    }}
    #journey-inbox-header {{
        height: auto;
    }}
    #journey-needs {{
        height: 1fr;
    }}
    """

    def __init__(self, snapshot: dict[str, Any]) -> None:
        super().__init__()
        self._snapshot = snapshot
        self._need_rows: list[str | None] = []

    def compose(self) -> ComposeResult:
        yield Header()
        watermark = (self._snapshot.get("source") or {}).get("watermark")
        if watermark:
            yield Static(str(watermark), id="watermark")
        yield Static("", id="journey-arc")
        yield Static("", id="journey-now")
        yield VerticalScroll(Static("", id="journey-roadmap-text"), id="journey-roadmap")
        with Vertical(id="journey-inbox"):
            yield Static("", id="journey-inbox-header")
            yield DataTable(id="journey-needs")
        yield Footer()

    def on_mount(self) -> None:
        inbox = self.query_one("#journey-inbox", Vertical)
        # The decision-inbox is a FIRST-CLASS, titled surface — not a sub-panel.
        inbox.border_title = "What needs you"
        table = self.query_one("#journey-needs", DataTable)
        table.add_columns(*_JOURNEY_NEEDS_COLUMNS)
        table.cursor_type = "row"
        self._bind_journey()
        # Draw the founder to the inbox when something actually needs them.
        if self._need_rows:
            table.focus()

    def rebind(self, snapshot: dict[str, Any]) -> None:
        """Re-bind to a freshly-folded snapshot (the live tail / refresh path)."""
        self._snapshot = snapshot
        self._bind_journey()

    def on_screen_resume(self) -> None:
        """Re-bind from the App's latest snapshot when a modal (detail/confirm) closes.

        After a decision is recorded, the App re-folds; resuming here drops the
        just-resolved item out of the inbox without any cross-modal rebind timing.
        """
        latest = getattr(self.app, "snapshot", None)
        if isinstance(latest, dict):
            self._snapshot = latest
        self._bind_journey()

    def _bind_journey(self) -> None:
        journey = self._snapshot.get("journey") or {}
        self.query_one("#journey-arc", Static).update(_journey_arc_text(journey))
        self.query_one("#journey-now", Static).update(_journey_now_text(journey))
        self.query_one("#journey-roadmap-text", Static).update(_journey_roadmap_text(journey))
        self.query_one("#journey-inbox-header", Static).update(
            _journey_needs_header_text(journey)
        )
        # The inbox border turns gate-red when work needs the founder, spark-green
        # when the queue is clear — the decision-inbox announces itself.
        needs = journey.get("needs_attention") or {}
        accent = SEMANTIC_HEX["gate"] if needs.get("open_count") else SEMANTIC_HEX["spark"]
        self.query_one("#journey-inbox", Vertical).styles.border = ("round", accent)
        table = self.query_one("#journey-needs", DataTable)
        table.clear()
        self._need_rows = []
        for item in needs.get("items", []):
            table.add_row(*_journey_need_row(item))
            # Carry ONLY the precomputed detail_ref — the L3 binds it, never
            # parses it (spec 3.7).
            self._need_rows.append(item.get("detail_ref"))

    def _open_detail(self, index: int) -> None:
        if not (0 <= index < len(self._need_rows)):
            return
        detail_ref = self._need_rows[index]
        journey = self._snapshot.get("journey") or {}
        # The ONLY lookup the L3 performs: the precomputed detail by its ref.
        detail = (journey.get("need_details") or {}).get(str(detail_ref)) or {}
        self.app.push_screen(JourneyDetailScreen(detail))

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        self._open_detail(event.cursor_row)

    def action_switch_persona(self, persona: str) -> None:
        # Delegate to the App, which owns the persona + persistence edge.
        self.app.action_switch_persona(persona)


class BoardScreen(Screen[None]):
    """The expert ops board — the Dev cockpit face (render-only).

    The full fleet board: left fleet-nav rail · the Scope board + seat-detail tabs
    · the governance/authority rail · the meter strip. Demoted from the default to
    a face you switch to with ``c`` (the founder journey is the default). Binds the
    precomputed snapshot only; all board/refusal/meter computation lives in L2.
    """

    BINDINGS = [
        Binding("c", "switch_persona('ceo')", "Founder view"),
        Binding("a", "filter('all')", "All"),
        Binding("m", "filter('mine')", "Mine"),
        Binding("l", "filter('live')", "Live"),
        # Back-compat alias: the old "journey" key now lands on the founder face.
        Binding("j", "switch_persona('ceo')", "Founder view", show=False),
    ]
    CSS = f"""
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

    def __init__(self, snapshot: dict[str, Any]) -> None:
        super().__init__()
        self._snapshot = snapshot
        self._active_filter = "all"
        self._row_lanes: list[str | None] = []

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

    def rebind(self, snapshot: dict[str, Any]) -> None:
        """Re-bind to a freshly-folded snapshot (the live tail / refresh path)."""
        self._snapshot = snapshot
        self._bind_snapshot()

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

    def action_filter(self, name: str) -> None:
        if name in _FILTER_KEYS:
            self._active_filter = name
            self._bind_snapshot()

    def action_switch_persona(self, persona: str) -> None:
        # Delegate to the App, which owns the persona + persistence edge.
        self.app.action_switch_persona(persona)


class CockpitApp(App[None]):
    """The read-only Cockpit TUI — two faces over ONE L2 snapshot.

    The solo-founder **journey** is the default face; the expert ops **board** is
    the Dev face you switch to. Which face you land on is a persisted preference,
    read by the composition root and injected here as ``persona`` plus an
    ``on_persona_change`` callback — the view performs NO file I/O of its own (the
    L3 source guard stays green). The snapshot fold + live tail stay on the App;
    the active screen re-binds in place.

    ce-ops#45 Slice 2: an optional ``on_resolve`` callback lets the decision-inbox
    actuate the canonical escalation-resolve gate (with a form-echo confirmation).
    The callback is wired by the composition root to ``v3_cli.resolve_escalation``;
    the cockpit NEVER writes governance state itself and never bypasses the gate.
    When ``on_resolve`` is absent (e.g. the seeded demo) the resolve affordance is
    hidden — the cockpit stays read-only.
    """

    TITLE = APP_TITLE
    BINDINGS = [
        Binding("q", "quit", "Quit"),
        Binding("r", "refresh_snapshot", "Refresh"),
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
    """

    def __init__(
        self,
        snapshot: dict[str, Any],
        *,
        reload: SnapshotLoader | None = None,
        watch_paths: Sequence[str] = (),
        persona: str = "ceo",
        on_persona_change: Callable[[str], None] | None = None,
        on_resolve: Callable[[str], dict[str, Any]] | None = None,
    ) -> None:
        super().__init__()
        # ce-ops#25: render the CE version token in the L3 header — title from
        # ``snapshot["source"]["ce_version"]`` with ``APP_TITLE`` as the
        # prefix/fallback (the token is data the L2 fold already carries).
        ce_ver = (snapshot.get("source") or {}).get("ce_version")
        if ce_ver:
            self.title = f"{APP_TITLE} · {ce_ver}"
        self._snapshot = snapshot
        self._reload = reload
        self._watch_paths = list(watch_paths)
        self._watch_task: asyncio.Task[None] | None = None
        # The two faces; ``ceo`` (the journey) is the default. An unknown injected
        # value falls back to the default face (the view never trusts junk).
        self._persona = persona if persona in _PERSONAS else _DEFAULT_PERSONA
        self._on_persona_change = on_persona_change
        # The canonical resolve gate, injected (Slice 2). Absent ⇒ read-only.
        self._on_resolve = on_resolve

    @property
    def persona(self) -> str:
        return self._persona

    @property
    def snapshot(self) -> dict[str, Any]:
        """The App's current (authoritative) L2 snapshot — screens re-bind from it."""
        return self._snapshot

    @property
    def resolve_enabled(self) -> bool:
        """True iff a canonical resolve seam is wired (live mode) — Slice 2."""
        return self._on_resolve is not None

    def _make_screen(self, persona: str) -> Screen[None]:
        if persona == _PERSONA_DEV:
            return BoardScreen(self._snapshot)
        return JourneyScreen(self._snapshot)

    async def on_mount(self) -> None:
        # Each face is a Textual MODE with its OWN screen stack, so switching is a
        # clean swap (never a base-screen pop). The factory closes over the App's
        # current snapshot; refreshes re-bind the active screen in place.
        self.add_mode(_PERSONA_CEO, lambda: self._make_screen(_PERSONA_CEO))
        self.add_mode(_PERSONA_DEV, lambda: self._make_screen(_PERSONA_DEV))
        await self.switch_mode(self._persona)
        if self._watch_paths and self._reload is not None:
            self._watch_task = asyncio.create_task(self._watch_loop())

    # -- persona / refresh / live tail ----------------------------------------
    def action_switch_persona(self, persona: str) -> None:
        """Switch the cockpit face and persist the choice (via the injected edge)."""
        target = persona if persona in _PERSONAS else self._persona
        if target == self._persona:
            return
        self._persona = target
        if self._on_persona_change is not None:
            # The ONLY persistence the cockpit does — and it happens in the
            # injected composition-root callback, never in this view module.
            self._on_persona_change(target)
        self.switch_mode(target)
        # Re-bind the (possibly previously-built) target face to the current
        # snapshot once it is the active screen.
        self.call_after_refresh(self._rebind_active)

    def _rebind_active(self) -> None:
        rebind = getattr(self.screen, "rebind", None)
        if callable(rebind):
            rebind(self._snapshot)

    def action_refresh_snapshot(self) -> None:
        if self._reload is not None:
            self._snapshot = self._reload()
            self._rebind_active()

    def action_resolve_need(self, need_id: str) -> None:
        """Actuate the canonical resolve gate for ONE decision, then re-fold (Slice 2).

        The cockpit writes NOTHING here: it calls the injected ``on_resolve``
        callback, which the composition root wires to the canonical
        ``v3_cli.resolve_escalation`` gate (schema-validated, fail-closed). After
        the gate runs, the snapshot is re-folded so the inbox reflects reality —
        the resolved item drops out of the open queue. Robust to a refusal: a
        plain message, never a crash.
        """
        if self._on_resolve is None or not need_id:
            return
        try:
            result = self._on_resolve(str(need_id))
        except Exception:  # never let a gate hiccup crash the read-only view
            result = {"ok": False}
        if isinstance(result, dict) and result.get("ok"):
            self.notify("Decision recorded — cleared from your inbox.")
        else:
            self.notify(
                "I could not record that — it may already be done.",
                severity="warning",
            )
        # Reflect reality either way (a re-fold re-reads the live records).
        if self._reload is not None:
            self._snapshot = self._reload()
            self._rebind_active()

    async def _watch_loop(self) -> None:
        """Tail the L1 roots and re-bind on change (the fold runs in L2 via reload)."""
        from watchfiles import awatch  # lazy: only the live-tail path needs it

        assert self._reload is not None
        async for _changes in awatch(*self._watch_paths):
            self._snapshot = self._reload()
            self._rebind_active()


def run_app(
    snapshot: dict[str, Any],
    *,
    reload: SnapshotLoader | None = None,
    watch_paths: Sequence[str] = (),
    persona: str = "ceo",
    on_persona_change: Callable[[str], None] | None = None,
    on_resolve: Callable[[str], dict[str, Any]] | None = None,
) -> int:
    """Run the Cockpit TUI over a prepared L2 snapshot; return a CLI exit code."""
    CockpitApp(
        snapshot,
        reload=reload,
        watch_paths=watch_paths,
        persona=persona,
        on_persona_change=on_persona_change,
        on_resolve=on_resolve,
    ).run()
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
