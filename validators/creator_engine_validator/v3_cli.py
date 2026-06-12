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

USER-FACING NAME (Operator-ratified design-lane directive, 2026-06-08):
``cev3`` is the INTERNAL console_script name — it exists ONLY to avoid the v1
``ce`` collision in this coexistence monorepo; users never type it. The
USER-FACING command is ``ce`` (``CE_CMD``): the pilot installs v3 ONLY (no v1
``ce`` to collide with), so the 7E installer exposes this CLI AS ``ce``, and all
user-facing output + help here speaks ``ce`` (the docs are the user-facing truth).
A version-stamped user command (``cev3``/``cev4``) is the anti-pattern this avoids.

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
import os
import re
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence

import yaml

from . import (
    coordination,
    evidence_sink,
    runtime_evidence_spine,
    v3_forge_join,
    v3_installer,
    v3_report,
    v3_seat_bridge,
    v3_session,
    v3_shaping,
    version,
)
from ._versions import V3_LOCAL_STATE_ROOT
from .forge.github_repo_config import ForgeConfigError
from .runner import usage_tap
from .runner.backend import CollectedEvidence
from .schema import validate_with_schema

#: Where Scope artifacts live, relative to the local-state ``--root``.
SCOPES_SUBDIR = "scopes"
_SCOPE_SUFFIX = ".scope.yaml"
ESCALATIONS_SUBDIR = "escalations"
_ESCALATION_SCHEMA = "schemas/escalation-record.schema.yaml"

#: The conserved Scope-record envelope constants (``schemas/scope.schema.yaml``).
_KIND = "scope-record"
_RECORD_TYPE = "scope"
_SCHEMA_VERSION = "1"

#: Scope-id slug (mirrors ``schemas/scope.schema.yaml``'s ``scope_id`` pattern).
_SCOPE_ID_RE = re.compile(r"^[a-z][a-z0-9-]{2,63}$")
_ESCALATION_ID_RE = re.compile(r"(^[a-z][a-z0-9-]{2,63}$)|(^[0-9a-f]{64}$)")
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

#: The USER-FACING command name (Operator-ratified directive). Users type ``ce``
#: (the pilot installs v3-only; the 7E installer exposes this CLI as ``ce``). The
#: internal console_script is ``cev3`` (monorepo coexistence only) — never shown.
CE_CMD = "ce"

#: In-product help — the SEED of the in-product guide (content reused from
#: ``docs/guide/understanding-ce.md``, not re-authored). ``ce guide`` prints it.
_GUIDE = """\
◆ Creator Engine — your own coding agent, under governance.

CE wraps a structured, stateful, artifact-aware workflow around the agent you
already use, so real work is planned, tracked, checked, and merged on purpose.
The thing that decides whether work is good lives OUTSIDE the agent — you judge
artifacts (a plan, a diff, the evidence, the PR), not a transcript.

The five stages — Frame → Shape → Build → Review → Ship:
  Frame    understand the problem (just thinking; nothing tracked yet)
  Shape    turn it into a bet — a Scope (Goal · Done-when · Budget · Change-type)
  Build    the agent does the work in one governed, sandboxed run
  Review   the result is graded against your Done-when — with evidence, not vibes
  Ship     the governed finish: a merged PR, delivered research, or a reasoned no-change

The Scope card (your unit of work):
  Goal         what you're trying to do
  Done-when    the checks that say it's finished (these get graded)
  Budget       a fixed cap you commit — not a time estimate (YOUR call to set)
  Change-type  what kind of change, and how risky
  Ready        a ✓ once the other four are valid — then you place the bet

A few things worth knowing:
  • You set the Budget. The agent never decides how much you'll spend.
  • The agent can make a change safer on its own, but only you can make it riskier.
  • Nothing is tracked until you say yes. Plain chat stays plain chat.

Commands:  ce session · ce scope · ce shape · ce ratify · ce drive · ce report
           ce status · ce show · ce artifacts · ce onboard · ce guide

These friendly words are a clear skin over a precise state machine — you can
always look underneath. Full guide: docs/guide/understanding-ce.md ; pilot path:
docs/guide/pilot-runbook.md.
"""


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
def _projection(scope: dict[str, Any], root: Path | None = None) -> dict[str, str]:
    """The {state, phase, board} projection over the conserved spec-lifecycle.

    v3.1-G1b: when ``root`` is given and an UNcollected dispatch record exists for
    the Scope, the projection feeds ``dispatched=True`` so a live run is visible
    (→ in_progress / Build / RUN) — the read-model sees the spawned seat. A
    collected dispatch no longer drives the signal (the run has folded its
    evidence; the Scope projects off its own committed state again).
    """
    dispatched = False
    scope_id = scope.get("scope_id")
    if root is not None and scope_id:
        dispatched = _has_uncollected_dispatch(root, str(scope_id))
    return coordination.project_scope_state(scope, dispatched=dispatched)


def _card_line(scope: dict[str, Any], root: Path | None = None) -> str:
    """One-line Scope card in the canon vocabulary (the skin over the fields)."""
    proj = _projection(scope, root)
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


def _phase_counts(scopes: list[dict[str, Any]], root: Path | None = None) -> dict[str, int]:
    counts = {phase: 0 for phase in coordination.COGNITIVE_PHASES}
    for s in scopes:
        counts[_projection(s, root)["phase"]] += 1
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
    if getattr(args, "spawn", False):
        return _drive_spawn(args, root, result, envelopes)
    lines = [
        f"{_BRAND} · BUILD dispatch assembled for Scope {result.scope_id!r} "
        f"(class {result.mutation_class})",
        f"    spend_envelopes: {json.dumps(envelopes, sort_keys=True)}",
        f"{_BRAND} · (assemble-only — pass --spawn to launch the governed seat)",
    ]
    return _emit(
        args, 0, lines,
        {"action": "dispatch_assembled", "scope_id": result.scope_id,
         "mutation_class": result.mutation_class, "runtime_policy": result.runtime_policy,
         "live_spawn": "available_via_--spawn"},
    )


def _drive_spawn(
    args: argparse.Namespace,
    root: Path,
    plan: coordination.DispatchPlan,
    envelopes: list[Any],
) -> int:
    """`--spawn`: materialize the dispatch → spawn the governed seat → seed the brief.

    The front gate already held (caller has a DispatchPlan). Scoped to the
    ``claude`` harness (defect-c declared OUT; codex is the G1-codex follow-up).
    The subprocess seams live in ``v3_seat_bridge`` (faked in CI).
    """
    if args.harness != v3_seat_bridge.BRIDGE_HARNESS:
        return _emit(
            args, 2,
            [f"{_BRAND} · drive --spawn refused: harness {args.harness!r} is not bridged "
             f"(only {v3_seat_bridge.BRIDGE_HARNESS!r}); codex drive-spawn is the G1-codex follow-up"],
            {"action": "spawn_refused", "reason": "harness_not_supported",
             "harness": args.harness, "followup": "G1-codex"},
        )
    unattended = not args.no_unattended
    record = v3_seat_bridge.materialize_dispatch(plan, root, unattended=unattended)
    try:
        spawn = v3_seat_bridge.spawn_seat(record)
        v3_seat_bridge.seed_brief(record)
    except v3_seat_bridge.SeatBridgeError as exc:
        # Fail-closed: the dispatch was materialized before the v1 launch leg, so a
        # refused spawn would otherwise sit on disk with terminal/spawned_at unset —
        # which the read-model would have mistaken for a live Build/RUN run. Stamp
        # the failure (value-free) so it projects as neither pending nor live; the
        # attempt is conserved, not deleted.
        v3_seat_bridge.mark_spawn_failed(record, exc)
        return _emit(
            args, 1,
            [f"{_BRAND} · drive --spawn refused: {exc}"],
            {"action": "spawn_refused", "reason": "launch_refused",
             "run_id": record.run_id, "detail": str(exc),
             "dispatch_path": str(record.dispatch_path)},
        )
    pane = spawn.terminal.get("pane_id")
    lines = [
        f"{_BRAND} · SPAWNED governed seat for Scope {plan.scope_id!r} "
        f"(class {plan.mutation_class}, run {record.run_id})",
        f"    spend_envelopes: {json.dumps(envelopes, sort_keys=True)}",
        f"    dispatch: {record.dispatch_path}",
        f"    pane: {pane}"
        + ("  [unattended]" if unattended else "  [interactive]"),
    ]
    return _emit(
        args, 0, lines,
        {"action": "spawned", "scope_id": plan.scope_id, "run_id": record.run_id,
         "mutation_class": plan.mutation_class, "unattended": unattended,
         "dispatch_path": str(record.dispatch_path), "pane_id": pane,
         "terminal": spawn.terminal, "resource_bound": spawn.resource_bound},
    )


# ---------------------------------------------------------------------------
# Dispatch-record storage seam + run evidence (G1b — .ce/state/dispatches, runs)
# ---------------------------------------------------------------------------
DISPATCHES_SUBDIR = "dispatches"
RUNS_SUBDIR = "runs"


def _dispatch_path(root: Path, run_id: str) -> Path:
    return root / DISPATCHES_SUBDIR / run_id / "dispatch.yaml"


def _run_evidence_path(root: Path, run_id: str) -> Path:
    return root / RUNS_SUBDIR / f"{run_id}.runtime-evidence.yaml"


def _load_dispatch(root: Path, run_id: str) -> dict[str, Any]:
    path = _dispatch_path(root, run_id)
    if not path.is_file():
        raise FileNotFoundError(f"no dispatch record for run {run_id!r} under {root / DISPATCHES_SUBDIR}")
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"malformed dispatch record at {path}")
    return data


def _find_dispatch_for_scope(root: Path, scope_id: str) -> dict[str, Any] | None:
    """The newest dispatch record for ``scope_id`` (run_id sorts lexically by utcstamp), or None."""
    ddir = root / DISPATCHES_SUBDIR
    if not ddir.is_dir():
        return None
    found: list[dict[str, Any]] = []
    for child in sorted(ddir.iterdir()):
        drec = child / "dispatch.yaml"
        if not drec.is_file():
            continue
        data = yaml.safe_load(drec.read_text(encoding="utf-8"))
        if isinstance(data, dict) and data.get("scope_id") == scope_id:
            found.append(data)
    if not found:
        return None
    return sorted(found, key=lambda d: str(d.get("run_id")))[-1]


def _has_uncollected_dispatch(root: Path, scope_id: str) -> bool:
    """True iff a LIVE dispatched run exists for ``scope_id`` (drives Build/RUN).

    A dispatch projects Build/RUN ONLY when it was ACTUALLY spawned (``spawned_at``
    / ``terminal`` stamped) and is neither collected nor spawn-failure-stamped. A
    materialized-but-refused/half spawn (terminal/spawned_at unset, or
    ``spawn_failed_at`` set) is NOT a live run — fail-closed, so a stale dispatch is
    never mistaken for an active one.
    """
    drec = _find_dispatch_for_scope(root, scope_id)
    if not drec:
        return False
    spawned = bool(drec.get("spawned_at") or drec.get("terminal"))
    return bool(spawned and not drec.get("collected_at") and not drec.get("spawn_failed_at"))


def _collected_run_evidence(root: Path, scope_id: str) -> Path | None:
    """The evidence chain path of ``scope_id``'s newest COLLECTED dispatch, if any."""
    drec = _find_dispatch_for_scope(root, scope_id)
    if not drec or not drec.get("collected_at"):
        return None
    chain = _run_evidence_path(root, str(drec.get("run_id")))
    return chain if chain.is_file() else None


