"""CE v3.5-B.1 — the Cockpit L2 read-model. THE harness-paper F1 surface.

This module IS the harness-paper **F1** ("read-only Deep-Telemetry projection"):
the ONE pure, JSON-serializable, view-agnostic projection/read-model the Cockpit
family folds L1 into. There is no separate ``harness_telemetry`` module — F1 is
``cockpit_readmodel`` (+ the ``cockpit_insights`` aggregate extension, a later
gate). Design-of-record: the v3.5-B Cockpit design (2026-06-09), §3.0 principle 6
([[ce-cockpit-frontend-agnostic-core]]).

The three-layer law (HARD constraint, testable):

* **L1 — source of truth** (read-only to the Cockpit): the hash-chained
  runtime-evidence chains persisted under the v3 local-state root
  (``<root>/<run_id>.runtime-evidence.yaml``, the ``evidence_sink`` layout), the
  Scope artifacts (``<root>/scopes/*.scope.yaml``), the v1 instance-local pane
  registry (``<ledger_root>/panes/**``) and the legacy advisory hook-observation
  log (``<observations_dir>/observations.ndjson``). The Cockpit writes NO
  governance state — it is observation + request + visible authority, never a
  new authority.
* **L2 — this module**: :func:`fold_snapshot` is a PURE fold (no disk,
  process-spawn, network, terminal, clock, rng) from L1-shaped values to ONE
  JSON-serializable snapshot dict. File-reads live ONLY in the narrow,
  injectable load seams (:func:`load_chains` / :func:`load_scopes` /
  :func:`load_panes` / :func:`load_observations`, composed by
  :func:`snapshot_from_roots`) — the ``usage_tap`` "pure core + 1 I/O edge"
  pattern. Importing this module imports neither ``textual`` nor ``watchfiles``.
* **L3 — ``v3_cockpit``**: binds to the snapshot and renders. ALL
  board/refusal/envelope/meter computation lives HERE, never in a Textual
  widget callback; a future GUI replaces L3 only, consuming this same snapshot
  (``ce cockpit --json`` makes that seam a first-class invocation).

v1-residue discipline (``v3_naming_hygiene``): this is a v3 module, so it never
embeds the v1 bootstrapping-harness state-root names. The v1 instance-local
roots are reached ONLY via explicit parameters or the launch-pinned environment
seams — :data:`LEDGER_ROOT_ENV` (``CE_LEDGER_ROOT``, the exact env var ``ce lane
launch`` already exports for the Ring-1 hook) and :data:`OBSERVATIONS_DIR_ENV`
(``CE_HOOK_OBSERVATIONS_DIR``). An unreachable source degrades HONESTLY to
``unavailable`` — never a fabricated entry (the honesty-tier discipline).

Stage vocabulary: the board column is the canon Frame→Shape→Build→Review→Ship
skin derived via ``coordination.PHASE_BY_STATE`` over the conserved Scope
``state`` projection — never a third vocabulary.

Defensive only — a read-only projection over CE's own governance state.
"""

from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any, Mapping

import yaml

from .. import coordination, seat_sentinel, v3_session
from ..runtime_evidence_spine import verify_chain
from .spend_gate import fleet_spend_meter, project_spend
from .usage_tap import UsageTurn, fleet_token_rate

#: Snapshot shape version (bumped additively; consumers tolerate additions).
SNAPSHOT_VERSION = 2

#: The demo flag (Fork 4): ``CE_DEMO=1`` swaps the data source for the seed and
#: renders the persistent watermark.
DEMO_ENV = "CE_DEMO"
#: The launch-pinned Active-Work-Ledger root (the SAME env seam ``ce lane
#: launch`` exports for the Ring-1 hook — Gate B). Absolute path.
LEDGER_ROOT_ENV = "CE_LEDGER_ROOT"
#: The hook-observation directory (the v1 instance-local advisory log + the
#: B.3 refusal chain live here). Absolute path; documented in
#: ``docs/architecture/cockpit.md``.
OBSERVATIONS_DIR_ENV = "CE_HOOK_OBSERVATIONS_DIR"

#: The persistent demo watermark (Fork 4 — a pitch demo is never mistaken for
#: live governance).
DEMO_WATERMARK = "DEMO — seeded data, not a live fleet"

#: L1 layout constants (the ``evidence_sink`` / ``v3_cli`` storage seams,
#: re-declared here because v3_cli is not an allowed import for this module).
CHAIN_SUFFIX = ".runtime-evidence.yaml"
RUNS_SUBDIR = "runs"
SCOPES_SUBDIR = "scopes"
SCOPE_SUFFIX = ".scope.yaml"
ESCALATIONS_SUBDIR = "escalations"
DISPATCHES_SUBDIR = "dispatches"
PANES_SUBDIR = "panes"
OBSERVATIONS_FILENAME = "observations.ndjson"
# ce-ops#38: the work-claim view-only cache (written by ``ce claim status
# --write-cache``). L1-shaped INPUT to the pure fold — never enforcement
# authority (dispatch always reads the live forge comments, never this file).
CLAIMS_SUBDIR = "claims"
CLAIMS_CACHE_FILENAME = "claims.json"

#: Source-availability states (honesty tiers for the snapshot itself).
AVAILABLE = "ok"
UNAVAILABLE = "unavailable"

#: v3.5-B.3 — the hook-side refusal chain (a ``runtime-evidence-chain``
#: document the Ring-1 hook appends governed denies to, beside the legacy
#: advisory log in the same observations directory).
REFUSAL_CHAIN_FILENAME = "refusal-chain.yaml"

#: The envelope access-matrix rows (rakkess pattern): the Ring-1 hook's
#: restricted-mechanics surface, mirrored as a declared constant (the v1
#: ``hook_check`` module is not importable across the version boundary).
RESTRICTED_MECHANICS = (
    "merge",
    "deploy",
    "publish",
    "alter_repo_settings",
    "pr_review",
    "pr_comment",
    "pr_lifecycle",
    "live_lane_launch",
    "live_integration_queue",
)
GRANTED = "granted"
WITHHELD = "withheld"

#: The standing authority fact ([[ce-governed-seat-cannot-push]]).
STANDING_PUSH_FACT = (
    "a governed seat is hard-blocked from `git push`; deploy authority "
    "lives with the Operator"
)

#: The G-i hard-vs-advisory posture split (mirrors the hook's governed
#: enforcement comment block).
POSTURE_HARD_DENIES = (
    "secret-path read (credential-like path)",
    "restricted mechanic without a matching ratified reviewer-venue "
    "side-effect-authority envelope (G2.007.2)",
)
POSTURE_ADVISORY = (
    "path-manifest mismatch (G-i: author-time scope containment is advisory; "
    "the PR-diff gate owns scope)",
)

#: Deciding-clause extraction (IAM explicit-vs-implicit deny pattern): a
#: governance clause id (e.g. G2.007.2) or a named secret-path rule counts as
#: an EXPLICIT deny; a reason citing neither is an IMPLICIT deny ("not covered
#: by any envelope").
_CLAUSE_RE = re.compile(r"\bG\d[\w.]*\b")
_SECRET_RULE_RE = re.compile(r"matched rule:\s*([^)]+)")

#: v3.5-B.4 — the honesty-tier badge enum (mandatory on every meter tile).
MEASURED = "MEASURED"
ESTIMATED = "ESTIMATED"
BADGE_UNAVAILABLE = "UNAVAILABLE"

#: v3.1-B.7 — the per-scope cost-tier enum for the fleet cost meter. MEASURED =
#: the run carries ≥1 priced ``runtime_spend_ledger`` leaf ($-metered, e.g. an
#: API/fleet seat); UNPRICED = the run has work evidence (a
#: ``runtime_agent_action`` or a ``runtime_run_outcome``) but ZERO priced leaves
#: — a subscription/OAuth seat whose cost is REAL but managed by limits/headroom,
#: never $-metered (so it is NEVER rendered as $0); UNAVAILABLE = an empty/absent
#: chain. The tier is derived PURELY from the chain.
COST_MEASURED = MEASURED
COST_UNPRICED = "UNPRICED"
COST_UNAVAILABLE = BADGE_UNAVAILABLE

