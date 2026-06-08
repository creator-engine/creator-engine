"""CE v3 work-driving CLI (G-7.0) — the distinct v3 entry point (``cev3``).

Drives the OUTER-loop Scope lifecycle from the developer's terminal: file a
Scope (the Frame→Shape output), place the bet (``ratify``), assemble the governed
dispatch (the front gate), and inspect projected state — surfacing the CANON
vocabulary (the Scope-card labels Goal / Done-when / Budget / Change-type / Ready
and the stage phases Frame → Shape → Build → Review → Ship) OVER the conserved
schema fields (``intent`` / ``acceptance_criteria`` / ``appetite`` /
``mutation_class`` + the spec-lifecycle ``state``). The labels are a presentation
skin; the schema fields and the 6-state machine are conserved verbatim.

DISTINCT entry point: ``cev3`` is a SEPARATE ``console_script`` backed by this
v3-classified module — added ALONGSIDE the retained v1 ``ce`` launcher
(``ce_cli``), never as a subcommand on it (that would create a ``shared→v3``
import edge; see ``_versions.BASELINE_SHARED_TO_VERSION_ALLOWLIST``). v1 is
retained whole; this surface is purely additive.

Local state (G-4.1): Scope artifacts persist under the neutral, CE-namespaced
local-state root ``_versions.V3_LOCAL_STATE_ROOT`` (``.ce/state``) — NEVER the v1
bootstrapping-harness local-state root (kept frozen for v1 only) and NEVER a
per-harness tool dir (``.claude/``). ``--root`` overrides the default (tests drive
a tmp root). The ``v3_naming_hygiene`` check guards this module's surface.

Boundary (CI-pure; the LIVE seam is DEFERRED): ``drive`` assembles the run inputs
via ``coordination.assemble_dispatch`` (the front gate — REFUSES unless the Scope
is DoR-ready AND ratified) and PRINTS the resulting ``DispatchPlan`` (whose
``runtime_policy`` already carries the appetite→cap ``run`` spend envelope the G-5
gate enforces unchanged). Actually spawning the run
(``run_assembly.make_run_driver`` / ``orchestrator.run_plan``) is the deferred
live seam — this CLI produces the inputs, exactly as G-6 landed the pure assembly
and G-4 / G-5 deferred their live taps. The branded session frame + unified
status line (G-7.1), the shaping detect-and-offer dialogue (G-7.2), and the
◆ CE Completion Report (G-7.3) land in later G-7 slices; this slice is the
work-driving spine they hang off — ``session`` / ``artifacts`` are thin seams here.

Value-free: a Scope carries intent / acceptance-criteria / appetite /
mutation_class / opaque ratification digests — NEVER a credential, secret, raw
account, host, or installation identifier. Defensive only — it governs CE's own
work intake; never an offensive capability.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from typing import Any, Sequence

import yaml

from . import coordination, v3_session, v3_shaping
from ._versions import V3_LOCAL_STATE_ROOT

#: Where Scope artifacts live, relative to the local-state ``--root``.
SCOPES_SUBDIR = "scopes"
_SCOPE_SUFFIX = ".scope.yaml"

#: The conserved Scope-record envelope constants (``schemas/scope.schema.yaml``).
_KIND = "scope-record"
_RECORD_TYPE = "scope"
_SCHEMA_VERSION = "1"

#: Scope-id slug (mirrors ``schemas/scope.schema.yaml``'s ``scope_id`` pattern).
_SCOPE_ID_RE = re.compile(r"^[a-z][a-z0-9-]{2,63}$")
#: Value-free 64-hex opaque digest (the bet's ``approver_ref``).
_HEX64_RE = re.compile(r"^[0-9a-f]{64}$")

#: The user-facing Scope-card labels (the canon skin) over the conserved fields.
CARD_LABELS = {
    "intent": "Goal",
    "acceptance_criteria": "Done-when",
    "appetite": "Budget",
    "mutation_class": "Change-type",
}

#: The brand prefix every CE line carries (``pilot-uiux-model.md``).
_BRAND = "◆ CE"  # ◆ CE


# ---------------------------------------------------------------------------
# Storage seam — Scope artifacts under .ce/state/scopes/ (path-neutral via --root)
# ---------------------------------------------------------------------------
def _scopes_dir(root: Path) -> Path:
    return root / SCOPES_SUBDIR


def _scope_path(root: Path, scope_id: str) -> Path:
    return _scopes_dir(root) / f"{scope_id}{_SCOPE_SUFFIX}"


def _scope_bytes(scope: dict[str, Any]) -> str:
    """Deterministic YAML serialization (sorted keys, block style)."""
    return yaml.safe_dump(scope, sort_keys=True, default_flow_style=False)


def _dump_scope(root: Path, scope: dict[str, Any]) -> Path:
    _scopes_dir(root).mkdir(parents=True, exist_ok=True)
    path = _scope_path(root, str(scope["scope_id"]))
    path.write_text(_scope_bytes(scope), encoding="utf-8")
    return path


def _load_scope(root: Path, scope_id: str) -> dict[str, Any]:
    path = _scope_path(root, scope_id)
    if not path.is_file():
        raise FileNotFoundError(f"no Scope {scope_id!r} under {_scopes_dir(root)}")
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"malformed Scope artifact at {path}")
    return data


def _iter_scopes(root: Path) -> list[dict[str, Any]]:
    d = _scopes_dir(root)
    if not d.is_dir():
        return []
    out: list[dict[str, Any]] = []
    for p in sorted(d.glob(f"*{_SCOPE_SUFFIX}")):
        data = yaml.safe_load(p.read_text(encoding="utf-8"))
        if isinstance(data, dict) and data.get("kind") == _KIND:
            out.append(data)
    return out


def _content_sha(scope: dict[str, Any]) -> str:
    """SHA256 of the ratified Scope content (excluding the bet itself).

    The bet (``ratification.ratified_scope_sha``) pins to the Scope body it was
    placed on — an opaque content digest, never the Scope text. Recomputed
    canonically (sorted keys) so it is deterministic.
    """
    body = {k: v for k, v in scope.items() if k != "ratification"}
    canonical = json.dumps(body, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()


# ---------------------------------------------------------------------------
# Rendering — surface the canon skin (Scope card + stage phase)
# ---------------------------------------------------------------------------
def _projection(scope: dict[str, Any]) -> dict[str, str]:
    """The {state, phase, board} projection over the conserved spec-lifecycle."""
    return coordination.project_scope_state(scope)


def _card_line(scope: dict[str, Any]) -> str:
    """One-line Scope card in the canon vocabulary (the skin over the fields)."""
    proj = _projection(scope)
    ready, _ = coordination.scope_is_ready(scope)
    ac = scope.get("acceptance_criteria") or []
    appetite = scope.get("appetite") or {}
    budget = (
        f"{appetite.get('amount')}{appetite.get('unit')}"
        if appetite.get("amount") is not None
        else "—"
    )
    goal_mark = "✓" if scope.get("intent") else "—"
    ready_mark = "✓" if (ready and coordination.is_ratified(scope)) else "—"
    return (
        f"{_BRAND} · {proj['phase']} → {scope.get('scope_id')!r}  "
        f"(Goal {goal_mark} · Done-when {len(ac)} · Budget {budget} · "
        f"Change-type {scope.get('mutation_class')} · Ready {ready_mark})"
    )


def _phase_counts(scopes: list[dict[str, Any]]) -> dict[str, int]:
    counts = {phase: 0 for phase in coordination.COGNITIVE_PHASES}
    for s in scopes:
        counts[_projection(s)["phase"]] += 1
    return counts


def _emit(args: argparse.Namespace, code: int, lines: list[str], payload: dict[str, Any]) -> int:
    """Print JSON (``--json``) or the human lines; return the exit code."""
    if getattr(args, "json_output", False):
        print(json.dumps({"ok": code == 0, **payload}, indent=2, sort_keys=True))
    else:
        for ln in lines:
            print(ln)
    return code


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------
def _cmd_scope(args: argparse.Namespace) -> int:
    """File (draft) a Scope from the Scope-card flags. The Frame→Shape output."""
    if not _SCOPE_ID_RE.match(args.scope_id or ""):
        return _emit(
            args, 2,
            [f"{_BRAND} · refused: --id must match ^[a-z][a-z0-9-]{{2,63}}$"],
            {"error": "invalid scope_id"},
        )
    scope: dict[str, Any] = {
        "kind": _KIND,
        "record_type": _RECORD_TYPE,
        "schema_version": _SCHEMA_VERSION,
        "scope_id": args.scope_id,
        "intent": args.goal,            # Goal → intent
        "mutation_class": args.change_type,  # Change-type → mutation_class
    }
    if args.done_when:
        scope["acceptance_criteria"] = list(args.done_when)  # Done-when → acceptance_criteria
    if args.budget is not None:
        appetite: dict[str, Any] = {"amount": args.budget, "unit": args.budget_unit}  # Budget → appetite
        if args.budget_window:
            appetite["window"] = args.budget_window
        scope["appetite"] = appetite
    if args.note:
        scope["note"] = args.note
    path = _dump_scope(Path(args.root), scope)
    ready, reasons = coordination.scope_is_ready(scope)
    lines = [
        f"{_BRAND} · filed Scope {args.scope_id!r} → {path}",
        _card_line(scope),
    ]
    if not ready:
        lines.append(f"{_BRAND} · not yet Ready: {'; '.join(reasons)}")
    return _emit(
        args, 0, lines,
        {"action": "filed", "scope_id": args.scope_id, "path": str(path),
         "projection": _projection(scope), "ready": ready, "reasons": reasons},
    )


def _cmd_ratify(args: argparse.Namespace) -> int:
    """Place the bet (the human-only front-gate ratification) on a Ready Scope."""
    root = Path(args.root)
    try:
        scope = _load_scope(root, args.scope_id)
    except (FileNotFoundError, ValueError) as exc:
        return _emit(args, 2, [f"{_BRAND} · ratify refused: {exc}"], {"error": str(exc)})
    if not _HEX64_RE.match(args.approver_ref or ""):
        return _emit(
            args, 2,
            [f"{_BRAND} · ratify refused: --approver-ref must be a 64-hex opaque digest "
             "(value-free; never a raw account)"],
            {"error": "invalid approver_ref"},
        )
    ready, reasons = coordination.scope_is_ready(scope)
    if not ready:
        # The bet is placed at Shape→Build, only once the Scope is Ready.
        return _emit(
            args, 1,
            [f"{_BRAND} · ratify refused: Scope is not Ready — {'; '.join(reasons)}"],
            {"error": "not_ready", "reasons": reasons},
        )
    scope.pop("ratification", None)
    scope["ratification"] = {
        "approver_ref": args.approver_ref,
        "ratified_scope_sha": _content_sha(scope),
    }
    path = _dump_scope(root, scope)
    lines = [
        f"{_BRAND} · bet placed on Scope {args.scope_id!r} → {path}",
        _card_line(scope),
    ]
    return _emit(
        args, 0, lines,
        {"action": "ratified", "scope_id": args.scope_id, "path": str(path),
         "projection": _projection(scope)},
    )


def _cmd_drive(args: argparse.Namespace) -> int:
    """Assemble the governed dispatch (the front gate) — the LIVE spawn is deferred."""
    root = Path(args.root)
    try:
        scope = _load_scope(root, args.scope_id)
    except (FileNotFoundError, ValueError) as exc:
        return _emit(args, 2, [f"{_BRAND} · drive refused: {exc}"], {"error": str(exc)})
    runtime_policy: dict[str, Any] = {}
    if args.policy:
        policy_path = Path(args.policy)
        if not policy_path.is_file():
            # Fail closed: never dispatch silently dropping an operator's intended
            # spend ceiling / runtime policy.
            return _emit(
                args, 2,
                [f"{_BRAND} · drive refused: --policy file not found: {policy_path}"],
                {"error": "policy_not_found", "policy": str(policy_path)},
            )
        loaded = yaml.safe_load(policy_path.read_text(encoding="utf-8"))
        if not isinstance(loaded, dict):
            return _emit(
                args, 2,
                [f"{_BRAND} · drive refused: --policy must be a YAML mapping "
                 f"(got {type(loaded).__name__}); refusing rather than drop your spend policy"],
                {"error": "policy_malformed", "policy": str(policy_path)},
            )
        runtime_policy = loaded
    result = coordination.assemble_dispatch(scope, runtime_policy)
    if isinstance(result, coordination.DispatchRefusal):
        lines = [
            f"{_BRAND} · drive REFUSED ({result.reason}) — the front gate held",
            *(f"    - {d}" for d in result.detail),
        ]
        return _emit(
            args, 1, lines,
            {"action": "refused", "reason": result.reason, "detail": list(result.detail)},
        )
    envelopes = result.runtime_policy.get("spend_envelopes", [])
    lines = [
        f"{_BRAND} · BUILD dispatch assembled for Scope {result.scope_id!r} "
        f"(class {result.mutation_class})",
        f"    spend_envelopes: {json.dumps(envelopes, sort_keys=True)}",
        f"{_BRAND} · (live run spawn is the deferred seam — inputs produced, not executed)",
    ]
    return _emit(
        args, 0, lines,
        {"action": "dispatch_assembled", "scope_id": result.scope_id,
         "mutation_class": result.mutation_class, "runtime_policy": result.runtime_policy,
         "live_spawn": "deferred"},
    )


def _cmd_status(args: argparse.Namespace) -> int:
    """List Scopes with their projected stage (the canon skin over the machine)."""
    scopes = _iter_scopes(Path(args.root))
    counts = _phase_counts(scopes)
    lines = [
        f"{_BRAND} · {len(scopes)} Scope(s) · "
        + " · ".join(f"{p} {counts[p]}" for p in coordination.COGNITIVE_PHASES),
    ]
    for s in sorted(scopes, key=lambda x: str(x.get("scope_id"))):
        lines.append("  " + _card_line(s))
    return _emit(
        args, 0, lines,
        {"action": "status", "count": len(scopes), "phase_counts": counts,
         "scopes": [{"scope_id": s.get("scope_id"), "projection": _projection(s)} for s in scopes]},
    )


def _cmd_show(args: argparse.Namespace) -> int:
    """Show one Scope: the canon-labelled fields + its projection + readiness."""
    try:
        scope = _load_scope(Path(args.root), args.scope_id)
    except (FileNotFoundError, ValueError) as exc:
        return _emit(args, 2, [f"{_BRAND} · {exc}"], {"error": str(exc)})
    proj = _projection(scope)
    ready, reasons = coordination.scope_is_ready(scope)
    lines = [
        _card_line(scope),
        f"    Goal (intent):        {scope.get('intent')}",
        f"    Done-when (criteria): {scope.get('acceptance_criteria') or '—'}",
        f"    Budget (appetite):    {scope.get('appetite') or '—'}",
        f"    Change-type (class):  {scope.get('mutation_class')}",
        f"    Stage / state / board: {proj['phase']} / {proj['state']} / {proj['board']}",
        f"    Ready: {'yes' if ready else 'no — ' + '; '.join(reasons)}"
        f" · bet placed: {'yes' if coordination.is_ratified(scope) else 'no'}",
    ]
    return _emit(
        args, 0, lines,
        {"action": "show", "scope_id": scope.get("scope_id"), "scope": scope,
         "projection": proj, "ready": ready, "reasons": reasons,
         "ratified": coordination.is_ratified(scope)},
    )


def _cmd_artifacts(args: argparse.Namespace) -> int:
    """Enumerate the on-disk artifacts for a Scope (the ◆ Report enriches this at G-7.3)."""
    root = Path(args.root)
    path = _scope_path(root, args.scope_id)
    if not path.is_file():
        return _emit(
            args, 2,
            [f"{_BRAND} · no Scope {args.scope_id!r} under {_scopes_dir(root)}"],
            {"error": "not_found"},
        )
    artifacts = [{"kind": "scope", "path": str(path), "inspect": f"cev3 show {args.scope_id}"}]
    lines = [f"{_BRAND} · artifacts for Scope {args.scope_id!r}:"]
    lines += [f"    {a['kind']:>10}  {a['path']}   ({a['inspect']})" for a in artifacts]
    lines.append(f"{_BRAND} · (run artifacts — PR / evidence / spend — land with the live drive seam)")
    return _emit(args, 0, lines, {"action": "artifacts", "scope_id": args.scope_id, "artifacts": artifacts})


def _cmd_shape(args: argparse.Namespace) -> int:
    """Run the Frame→Shape grill-me over a partial draft (gaps + minimum questions).

    The agent drafts every field EXCEPT the Budget (human-only). Surfaces the
    gap-aware Scope card, the minimum questions to close, and (with --persona +
    --signal) the detect-and-offer decision. A pure dialogue helper — it does not
    write a Scope artifact (that is `cev3 scope` once the gaps are closed).
    """
    draft: dict[str, Any] = {"scope_id": args.scope_id}
    if args.goal:
        draft["intent"] = args.goal
    if args.done_when:
        draft["acceptance_criteria"] = list(args.done_when)
    if args.change_type:
        draft["mutation_class"] = args.change_type
    # NB: Budget (appetite) is intentionally NOT drafted — it is human-only.
    result = v3_shaping.shape(draft)
    lines = [result.card]
    if result.gaps:
        lines.append(f"{_BRAND} · to reach Ready, close {len(result.gaps)} gap(s):")
        for g in result.gaps:
            who = "  (your call — Budget is yours to set)" if g.human_only else ""
            lines.append(f"    - {g.label}: {g.question}{who}")
    else:
        lines.append(f"{_BRAND} · Ready — place the bet with `cev3 ratify {args.scope_id}`")
    offer = None
    if args.persona and args.signal:
        # pass the actual change-type (None when not yet proposed) so the dial
        # biases conservative for an unknown class, per shaping-ux.md.
        offer = v3_shaping.should_offer(args.persona, args.change_type, args.signal)
        thr = v3_shaping.offer_threshold(args.persona, args.change_type)
        band = v3_shaping.risk_class(args.change_type)
        verb = "WOULD offer to crystallize this into a Scope" if offer else "holds (free chat — Frame)"
        lines.append(
            f"{_BRAND} · detect-and-offer [{args.persona}/{band}-risk · signal {args.signal} · needs {thr}]: {verb}"
        )
    return _emit(args, 0, lines, {
        "action": "shape", "scope_id": args.scope_id, "ready": result.ready,
        "gaps": [{"field": g.field, "label": g.label, "human_only": g.human_only} for g in result.gaps],
        "questions": list(result.questions), "offer": offer,
    })


def _cmd_session(args: argparse.Namespace) -> int:
    """The governed session frame + the unified context/spend status line (G-7.1).

    The context-% is the harness's authoritative number (CONSUMED via
    ``--context-pct``; the live per-turn tap is the deferred seam). The spend
    meter folds the REAL G-5 ``project_spend`` projection over an evidence spine
    (``--spine``) against the run cap (``--cap``); absent those it is unmetered.
    """
    counts = _phase_counts(_iter_scopes(Path(args.root)))
    context = v3_session.context_meter(args.context_pct)
    if args.spine and args.cap is not None:
        records = yaml.safe_load(Path(args.spine).read_text(encoding="utf-8"))
        if isinstance(records, dict):
            records = records.get("records") or records.get("leaves") or []
        spend = v3_session.spend_meter_from_spine(
            records or [], args.cap, scope="run", unit=args.unit, run_id=args.run_id
        )
    else:
        spend = v3_session.spend_meter(None, None, args.unit)
    lines = v3_session.render_session(
        counts, context=context, spend=spend, at_boundary=not args.mid_output,
        repo=args.repo, transport=args.transport, backend=args.backend, root=args.root,
    )
    return _emit(
        args, 0, lines,
        {"action": "session", "root": args.root, "phase_counts": counts,
         "context": {"pct": context.pct, "state": context.state},
         "spend": {"state": spend.state, "ratio": spend.ratio,
                   "spent": v3_session.fmt_amount(spend.spent) if spend.spent is not None else None,
                   "cap": v3_session.fmt_amount(spend.cap) if spend.cap is not None else None,
                   "unit": spend.unit}},
    )


# ---------------------------------------------------------------------------
# Parser + entry point
# ---------------------------------------------------------------------------
def _add_root(p: argparse.ArgumentParser) -> None:
    p.add_argument(
        "--root", default=V3_LOCAL_STATE_ROOT,
        help=f"v3 local-state root (default: {V3_LOCAL_STATE_ROOT})",
    )
    p.add_argument("--json", action="store_true", dest="json_output", help="emit machine-readable JSON")


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="cev3",
        description="Creator Engine v3 — file, ratify, and drive work as a governed Scope "
        "(Frame → Shape → Build → Review → Ship).",
    )
    sub = parser.add_subparsers(dest="command")

    p_scope = sub.add_parser("scope", help="file a Scope (Goal/Done-when/Budget/Change-type)")
    p_scope.add_argument("scope_id", metavar="ID", help="stable Scope slug")
    p_scope.add_argument("--goal", required=True, help="Goal (the intent / framed problem)")
    p_scope.add_argument("--done-when", action="append", default=[], metavar="CRITERION",
                         help="a Done-when acceptance criterion (repeatable)")
    p_scope.add_argument("--budget", type=float, default=None, help="Budget amount (a fixed cap, not an estimate)")
    p_scope.add_argument("--budget-unit", choices=["$", "%"], default="$",
                         help="Budget unit: $ = API-USD, %% = single-seat meter")
    p_scope.add_argument("--budget-window", choices=["per_run", "rolling_5h", "rolling_weekly", "total"],
                         default=None, help="optional Budget accounting window")
    p_scope.add_argument("--change-type", required=True, choices=sorted(coordination.MUTATION_CLASSES),
                         help="Change-type (the mutation_class risk tier)")
    p_scope.add_argument("--note", default=None, help="optional advisory note (no secrets)")
    _add_root(p_scope)

    p_ratify = sub.add_parser("ratify", help="place the bet on a Ready Scope (human-only front gate)")
    p_ratify.add_argument("scope_id", metavar="ID", help="the Scope to ratify")
    p_ratify.add_argument("--approver-ref", required=True, metavar="HEX64",
                          help="value-free 64-hex opaque ratifier digest (never a raw account)")
    _add_root(p_ratify)

    p_drive = sub.add_parser("drive", help="assemble the governed dispatch (front gate; live spawn deferred)")
    p_drive.add_argument("scope_id", metavar="ID", help="the Scope to drive")
    p_drive.add_argument("--policy", default=None, help="optional runtime-policy YAML to merge the run envelope into")
    _add_root(p_drive)

    p_status = sub.add_parser("status", help="list Scopes by projected stage")
    _add_root(p_status)

    p_show = sub.add_parser("show", help="show one Scope (canon labels + projection)")
    p_show.add_argument("scope_id", metavar="ID", help="the Scope to show")
    _add_root(p_show)

    p_art = sub.add_parser("artifacts", help="enumerate a Scope's artifacts")
    p_art.add_argument("scope_id", metavar="ID", help="the Scope whose artifacts to list")
    _add_root(p_art)

    p_shape = sub.add_parser("shape", help="run the Frame→Shape grill-me on a partial draft (gaps + questions)")
    p_shape.add_argument("scope_id", metavar="ID", help="working Scope slug")
    p_shape.add_argument("--goal", default=None, help="Goal (intent) — agent-draftable")
    p_shape.add_argument("--done-when", action="append", default=[], metavar="CRITERION",
                         help="a Done-when criterion (repeatable) — agent-draftable")
    p_shape.add_argument("--change-type", default=None, choices=sorted(coordination.MUTATION_CLASSES),
                         help="proposed Change-type (mutation_class) — agent proposes; human tightens free")
    p_shape.add_argument("--persona", default=None, choices=["dev", "ceo"],
                         help="persona for the detect-and-offer dial")
    p_shape.add_argument("--signal", default=None, choices=list(v3_shaping.SIGNAL_ORDER),
                         help="detected intent-to-act signal strength (for the dial)")
    p_shape.add_argument("--json", action="store_true", dest="json_output", help="emit machine-readable JSON")

    p_session = sub.add_parser("session", help="launch the governed session frame + status line")
    p_session.add_argument("--context-pct", type=float, default=None,
                           help="the harness's authoritative context-window %% (consumed, never recomputed)")
    p_session.add_argument("--spine", default=None, help="runtime-evidence chain YAML to fold the G-5 spend projection over")
    p_session.add_argument("--cap", type=float, default=None, help="the run spend cap to meter against")
    p_session.add_argument("--unit", choices=["$", "%"], default="$", help="spend unit ($=API / %%=seat)")
    p_session.add_argument("--run-id", default=None, help="restrict the spend fold to this run_id")
    p_session.add_argument("--mid-output", action="store_true",
                           help="suppress boundary-only nudges (we are mid-output, not at a turn boundary)")
    p_session.add_argument("--repo", default="—", help="repo label for the banner")
    p_session.add_argument("--transport", default="—", help="transport label for the banner")
    p_session.add_argument("--backend", default="—", help="runtime backend label for the banner")
    _add_root(p_session)

    return parser


_DISPATCH = {
    "scope": _cmd_scope,
    "shape": _cmd_shape,
    "ratify": _cmd_ratify,
    "drive": _cmd_drive,
    "status": _cmd_status,
    "show": _cmd_show,
    "artifacts": _cmd_artifacts,
    "session": _cmd_session,
}


def main(argv: Sequence[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    command = args.command or "session"
    handler = _DISPATCH.get(command)
    if handler is None:  # pragma: no cover - argparse guards the choices
        parser.print_help()
        return 2
    return handler(args)


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