def _forge_surface_for_scope(root: Path, scope_id: str) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
    """The newest author ``change`` block + the newest live reviewer dispatch for a Scope (G2c).

    Returns ``(change_block, review_dispatch)`` — either may be ``None``. The author change block is
    the value-free PR pointer a ``cev3 pr --apply`` stamped; the review dispatch is a ``role:
    reviewer`` dispatch that was spawned and not failure-stamped (a LIVE venue).
    """
    ddir = root / DISPATCHES_SUBDIR
    if not ddir.is_dir():
        return None, None
    authors: list[dict[str, Any]] = []
    reviews: list[dict[str, Any]] = []
    for child in sorted(ddir.iterdir()):
        drec = child / "dispatch.yaml"
        if not drec.is_file():
            continue
        data = yaml.safe_load(drec.read_text(encoding="utf-8"))
        if not isinstance(data, dict) or data.get("scope_id") != scope_id:
            continue
        if data.get("role") == "reviewer":
            if data.get("spawned_at") and not data.get("spawn_failed_at"):
                reviews.append(data)
        elif data.get("change"):
            authors.append(data)
    change_block = (
        sorted(authors, key=lambda d: str(d.get("run_id")))[-1].get("change") if authors else None
    )
    review = sorted(reviews, key=lambda d: str(d.get("run_id")))[-1] if reviews else None
    return change_block, review


def _resolve_run_evidence(args: argparse.Namespace, root: Path) -> tuple[str | None, str | None]:
    """Resolve (evidence-path, run_id) for report/artifacts.

    An explicit ``--evidence`` always wins; otherwise, when the Scope has a
    COLLECTED dispatch, default to its persisted chain
    (``<root>/runs/<run_id>.runtime-evidence.yaml``) so the read-model surfaces a
    finished run with zero extra flags.
    """
    evidence = getattr(args, "evidence", None)
    run_id = getattr(args, "run_id", None)
    if not evidence:
        drec = _find_dispatch_for_scope(root, args.scope_id)
        if drec and drec.get("collected_at"):
            chain = _run_evidence_path(root, str(drec.get("run_id")))
            if chain.is_file():
                evidence = str(chain)
                run_id = run_id or str(drec.get("run_id"))
    return evidence, run_id


def _policy_sha(policy: dict[str, Any]) -> str:
    """The 64-hex policy binding for the run's records.

    Delegates to the canonical derivation (``v3_forge_join.policy_sha``) so the ``cev3 collect``
    fold and the ``cev3 pr`` forge-join bind a run's records under the SAME policy digest — the
    derivation lives in exactly one place (extracted, not duplicated).
    """
    return v3_forge_join.policy_sha(policy)


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class EscalationSyncRefused(Exception):
    """Fail-closed refusal for `ce escalation sync`."""


def _escalations_dir(root: Path) -> Path:
    return root / ESCALATIONS_SUBDIR


def _escalation_path(root: Path, escalation_id: str) -> Path:
    return _escalations_dir(root) / f"{escalation_id}.yaml"


def _escalation_bytes(record: dict[str, Any]) -> str:
    return yaml.safe_dump(record, sort_keys=True, default_flow_style=False)


def _escalation_schema_errors(record: dict[str, Any], path: Path) -> list[str]:
    return [
        e.format()
        for e in validate_with_schema(
            record,
            _ESCALATION_SCHEMA,
            path,
            code="VAL-ESCALATION-RECORD-SCHEMA",
            contract=_ESCALATION_SCHEMA,
        )
    ]


def _write_escalation(root: Path, record: dict[str, Any]) -> Path:
    path = _escalation_path(root, str(record["escalation_id"]))
    _escalations_dir(root).mkdir(parents=True, exist_ok=True)
    path.write_text(_escalation_bytes(record), encoding="utf-8")
    return path


def _load_escalation(root: Path, escalation_id: str) -> dict[str, Any]:
    path = _escalation_path(root, escalation_id)
    if not path.is_file():
        raise FileNotFoundError(f"no escalation {escalation_id!r} under {_escalations_dir(root)}")
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or data.get("kind") != "escalation-record":
        raise ValueError(f"malformed escalation record at {path}")
    return data


def _iter_escalations(root: Path) -> list[dict[str, Any]]:
    d = _escalations_dir(root)
    if not d.is_dir():
        return []
    out: list[dict[str, Any]] = []
    for path in sorted(d.glob("*.yaml")):
        try:
            data = yaml.safe_load(path.read_text(encoding="utf-8"))
        except (OSError, yaml.YAMLError):
            continue
        if isinstance(data, dict) and data.get("kind") == "escalation-record":
            out.append(data)
    return out


def _require_valid_escalation_id(args: argparse.Namespace, escalation_id: str) -> int | None:
    if _ESCALATION_ID_RE.match(escalation_id or ""):
        return None
    return _emit(
        args,
        2,
        [f"{_BRAND} · escalation refused: id must be a slug or 64-hex digest"],
        {"error": "invalid_escalation_id"},
    )


def _cmd_escalation_open(args: argparse.Namespace) -> int:
    root = Path(args.root)
    invalid = _require_valid_escalation_id(args, args.escalation_id)
    if invalid is not None:
        return invalid
    path = _escalation_path(root, args.escalation_id)
    if path.exists():
        return _emit(
            args,
            2,
            [f"{_BRAND} · escalation open refused: {args.escalation_id!r} already exists"],
            {"error": "duplicate_escalation_id", "path": str(path)},
        )
    record: dict[str, Any] = {
        "kind": "escalation-record",
        "record_type": "escalation",
        "schema_version": "1",
        "escalation_id": args.escalation_id,
        "title": args.title,
        "decision_needed": args.decision,
        "recommendation": args.recommend,
        "created_at": _utc_now_iso(),
    }
    if args.source_ref:
        record["source_ref"] = args.source_ref
    errors = _escalation_schema_errors(record, path)
    if errors:
        return _emit(
            args,
            2,
            [f"{_BRAND} · escalation open refused: schema-invalid", *errors],
            {"error": "schema_invalid", "detail": errors},
        )
    written = _write_escalation(root, record)
    return _emit(
        args,
        0,
        [f"{_BRAND} · opened AWAITING-OPERATOR escalation {args.escalation_id!r} → {written}"],
        {"action": "escalation_opened", "escalation_id": args.escalation_id, "path": str(written)},
    )


def _cmd_escalation_resolve(args: argparse.Namespace) -> int:
    root = Path(args.root)
    invalid = _require_valid_escalation_id(args, args.escalation_id)
    if invalid is not None:
        return invalid
    try:
        record = _load_escalation(root, args.escalation_id)
    except (FileNotFoundError, ValueError) as exc:
        return _emit(args, 2, [f"{_BRAND} · escalation resolve refused: {exc}"], {"error": str(exc)})
    record["resolved_at"] = _utc_now_iso()
    if args.resolution:
        record["resolution"] = args.resolution
    path = _escalation_path(root, args.escalation_id)
    errors = _escalation_schema_errors(record, path)
    if errors:
        return _emit(
            args,
            2,
            [f"{_BRAND} · escalation resolve refused: schema-invalid", *errors],
            {"error": "schema_invalid", "detail": errors},
        )
    written = _write_escalation(root, record)
    return _emit(
        args,
        0,
        [f"{_BRAND} · resolved escalation {args.escalation_id!r} → {written}"],
        {"action": "escalation_resolved", "escalation_id": args.escalation_id, "path": str(written)},
    )


def _extract_issue_field(body: Any, *labels: str) -> str | None:
    text = str(body or "")
    wanted = {label.lower().replace("_", " ") for label in labels}
    for line in text.splitlines():
        clean = line.strip().strip("*").strip()
        if ":" not in clean:
            continue
        name, value = clean.split(":", 1)
        normalized = name.strip().lower().replace("_", " ")
        if normalized in wanted and value.strip():
            return value.strip()
    return None


def _issue_escalation_id(issue: dict[str, Any]) -> str:
    number = issue.get("number")
    if isinstance(number, int) or (isinstance(number, str) and number.isdigit()):
        return f"awaiting-operator-{number}"
    source = str(issue.get("url") or issue.get("title") or "awaiting-operator")
    return hashlib.sha256(source.encode("utf-8")).hexdigest()