#: Fork 5 (ratified): the subscription-headroom slot ships as a LABELLED
#: placeholder — never a fabricated estimate. The real estimator lands
#: post-research as its own gate.
SUBSCRIPTION_PLACEHOLDER = (
    "ESTIMATED — estimator not yet shipped; method TBD by its own research task"
)

#: Breach-tier action semantics (the G-5 two-tier circuit breaker, verbatim).
_BREACH_ACTIONS = {"soft": "alert + continue", "hard": "pause + escalate"}

#: v3.5-B.2 — outcome colors for stream spans (Temporal pattern), expressed in
#: CE's semantic palette names (refused -> gate, verified/allowed -> spark,
#: pending/escalate -> amber).
_CLASS_COLORS = {"allowed": "spark", "denied": "gate", "escalate": "amber"}

#: Seat statuses that count as LIVE for the crabfleet all/mine/live filters.
_LIVE_STATUSES = frozenset({"starting", "active", "blocked", "closing"})


# ---------------------------------------------------------------------------
# The PURE fold — L1-shaped values -> ONE JSON-serializable snapshot
# ---------------------------------------------------------------------------
def _seat_card(
    pane: Mapping[str, Any],
    chains: Mapping[str, Any],
    models: Mapping[str, str],
    harnesses: Mapping[str, str],
) -> dict[str, Any]:
    """Project one pane-registry record to a seat card (PURE).

    ``run_id`` is attributed by the documented join rule: a chain whose
    ``run_id`` equals the seat's ``lane_id`` belongs to the seat (the demo seed
    follows it; a live seat without such a chain carries ``None`` — declared,
    not guessed). ``model`` is the newest spend-ledger leaf's model on the
    seat's chain; ``harness`` comes from the governance sidecar beside the pane
    record — both real provenance, ``None`` where absent.
    """
    lane_id = pane.get("lane_id")
    lane_key = str(lane_id)
    terminal = pane.get("terminal") if isinstance(pane.get("terminal"), Mapping) else {}
    return {
        "controller_id": pane.get("controller_id"),
        "lane_id": lane_id,
        "role": pane.get("role"),
        "status": pane.get("status"),
        "last_seen_at": pane.get("last_seen_at"),
        "terminal_kind": terminal.get("kind"),
        "envelope_ref": pane.get("envelope_ref"),
        "worktree_path": pane.get("worktree_path"),
        "branch": pane.get("branch"),
        "run_id": lane_id if lane_id in chains else None,
        "model": models.get(lane_key),
        "harness": harnesses.get(lane_key),
    }