def _project_issue_to_escalation(
    issue: dict[str, Any],
    *,
    existing_by_source: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    source_ref = str(issue.get("url") or "")
    if not source_ref:
        raise EscalationSyncRefused("gh issue payload missing url")
    title = str(issue.get("title") or "").strip()
    created_at = str(issue.get("createdAt") or "").strip()
    if not title or not created_at:
        raise EscalationSyncRefused(f"gh issue payload for {source_ref} missing title/createdAt")
    decision = _extract_issue_field(issue.get("body"), "decision needed", "decision_needed", "decision")
    recommendation = _extract_issue_field(issue.get("body"), "recommendation", "recommended")
    if not decision or not recommendation:
        raise EscalationSyncRefused(
            f"gh issue {source_ref} must contain 'Decision needed:' and 'Recommendation:' lines"
        )

    existing = existing_by_source.get(source_ref) or {}
    record = {
        "kind": "escalation-record",
        "record_type": "escalation",
        "schema_version": "1",
        "escalation_id": existing.get("escalation_id") or _issue_escalation_id(issue),
        "title": title,
        "decision_needed": decision,
        "recommendation": recommendation,
        "created_at": created_at,
        "source_ref": source_ref,
    }
    state = str(issue.get("state") or "").lower()
    if state == "closed":
        closed_at = str(issue.get("closedAt") or "").strip()
        if not closed_at:
            raise EscalationSyncRefused(f"closed gh issue {source_ref} missing closedAt")
        record["resolved_at"] = closed_at
        record["resolution"] = "closed on forge"
    return record


def project_escalation_sync(
    issues: list[Any],
    existing: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """PURE gh-issue JSON payload -> escalation-record bodies."""
    existing_by_source = {
        str(record.get("source_ref")): record
        for record in existing
        if isinstance(record, Mapping) and record.get("source_ref")
    }
    planned: dict[str, dict[str, Any]] = {}
    for issue in issues:
        if not isinstance(issue, dict):
            raise EscalationSyncRefused("gh issue payload must be a list of objects")
        record = _project_issue_to_escalation(issue, existing_by_source=existing_by_source)
        planned[str(record["source_ref"])] = record
    return [planned[k] for k in sorted(planned)]


def _load_gh_issues(
    repo: str,
    label: str,
    *,
    runner: Any | None = None,
) -> list[Any]:
    if runner is None:
        runner = subprocess.run
    argv = [
        "gh",
        "issue",
        "list",
        "--repo",
        repo,
        "--label",
        label,
        "--state",
        "all",
        "--json",
        "number,title,url,body,createdAt,closedAt,state",
    ]
    completed = runner(argv, capture_output=True, text=True)
    if getattr(completed, "returncode", 1) != 0:
        stderr = getattr(completed, "stderr", "") or ""
        raise EscalationSyncRefused(stderr.strip() or "gh issue list failed")
    try:
        payload = json.loads(getattr(completed, "stdout", "") or "")
    except (TypeError, json.JSONDecodeError) as exc:
        raise EscalationSyncRefused(f"gh issue list returned unparsable JSON: {exc}") from exc
    if not isinstance(payload, list):
        raise EscalationSyncRefused("gh issue list JSON must be a list")
    return payload


def _cmd_escalation_sync(args: argparse.Namespace) -> int:
    root = Path(args.root)
    try:
        payload = _load_gh_issues(args.repo, args.label)
        planned = project_escalation_sync(payload, _iter_escalations(root))
    except EscalationSyncRefused as exc:
        return _emit(
            args,
            1,
            [f"{_BRAND} · escalation sync REFUSED: {exc}"],
            {"error": "sync_refused", "detail": str(exc), "written": 0},
        )

    all_errors: list[str] = []
    for record in planned:
        all_errors.extend(_escalation_schema_errors(record, _escalation_path(root, str(record["escalation_id"]))))
    if all_errors:
        return _emit(
            args,
            1,
            [f"{_BRAND} · escalation sync REFUSED: schema-invalid payload", *all_errors],
            {"error": "schema_invalid", "detail": all_errors, "written": 0},
        )

    written = [_write_escalation(root, record) for record in planned]
    return _emit(
        args,
        0,
        [f"{_BRAND} · synced {len(written)} escalation record(s) from {args.repo} label {args.label!r}"],
        {"action": "escalation_synced", "count": len(written), "paths": [str(p) for p in written]},
    )


def _cmd_escalation(args: argparse.Namespace) -> int:
    if args.escalation_command == "open":
        return _cmd_escalation_open(args)
    if args.escalation_command == "resolve":
        return _cmd_escalation_resolve(args)
    if args.escalation_command == "sync":
        return _cmd_escalation_sync(args)
    return 2


# ---------------------------------------------------------------------------
# notify — the v3.1-B.8 Operator-notify feed (once | watch | status)
# ---------------------------------------------------------------------------
def _notify_sync_tick(
    root: Path, repo: str, label: str, *, runner: Any | None = None
) -> dict[str, Any]:
    """Mirror forge awaiting-operator issues into local records BEFORE the fold (reuse).

    Cross-host fan-in (Fork 4): the existing ``_load_gh_issues`` + pure
    ``project_escalation_sync`` legs, run each poll tick. **Tolerant** — forge
    downtime must never block local alerting, so a refusal is returned (logged by the
    caller) and the fold over local records proceeds.
    """
    try:
        payload = _load_gh_issues(repo, label, runner=runner)
        planned = project_escalation_sync(payload, _iter_escalations(root))
    except EscalationSyncRefused as exc:
        return {"ok": False, "error": str(exc), "written": 0}
    written = 0
    for record in planned:
        errs = _escalation_schema_errors(record, _escalation_path(root, str(record["escalation_id"])))
        if errs:
            continue
        _write_escalation(root, record)
        written += 1
    return {"ok": True, "written": written}


def _cmd_notify_once(args: argparse.Namespace, *, runner: Any | None = None) -> int:
    from .runner import notify_feed

    root = Path(args.root)
    sync_note: dict[str, Any] | None = None
    if getattr(args, "sync_repo", None):
        sync_note = _notify_sync_tick(root, args.sync_repo, args.sync_label, runner=runner)
    try:
        summary = notify_feed.run_once(root, runner=runner)
    except notify_feed.NotifyConfigError as exc:
        return _emit(
            args, 2,
            [f"{_BRAND} · notify once REFUSED: malformed notify config — {exc}"],
            {"error": "notify_config_invalid", "detail": str(exc)},
        )
    lines = [
        f"{_BRAND} · notify once — dispatched {summary['dispatched']} "
        f"({summary['ok']} ok · {summary['failed']} failed) over sinks "
        f"{', '.join(summary['sinks']) or '—'}"
    ]
    payload: dict[str, Any] = {"action": "notify_once", **summary}
    if sync_note is not None:
        state = "ok" if sync_note["ok"] else f"FAILED (tolerated): {sync_note.get('error')}"
        lines.append(f"    sync · {args.sync_repo} {state} ({sync_note.get('written', 0)} mirrored)")
        payload["sync"] = sync_note
    return _emit(args, 0, lines, payload)


def _cmd_notify_status(args: argparse.Namespace) -> int:
    from .runner import notify_feed

    root = Path(args.root)
    try:
        config = notify_feed.load_config(root)
    except notify_feed.NotifyConfigError as exc:
        return _emit(
            args, 2,
            [f"{_BRAND} · notify status REFUSED: malformed notify config — {exc}"],
            {"error": "notify_config_invalid", "detail": str(exc)},
        )
    escalations = notify_feed.load_escalations(root) or []
    ledger = notify_feed.load_ledger(root)
    fold = notify_feed.fold_notify_feed(escalations, ledger, config)
    counts = fold["counts"]
    lines = [
        f"{_BRAND} · notify status — open {counts['open_count']} · resolved "
        f"{counts['resolved_count']} · pending entry {counts['pending_entry']} / exit "
        f"{counts['pending_exit']} · delivered {counts['delivered']} · failed {counts['failed']}",
        f"    sinks · {', '.join(fold['sinks']) or '—'}",
    ]
    return _emit(args, 0, lines, {"action": "notify_status", "counts": counts, "sinks": fold["sinks"]})


def _cmd_notify_watch(args: argparse.Namespace, *, runner: Any | None = None) -> int:
    import time

    from .runner import notify_feed

    root = Path(args.root)
    interval = max(1, int(args.interval))
    # Validate the config LOUDLY up front (exit 2) before entering the loop.
    try:
        notify_feed.load_config(root)
    except notify_feed.NotifyConfigError as exc:
        return _emit(
            args, 2,
            [f"{_BRAND} · notify watch REFUSED: malformed notify config — {exc}"],
            {"error": "notify_config_invalid", "detail": str(exc)},
        )
    print(
        f"{_BRAND} · notify watch — root {root} · interval {interval}s · "
        f"sync {args.sync_repo or 'off'} (Ctrl-C to stop)",
        flush=True,
    )
    try:
        while True:
            if getattr(args, "sync_repo", None):
                note = _notify_sync_tick(root, args.sync_repo, args.sync_label, runner=runner)
                if not note["ok"]:
                    print(
                        f"{_BRAND} · notify watch — forge sync FAILED (tolerated, "
                        f"local fold proceeds): {note.get('error')}",
                        flush=True,
                    )
            try:
                summary = notify_feed.run_once(root, runner=runner)
                if summary["dispatched"]:
                    print(
                        f"{_BRAND} · notify watch — dispatched {summary['dispatched']} "
                        f"({summary['failed']} failed)",
                        flush=True,
                    )
            except notify_feed.NotifyConfigError as exc:
                # The daemon must not die on a mid-flight bad edit; surface it loudly.
                print(
                    f"{_BRAND} · notify watch — config became invalid (alerting PAUSED "
                    f"until fixed): {exc}",
                    flush=True,
                )
            time.sleep(interval)
    except KeyboardInterrupt:  # pragma: no cover - interactive stop
        return 0


def _cmd_notify(args: argparse.Namespace) -> int:
    if args.notify_command == "once":
        return _cmd_notify_once(args)
    if args.notify_command == "watch":
        return _cmd_notify_watch(args)
    if args.notify_command == "status":
        return _cmd_notify_status(args)
    return 2


def _claude_config_dir(args: argparse.Namespace) -> Path:
    """Resolve the harness config dir for stamped-id transcript lookup (D6/F9).

    Precedence: ``--claude-config-dir`` → ``$CLAUDE_CONFIG_DIR`` → ``~/.claude``.
    """
    explicit = getattr(args, "claude_config_dir", None)
    if explicit:
        return Path(explicit)
    env = os.environ.get("CLAUDE_CONFIG_DIR")
    return Path(env) if env else Path.home() / ".claude"


def _resolve_collect_transcript(
    args: argparse.Namespace, session_id: Any, run_id: str
) -> tuple[Path | None, str, tuple[int, list[str], dict[str, Any]] | None]:
    """D6/F9 transcript resolution: the dispatch NAMES its transcript, collect never guesses.

    Returns ``(transcript_path | None, transcript_source, refusal | None)`` where ``refusal``
    is an ``(exit_code, lines, payload)`` triple for :func:`_emit`. Resolution order:

    * ``--transcript-override`` given → fold it, ``operator_override`` (the loud salvage hatch);
    * a stamped ``harness_session_id`` present:
        - explicit ``--transcript`` → fold ONLY if its stem equals the stamped id, else REFUSE
          (the #14/#21 mis-fold, machine-blocked);
        - no ``--transcript`` → resolve by EXACT KEY ``<config>/projects/*/<id>.jsonl``: one hit →
          fold (``stamped``); zero or many → REFUSE;
    * no stamped id (pre-F9 record) → today's behavior conserved (optional ``--transcript``),
      ``unstamped``.
    """
    override = getattr(args, "transcript_override", None)
    explicit = getattr(args, "transcript", None)
    sid = str(session_id) if session_id else ""

    def _not_found(path: Path, kind: str) -> tuple[int, list[str], dict[str, Any]]:
        return (
            2,
            [f"{_BRAND} · collect refused: {kind} not found: {path}"],
            {"error": "transcript_not_found", "transcript": str(path)},
        )

    if override:
        tp = Path(override)
        if not tp.is_file():
            return None, "", _not_found(tp, "transcript-override")
        return tp, "operator_override", None

    if sid:
        if explicit:
            tp = Path(explicit)
            if not tp.is_file():
                return None, "", _not_found(tp, "transcript")
            if tp.stem != sid:
                return None, "", (
                    2,
                    [f"{_BRAND} · collect refused: --transcript {tp.name!r} does not match the "
                     f"run's stamped harness session id {sid!r} — refusing the mis-fold "
                     f"(pass --transcript-override to fold a salvaged transcript anyway)"],
                    {"error": "transcript_id_mismatch", "run_id": run_id,
                     "stamped_session_id": sid, "given_stem": tp.stem},
                )
            return tp, "stamped", None
        cfg = _claude_config_dir(args)
        hits = sorted((cfg / "projects").glob(f"*/{sid}.jsonl"))
        if not hits:
            return None, "", (
                2,
                [f"{_BRAND} · collect refused: no harness transcript for stamped session id "
                 f"{sid!r} under {cfg / 'projects'}/*/ — a spawned seat must have a transcript "
                 f"(pass --transcript-override to fold a salvaged one)"],
                {"error": "stamped_transcript_missing", "run_id": run_id,
                 "harness_session_id": sid, "config_dir": str(cfg)},
            )
        if len(hits) > 1:
            return None, "", (
                2,
                [f"{_BRAND} · collect refused: {len(hits)} transcripts match stamped session id "
                 f"{sid!r} — refusing an ambiguous fold (chain integrity over convenience)"],
                {"error": "stamped_transcript_ambiguous", "run_id": run_id,
                 "harness_session_id": sid, "matches": [str(h) for h in hits]},
            )
        return hits[0], "stamped", None

    # pre-F9 record: no stamped id — conserve today's behavior.
    if explicit:
        tp = Path(explicit)
        if not tp.is_file():
            return None, "", _not_found(tp, "transcript")
        return tp, "unstamped", None
    return None, "unstamped", None


def _cmd_collect(args: argparse.Namespace) -> int:
    """Fold a finished seat run into a conserved evidence chain (G1b run→evidence).

    Reads the dispatch record, folds the harness transcript into
    ``runtime_spend_ledger`` leaves (the live per-turn tap stays the declared
    deferred seam — this is post-hoc metering), appends the typed terminal
    ``runtime_run_outcome``, hash-chains them, and persists
    ``<root>/runs/<run_id>.runtime-evidence.yaml`` (refusing to overwrite an
    existing chain). Marks the dispatch ``collected_at``.
    """
    root = Path(args.root)
    run_id = args.run_id
    try:
        dispatch = _load_dispatch(root, run_id)
    except (FileNotFoundError, ValueError) as exc:
        return _emit(args, 2, [f"{_BRAND} · collect refused: {exc}"], {"error": str(exc)})
    if dispatch.get("scope_id") != args.scope_id:
        return _emit(
            args, 2,
            [f"{_BRAND} · collect refused: run {run_id!r} belongs to Scope "
             f"{dispatch.get('scope_id')!r}, not {args.scope_id!r}"],
            {"error": "scope_mismatch", "run_id": run_id,
             "dispatch_scope_id": dispatch.get("scope_id")},
        )
    chain_path = _run_evidence_path(root, run_id)
    if chain_path.exists():
        # Conserved evidence is append-only; never silently re-fold a collected run.
        return _emit(
            args, 2,
            [f"{_BRAND} · collect refused: run {run_id!r} already collected at {chain_path}"],
            {"error": "already_collected", "run_id": run_id, "evidence": str(chain_path)},
        )

    # The merged runtime policy the seat ran under — read AS DATA for the rates + binding.
    policy: dict[str, Any] = {}
    policy_ref = dispatch.get("runtime_policy_ref")
    if policy_ref and Path(policy_ref).is_file():
        loaded = yaml.safe_load(Path(policy_ref).read_text(encoding="utf-8"))
        if isinstance(loaded, dict):
            policy = loaded
    policy_sha = _policy_sha(policy)
    model_rates = policy.get("model_rates") or []

    # 1) The typed terminal outcome + its value-free change_set pointer (determined FIRST so a
    #    missing-outcome refusal is independent of transcript resolution).
    #    v3.1-G2a: when the dispatch carries a forge-stamped `change` block (a `cev3 pr --apply`
    #    opened a real PR), derive the change_set FROM IT — closing G1's "head_sha defaults to the
    #    run id" honesty gap with a forge-derived fact — and default --outcome to pr_opened. Explicit
    #    flags still win; the operator-typed fallback is byte-conserved for runs that opened no PR.
    change_block = dispatch.get("change") or {}
    outcome = args.outcome or ("pr_opened" if change_block else None)
    if outcome is None:
        return _emit(
            args, 2,
            [f"{_BRAND} · collect refused: --outcome is required "
             f"(run {run_id!r} carries no stamped change block to derive it from)"],
            {"error": "outcome_required", "run_id": run_id},
        )

    # 2) Resolve the harness transcript by the stamped session id — never by guess (D6/F9).
    #    The mis-fold that metered the orchestrator on the #14/#21 chains is machine-blocked.
    session_id = dispatch.get("harness_session_id")
    tpath, transcript_source, refusal = _resolve_collect_transcript(args, session_id, run_id)
    if refusal is not None:
        code, lines, payload = refusal
        return _emit(args, code, lines, payload)

    # 3) Spend ledger leaves — fold the RESOLVED transcript by REUSING the usage tap
    #    (compute_cost + meter_record_body); unpriced turns are surfaced, never $0.
    ledger_bodies: list[dict[str, Any]] = []
    unpriced = 0
    if tpath is not None:
        turns = usage_tap.tap_transcript_file(tpath)
        ledger_bodies, unpriced_turns = usage_tap.usage_turns_to_ledger(
            turns, model_rates=model_rates, fleet_id=run_id,
            policy_sha=policy_sha, run_id_of=lambda _t: run_id,
        )
        unpriced = len(unpriced_turns)
    change_set: dict[str, Any] = {
        "branch": args.branch or change_block.get("branch") or run_id,
        "base": args.base or change_block.get("base") or "main",
        "manifest_paths": list(args.manifest_paths or change_block.get("manifest_paths") or []),
        "head_sha": args.head_sha or change_block.get("head_sha") or run_id,
    }
    pr_number = args.pr if args.pr is not None else change_block.get("pr_number")
    if pr_number is not None:
        change_set["pr_number"] = pr_number
    # F6: propagate the value-free base-only re-stamp anchor so `cev3 merge` can machine-prove a
    # later base-only motion. A chain without `base_sha` is legacy-unprovable, never overridden.
    base_sha = change_block.get("base_sha")
    if base_sha:
        change_set["base_sha"] = base_sha
    outcome_body = {
        "kind": runtime_evidence_spine.RUN_OUTCOME_RECORD_KIND,
        "record_type": runtime_evidence_spine.RUN_OUTCOME_RECORD_TYPE,
        "schema_version": "1",
        "policy_sha": policy_sha,
        "run_id": run_id,
        "recorded_at": _utc_now_iso(),
        "outcome": outcome,
        "change_set": change_set,
    }

    # 4) Hash-chain the leaves then the terminal outcome; persist via the existing
    #    sink (refuses empty / non-uniform run_id / hash-broken / schema-invalid).
    chain: list[dict[str, Any]] = []
    for body in [*ledger_bodies, outcome_body]:
        chain.append(runtime_evidence_spine.append(chain, body))
    sink = evidence_sink.file_evidence_sink(_run_evidence_path(root, run_id).parent)
    try:
        receipt = sink(CollectedEvidence(
            handle_ref=run_id,
            records=tuple(chain),
            note=f"v3.1-G1 collect: run {run_id} folded {len(ledger_bodies)} spend leaf(s) "
                 f"+ outcome {outcome} (transcript_source: {transcript_source})",
        ))
    except evidence_sink.EvidencePersistRefused as exc:
        return _emit(
            args, 1,
            [f"{_BRAND} · collect refused: {exc}"],
            {"error": "persist_refused", "detail": str(exc), "run_id": run_id},
        )

    # 4) Mark the dispatch collected (an uncollected dispatch projects Build/RUN) + stamp the
    #    D6/F9 transcript-source honesty marker (the schema'd spend leaves stay untouched).
    dispatch["collected_at"] = _utc_now_iso()
    dispatch["transcript_source"] = transcript_source
    _dispatch_path(root, run_id).write_text(
        yaml.safe_dump(dispatch, sort_keys=True, default_flow_style=False), encoding="utf-8"
    )

    lines = [
        f"{_BRAND} · COLLECTED run {run_id!r} for Scope {args.scope_id!r} "
        f"(outcome {outcome}, {len(ledger_bodies)} spend leaf(s)"
        + (f", {unpriced} unpriced" if unpriced else "") + ")",
        f"    evidence: {receipt.path}",
    ]
    return _emit(
        args, 0, lines,
        {"action": "collected", "scope_id": args.scope_id, "run_id": run_id,
         "outcome": outcome, "pr": pr_number, "evidence": str(receipt.path),
         "spend_leaves": len(ledger_bodies), "unpriced_turns": unpriced,
         "transcript_source": transcript_source,
         "record_count": receipt.record_count},
    )


def _cmd_pr(args: argparse.Namespace) -> int:
    """Push the seat's authored branch + open its PR through the v3 forge (G2a, plan-by-default).

    Plan-by-default: without ``--apply`` it prints the would-push/would-open plan and mutates
    nothing. With ``--apply`` it drives ``v3_forge_join.open_change_for_run``
    (mint→push→open under a JIT least-privilege token, revoked in a finally) and stamps the
    value-free ``change`` block onto the dispatch. The ORCHESTRATOR/Operator session invokes this —
    a §7-governed seat is hook-denied the underlying push anyway (the authority model is conserved,
    now with the mechanical push automated v3-side).
    """
    root = Path(args.root)
    run_id = args.run_id
    # Precondition: the run must belong to the named Scope (the collect discipline).
    try:
        dispatch = _load_dispatch(root, run_id)
    except (FileNotFoundError, ValueError) as exc:
        return _emit(args, 2, [f"{_BRAND} · pr refused: {exc}"], {"error": str(exc)})
    if dispatch.get("scope_id") != args.scope_id:
        return _emit(
            args, 2,
            [f"{_BRAND} · pr refused: run {run_id!r} belongs to Scope "
             f"{dispatch.get('scope_id')!r}, not {args.scope_id!r}"],
            {"error": "scope_mismatch", "run_id": run_id,
             "dispatch_scope_id": dispatch.get("scope_id")},
        )
    try:
        app_config = v3_forge_join.load_app_config(args.app_config)
        ref = v3_forge_join.open_change_for_run(
            root, run_id, app_config=app_config, branch=args.branch,
            manifest_paths=args.manifest_paths, base=args.base,
            source_dir=args.source_dir, apply=args.apply,
        )
    except (v3_forge_join.ForgeJoinRefused, ForgeConfigError) as exc:
        return _emit(
            args, 1,
            [f"{_BRAND} · pr refused: {exc}"],
            {"action": "pr_refused", "run_id": run_id, "detail": str(exc)},
        )
    opened = bool(args.apply) and ref.pr_number is not None
    if opened:
        lines = [
            f"{_BRAND} · OPENED PR #{ref.pr_number} for Scope {args.scope_id!r} (run {run_id})",
            f"    branch {ref.branch} → {ref.base} · head {ref.head_sha}",
            f"    dispatch: {_dispatch_path(root, run_id)}",
            f"    next: {CE_CMD} review {args.scope_id} --run {run_id} --spawn",
        ]
    else:
        lines = [
            f"{_BRAND} · PR PLAN for Scope {args.scope_id!r} (run {run_id}) — nothing mutated",
            f"    would push branch {ref.branch} → {ref.base} on {ref.repo}",
            f"{_BRAND} · (plan-only — pass --apply to push + open the PR)",
        ]
    return _emit(
        args, 0, lines,
        {"action": "pr_opened" if opened else "pr_planned",
         "scope_id": args.scope_id, "run_id": run_id, "apply": bool(args.apply),
         "pr_number": ref.pr_number, "branch": ref.branch, "base": ref.base,
         "head_sha": ref.head_sha, "repo": ref.repo,
         "dispatch_path": str(_dispatch_path(root, run_id))},
    )


def _cmd_review(args: argparse.Namespace) -> int:
    """Dispatch a distinct CE-governed reviewer venue for a run's opened PR (G2b).

    Preconditions: the author dispatch exists, belongs to the named Scope, and carries a
    forge-stamped ``change`` block with a real ``pr_number``/``head_sha`` (no PR ⇒ refuse with a
    pointer to ``cev3 pr``). Materializes the reviewer-authority envelope + a ``role: reviewer``
    dispatch; with ``--spawn`` it provisions + launches the venue (pco-allocate → ``ce lane launch
    --json`` → seed). The review SUBMISSION (``gh pr review``) stays the venue's OWN governed act
    under the live Ring-1 hook + envelope; v3 RECORDS the venue and later folds its outcome via the
    unchanged ``cev3 collect ... --outcome review_submitted``.
    """
    root = Path(args.root)
    author_run_id = args.run_id
    try:
        author = _load_dispatch(root, author_run_id)
    except (FileNotFoundError, ValueError) as exc:
        return _emit(args, 2, [f"{_BRAND} · review refused: {exc}"], {"error": str(exc)})
    if author.get("scope_id") != args.scope_id:
        return _emit(
            args, 2,
            [f"{_BRAND} · review refused: run {author_run_id!r} belongs to Scope "
             f"{author.get('scope_id')!r}, not {args.scope_id!r}"],
            {"error": "scope_mismatch", "run_id": author_run_id,
             "dispatch_scope_id": author.get("scope_id")},
        )
    change = author.get("change") or {}
    pr_number = change.get("pr_number")
    head_sha = change.get("head_sha")
    if not pr_number or not head_sha:
        return _emit(
            args, 2,
            [f"{_BRAND} · review refused: run {author_run_id!r} has no opened PR to review",
             f"{_BRAND} · open it first: {CE_CMD} pr {args.scope_id} --run {author_run_id} "
             f"--branch <branch> --manifest-path <path> --app-config <cfg> --apply"],
            {"error": "no_pr", "run_id": author_run_id},
        )
    if args.spawn and (not args.venue_root or not args.ledger_root):
        return _emit(
            args, 2,
            [f"{_BRAND} · review --spawn refused: --venue-root and --ledger-root are required "
             "to provision the out-of-repo reviewer venue"],
            {"error": "spawn_inputs_missing", "run_id": author_run_id},
        )

    unattended = not getattr(args, "no_unattended", False)
    rec = v3_seat_bridge.materialize_review_dispatch(
        author, root, reviewer_actor=args.reviewer_actor,
        pr_number=int(pr_number), head_sha=str(head_sha),
        unattended=unattended,
    )
    if not args.spawn:
        lines = [
            f"{_BRAND} · REVIEW dispatch assembled for Scope {args.scope_id!r} "
            f"(PR #{pr_number}, review run {rec.run_id})",
            f"    envelope: {rec.data['review_of']['envelope_ref']}",
            f"    dispatch: {rec.dispatch_path}",
            f"{_BRAND} · (assemble-only — pass --spawn to launch the governed reviewer venue)",
        ]
        return _emit(
            args, 0, lines,
            {"action": "review_assembled", "scope_id": args.scope_id,
             "author_run_id": author_run_id, "review_run_id": rec.run_id,
             "pr_number": int(pr_number),
             "envelope_ref": rec.data["review_of"]["envelope_ref"],
             "dispatch_path": str(rec.dispatch_path)},
        )
    try:
        spawn = v3_seat_bridge.spawn_review_venue(
            rec, controller_id=args.controller_id,
            venue_root=args.venue_root, ledger_root=args.ledger_root,
            seat_env_file=getattr(args, "seat_env_file", None),
        )
    except v3_seat_bridge.SeatBridgeError as exc:
        # spawn_review_venue stamps mark_spawn_failed on any leg's refusal (conserved, not deleted).
        return _emit(
            args, 1,
            [f"{_BRAND} · review --spawn refused: {exc}"],
            {"action": "spawn_refused", "reason": "venue_launch_refused",
             "review_run_id": rec.run_id, "detail": str(exc),
             "dispatch_path": str(rec.dispatch_path)},
        )
    pane = spawn.terminal.get("pane_id")
    lines = [
        f"{_BRAND} · SPAWNED reviewer venue for Scope {args.scope_id!r} "
        f"(PR #{pr_number}, review run {rec.run_id})",
        f"    envelope: {rec.data['review_of']['envelope_ref']}",
        f"    dispatch: {rec.dispatch_path}",
        f"    pane: {pane}  [reviewer]",
        f"    next: {CE_CMD} collect {args.scope_id} --run {rec.run_id} "
        f"--outcome review_submitted --pr {pr_number}",
    ]
    return _emit(
        args, 0, lines,
        {"action": "spawned_review", "scope_id": args.scope_id,
         "author_run_id": author_run_id, "review_run_id": rec.run_id,
         "pr_number": int(pr_number), "pane_id": pane, "terminal": spawn.terminal,
         "envelope_ref": rec.data["review_of"]["envelope_ref"],
         "dispatch_path": str(rec.dispatch_path)},
    )


def _cmd_merge(args: argparse.Namespace) -> int:
    """Gate-read (or apply) a squash-merge of the run's opened PR through the v3 forge (G2c).

    Plan-by-default surfaces the gate snapshot (would_merge / review / checks / mergeable) and
    mutates nothing. ``--apply`` is the Operator's explicit gated act (human-gate RATIFY+MERGE
    conserved — the merge MECHANISM goes through v3, the DECISION stays human; server-side branch
    protection + CODEOWNERS still rule), driven under the Operator's ambient ``gh`` as the DISTINCT
    merge identity (never the per-run token). A non-merged result attests NOTHING.
    """
    root = Path(args.root)
    run_id = args.run_id
    try:
        dispatch = _load_dispatch(root, run_id)
    except (FileNotFoundError, ValueError) as exc:
        return _emit(args, 2, [f"{_BRAND} · merge refused: {exc}"], {"error": str(exc)})
    if dispatch.get("scope_id") != args.scope_id:
        return _emit(
            args, 2,
            [f"{_BRAND} · merge refused: run {run_id!r} belongs to Scope "
             f"{dispatch.get('scope_id')!r}, not {args.scope_id!r}"],
            {"error": "scope_mismatch", "run_id": run_id,
             "dispatch_scope_id": dispatch.get("scope_id")},
        )
    merge_runner = v3_forge_join.ambient_gh_runner()
    try:
        result = v3_forge_join.merge_for_run(
            root, run_id, merge_gh_runner=merge_runner, apply=args.apply,
        )
    except (v3_forge_join.ForgeJoinRefused, ForgeConfigError) as exc:
        return _emit(
            args, 1,
            [f"{_BRAND} · merge refused: {exc}"],
            {"action": "merge_refused", "run_id": run_id, "detail": str(exc)},
        )
    snapshot = result.to_dict()
    # F6: a head that moved is reported as an automatic base-only re-stamp or a refusal — never an
    # override. The status line names which tier acted.
    restamp_note = ""
    if result.head_status == v3_forge_join.HEAD_BASE_ONLY_RESTAMPED:
        restamp_note = (f" · base-only RE-STAMPED {result.old_head_sha}→{result.new_head_sha} "
                        "(machine_rebase_equivalence)")
    elif result.head_status == v3_forge_join.HEAD_BASE_ONLY_RESTAMP:
        restamp_note = f" · base-only re-stamp AVAILABLE {result.old_head_sha}→{result.new_head_sha}"
    if args.apply and result.merged:
        lines = [
            f"{_BRAND} · MERGED PR #{result.pr_number} for Scope {args.scope_id!r} (run {run_id})"
            + restamp_note,
            f"    squash commit: {result.merge_commit_sha}",
        ]
        if result.restamp_recorded:
            lines.append("    runtime_change_restamp recorded (base-only machine equivalence)")
        # The squash tree-equivalence audit is the what-was-TESTED == what-MERGES proof; a false
        # verdict is an operator-visible integrity alarm, never a silent pass.
        if result.audit_tree_equivalence is False:
            lines.append(f"{_BRAND} · ⚠ MERGE-AUDIT TREE MISMATCH — tested tree != merged tree; "
                         "operator review required (merge_audit_tree_mismatch)")
            return _emit(args, 1, lines, {"action": "merge_audit_tree_mismatch",
                                          "scope_id": args.scope_id, "run_id": run_id, **snapshot})
        lines.append(f"    next: {CE_CMD} report {args.scope_id} --run {run_id}")
        return _emit(args, 0, lines, {"action": "merged", "scope_id": args.scope_id,
                                      "run_id": run_id, **snapshot})
    if args.apply:
        # eligible gate but the server reported merged=false (rare) — attests nothing.
        lines = [f"{_BRAND} · merge NOT completed for PR #{result.pr_number} "
                 f"(merged={result.merged}); nothing attested"]
        return _emit(args, 1, lines, {"action": "merge_not_completed", "scope_id": args.scope_id,
                                      "run_id": run_id, **snapshot})
    verdict = "WOULD merge" if result.would_merge else "would NOT merge (gate not satisfied)"
    lines = [
        f"{_BRAND} · MERGE PLAN for PR #{result.pr_number} (Scope {args.scope_id!r}, run {run_id})"
        + restamp_note,
        f"    head_status={result.head_status} · {verdict}: review={result.review_decision} · "
        f"checks={result.rollup_state} · mergeable={result.mergeable}",
        f"{_BRAND} · (plan-only — pass --apply for the Operator's gated merge)",
    ]
    return _emit(args, 0, lines, {"action": "merge_planned", "scope_id": args.scope_id,
                                  "run_id": run_id, **snapshot})


def _cmd_status(args: argparse.Namespace) -> int:
    """List Scopes with their projected stage (the canon skin over the machine)."""
    root = Path(args.root)
    scopes = _iter_scopes(root)
    counts = _phase_counts(scopes, root)
    lines = [
        f"{_BRAND} · {len(scopes)} Scope(s) · "
        + " · ".join(f"{p} {counts[p]}" for p in coordination.COGNITIVE_PHASES),
    ]
    scope_payloads: list[dict[str, Any]] = []
    for s in sorted(scopes, key=lambda x: str(x.get("scope_id"))):
        # v3.1-G2c: surface the opened PR + a live reviewer venue on the Scope line.
        change_block, review = _forge_surface_for_scope(root, str(s.get("scope_id")))
        pr_number = change_block.get("pr_number") if change_block else None
        review_run_id = review.get("run_id") if review else None
        badge = (f"  · PR #{pr_number}" if pr_number else "") + ("  · ⊙ review" if review else "")
        lines.append("  " + _card_line(s, root) + badge)
        scope_payloads.append(
            {"scope_id": s.get("scope_id"), "projection": _projection(s, root),
             "pr": pr_number, "review_run_id": review_run_id}
        )
    return _emit(
        args, 0, lines,
        {"action": "status", "count": len(scopes), "phase_counts": counts, "scopes": scope_payloads},
    )


def _cmd_show(args: argparse.Namespace) -> int:
    """Show one Scope: the canon-labelled fields + its projection + readiness."""
    root = Path(args.root)
    try:
        scope = _load_scope(root, args.scope_id)
    except (FileNotFoundError, ValueError) as exc:
        return _emit(args, 2, [f"{_BRAND} · {exc}"], {"error": str(exc)})
    proj = _projection(scope, root)
    ready, reasons = coordination.scope_is_ready(scope)
    lines = [
        _card_line(scope, root),
        f"    Goal (intent):        {scope.get('intent')}",
        f"    Done-when (criteria): {scope.get('acceptance_criteria') or '—'}",
        f"    Budget (appetite):    {scope.get('appetite') or '—'}",
        f"    Change-type (class):  {scope.get('mutation_class')}",
        f"    Stage / state / board: {proj['phase']} / {proj['state']} / {proj['board']}",
        f"    Ready: {'yes' if ready else 'no — ' + '; '.join(reasons)}"
        f" · bet placed: {'yes' if coordination.is_ratified(scope) else 'no'}",
    ]
    # v3.1-G2c: surface the forge state — the opened PR + a live reviewer venue, if any.
    change_block, review = _forge_surface_for_scope(root, str(scope.get("scope_id")))
    pr_number = change_block.get("pr_number") if change_block else None
    review_run_id = review.get("run_id") if review else None
    if change_block:
        lines.append(
            f"    PR: #{pr_number} ({change_block.get('branch')} → {change_block.get('base')})"
        )
    if review:
        rv = review.get("review_of") or {}
        lines.append(f"    Review venue: {review_run_id} (PR #{rv.get('pr_number')})")
    return _emit(
        args, 0, lines,
        {"action": "show", "scope_id": scope.get("scope_id"), "scope": scope,
         "projection": proj, "ready": ready, "reasons": reasons,
         "ratified": coordination.is_ratified(scope),
         "pr": pr_number, "review_run_id": review_run_id},
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
    artifacts = [{"kind": "scope", "path": str(path), "label": f"Scope {args.scope_id}",
                  "inspect": f"{CE_CMD} show {args.scope_id}"}]
    # G-7.3 / G1b: with a run evidence chain, also enumerate the run artifacts (PR /
    # evidence-chain / spend) via the ◆ Completion-Report artifact-awareness fold.
    # The chain defaults to a collected dispatch's chain (explicit --evidence wins).
    evidence, run_id = _resolve_run_evidence(args, root)
    if evidence:
        records = yaml.safe_load(Path(evidence).read_text(encoding="utf-8"))
        if isinstance(records, dict):
            records = records.get("records") or records.get("leaves") or []
        summary = v3_report.summary_from_evidence(
            records or [], scope_id=args.scope_id, run_id=run_id,
            budget=getattr(args, "cap", None),
        )
        artifacts += [a for a in v3_report.enumerate_artifacts(summary) if a["kind"] != "scope"]
    lines = [f"{_BRAND} · artifacts for Scope {args.scope_id!r}:"]
    lines += [f"    {a['kind']:>10}  {a.get('path', a['label'])}   ({a['inspect']})" for a in artifacts]
    if not evidence:
        lines.append(f"{_BRAND} · (pass --evidence <chain> to enumerate run artifacts: PR / evidence / spend)")
    return _emit(args, 0, lines, {"action": "artifacts", "scope_id": args.scope_id, "artifacts": artifacts})


def _cmd_report(args: argparse.Namespace) -> int:
    """Render the per-run ◆ CE Completion Report (Outcome · Verdict · Next + Artifacts).

    Folds the REAL conserved outcome + spend off the run evidence chain
    (``--evidence``); the grading synthesis (Done-when / CI / in-scope) is injected
    via flags (its live assembly is the deferred seam).
    """
    root = Path(getattr(args, "root", V3_LOCAL_STATE_ROOT))
    evidence, run_id = _resolve_run_evidence(args, root)
    records: list[Any] = []
    if evidence:
        loaded = yaml.safe_load(Path(evidence).read_text(encoding="utf-8"))
        if isinstance(loaded, dict):
            loaded = loaded.get("records") or loaded.get("leaves") or []
        records = loaded or []
    grading: dict[str, Any] = {}
    if args.change_type:
        grading["change_type"] = args.change_type
    if args.done_when_total is not None:
        grading["done_when_total"] = args.done_when_total
        grading["done_when_met"] = args.done_when_met if args.done_when_met is not None else args.done_when_total
    if args.ci:
        grading["ci"] = args.ci
    if args.in_scope is not None:
        grading["in_scope"] = args.in_scope
    if args.budget_size:
        grading["budget_size"] = args.budget_size
    summary = v3_report.summary_from_evidence(
        records, scope_id=args.scope_id, run_id=run_id, budget=args.cap, unit=args.unit, **grading,
    )
    if args.pr is not None:
        summary["pr"] = args.pr
    lines = v3_report.render_report(summary)
    return _emit(args, 0, lines, {
        "action": "report", "run_id": summary.get("run_id"), "scope_id": args.scope_id,
        "outcome": summary.get("outcome"), "outcome_label": v3_report.outcome_label(summary.get("outcome")),
        "verdict": v3_report.render_verdict(summary), "next": v3_report.render_next(summary),
        "artifacts": v3_report.enumerate_artifacts(summary),
    })


def _cmd_shape(args: argparse.Namespace) -> int:
    """Run the Frame→Shape grill-me over a partial draft (gaps + minimum questions).

    The agent drafts every field EXCEPT the Budget (human-only). Surfaces the
    gap-aware Scope card, the minimum questions to close, and (with --persona +
    --signal) the detect-and-offer decision. A pure dialogue helper — it does not
    write a Scope artifact (that is `ce scope` once the gaps are closed).
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
        lines.append(f"{_BRAND} · Ready — place the bet with `{CE_CMD} ratify {args.scope_id}`")
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
    counts = _phase_counts(_iter_scopes(Path(args.root)), Path(args.root))
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
    ce_ver = version.ce_version()
    lines = v3_session.render_session(
        counts, context=context, spend=spend, at_boundary=not args.mid_output,
        repo=args.repo, transport=args.transport, backend=args.backend, root=args.root,
        version=ce_ver,
    )
    return _emit(
        args, 0, lines,
        {"action": "session", "root": args.root, "phase_counts": counts,
         "ce_version": ce_ver,
         "context": {"pct": context.pct, "state": context.state},
         "spend": {"state": spend.state, "ratio": spend.ratio,
                   "spent": v3_session.fmt_amount(spend.spent) if spend.spent is not None else None,
                   "cap": v3_session.fmt_amount(spend.cap) if spend.cap is not None else None,
                   "unit": spend.unit}},
    )


def _cmd_onboard(args: argparse.Namespace) -> int:
    """Two-mode install — verify the signed spec, then DRY-RUN the install plan.

    v3.5-E.3 (one engine, two modes): the same verified journey, with answers
    coming from ``interactive > answers-file > detected > default``.

    ``--inventory`` emits the operator-input inventory (the awareness artifact
    an agent reads to PREPARE the answers file); ``--answers f.yaml`` loads the
    IaC answers file (schema-validated, fail-closed on unknown keys, secrets by
    SecretRef only); ``--plan`` is the terraform-plan analog (the full plan
    including the EXACT remaining asks + the decomposed GitHub leg);
    ``--non-interactive`` turns the final ask into a fail-closed refusal that
    enumerates exactly what is missing.

    Order is load-bearing and unchanged (design §2.4): ``require_verified``
    FIRST — the answers file configures the VERIFIED procedure; nothing in it
    (and no flag here) can substitute for the signature gate. The CLI is the
    I/O edge (it reads the spec, the schema document, and the answers file,
    and runs the live read-only probes); the engine in ``v3_installer`` stays
    pure. The deeper GitHub probes (origin remote, token scopes, installation)
    are the E.4 live-drive seam — unprobed planners stay fail-closed.
    """
    spec_path = Path(args.spec)
    if not spec_path.is_file():
        return _emit(args, 2, [f"{_BRAND} · onboard refused: spec not found: {spec_path}"],
                     {"error": "spec_not_found"})
    spec_bytes = spec_path.read_bytes()
    self_attested = args.sig_value is None
    signature = {"key_id": args.key_id, "algo": v3_installer.CONTENT_ALGO,
                 "value": args.sig_value or v3_installer.content_digest(spec_bytes)}
    # 1. verify FIRST — unbypassed; --inventory/--plan ride the same gate.
    try:
        verified = v3_installer.require_verified(
            spec_bytes, signature, pinned_keys=v3_installer.PINNED_KEYS
        )
    except v3_installer.InstallRefused as exc:
        return _emit(args, 1, [f"{_BRAND} · onboard REFUSED: {exc}"],
                     {"error": "refused", "detail": str(exc)})
    # 2. the answers schema + the answers file (the CLI is the I/O edge; the
    #    engine is pure — the schema document is injected as a dict).
    schema_path = Path(args.answers_schema)
    try:
        schema = yaml.safe_load(schema_path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as exc:
        return _emit(args, 2,
                     [f"{_BRAND} · onboard refused: answers schema unreadable: {exc}"],
                     {"error": "schema_unreadable", "detail": str(exc)})
    answers: dict[str, Any] = {}
    answers_sha = None
    if args.answers:
        answers_path = Path(args.answers)
        if not answers_path.is_file():
            return _emit(args, 2,
                         [f"{_BRAND} · onboard refused: answers file not found: {answers_path}"],
                         {"error": "answers_not_found"})
        answers_bytes = answers_path.read_bytes()
        # the evidence binding's hashable input (SecretRefs are inert strings)
        answers_sha = v3_installer.content_digest(answers_bytes)
        try:
            loaded = yaml.safe_load(answers_bytes.decode("utf-8"))
        except (UnicodeDecodeError, yaml.YAMLError) as exc:
            return _emit(args, 1,
                         [f"{_BRAND} · onboard REFUSED: answers file is not valid YAML: {exc}"],
                         {"error": "refused", "detail": str(exc)})
        try:
            answers = v3_installer.require_valid_answers(loaded, schema=schema)
        except v3_installer.InstallRefused as exc:
            return _emit(args, 1, [f"{_BRAND} · onboard REFUSED: {exc}"],
                         {"error": "refused", "detail": str(exc)})
    # 3. live read-only detection the CLI can do TODAY (deeper probes = E.4).
    detected: dict[str, Any] = {}
    present_harnesses = [name for name, binary in
                         (("claude-code", "claude"), ("codex", "codex")) if _which(binary)]
    if present_harnesses:
        detected["provider.harness"] = (
            present_harnesses[0] if len(present_harnesses) == 1 else "both"
        )
    # 4. --inventory: the awareness artifact (schema-derived, never hand-kept).
    if args.inventory:
        rows = v3_installer.inventory_emission(
            schema, detected=detected, answers=answers or None
        )
        lines = [
            f"{_BRAND} · onboard inventory — {len(rows)} inputs "
            f"(spec verified against pinned key {verified.key_id!r})"
        ]
        for row in rows:
            modes = "/".join(row["modes"]) or "—"
            optional = " · optional" if row["optional"] else ""
            lines.append(
                f"    step {row['step']} · {row['key']} "
                f"[{row['sensitivity']} · {modes}{optional}] → {row['status']}"
            )
        lines.append(
            f"{_BRAND} · prepare {v3_installer.ANSWERS_BASENAME} from this "
            "(secrets ONLY as env:// file:// prompt:// keychain:// refs), then: "
            f"{CE_CMD} onboard --spec <spec> --answers <file> --plan"
        )
        return _emit(args, 0, lines, {
            "action": "onboard_inventory",
            "verified": {"ok": True, "key_id": verified.key_id},
            "self_attested": self_attested,
            "inventory": [dict(row) for row in rows],
        })
    # 5. the precedence merge + the missing list + the scoped sudo-grant diff.
    merged = v3_installer.merge_answers(schema, answers=answers or None, detected=detected)
    missing = v3_installer.missing_answers(schema, merged)
    probe = {tool: _which(tool) for tool in v3_installer.REQUIRED_DEPENDENCIES}
    dep_plan = v3_installer.plan_dependencies(v3_installer.REQUIRED_DEPENDENCIES, probe)
    grant_diff = v3_installer.sudo_grant_diff(merged.value("host.sudo_grant"), dep_plan)
    # 6. --non-interactive: fail-closed (the terraform -input=false analog).
    if args.non_interactive:
        try:
            v3_installer.require_complete(missing)
            if grant_diff.uncovered:
                raise v3_installer.InstallRefused(
                    "non-interactive mode is fail-closed — planned privileged "
                    f"installs outside the sudo grant: {', '.join(grant_diff.uncovered)} "
                    f"(host.sudo_grant covers: {', '.join(grant_diff.grant) or 'nothing'})"
                )
        except v3_installer.InstallRefused as exc:
            return _emit(args, 1, [f"{_BRAND} · onboard REFUSED: {exc}"], {
                "error": "refused", "detail": str(exc),
                "missing": [{"key": m.key, "step": m.step, "reason": m.reason} for m in missing],
                "sudo_uncovered": list(grant_diff.uncovered),
            })
    # 7. the cost profile — CLI flags are the interactive override (precedence);
    #    otherwise a custom answers profile supplies the (stripped) binding.
    opt_out = args.opt_out
    optout_ratification = None
    if args.opt_out:
        optout_ratification = {"ratified_prompt_sha": args.ratified_prompt_sha or "",
                               "approver_ref": args.approver_ref or ""}
    elif answers:
        try:
            binding = v3_installer.optout_binding_from_answers(answers)
        except v3_installer.InstallRefused as exc:
            return _emit(args, 1, [f"{_BRAND} · onboard REFUSED: {exc}"],
                         {"error": "refused", "detail": str(exc)})
        if binding is not None:
            opt_out, optout_ratification = True, binding
    try:
        plan = v3_installer.build_install_plan(
            spec_bytes, signature, pinned_keys=v3_installer.PINNED_KEYS, probe=probe,
            mode=args.mode, opt_out=opt_out, optout_ratification=optout_ratification,
        )
    except v3_installer.InstallRefused as exc:
        return _emit(args, 1, [f"{_BRAND} · onboard REFUSED: {exc}"], {"error": "refused", "detail": str(exc)})
    # 8. --plan: compose the decomposed GitHub leg (pure planners; the CLI-level
    #    probe carries only what it can read today — unprobed = fail-closed).
    github_leg = None
    if args.show_plan and answers.get("github"):
        github_leg = v3_installer.build_github_leg_plan(answers, schema=schema, probe={})
    lines = [
        f"{_BRAND} · onboard (dry-run · {plan['mode']}) — spec verified against pinned key "
        f"{plan['verified']['key_id']!r}",
        f"    dependencies · install {plan['dependencies']['install'] or '—'} · "
        f"skip {plan['dependencies']['skip']} · sudo {'yes' if plan['dependencies']['needs_sudo'] else 'no'}",
        f"    cost profile · {plan['profile']['mode']} → {plan['profile']['runtime_policy']}",
    ]
    if plan["educate"]:
        lines.append(f"    {_BRAND} opt-out · {plan['educate']}")
    if args.answers:
        source_counts: dict[str, int] = {}
        for entry in merged.resolved.values():
            source_counts[entry.source] = source_counts.get(entry.source, 0) + 1
        lines.append(
            f"    answers · {args.answers} (sha256 {answers_sha}) — sources "
            + " · ".join(f"{source}:{count}" for source, count in sorted(source_counts.items()))
        )
        if dep_plan.needs_sudo:
            lines.append(
                "    sudo grant · covered "
                f"{list(grant_diff.covered) or '—'} · OUTSIDE the grant {list(grant_diff.uncovered) or '—'}"
            )
        for conflict in merged.conflicts:
            lines.append(
                f"    CONFLICT · {conflict.key}: file {conflict.file_value!r} contradicts "
                f"detected {conflict.detected_value!r} — resolve interactively"
            )
        if missing:
            lines.append(
                "    remaining asks · "
                + "; ".join(f"step {m.step}: {m.key} ({m.reason})" for m in missing)
            )
        else:
            lines.append("    remaining asks · none — apply-ready (the live drive is deferred)")
    if github_leg is not None:
        click = "click required (first run)" if github_leg["app"]["click_required"] \
            else f"click skipped (installation {github_leg['app']['installation_id']} detected/declared)"
        lines.append(
            f"    github leg · repo {github_leg['repo']['action']} · App {click} · "
            f"protection drift {len(github_leg['branch_protection']['drift'])} · "
            f"{'converged' if github_leg['converged'] else 'NOT converged (live probes deferred to the E.4 drive)'}"
        )
    lines += [
        f"    expose CLI · `{plan['expose_cli']['command']}` (via {plan['expose_cli']['via']})",
        f"{_BRAND} · you approve only: {', '.join(plan['human_approves'])}",
        f"{_BRAND} · deferred live: {'; '.join(plan['deferred_live_seams'])}",
    ]
    if self_attested:
        # honesty: with no published --sig-value the content floor only self-attests
        # integrity (not authenticity). The real check needs the published signature
        # value + the asymmetric verifier — pass --sig-value before a live drive.
        lines.append(
            f"{_BRAND} · NOTE: no --sig-value given — verification is self-attested integrity "
            "only (NOT authenticity); pass the published signature value before a live install."
        )
    payload = {
        "action": "onboard", "self_attested": self_attested, **plan,
        "answers": ({
            "path": args.answers, "sha256": answers_sha,
            "sources": {k: e.source for k, e in sorted(merged.resolved.items())},
            "conflicts": [{"key": c.key, "file": c.file_value, "detected": c.detected_value}
                          for c in merged.conflicts],
            "missing": [{"key": m.key, "step": m.step, "reason": m.reason} for m in missing],
            "sudo_grant": {"grant": list(grant_diff.grant), "covered": list(grant_diff.covered),
                           "uncovered": list(grant_diff.uncovered)},
        } if args.answers else None),
        "github_leg": github_leg,
        "non_interactive": bool(args.non_interactive),
    }
    return _emit(args, 0, lines, payload)


def _cmd_cockpit(args: argparse.Namespace) -> int:
    """The Cockpit (v3.5-B.1): the governed fleet board, read-only.

    Principle-6 routing: the L2 snapshot fold (``runner.cockpit_readmodel``) is
    textual-free and ``--json`` dumps it directly — the future-GUI seam as a
    first-class invocation. ONLY the TUI path lazy-imports ``v3_cockpit`` (and
    thereby ``textual``); non-cockpit subcommands and ``--json`` never do.
    ``CE_DEMO=1`` swaps the data source for the seeded demo fleet (with the
    persistent watermark); live mode reads the v3 state root plus the
    launch-pinned ``CE_LEDGER_ROOT`` / ``CE_HOOK_OBSERVATIONS_DIR`` seams.

    ``--serve`` (v3.5-B.6) opens the SAME app in a browser on demand:
    loopback-only bind + token gate + Host validation, enforced by the pure
    serve config in ``v3_cockpit``; the serve deps load ONLY on this path. A
    non-loopback ``--host`` is refused loudly before any socket exists.
    """
    if getattr(args, "serve", False):
        import shlex
        import sys

        from . import v3_cockpit  # LAZY: the serve path is a cockpit path

        command = (
            f"{shlex.quote(sys.executable)} -m creator_engine_validator.v3_cli "
            f"cockpit --root {shlex.quote(str(args.root))}"
        )
        try:
            config = v3_cockpit.build_serve_config(
                command=command,
                token=v3_cockpit.generate_token(),
                host=args.host,
                port=args.port,
            )
        except ValueError as exc:
            print(f"{CE_CMD} cockpit --serve: {exc}", file=sys.stderr)
            return 2
        return v3_cockpit.run_serve(config)

    from .runner import cockpit_readmodel as _readmodel  # L2 — textual-free

    # ce-ops#25: resolve the CE version token ONCE here (Open-Q1) and pass it as
    # DATA into demo + live snapshot construction — the L2 fold and the watch
    # loop never run git. Demo and live therefore expose the SAME token.
    ce_ver = version.ce_version()
    demo = os.environ.get(_readmodel.DEMO_ENV) == "1"
    root = Path(args.root)
    if demo:
        from .runner import cockpit_demo_seed as _seed

        def _load() -> dict[str, Any]:
            return _readmodel.fold_snapshot(demo=True, ce_version=ce_ver, **_seed.seed())

        watch: list[str] = []
    else:

        def _load() -> dict[str, Any]:
            return _readmodel.snapshot_from_roots(root, ce_version=ce_ver)

        watch = _readmodel.watch_paths(root)
    snapshot = _load()
    if getattr(args, "json_output", False):
        print(json.dumps(snapshot, indent=2, sort_keys=True))
        return 0
    from . import v3_cockpit  # LAZY: textual loads ONLY on the TUI path

    return v3_cockpit.run_app(snapshot, reload=_load, watch_paths=watch)


def _cmd_guide(args: argparse.Namespace) -> int:
    """Print the in-product guide (the seed of ``docs/guide/understanding-ce.md``)."""
    if getattr(args, "json_output", False):
        print(json.dumps({"ok": True, "action": "guide", "guide": _GUIDE}, indent=2))
    else:
        print(_GUIDE)
    return 0


def _which(tool: str) -> bool:
    """Read-only presence probe (the FIX is deferred). ``python`` ≈ python3."""
    if tool == "python":
        return bool(shutil.which("python") or shutil.which("python3"))
    return bool(shutil.which(tool))


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
        prog=CE_CMD,
        description="Creator Engine v3 — file, ratify, and drive work as a governed Scope "
        "(Frame → Shape → Build → Review → Ship).",
    )
    # ce-ops#25: top-level ``cev3 --version`` prints the derived CE token and
    # exits BEFORE the default ``session`` dispatch (the action exits in
    # parse_args, ahead of ``args.command`` resolution in ``main``).
    version.add_version_flag(parser)
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

    p_drive = sub.add_parser("drive", help="assemble the governed dispatch (front gate); --spawn launches the seat")
    p_drive.add_argument("scope_id", metavar="ID", help="the Scope to drive")
    p_drive.add_argument("--policy", default=None, help="optional runtime-policy YAML to merge the run envelope into")
    p_drive.add_argument("--spawn", action="store_true",
                         help="materialize the dispatch and spawn a real governed seat (v3.1-G1)")
    p_drive.add_argument("--harness", default="claude",
                         help="seat harness (only 'claude' is bridged; codex is the G1-codex follow-up)")
    p_drive.add_argument("--no-unattended", action="store_true",
                         help="opt the spawned seat back into interactive approval modals")
    _add_root(p_drive)

    p_collect = sub.add_parser("collect", help="fold a finished seat run's transcript + outcome into evidence")
    p_collect.add_argument("scope_id", metavar="ID", help="the Scope the run delivered")
    p_collect.add_argument("--run", required=True, dest="run_id", metavar="RUN_ID", help="the dispatched run id")
    p_collect.add_argument("--transcript", default=None,
                           help="OPTIONAL override path to the seat harness .jsonl transcript. Normally "
                                "OMIT it: collect resolves the transcript by the harness session id "
                                "stamped at spawn (D6/F9). When given, it is folded ONLY if its stem "
                                "matches the stamped id — else refused (the #14/#21 mis-fold, blocked)")
    p_collect.add_argument("--transcript-override", default=None, dest="transcript_override",
                           help="SALVAGE hatch: fold this transcript despite no/mismatched stamped id "
                                "(e.g. a crashed/relocated harness transcript). Loudly honesty-stamped "
                                "transcript_source: operator_override")
    p_collect.add_argument("--claude-config-dir", default=None, dest="claude_config_dir",
                           help="override the harness config dir for stamped-id transcript resolution "
                                "(default: $CLAUDE_CONFIG_DIR or ~/.claude)")
    p_collect.add_argument("--outcome", default=None, choices=list(v3_seat_bridge.OUTCOME_VOCABULARY),
                           help="the conserved terminal outcome (defaults to pr_opened when the "
                                "dispatch carries a forge-stamped change block; otherwise required)")
    p_collect.add_argument("--pr", type=int, default=None, help="PR number (if the run opened one)")
    p_collect.add_argument("--branch", default=None, help="value-free change branch ref (default: run id / change block)")
    p_collect.add_argument("--base", default=None, help="value-free change base ref (default: main / change block)")
    p_collect.add_argument("--head-sha", default=None, dest="head_sha",
                           help="value-free change head sha (default: run id)")
    p_collect.add_argument("--manifest-path", action="append", default=None, dest="manifest_paths",
                           help="value-free change manifest path (repeatable)")
    _add_root(p_collect)

    p_pr = sub.add_parser(
        "pr", help="push the seat's authored branch + open its PR through the v3 forge "
                   "(plan-by-default; --apply pushes + opens)")
    p_pr.add_argument("scope_id", metavar="ID", help="the Scope the run delivered")
    p_pr.add_argument("--run", required=True, dest="run_id", metavar="RUN_ID", help="the dispatched run id")
    p_pr.add_argument("--branch", required=True, help="the seat's authored head branch to push + open")
    p_pr.add_argument("--manifest-path", action="append", required=True, dest="manifest_paths",
                      metavar="PATH", help="an authorized change manifest path (repeatable, required)")
    p_pr.add_argument("--base", default="main", help="the PR base branch (default: main)")
    p_pr.add_argument(
        "--app-config", required=True, dest="app_config",
        help="REQUIRED path to the host GitHub-App config JSON — NO default (host filenames "
             "differ: laptop ~/.ce-keys/ce-forge-app.json, CE-DEV-1 ~/.ce-keys/ce-forge-dev1.json; "
             "a default would silently miss on one host)",
    )
    p_pr.add_argument("--source-dir", default=".", dest="source_dir",
                      help="local checkout holding the authored branch (default: cwd)")
    p_pr.add_argument("--apply", action="store_true",
                      help="push + open the PR for real (default: plan-only — mutates nothing)")
    _add_root(p_pr)

    p_review = sub.add_parser(
        "review", help="dispatch a distinct CE-governed reviewer venue for a run's opened PR "
                       "(assemble-only; --spawn launches the venue)")
    p_review.add_argument("scope_id", metavar="ID", help="the Scope the author run delivered")
    p_review.add_argument("--run", required=True, dest="run_id", metavar="RUN_ID",
                          help="the AUTHOR run id whose opened PR is reviewed")
    p_review.add_argument("--reviewer-actor", required=True, dest="reviewer_actor",
                          help="the host-bound reviewer LOGIN (DATA — a login, never a token; e.g. "
                               "ubuntuaws745-cmyk on the laptop, cedev1vps-cmd on CE-DEV-1)")
    p_review.add_argument("--spawn", action="store_true",
                          help="provision + launch the governed reviewer venue (default: assemble-only)")
    p_review.add_argument("--venue-root", default=None, dest="venue_root",
                          help="out-of-repo zone the venue worktree is provisioned under "
                               "(required with --spawn; execution-zones directive)")
    p_review.add_argument("--ledger-root", default=None, dest="ledger_root",
                          help="Active-Work ledger root for the venue claim (required with --spawn)")
    p_review.add_argument("--controller-id", default="cev3-review", dest="controller_id",
                          help="controller id for the venue lane (default: cev3-review)")
    p_review.add_argument("--no-unattended", action="store_true", dest="no_unattended",
                          help="opt the reviewer venue back into interactive approval modals "
                               "(default: unattended, mirroring the author seat — D1/F3)")
    p_review.add_argument("--seat-env-file", default=None, dest="seat_env_file",
                          help="path to an owner-only (0600-class) env file sourced into the "
                               "venue claude (the reviewer credential contract — D2/F4); the file "
                               "PATH transits argv, the secret VALUE never does")
    _add_root(p_review)

    p_merge = sub.add_parser(
        "merge", help="gate-read (or apply) a squash-merge of a run's opened PR "
                      "(plan-by-default; --apply is the Operator's gated act)")
    p_merge.add_argument("scope_id", metavar="ID", help="the Scope the run delivered")
    p_merge.add_argument("--run", required=True, dest="run_id", metavar="RUN_ID",
                         help="the run whose collected chain carries the opened PR")
    p_merge.add_argument("--apply", action="store_true",
                         help="perform the gated squash-merge (default: plan-only — read the gate)")
    _add_root(p_merge)

    p_escalation = sub.add_parser(
        "escalation",
        help="manage local AWAITING-OPERATOR escalation records",
    )
    escalation_sub = p_escalation.add_subparsers(dest="escalation_command", required=True)

    p_escalation_open = escalation_sub.add_parser(
        "open",
        help="write a local AWAITING-OPERATOR escalation record",
    )
    p_escalation_open.add_argument("--id", required=True, dest="escalation_id", help="escalation slug or digest")
    p_escalation_open.add_argument("--title", required=True, help="short escalation title")
    p_escalation_open.add_argument("--decision", required=True, help="decision the Operator must make")
    p_escalation_open.add_argument("--recommend", required=True, help="recommended option")
    p_escalation_open.add_argument("--source-ref", default=None, help="optional value-free source marker")
    _add_root(p_escalation_open)

    p_escalation_resolve = escalation_sub.add_parser(
        "resolve",
        help="stamp a local escalation resolved",
    )
    p_escalation_resolve.add_argument("escalation_id", metavar="ID", help="escalation slug or digest")
    p_escalation_resolve.add_argument("--resolution", default=None, help="optional value-free resolution summary")
    _add_root(p_escalation_resolve)

    p_escalation_sync = escalation_sub.add_parser(
        "sync",
        help="mirror awaiting-operator issues from gh into local escalation records",
    )
    p_escalation_sync.add_argument("--repo", required=True, help="GitHub repo in owner/name form")
    p_escalation_sync.add_argument("--label", default="awaiting-operator", help="issue label to mirror")
    _add_root(p_escalation_sync)

    p_notify = sub.add_parser(
        "notify",
        help="Operator-notify feed — alert on AWAITING-OPERATOR entry/exit "
             "(once | watch | status; pluggable desktop/exec sinks)",
    )
    notify_sub = p_notify.add_subparsers(dest="notify_command", required=True)

    p_notify_once = notify_sub.add_parser(
        "once",
        help="a single fold→dispatch→record pass (the cron-able / testable primitive)",
    )
    p_notify_once.add_argument("--sync-repo", default=None, dest="sync_repo",
                               help="optional GitHub repo (owner/name) to mirror forge "
                                    "awaiting-operator issues from BEFORE the fold (cross-host fan-in)")
    p_notify_once.add_argument("--sync-label", default="awaiting-operator", dest="sync_label",
                               help="issue label to mirror (default: awaiting-operator)")
    _add_root(p_notify_once)

    p_notify_watch = notify_sub.add_parser(
        "watch",
        help="poll loop: (optional sync) → fold → dispatch → record → sleep",
    )
    p_notify_watch.add_argument("--interval", type=int, default=30,
                                help="poll interval in seconds (default: 30)")
    p_notify_watch.add_argument("--sync-repo", default=None, dest="sync_repo",
                                help="optional GitHub repo (owner/name) for cross-host fan-in each tick")
    p_notify_watch.add_argument("--sync-label", default="awaiting-operator", dest="sync_label",
                                help="issue label to mirror (default: awaiting-operator)")
    _add_root(p_notify_watch)

    p_notify_status = notify_sub.add_parser(
        "status",
        help="pure-fold counts (open / pending / delivered / failed) — no dispatch",
    )
    _add_root(p_notify_status)

    p_status = sub.add_parser("status", help="list Scopes by projected stage")
    _add_root(p_status)

    p_show = sub.add_parser("show", help="show one Scope (canon labels + projection)")
    p_show.add_argument("scope_id", metavar="ID", help="the Scope to show")
    _add_root(p_show)

    p_art = sub.add_parser("artifacts", help="enumerate a Scope's (and a run's) artifacts")
    p_art.add_argument("scope_id", metavar="ID", help="the Scope whose artifacts to list")
    p_art.add_argument("--evidence", default=None, help="run evidence chain YAML — also enumerate run artifacts")
    p_art.add_argument("--run-id", default=None, help="run id to fold the evidence for")
    p_art.add_argument("--cap", type=float, default=None, help="run spend cap (to surface the spend artifact)")
    _add_root(p_art)

    p_report = sub.add_parser("report", help="render the per-run ◆ CE Completion Report")
    p_report.add_argument("scope_id", metavar="ID", help="the Scope the run delivered")
    p_report.add_argument("--evidence", default=None, help="run evidence chain YAML (folds Outcome + spend)")
    p_report.add_argument("--run-id", default=None, help="run id")
    p_report.add_argument("--pr", type=int, default=None, help="PR number (if the run opened one)")
    p_report.add_argument("--change-type", default=None, choices=sorted(coordination.MUTATION_CLASSES),
                          help="Change-type (mutation_class) for the Next step")
    p_report.add_argument("--done-when-total", type=int, default=None, help="number of Done-when criteria")
    p_report.add_argument("--done-when-met", type=int, default=None, help="Done-when criteria met")
    p_report.add_argument("--ci", default=None, help="CI status (e.g. green)")
    p_report.add_argument("--in-scope", dest="in_scope", action="store_true", default=None,
                          help="the diff stayed inside the closed manifest (in scope ✓)")
    p_report.add_argument("--out-of-scope", dest="in_scope", action="store_false",
                          help="the diff left the closed manifest")
    p_report.add_argument("--cap", type=float, default=None, help="run spend cap (Budget) to meter spend against")
    p_report.add_argument("--unit", choices=["$", "%"], default="$", help="spend unit")
    p_report.add_argument("--budget-size", default=None, help="appetite size label (e.g. S) for 'of Budget S'")
    p_report.add_argument(
        "--root", default=V3_LOCAL_STATE_ROOT,
        help=f"v3 local-state root (to default --evidence from a collected run; default: {V3_LOCAL_STATE_ROOT})",
    )
    p_report.add_argument("--json", action="store_true", dest="json_output", help="emit machine-readable JSON")

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

    p_onboard = sub.add_parser(
        "onboard",
        help="two-mode install: verify the signed spec + dry-run the plan "
             "(agent loop: --inventory → prepare answers → --plan → apply)",
    )
    p_onboard.add_argument("--spec", required=True, help="path to the served install spec to verify")
    p_onboard.add_argument("--key-id", default="ce-root-v1", help="the signing key id (must be pinned)")
    p_onboard.add_argument("--sig-value", default=None,
                           help="the published signature value (default: the spec's own content digest)")
    p_onboard.add_argument("--mode", choices=["one-liner", "agent-native"], default="agent-native",
                           help="install mode")
    p_onboard.add_argument("--answers", default=None,
                           help="path to the ce-install.answers.yaml IaC answers file "
                                "(schema-validated; fail-closed on unknown keys; secrets by SecretRef only)")
    p_onboard.add_argument("--answers-schema", default=v3_installer.ANSWERS_SCHEMA_PATH,
                           help="the answers schema document (the input-inventory source of truth)")
    p_onboard.add_argument("--inventory", action="store_true",
                           help="emit the operator-input inventory (the agent-awareness artifact) and exit")
    p_onboard.add_argument("--plan", action="store_true", dest="show_plan",
                           help="terraform-plan analog: the full plan incl. the exact remaining asks "
                                "+ the decomposed GitHub leg (no execution)")
    p_onboard.add_argument("--non-interactive", action="store_true",
                           help="fail-closed: refuse with the exact missing list instead of ever asking")
    p_onboard.add_argument("--opt-out", action="store_true",
                           help="opt out of spend CAPS (ratified-human-only; detection net stays on)")
    p_onboard.add_argument("--ratified-prompt-sha", default=None, help="64-hex opt-out ratification digest")
    p_onboard.add_argument("--approver-ref", default=None, help="64-hex opt-out approver digest")
    p_onboard.add_argument("--json", action="store_true", dest="json_output", help="emit machine-readable JSON")

    p_guide = sub.add_parser("guide", help="print the in-product CE guide (what CE is + the five stages)")
    p_guide.add_argument("--json", action="store_true", dest="json_output", help="emit machine-readable JSON")

    p_cockpit = sub.add_parser(
        "cockpit",
        help="the governed fleet Cockpit — read-only board + governance view "
        "(CE_DEMO=1 for the seeded demo; --json dumps the L2 snapshot, textual-free; "
        "--serve opens the same app in a browser: loopback-only, token-gated)",
    )
    _add_root(p_cockpit)
    p_cockpit.add_argument(
        "--serve", action="store_true",
        help="serve the SAME app in a browser on demand (127.0.0.1-only, "
        "token-gated, Host-validated; exits with the command — no daemon)",
    )
    p_cockpit.add_argument(
        "--host", default="127.0.0.1",
        help="serve bind host — loopback ONLY; any non-loopback value is refused",
    )
    p_cockpit.add_argument(
        "--port", type=int, default=8000, help="serve port (default: 8000)",
    )

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
    "collect": _cmd_collect,
    "pr": _cmd_pr,
    "review": _cmd_review,
    "merge": _cmd_merge,
    "escalation": _cmd_escalation,
    "notify": _cmd_notify,
    "status": _cmd_status,
    "show": _cmd_show,
    "artifacts": _cmd_artifacts,
    "report": _cmd_report,
    "onboard": _cmd_onboard,
    "guide": _cmd_guide,
    "session": _cmd_session,
    "cockpit": _cmd_cockpit,
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