def _board_card(
    scope: Mapping[str, Any],
    signals: Mapping[str, Any],
    *,
    pane: Mapping[str, Any] | None = None,
    envelope: Any = None,
    harness: str | None = None,
    model: str | None = None,
    outcome: Mapping[str, Any] | None = None,
    refusal: Mapping[str, Any] | None = None,
    breach: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Project one Scope (+ seat join + evidence terminals) to a board card (PURE).

    The stage column is the canon skin: ``coordination.project_scope_state``
    derives the conserved ``state`` from the signals, and ``PHASE_BY_STATE`` /
    ``BOARD_BY_STATE`` project the phase/board labels — never a third
    vocabulary. Seat join rule: the pane whose ``lane_id`` equals the
    ``scope_id`` (a lane allocated FOR a Scope is named after it); no match =
    an unseated card, never a guess. A BLOCKED card surfaces *why* inline —
    the latest refusal-chain entry or spend breach for its run — linking to
    the governance panel.
    """
    projection = coordination.project_scope_state(dict(scope), **dict(signals))
    ready, _reasons = coordination.scope_is_ready(scope)
    pane = pane if isinstance(pane, Mapping) else None
    envelope_record = _envelope_record(envelope)
    envelope_ref = pane.get("envelope_ref") if pane else None
    if envelope_record:
        envelope_badge: str | None = f"granted:{envelope_record.get('mechanic')}"
    elif envelope_ref == "none":
        envelope_badge = "none"
    else:
        envelope_badge = None
    status = pane.get("status") if pane else None
    blocked = status == "blocked"
    blocked_source = None
    blocked_reason = None
    if blocked:
        if refusal is not None:
            blocked_source = "refusal-chain"
            blocked_reason = refusal.get("decision_reason")
        elif breach is not None:
            blocked_source = "spend-breach"
            blocked_reason = breach.get("reason")
        else:
            blocked_reason = "blocked (no refusal or breach on the spine)"
    return {
        "scope_id": scope.get("scope_id"),
        "title": scope.get("intent"),
        "state": projection["state"],
        "phase": projection["phase"],
        "board_label": projection["board"],
        "mutation_class": scope.get("mutation_class"),
        "ready": bool(ready),
        "ratified": coordination.is_ratified(scope),
        "seat": {
            "controller_id": pane.get("controller_id") if pane else None,
            "lane_id": pane.get("lane_id") if pane else None,
            "role": pane.get("role") if pane else None,
            "status": status,
            "harness": harness,
            "model": model,
        },
        "status_chip": status or "unseated",
        "role_badge": pane.get("role") if pane else None,
        "envelope_badge": envelope_badge,
        # The per-seat resource-headroom sparkline SLOT (Fork 5 honesty: the
        # estimator is unshipped, so the slot is declared UNAVAILABLE).
        "headroom_slot": {"badge": BADGE_UNAVAILABLE, "points": []},
        "outcome_chip": outcome.get("outcome") if outcome else None,
        "blocked": blocked,
        "blocked_source": blocked_source,
        "blocked_reason": blocked_reason,
    }


def _envelope_record(candidate: Any) -> dict[str, Any] | None:
    """Unwrap a ``reviewer_authority_envelope`` mapping (wrapped or bare). PURE."""
    if not isinstance(candidate, Mapping):
        return None
    record = candidate.get("reviewer_authority_envelope", candidate)
    if not isinstance(record, Mapping):
        return None
    if not record.get("envelope_id") or not record.get("mechanic"):
        return None
    return dict(record)


def _seat_governance(seat: Mapping[str, Any], envelope: Any) -> dict[str, Any]:
    """Project one seat's authority view: the access matrix + attribution (PURE).

    Rakkess pattern: rows = the restricted mechanics, cells = granted/withheld.
    A cell is GRANTED only by a validated reviewer-authority envelope naming
    that exact mechanic; everything else is withheld (deny-by-default — the
    visible form of envelope isolation).
    """
    record = _envelope_record(envelope)
    matrix = {mechanic: WITHHELD for mechanic in RESTRICTED_MECHANICS}
    if record and record.get("mechanic") in matrix:
        matrix[str(record["mechanic"])] = GRANTED
    envelope_ref = seat.get("envelope_ref")
    return {
        "controller_id": seat.get("controller_id"),
        "lane_id": seat.get("lane_id"),
        "role": seat.get("role"),
        "envelope_ref": envelope_ref,
        "no_write_authority": envelope_ref == "none",
        "envelope": record,
        "matrix": matrix,
    }


def can_i(seat_governance: Mapping[str, Any], mechanic: str, *, pr_number: int | None = None) -> dict[str, Any]:
    """The ``can-i`` probe: answer "may this seat perform <mechanic>?" from the matrix (PURE).

    Answers come from the SAME matrix the panel renders (never a parallel
    rule set). ``pr_number`` narrows a ``pr_review`` grant to the envelope's
    exact PR — wrong PR is an implicit deny, exactly like the Ring-1 hook.
    """
    matrix = seat_governance.get("matrix") or {}
    if mechanic not in matrix:
        return {
            "allowed": False,
            "why": f"unknown mechanic {mechanic!r} — withheld by default (deny-by-default)",
        }
    if mechanic == "deploy" and matrix.get("deploy") != GRANTED:
        return {"allowed": False, "why": STANDING_PUSH_FACT}
    if matrix.get(mechanic) != GRANTED:
        return {
            "allowed": False,
            "why": f"{mechanic} is not covered by any envelope (implicit deny)",
        }
    envelope = seat_governance.get("envelope") or {}
    if mechanic == "pr_review" and pr_number is not None:
        granted_pr = envelope.get("pr_number")
        if granted_pr != pr_number:
            return {
                "allowed": False,
                "why": (
                    f"envelope {envelope.get('envelope_id')} covers pr_number "
                    f"{granted_pr}, not {pr_number} (implicit deny)"
                ),
            }
    return {
        "allowed": True,
        "why": (
            f"granted by envelope {envelope.get('envelope_id')} "
            f"(mechanic {mechanic}, ratified_prompt_sha {envelope.get('ratified_prompt_sha')})"
        ),
    }


def _deciding_clause(reason: Any) -> str | None:
    """Extract the deciding clause from a deny reason (IAM 'show statement'). PURE."""
    text = str(reason or "")
    clause = _CLAUSE_RE.search(text)
    if clause:
        return clause.group(0)
    secret_rule = _SECRET_RULE_RE.search(text)
    if secret_rule:
        return f"secret-path rule: {secret_rule.group(1).strip()}"
    return None


def _refusal_entry(record: Mapping[str, Any]) -> dict[str, Any]:
    """Project one chain record to a REFUSED-feed entry (OPA decision-log shape). PURE."""
    clause = _deciding_clause(record.get("decision_reason"))
    return {
        "source": "refusal-chain",
        "advisory": False,
        "recorded_at": record.get("recorded_at"),
        "run_id": record.get("run_id"),
        "op": record.get("op"),
        "mutation_class": record.get("mutation_class"),
        "target": record.get("target"),
        "tool": record.get("tool"),
        "classification": record.get("classification"),
        "decision_mode": record.get("decision_mode"),
        "decision_reason": record.get("decision_reason"),
        "deny_kind": "explicit" if clause else "implicit",
        "deciding_clause": clause,
    }


def _legacy_entry(observation: Mapping[str, Any]) -> dict[str, Any]:
    """Project one legacy NDJSON observation to a labelled advisory entry. PURE."""
    return {
        "source": "legacy-observations",
        "advisory": True,
        "recorded_at": observation.get("observedAt"),
        "event": observation.get("hookEventName"),
        "raw": dict(observation),
    }


def _float_or_none(value: Any) -> float | None:
    return float(value) if value is not None else None


# ---------------------------------------------------------------------------
# v3.5-B.2 — board-card enrichment + seat-detail folds (PURE)
# ---------------------------------------------------------------------------
def _parse_iso(value: Any) -> Any:
    """Parse an input ISO-8601 stamp (Z-tolerant) or None (PURE — stamps are inputs)."""
    if not isinstance(value, str) or not value.strip():
        return None
    text = value.strip()
    if text.endswith("Z"):
        text = f"{text[:-1]}+00:00"
    try:
        from datetime import datetime

        return datetime.fromisoformat(text)
    except ValueError:
        return None


def _models_from_chains(chain_map: Mapping[str, list[dict[str, Any]]]) -> dict[str, str]:
    """run_id -> the newest spend-ledger leaf's model (real provenance, never guessed)."""
    out: dict[str, str] = {}
    for run_id, chain in chain_map.items():
        for record in chain:  # chain order == append order; last wins (newest)
            if isinstance(record, Mapping) and record.get("record_type") == "runtime_spend_ledger":
                model = record.get("model")
                if model:
                    out[str(run_id)] = str(model)
    return out


def _last_of_type(chain: list[dict[str, Any]], record_type: str) -> dict[str, Any] | None:
    found = None
    for record in chain:
        if isinstance(record, Mapping) and record.get("record_type") == record_type:
            found = record
    return dict(found) if found else None


def _stream_groups(chain: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Collapse consecutive identical agent actions into Temporal-style spans (PURE).

    Group key = (op, target, tool, classification); ``count > 1`` on one span
    is the RETRY badge; outcome color = the CE semantic palette name. Non-action
    records project as single labelled events in stream order.
    """
    groups: list[dict[str, Any]] = []
    last_key: tuple[Any, ...] | None = None
    for record in chain:
        if not isinstance(record, Mapping):
            continue
        if record.get("record_type") == "runtime_agent_action":
            key = (
                record.get("op"),
                record.get("target"),
                record.get("tool"),
                record.get("classification"),
            )
            if groups and last_key == key:
                groups[-1]["count"] += 1
                groups[-1]["last_at"] = record.get("recorded_at")
            else:
                groups.append(
                    {
                        "kind": "actions",
                        "op": record.get("op"),
                        "mutation_class": record.get("mutation_class"),
                        "target": record.get("target"),
                        "tool": record.get("tool"),
                        "classification": record.get("classification"),
                        "decision_reason": record.get("decision_reason"),
                        "count": 1,
                        "first_at": record.get("recorded_at"),
                        "last_at": record.get("recorded_at"),
                        "color": _CLASS_COLORS.get(str(record.get("classification")), "amber"),
                    }
                )
            last_key = key
        else:
            groups.append(
                {
                    "kind": str(record.get("record_type") or "record"),
                    "recorded_at": record.get("recorded_at"),
                }
            )
            last_key = None
    for group in groups:
        if group.get("kind") == "actions":
            group["retry"] = group["count"] > 1
    return groups


def _fold_seat_detail(chain: list[dict[str, Any]]) -> dict[str, Any]:
    """Fold ONE seat's evidence chain into the five seat-detail tabs (PURE).

    Stream = collapsed event-groups; Diffs = write-target summary off the
    action records; Evidence = the chain + a TRUTHFUL ``verify_chain`` badge
    (a tampered chain shows findings, never a green badge); Waterfall = stage
    durations between consecutive lifecycle attestations; Outcome = the
    terminal disposition + the ratification record.
    """
    write_counts: dict[str, int] = {}
    for record in chain:
        if (
            isinstance(record, Mapping)
            and record.get("record_type") == "runtime_agent_action"
            and record.get("op") == "write"
            and record.get("classification") == "allowed"
            and record.get("target")
        ):
            path = str(record["target"])
            write_counts[path] = write_counts.get(path, 0) + 1

    if chain:
        verified = verify_chain(chain) == []
        evidence = {
            "record_count": len(chain),
            "verified": verified,
            "badge": "clean" if verified else "findings",
        }
    else:
        evidence = {"record_count": 0, "verified": None, "badge": "no-chain"}

    lifecycle = [
        record
        for record in chain
        if isinstance(record, Mapping) and record.get("record_type") == "runtime_evidence"
        and record.get("lifecycle_phase")
    ]
    stages: list[dict[str, Any]] = []
    for current, following in zip(lifecycle, lifecycle[1:]):
        start = _parse_iso(current.get("recorded_at"))
        end = _parse_iso(following.get("recorded_at"))
        stages.append(
            {
                "stage": current.get("lifecycle_phase"),
                "started_at": current.get("recorded_at"),
                "ended_at": following.get("recorded_at"),
                "duration_seconds": (
                    (end - start).total_seconds() if start is not None and end is not None else None
                ),
            }
        )

    outcome_record = _last_of_type(chain, "runtime_run_outcome")
    ratification_record = _last_of_type(chain, "runtime_ratification")
    return {
        "stream": {"groups": _stream_groups(chain)},
        "diffs": {
            "source": "evidence-records",
            "files": [
                {"path": path, "writes": count} for path, count in sorted(write_counts.items())
            ],
        },
        "evidence": evidence,
        "waterfall": {"stages": stages},
        "outcome": {
            "outcome": outcome_record.get("outcome") if outcome_record else None,
            "change_set": dict(outcome_record.get("change_set") or {}) if outcome_record else None,
            "ratification": (
                {
                    "ratified_prompt_sha": ratification_record.get("ratified_prompt_sha"),
                    "approver_ref": ratification_record.get("approver_ref"),
                    "ratified_head_sha": ratification_record.get("ratified_head_sha"),
                    "binding_ref": ratification_record.get("binding_ref"),
                    "recorded_at": ratification_record.get("recorded_at"),
                }
                if ratification_record
                else None
            ),
        },
    }


def _fold_meters(
    chains: Mapping[str, list[dict[str, Any]]] | None,
    usage_turns: list[dict[str, Any]] | None,
    context_pct: Any,
) -> dict[str, Any]:
    """Fold the unified resource/health meter strip (v3.5-B.4). PURE.

    REUSE, never re-implement (the no-parallel-math law): spend ($) rides
    ``spend_gate.fleet_spend_meter``; token-rate rides
    ``usage_tap.fleet_token_rate``; context-% rides ``v3_session.context_meter``
    (the harness's authoritative number, CONSUMED — never recomputed); the
    per-run breaker state on a breach banner rides
    ``v3_session.spend_meter_from_spine`` (the real G-5 projection). The
    subscription-headroom slot is the Fork-5 LABELLED PLACEHOLDER — never a
    number. Every tile carries a MEASURED/ESTIMATED/UNAVAILABLE badge; an
    absent source is UNAVAILABLE, never a guess.
    """
    flat_records: list[dict[str, Any]] = [
        record for chain in (chains or {}).values() for record in chain
    ]

    if chains is not None:
        spend = fleet_spend_meter(flat_records, unit="$")
        spend_tile: dict[str, Any] = {
            "badge": MEASURED,
            "unit": spend.unit,
            "spend": _float_or_none(spend.spend),
            "record_count": spend.record_count,
            "run_count": spend.run_count,
            "span_hours": _float_or_none(spend.span_hours),
            "spend_per_hour": _float_or_none(spend.spend_per_hour),
        }
    else:
        spend_tile = {
            "badge": BADGE_UNAVAILABLE,
            "unit": "$",
            "spend": None,
            "record_count": None,
            "run_count": None,
            "span_hours": None,
            "spend_per_hour": None,
        }

    if usage_turns is not None:
        turns = [
            UsageTurn(
                session_id=str(t.get("session_id") or ""),
                model=str(t.get("model") or ""),
                recorded_at=str(t.get("recorded_at") or ""),
                usage=dict(t.get("usage") or {}),
            )
            for t in usage_turns
            if isinstance(t, Mapping)
        ]
        rate = fleet_token_rate(turns)
        token_tile: dict[str, Any] = {
            "badge": MEASURED,
            "total_tokens": rate.total_tokens,
            "turn_count": rate.turn_count,
            "span_hours": _float_or_none(rate.span_hours),
            "tokens_per_hour": _float_or_none(rate.tokens_per_hour),
        }
    else:
        token_tile = {
            "badge": BADGE_UNAVAILABLE,
            "total_tokens": None,
            "turn_count": None,
            "span_hours": None,
            "tokens_per_hour": None,
        }

    if context_pct is not None:
        context = v3_session.context_meter(context_pct)
        context_tile: dict[str, Any] = {
            "badge": MEASURED,
            "pct": context.pct,
            "state": context.state,
        }
    else:
        context_tile = {"badge": BADGE_UNAVAILABLE, "pct": None, "state": "unknown"}

    banners: list[dict[str, Any]] = []
    for record in flat_records:
        if not isinstance(record, Mapping):
            continue
        if record.get("record_type") != "runtime_spend_breach":
            continue
        run_id = record.get("run_id")
        limit = record.get("limit")
        run_meter = v3_session.spend_meter_from_spine(
            flat_records, limit, run_id=str(run_id), unit=str(record.get("breach_unit") or "$")
        )
        banners.append(
            {
                "tier": record.get("tier"),
                "action": _BREACH_ACTIONS.get(str(record.get("tier")), "alert + continue"),
                "signal": record.get("signal"),
                "breach_scope": record.get("breach_scope"),
                "unit": record.get("breach_unit"),
                "limit": limit,
                "observed": record.get("observed"),
                "run_id": run_id,
                "reason": record.get("decision_reason"),
                "recorded_at": record.get("recorded_at"),
                "run_meter": {
                    "spent": _float_or_none(run_meter.spent),
                    "cap": _float_or_none(run_meter.cap),
                    "ratio": run_meter.ratio,
                    "state": run_meter.state,
                },
            }
        )
    banners.sort(key=lambda b: str(b.get("recorded_at") or ""), reverse=True)

    return {
        "spend": spend_tile,
        "token_rate": token_tile,
        "context": context_tile,
        "subscription_headroom": {
            "badge": ESTIMATED,
            "value": None,
            "placeholder": SUBSCRIPTION_PLACEHOLDER,
        },
        # v3.1-B.7 — the per-scope fleet cost meter (MEASURED $ + UNPRICED
        # subscription honesty tiers). Folded from the SAME chains; the
        # ``chains is None`` UNAVAILABLE discipline lives inside the fold.
        "cost": fold_cost_meter(chains),
        "banners": banners,
    }


def _priced_leaves(chain: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """The run's ``$``-unit ``runtime_spend_ledger`` leaves (the MEASURED evidence)."""
    return [
        record
        for record in chain
        if isinstance(record, Mapping)
        and record.get("record_type") == "runtime_spend_ledger"
        and record.get("unit") == "$"
    ]


def fold_cost_meter(
    chains: Mapping[str, list[dict[str, Any]]] | None,
) -> dict[str, Any]:
    """Fold the fleet COST meter (v3.1-B.7) — per-scope $ + fleet total. PURE.

    A READ-ONLY projection over the ``runtime_spend_ledger`` leaves of every
    collected run (``run_id == scope_id`` join). REUSE, never re-implement (the
    no-parallel-math law): per-scope $ rides ``spend_gate.project_spend`` and the
    fleet rollup rides ``spend_gate.fleet_spend_meter`` — this module computes no
    $ math of its own. A demo surface, NOT the G-5/v3.5-G tokenomics engine; it
    adds nothing to the admission/breaker semantics, it only makes the fleet's
    cost legible and HONEST: what we MEASURED in $, and what ran on a subscription
    (UNPRICED — managed by limits/headroom, never rendered as $0).

    Honesty tiers (derived purely from each chain): a row is **MEASURED** with
    ≥1 priced leaf, **UNPRICED** when it has work evidence (an action or an
    outcome) but zero priced leaves, **UNAVAILABLE** on an empty chain. The
    measured fleet total is an explicit FLOOR on true cost — the headroom note
    states how many runs are unpriced. ``chains is None`` ⇒ the whole section is
    UNAVAILABLE (the honesty-tier discipline, mirroring ``_fold_meters``).
    """
    if chains is None:
        return {
            "badge": BADGE_UNAVAILABLE,
            "unit": "$",
            "scopes": [],
            "fleet": {
                "badge": BADGE_UNAVAILABLE,
                "unit": "$",
                "measured_spend": None,
                "measured_run_count": None,
                "unpriced_run_count": None,
                "total_run_count": None,
                "span_hours": None,
                "spend_per_hour": None,
            },
            "headroom_note": None,
        }

    flat_records: list[dict[str, Any]] = [
        record for chain in chains.values() for record in chain
    ]
    fleet = fleet_spend_meter(flat_records, unit="$")

    rows: list[dict[str, Any]] = []
    measured_run_count = 0
    unpriced_run_count = 0
    for run_id, chain in chains.items():
        priced = _priced_leaves(chain)
        actions = [
            r
            for r in chain
            if isinstance(r, Mapping) and r.get("record_type") == "runtime_agent_action"
        ]
        has_outcome = any(
            isinstance(r, Mapping) and r.get("record_type") == "runtime_run_outcome"
            for r in chain
        )
        if priced:
            tier = COST_MEASURED
            measured_run_count += 1
            # REUSE project_spend for the per-run $ (never a parallel sum).
            spend: float | None = _float_or_none(
                project_spend(chain, "run", run_id=str(run_id), unit="$")
            )
        elif actions or has_outcome:
            tier = COST_UNPRICED
            unpriced_run_count += 1
            # NEVER a $ figure for an unpriced run (the silent-$0 lie this whole
            # honesty tier exists to prevent) — its cost is real but not metered.
            spend = None
        else:
            tier = COST_UNAVAILABLE
            spend = None
        models = sorted({str(r.get("model")) for r in priced if r.get("model")})
        row: dict[str, Any] = {
            "scope_id": str(run_id),
            "tier": tier,
            "spend": spend,
            "leaf_count": len(priced),
            "models": models,
        }
        if tier == COST_UNPRICED:
            # The chain-visible proxy for "turns of unpriced work" (the exact
            # collect-time `unpriced` count is dropped off the chain today; the
            # faithful version is a later hardening — Fork A-3).
            row["unpriced_turns"] = len(actions)
        rows.append(row)
    rows.sort(key=lambda r: str(r.get("scope_id")))

    total_run_count = len(chains)
    if total_run_count == 0:
        headroom_note = "no collected runs yet — the fleet cost meter is empty"
    elif unpriced_run_count:
        headroom_note = (
            f"measured $ is a FLOOR on true fleet cost: {unpriced_run_count} of "
            f"{total_run_count} runs are unpriced (subscription — managed by "
            f"LIMITS/HEADROOM, not $)"
        )
    else:
        headroom_note = (
            f"all {total_run_count} runs are $-measured; measured $ is the full "
            f"metered fleet cost"
        )

    return {
        "badge": MEASURED,
        "unit": "$",
        "scopes": rows,
        "fleet": {
            "badge": MEASURED,
            "unit": fleet.unit,
            "measured_spend": _float_or_none(fleet.spend),
            "measured_run_count": measured_run_count,
            "unpriced_run_count": unpriced_run_count,
            "total_run_count": total_run_count,
            "span_hours": _float_or_none(fleet.span_hours),
            "spend_per_hour": _float_or_none(fleet.spend_per_hour),
        },
        "headroom_note": headroom_note,
    }


def _fold_escalations(escalations: list[dict[str, Any]] | None) -> dict[str, Any]:
    """Fold local escalation records into the AWAITING-OPERATOR queue (PURE)."""
    records = [e for e in (escalations or []) if isinstance(e, Mapping)]
    open_records = [e for e in records if not e.get("resolved_at")]
    open_records.sort(key=lambda e: str(e.get("created_at") or ""))
    open_entries = []
    for rank, record in enumerate(open_records, start=1):
        open_entries.append(
            {
                "escalation_id": record.get("escalation_id"),
                "title": record.get("title"),
                "decision_needed": record.get("decision_needed"),
                "recommendation": record.get("recommendation"),
                "created_at": record.get("created_at"),
                "source_ref": record.get("source_ref"),
                "age_rank": rank,
            }
        )
    return {
        "open": open_entries,
        "open_count": len(open_entries),
        "resolved_count": len([e for e in records if e.get("resolved_at")]),
    }


def _normalized_spend_envelope(candidate: Any) -> dict[str, Any] | None:
    """Project a runtime-policy spend envelope to the Cockpit's cap/unit/window shape."""
    if not isinstance(candidate, Mapping):
        return None
    cap = candidate.get("amount")
    if cap is None:
        cap = candidate.get("cap")
    if cap is None:
        cap = candidate.get("cap_usd")
    unit = candidate.get("unit")
    if unit is None and candidate.get("cap_usd") is not None:
        unit = "$"
    window = candidate.get("window")
    if cap is None and unit is None and window is None:
        return None
    return {"cap": cap, "unit": unit, "window": window}


def _run_spend_envelope(policy: Any) -> dict[str, Any] | None:
    """Extract the run-scope spend envelope from a runtime-policy mapping (PURE)."""
    if not isinstance(policy, Mapping):
        return None
    for envelope in policy.get("spend_envelopes") or []:
        if isinstance(envelope, Mapping) and envelope.get("scope") == "run":
            return _normalized_spend_envelope(envelope)
    return None


def _dispatch_payload(item: Any) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
    """Return (dispatch-record, spend-envelope) from raw or loader-wrapped input."""
    if not isinstance(item, Mapping):
        return None, None
    if isinstance(item.get("dispatch"), Mapping):
        return dict(item["dispatch"]), _normalized_spend_envelope(item.get("spend_envelope"))
    envelope = item.get("_spend_envelope")
    return dict(item), _normalized_spend_envelope(envelope)


def _dispatch_state(record: Mapping[str, Any]) -> str:
    """Derive the G1 lifecycle state from value-free stamp presence (PURE)."""
    if record.get("spawn_failed_at"):
        return "failed"
    if record.get("collected_at"):
        return "collected"
    if record.get("spawned_at") or record.get("terminal"):
        return "spawned"
    return "assembled"


def _fold_dispatches(
    dispatches: list[dict[str, Any]] | None,
) -> tuple[dict[str, Any], set[str]]:
    """Fold G1 dispatch records and return dispatch-derived board signals (PURE)."""
    entries: list[dict[str, Any]] = []
    dispatch_signal_scope_ids: set[str] = set()
    for item in dispatches or []:
        record, spend_envelope = _dispatch_payload(item)
        if not isinstance(record, Mapping) or record.get("kind") != "dispatch-record":
            continue
        state = _dispatch_state(record)
        scope_id = record.get("scope_id")
        if scope_id and state in {"assembled", "spawned"}:
            dispatch_signal_scope_ids.add(str(scope_id))
        terminal = record.get("terminal") if isinstance(record.get("terminal"), Mapping) else {}
        entries.append(
            {
                "run_id": record.get("run_id"),
                "scope_id": scope_id,
                "mutation_class": record.get("mutation_class"),
                "harness": record.get("harness"),
                "unattended": record.get("unattended"),
                "state": state,
                "spawned_at": record.get("spawned_at"),
                "collected_at": record.get("collected_at"),
                "spawn_failed_at": record.get("spawn_failed_at"),
                "spawn_failure_reason": record.get("spawn_failure_reason"),
                "terminal_kind": terminal.get("kind"),
                "resource_bound": record.get("resource_bound"),
                "spend_envelope": spend_envelope,
            }
        )
    entries.sort(
        key=lambda e: (e.get("spawned_at") is not None, str(e.get("spawned_at") or "")),
        reverse=True,
    )
    return (
        {
            "entries": entries,
            "count": len(entries),
            "live_count": len([e for e in entries if e.get("state") == "spawned"]),
            "failed_count": len([e for e in entries if e.get("state") == "failed"]),
        },
        dispatch_signal_scope_ids,
    )


def _fold_claims(
    claims: Mapping[str, Any] | None,
    controller_id: str | None,
) -> dict[str, Any]:
    """Fold the ce-ops#38 work-claim view-only cache into the ops-board section (PURE).

    ``None`` means the cache is unreachable (degrades honestly to ``unavailable``);
    a dict is the parsed ``claims.json``. Counts are recomputed from the entries
    (never trusted blindly from the cache) so the surface is honest; ``foreign``
    is an active claim NOT held by this controller. This is observation only — the
    cache MUST NOT (and does not) authorize any dispatch.
    """
    if claims is None or not isinstance(claims, Mapping):
        return {
            "entries": [], "active_count": 0, "stale_count": 0, "foreign_count": 0,
            "invalid_count": 0, "availability": UNAVAILABLE, "cache_fetched_at": None,
            "repo": None, "work_key": None,
        }
    raw_entries = claims.get("entries")
    entries = [dict(e) for e in raw_entries if isinstance(e, Mapping)] if isinstance(raw_entries, list) else []
    active = [e for e in entries if e.get("status") == "active"]
    stale = [e for e in active if e.get("stale")]
    foreign = [
        e for e in active
        if controller_id is None or e.get("holder") != controller_id
    ]
    invalid_count = claims.get("invalid_count")
    if not isinstance(invalid_count, int):
        invalid_count = len([e for e in entries if e.get("status") == "invalid"])
    return {
        "entries": entries,
        "active_count": len(active),
        "stale_count": len(stale),
        "foreign_count": len(foreign),
        "invalid_count": invalid_count,
        "availability": AVAILABLE,
        "cache_fetched_at": claims.get("fetched_at"),
        "repo": claims.get("repo"),
        "work_key": claims.get("work_key"),
    }


def _seat_event_summary(events: list[dict[str, Any]]) -> dict[str, Any]:
    """Project one seat's append-only event stream to a flat, JSON-safe summary (PURE)."""
    launched = next((e for e in events if e.get("event") == "launched"), None)
    exited = next((e for e in reversed(events) if e.get("event") == "exited"), None)
    outcome_ev = next(
        (e for e in reversed(events) if e.get("event") == "outcome_resolved"), None
    )
    if exited is not None:
        terminal_state = "exited"
    elif launched is not None:
        terminal_state = "live"  # launched, no exit observed — UNKNOWN-TERMINAL, not success
    else:
        terminal_state = "unknown"
    return {
        "count": len(events),
        "terminal_state": terminal_state,
        "pid": launched.get("pid") if isinstance(launched, dict) else None,
        "exit_code": exited.get("exit_code") if isinstance(exited, dict) else None,
        "outcome": outcome_ev.get("outcome") if isinstance(outcome_ev, dict) else None,
        "outcome_source": (
            outcome_ev.get("outcome_source") if isinstance(outcome_ev, dict) else None
        ),
        "last_ts": events[-1].get("ts") if events else None,
    }


def _fold_seat_events(
    seat_events: Mapping[str, list[dict[str, Any]]] | None,
) -> dict[str, Any]:
    """Fold ce-ops#26 seat lifecycle events into the cockpit section (PURE)."""
    seats = {
        str(seat_id): _seat_event_summary(list(events or []))
        for seat_id, events in (seat_events or {}).items()
    }
    return {
        "seats": seats,
        "count": len(seats),
        "live_count": len([s for s in seats.values() if s["terminal_state"] == "live"]),
        "exited_count": len([s for s in seats.values() if s["terminal_state"] == "exited"]),
    }


def fold_snapshot(
    *,
    panes: list[dict[str, Any]] | None = None,
    scopes: list[dict[str, Any]] | None = None,
    scope_signals: Mapping[str, Mapping[str, Any]] | None = None,
    chains: Mapping[str, list[dict[str, Any]]] | None = None,
    observations: list[dict[str, Any]] | None = None,
    refusal_chain: list[dict[str, Any]] | None = None,
    escalations: list[dict[str, Any]] | None = None,
    dispatches: list[dict[str, Any]] | None = None,
    seat_events: Mapping[str, list[dict[str, Any]]] | None = None,
    claims: Mapping[str, Any] | None = None,
    envelopes: Mapping[str, Any] | None = None,
    usage_turns: list[dict[str, Any]] | None = None,
    context_pct: Any = None,
    harnesses: Mapping[str, str] | None = None,
    controller_id: str | None = None,
    demo: bool = False,
    roots: Mapping[str, str | None] | None = None,
    ce_version: str | None = None,
) -> dict[str, Any]:
    """Fold L1-shaped values into the ONE JSON-serializable Cockpit snapshot (PURE).

    ``None`` for a source means UNREACHABLE (degrades honestly to
    ``unavailable``); an empty list means reachable-but-empty. ``scope_signals``
    maps ``scope_id`` to the committed-signal kwargs of
    ``coordination.project_scope_state`` (``dispatched``/``reviewed``/
    ``final_ratified``/``merged``); live derivation of those signals from
    chains is a later-gate fold — absent signals project the Scope's own
    derivable state, never an invented one. ``refusal_chain`` is the hook-side
    hash-chained refusal log (v3.5-B.3); ``envelopes`` maps ``lane_id`` to a
    resolved reviewer-authority envelope (live: read via the pane registry's
    ``envelope_ref``; demo: provided by the seed). ``usage_turns`` (UsageTurn-
    shaped dicts) and ``context_pct`` (the harness's authoritative number) feed
    the v3.5-B.4 meter strip — their LIVE taps are deferred seams, so live
    snapshots carry them as ``None`` (UNAVAILABLE) until those land.
    """
    dispatch_section, dispatch_signal_scope_ids = _fold_dispatches(dispatches)
    # ce-ops#26: fold the one seat-events contract and join each dispatch entry to
    # its events by seat_id == run_id (the directory IS the join — no new pointer).
    seat_events_section = _fold_seat_events(seat_events)
    for entry in dispatch_section["entries"]:
        summary = seat_events_section["seats"].get(str(entry.get("run_id")))
        if summary is not None:
            entry["sentinel"] = summary
    signals = {str(k): dict(v) for k, v in (scope_signals or {}).items()}
    for scope_id in dispatch_signal_scope_ids:
        signals.setdefault(scope_id, {}).setdefault("dispatched", True)
    chain_map = dict(chains or {})
    envelope_map = dict(envelopes or {})
    harness_map = {str(k): str(v) for k, v in (harnesses or {}).items()}
    models = _models_from_chains(chain_map)
    meters = _fold_meters(chains, usage_turns, context_pct)
    escalation_section = _fold_escalations(escalations)
    claims_section = _fold_claims(claims, controller_id)

    seats = [
        _seat_card(p, chain_map, models, harness_map)
        for p in (panes or [])
        if isinstance(p, Mapping)
    ]
    seats.sort(key=lambda s: (str(s.get("controller_id")), str(s.get("lane_id"))))
    panes_by_lane = {
        str(p.get("lane_id")): p for p in (panes or []) if isinstance(p, Mapping)
    }

    # Per-run terminals + blocked-why inputs (the board join sources).
    outcome_by_run = {
        run_id: _last_of_type(chain, "runtime_run_outcome")
        for run_id, chain in chain_map.items()
    }
    refusal_by_run: dict[str, dict[str, Any]] = {}
    for record in refusal_chain or []:
        if isinstance(record, Mapping) and record.get("classification") == "denied":
            refusal_by_run[str(record.get("run_id"))] = dict(record)
    breach_by_run: dict[str, dict[str, Any]] = {}
    for banner in meters["banners"]:  # newest first; keep the newest per run
        breach_by_run.setdefault(str(banner.get("run_id")), banner)

    cards = []
    for scope in scopes or []:
        if not isinstance(scope, Mapping):
            continue
        scope_id = str(scope.get("scope_id"))
        pane = panes_by_lane.get(scope_id)
        cards.append(
            _board_card(
                scope,
                signals.get(scope_id, {}),
                pane=pane,
                envelope=envelope_map.get(scope_id),
                harness=harness_map.get(scope_id),
                model=models.get(scope_id),
                outcome=outcome_by_run.get(scope_id),
                refusal=refusal_by_run.get(scope_id),
                breach=breach_by_run.get(scope_id),
            )
        )
    cards.sort(key=lambda c: str(c.get("scope_id")))
    phase_counts = {phase: 0 for phase in coordination.COGNITIVE_PHASES}
    for card in cards:
        phase_counts[card["phase"]] += 1

    # The crabfleet all/mine/live filter triad, FOLDED HERE (principle 6):
    # L3 only binds the precomputed id lists.
    filters = {
        "all": [c["scope_id"] for c in cards],
        "mine": [
            c["scope_id"]
            for c in cards
            if controller_id is not None and c["seat"]["controller_id"] == controller_id
        ],
        "live": [c["scope_id"] for c in cards if c["seat"]["status"] in _LIVE_STATUSES],
    }

    seat_detail = {
        lane: _fold_seat_detail(chain_map.get(lane) or []) for lane in panes_by_lane
    }

    # ★ REFUSED (v3.5-B.3): chain-derived entries are first-class; the legacy
    # advisory log rides along, labelled. Newest first (a live feed).
    chain_entries = [
        _refusal_entry(r)
        for r in (refusal_chain or [])
        if isinstance(r, Mapping) and r.get("classification") in ("denied", "escalate")
    ]
    legacy_entries = [_legacy_entry(o) for o in (observations or []) if isinstance(o, Mapping)]
    feed = sorted(
        chain_entries + legacy_entries,
        key=lambda e: str(e.get("recorded_at") or ""),
        reverse=True,
    )
    source_labels = []
    if refusal_chain is not None:
        source_labels.append("refusal-chain (hash-chained)")
    if observations is not None:
        source_labels.append("legacy hook observations (advisory)")

    evidence = {
        str(run_id): {
            "record_count": len(chain),
            "verified": verify_chain(chain) == [],
        }
        for run_id, chain in chain_map.items()
    }

    governance = {
        "mechanics": list(RESTRICTED_MECHANICS),
        "seats": {
            str(seat.get("lane_id")): _seat_governance(
                seat, envelope_map.get(str(seat.get("lane_id")))
            )
            for seat in seats
        },
        "standing_facts": [STANDING_PUSH_FACT],
        "posture": {
            "hard_denies": list(POSTURE_HARD_DENIES),
            "advisory": list(POSTURE_ADVISORY),
        },
    }

    return {
        "snapshot_version": SNAPSHOT_VERSION,
        "source": {
            "mode": "demo" if demo else "live",
            "demo": bool(demo),
            "watermark": DEMO_WATERMARK if demo else None,
            # ce-ops#25: the derived CE version token, resolved ONCE by the
            # caller (``v3_cli._cmd_cockpit``) and folded in as data — additive
            # field, no ``SNAPSHOT_VERSION`` bump (Open-Q4).
            "ce_version": ce_version,
            "roots": dict(roots or {}),
        },
        "availability": {
            "seats": AVAILABLE if panes is not None else UNAVAILABLE,
            "board": AVAILABLE if scopes is not None else UNAVAILABLE,
            "evidence": AVAILABLE if chains is not None else UNAVAILABLE,
            "escalations": AVAILABLE if escalations is not None else UNAVAILABLE,
            "dispatches": AVAILABLE if dispatches is not None else UNAVAILABLE,
            "seat_events": AVAILABLE if seat_events is not None else UNAVAILABLE,
            "claims": AVAILABLE if claims is not None else UNAVAILABLE,
            "refusals": (
                AVAILABLE
                if (refusal_chain is not None or observations is not None)
                else UNAVAILABLE
            ),
        },
        "seats": seats,
        "board": {
            "columns": list(coordination.COGNITIVE_PHASES),
            "cards": cards,
            "phase_counts": phase_counts,
            "filters": filters,
        },
        "seat_detail": seat_detail,
        "refusals": {
            "source_label": " + ".join(source_labels) or "unavailable",
            "count": len(feed),
            "entries": feed,
            "chain_verified": (
                verify_chain(refusal_chain) == [] if refusal_chain is not None else None
            ),
        },
        "escalations": escalation_section,
        "dispatches": dispatch_section,
        "seat_events": seat_events_section,
        "claims": claims_section,
        "governance": governance,
        "meters": meters,
        "evidence": evidence,
    }


# ---------------------------------------------------------------------------
# The narrow, injectable load seams (the ONLY file reads in this module)
# ---------------------------------------------------------------------------
def load_chains(state_root: Path) -> dict[str, list[dict[str, Any]]]:
    """Read every ``*.runtime-evidence.yaml`` chain document directly under ``state_root``.

    Returns ``run_id -> records``. Chains persist at ``<root>/runs/<run_id>.runtime-evidence.yaml``
    (the ``evidence_sink`` / ``RUNS_SUBDIR`` layout shared with ``v3_forge_join``), so callers must
    pass ``<root>/runs`` — :func:`snapshot_from_roots` does (the F7 fix). This loader globs the
    directory it is GIVEN, never assuming a subdir. Tolerant: a malformed document is skipped, never
    raised (read-only observability must not crash the view).
    """
    chains: dict[str, list[dict[str, Any]]] = {}
    root = Path(state_root)
    if not root.is_dir():
        return chains
    for path in sorted(root.glob(f"*{CHAIN_SUFFIX}")):
        try:
            doc = yaml.safe_load(path.read_text(encoding="utf-8"))
        except (OSError, yaml.YAMLError):
            continue
        if not isinstance(doc, dict):
            continue
        records = doc.get("records")
        if not isinstance(records, list):
            continue
        run_id = path.name[: -len(CHAIN_SUFFIX)]
        chains[run_id] = [r for r in records if isinstance(r, dict)]
    return chains


def load_scopes(state_root: Path) -> list[dict[str, Any]] | None:
    """Read the Scope artifacts under ``<state_root>/scopes/`` (the v3_cli layout).

    ``None`` when the scopes directory is unreachable (source absent — distinct
    from reachable-but-empty).
    """
    scopes_dir = Path(state_root) / SCOPES_SUBDIR
    if not scopes_dir.is_dir():
        return None
    out: list[dict[str, Any]] = []
    for path in sorted(scopes_dir.glob(f"*{SCOPE_SUFFIX}")):
        try:
            doc = yaml.safe_load(path.read_text(encoding="utf-8"))
        except (OSError, yaml.YAMLError):
            continue
        if isinstance(doc, dict) and doc.get("kind") == "scope-record":
            out.append(doc)
    return out


def load_escalations(state_root: Path) -> list[dict[str, Any]] | None:
    """Read escalation records under ``<state_root>/escalations/`` (read-only).

    ``None`` when the escalations directory is unreachable. Malformed files are
    skipped so one bad local mirror record cannot crash the Cockpit.
    """
    escalations_dir = Path(state_root) / ESCALATIONS_SUBDIR
    if not escalations_dir.is_dir():
        return None
    out: list[dict[str, Any]] = []
    for path in sorted(escalations_dir.glob("*.yaml")):
        try:
            doc = yaml.safe_load(path.read_text(encoding="utf-8"))
        except (OSError, yaml.YAMLError):
            continue
        if isinstance(doc, dict) and doc.get("kind") == "escalation-record":
            out.append(doc)
    return out


def load_dispatches(state_root: Path) -> list[dict[str, Any]] | None:
    """Read dispatch records under ``<state_root>/dispatches/*/dispatch.yaml``.

    The sibling ``runtime-policy.yaml`` is best-effort-read as data to expose
    the run-scope spend envelope. ``None`` means the dispatches directory is
    unreachable; malformed records are skipped.
    """
    dispatches_dir = Path(state_root) / DISPATCHES_SUBDIR
    if not dispatches_dir.is_dir():
        return None
    out: list[dict[str, Any]] = []
    for path in sorted(dispatches_dir.glob("*/dispatch.yaml")):
        try:
            doc = yaml.safe_load(path.read_text(encoding="utf-8"))
        except (OSError, yaml.YAMLError):
            continue
        if not (isinstance(doc, dict) and doc.get("kind") == "dispatch-record"):
            continue
        spend_envelope = None
        policy_path = path.parent / "runtime-policy.yaml"
        if policy_path.is_file():
            try:
                policy = yaml.safe_load(policy_path.read_text(encoding="utf-8"))
            except (OSError, yaml.YAMLError):
                policy = None
            spend_envelope = _run_spend_envelope(policy)
        out.append({"dispatch": doc, "spend_envelope": spend_envelope})
    return out


def load_claims(state_root: Path) -> dict[str, Any] | None:
    """Read the ce-ops#38 work-claim view-only cache under ``<state_root>/claims/claims.json``.

    ``None`` when the cache is unreachable/malformed (degrades honestly to
    ``unavailable`` in the fold — never guessed data). This is the ONLY claim
    read the Cockpit performs; it is display data and is NEVER consulted by
    dispatch enforcement (that always reads the live forge comments).
    """
    path = Path(state_root) / CLAIMS_SUBDIR / CLAIMS_CACHE_FILENAME
    if not path.is_file():
        return None
    try:
        doc = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    return doc if isinstance(doc, dict) else None


def load_seat_events(state_root: Path) -> dict[str, list[dict[str, Any]]] | None:
    """Read the per-seat lifecycle events under ``<state_root>/dispatches/*/events.jsonl``.

    Delegates to the **shared** ``seat_sentinel`` parser (ce-ops#26) — tolerant:
    malformed lines are skipped, never raised (read-only observability must not
    crash the view). ``None`` when the dispatches directory is unreachable. The
    file lives inside the subtree ``watch_paths`` already names, so no new watch
    root is needed (the cockpit's live tail fires on it for free).
    """
    return seat_sentinel.load_seat_events(state_root)


def load_panes(ledger_root: Path) -> list[dict[str, Any]] | None:
    """Read pane-registry records under ``<ledger_root>/panes/**`` (read-only).

    ``None`` when the panes directory is unreachable.
    """
    panes_dir = Path(ledger_root) / PANES_SUBDIR
    if not panes_dir.is_dir():
        return None
    out: list[dict[str, Any]] = []
    for path in sorted(panes_dir.rglob("*.yaml")):
        try:
            doc = yaml.safe_load(path.read_text(encoding="utf-8"))
        except (OSError, yaml.YAMLError):
            continue
        if isinstance(doc, dict) and doc.get("kind") == "pane-registry-record":
            out.append(doc)
    return out


def load_observations(observations_dir: Path) -> list[dict[str, Any]] | None:
    """Read the legacy advisory NDJSON hook-observation log (read-only).

    ``None`` when the log is unreachable. Malformed lines are skipped.
    """
    path = Path(observations_dir) / OBSERVATIONS_FILENAME
    if not path.is_file():
        return None
    out: list[dict[str, Any]] = []
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return None
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            record = json.loads(line)
        except ValueError:
            continue
        if isinstance(record, dict):
            out.append(record)
    return out


def load_harnesses(ledger_root: Path) -> dict[str, str]:
    """Read each lane's harness from the governance sidecar beside its pane record.

    The sidecar layout is ``panes/<controller>/<lane>.<harness>-governance.json``
    carrying a ``harness`` field; the lane id is the filename stem before the
    first dot. Best-effort and read-only.
    """
    panes_dir = Path(ledger_root) / PANES_SUBDIR
    if not panes_dir.is_dir():
        return {}
    out: dict[str, str] = {}
    for path in sorted(panes_dir.rglob("*.json")):
        try:
            doc = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if isinstance(doc, dict) and isinstance(doc.get("harness"), str):
            lane_id = path.name.split(".", 1)[0]
            out[lane_id] = doc["harness"]
    return out


def load_refusal_chain(observations_dir: Path) -> list[dict[str, Any]] | None:
    """Read the hook-side refusal chain document (read-only; v3.5-B.3).

    ``None`` when the chain file is unreachable; malformed documents yield
    ``None`` too (the feed then declares the source absent, never guesses).
    """
    path = Path(observations_dir) / REFUSAL_CHAIN_FILENAME
    if not path.is_file():
        return None
    try:
        doc = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError):
        return None
    if not isinstance(doc, dict):
        return None
    records = doc.get("records")
    if not isinstance(records, list):
        return None
    return [r for r in records if isinstance(r, dict)]


def load_envelopes(panes: list[dict[str, Any]] | None) -> dict[str, Any]:
    """Resolve each pane's ``envelope_ref`` to a reviewer-authority envelope (read-only).

    Mirrors the Ring-1 hook's resolution: the ref is honored as an absolute
    path or a cwd-relative path; only a YAML document carrying a
    ``reviewer_authority_envelope`` mapping resolves (a manifest-carrier or
    prompt ref simply yields no envelope — the matrix stays all-withheld).
    Best-effort: unreadable refs resolve to nothing.
    """
    out: dict[str, Any] = {}
    for pane in panes or []:
        if not isinstance(pane, Mapping):
            continue
        ref = pane.get("envelope_ref")
        if not isinstance(ref, str) or not ref or ref == "none":
            continue
        path = Path(ref)
        if not path.is_file():
            continue
        try:
            doc = yaml.safe_load(path.read_text(encoding="utf-8"))
        except (OSError, yaml.YAMLError):
            continue
        record = _envelope_record(doc) if isinstance(doc, Mapping) else None
        if record is not None:
            out[str(pane.get("lane_id"))] = record
    return out


def _resolve(value: Path | str | None, environ: Mapping[str, str], env_key: str) -> Path | None:
    if value:
        return Path(value)
    env_value = environ.get(env_key, "")
    return Path(env_value) if env_value else None


def snapshot_from_roots(
    state_root: Path | str,
    *,
    ledger_root: Path | str | None = None,
    observations_dir: Path | str | None = None,
    demo: bool = False,
    environ: Mapping[str, str] | None = None,
    ce_version: str | None = None,
) -> dict[str, Any]:
    """Compose the load seams over the LIVE roots and fold the snapshot (the I/O edge).

    Resolution: an explicit argument wins; else the launch-pinned environment
    (:data:`LEDGER_ROOT_ENV` / :data:`OBSERVATIONS_DIR_ENV`); else the source is
    absent and the snapshot declares it ``unavailable``. The ``CE_DEMO`` data
    source is routed by the caller (``v3_cli``) through the seed module — this
    function reads live state only.
    """
    env = environ if environ is not None else os.environ
    state = Path(state_root)
    ledger = _resolve(ledger_root, env, LEDGER_ROOT_ENV)
    observations = _resolve(observations_dir, env, OBSERVATIONS_DIR_ENV)

    chains = load_chains(state / RUNS_SUBDIR) if state.is_dir() else None
    panes = load_panes(ledger) if ledger else None
    return fold_snapshot(
        panes=panes,
        scopes=load_scopes(state),
        chains=chains,
        observations=load_observations(observations) if observations else None,
        refusal_chain=load_refusal_chain(observations) if observations else None,
        escalations=load_escalations(state) if state.is_dir() else None,
        dispatches=load_dispatches(state) if state.is_dir() else None,
        seat_events=load_seat_events(state) if state.is_dir() else None,
        claims=load_claims(state) if state.is_dir() else None,
        envelopes=load_envelopes(panes),
        harnesses=load_harnesses(ledger) if ledger else None,
        demo=demo,
        ce_version=ce_version,
        roots={
            "state_root": str(state),
            "ledger_root": str(ledger) if ledger else None,
            "observations_dir": str(observations) if observations else None,
        },
    )


def watch_paths(
    state_root: Path | str,
    *,
    ledger_root: Path | str | None = None,
    observations_dir: Path | str | None = None,
    environ: Mapping[str, str] | None = None,
) -> list[str]:
    """Return the EXISTING L1 roots an L3 tail should watch (pure path math + stat).

    The watchfiles tail itself lives in L3/app wiring (the fold stays here);
    this helper only names the directories worth watching.
    """
    env = environ if environ is not None else os.environ
    state = Path(state_root)
    candidates = [
        state,
        state / ESCALATIONS_SUBDIR,
        state / DISPATCHES_SUBDIR,
        state / CLAIMS_SUBDIR,
        _resolve(ledger_root, env, LEDGER_ROOT_ENV),
        _resolve(observations_dir, env, OBSERVATIONS_DIR_ENV),
    ]
    return [str(p) for p in candidates if p is not None and p.is_dir()]
