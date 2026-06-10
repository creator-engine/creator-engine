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
  subprocess, socket, terminal, clock, rng) from L1-shaped values to ONE
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

from .. import coordination
from ..runtime_evidence_spine import verify_chain

#: Snapshot shape version (bumped additively; consumers tolerate additions).
SNAPSHOT_VERSION = 1

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
SCOPES_SUBDIR = "scopes"
SCOPE_SUFFIX = ".scope.yaml"
PANES_SUBDIR = "panes"
OBSERVATIONS_FILENAME = "observations.ndjson"

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


# ---------------------------------------------------------------------------
# The PURE fold — L1-shaped values -> ONE JSON-serializable snapshot
# ---------------------------------------------------------------------------
def _seat_card(pane: Mapping[str, Any], chains: Mapping[str, Any]) -> dict[str, Any]:
    """Project one pane-registry record to a seat card (PURE).

    ``run_id`` is attributed by the documented join rule: a chain whose
    ``run_id`` equals the seat's ``lane_id`` belongs to the seat (the demo seed
    follows it; a live seat without such a chain carries ``None`` — declared,
    not guessed).
    """
    lane_id = pane.get("lane_id")
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
    }


def _board_card(scope: Mapping[str, Any], signals: Mapping[str, Any]) -> dict[str, Any]:
    """Project one Scope artifact (+ its committed signals) to a board card (PURE).

    The stage column is the canon skin: ``coordination.project_scope_state``
    derives the conserved ``state`` from the signals, and ``PHASE_BY_STATE`` /
    ``BOARD_BY_STATE`` project the phase/board labels — never a third
    vocabulary.
    """
    projection = coordination.project_scope_state(dict(scope), **dict(signals))
    ready, _reasons = coordination.scope_is_ready(scope)
    return {
        "scope_id": scope.get("scope_id"),
        "title": scope.get("intent"),
        "state": projection["state"],
        "phase": projection["phase"],
        "board_label": projection["board"],
        "mutation_class": scope.get("mutation_class"),
        "ready": bool(ready),
        "ratified": coordination.is_ratified(scope),
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


def fold_snapshot(
    *,
    panes: list[dict[str, Any]] | None = None,
    scopes: list[dict[str, Any]] | None = None,
    scope_signals: Mapping[str, Mapping[str, Any]] | None = None,
    chains: Mapping[str, list[dict[str, Any]]] | None = None,
    observations: list[dict[str, Any]] | None = None,
    refusal_chain: list[dict[str, Any]] | None = None,
    envelopes: Mapping[str, Any] | None = None,
    demo: bool = False,
    roots: Mapping[str, str | None] | None = None,
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
    ``envelope_ref``; demo: provided by the seed).
    """
    signals = scope_signals or {}
    chain_map = dict(chains or {})
    envelope_map = dict(envelopes or {})

    seats = [_seat_card(p, chain_map) for p in (panes or []) if isinstance(p, Mapping)]
    seats.sort(key=lambda s: (str(s.get("controller_id")), str(s.get("lane_id"))))

    cards = [
        _board_card(s, signals.get(str(s.get("scope_id")), {}))
        for s in (scopes or [])
        if isinstance(s, Mapping)
    ]
    cards.sort(key=lambda c: str(c.get("scope_id")))
    phase_counts = {phase: 0 for phase in coordination.COGNITIVE_PHASES}
    for card in cards:
        phase_counts[card["phase"]] += 1

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
            "roots": dict(roots or {}),
        },
        "availability": {
            "seats": AVAILABLE if panes is not None else UNAVAILABLE,
            "board": AVAILABLE if scopes is not None else UNAVAILABLE,
            "evidence": AVAILABLE if chains is not None else UNAVAILABLE,
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
        },
        "refusals": {
            "source_label": " + ".join(source_labels) or "unavailable",
            "count": len(feed),
            "entries": feed,
            "chain_verified": (
                verify_chain(refusal_chain) == [] if refusal_chain is not None else None
            ),
        },
        "governance": governance,
        "evidence": evidence,
    }


# ---------------------------------------------------------------------------
# The narrow, injectable load seams (the ONLY file reads in this module)
# ---------------------------------------------------------------------------
def load_chains(state_root: Path) -> dict[str, list[dict[str, Any]]]:
    """Read every ``*.runtime-evidence.yaml`` chain document under ``state_root``.

    Returns ``run_id -> records`` (the ``evidence_sink`` persisted layout:
    ``<root>/<run_id>.runtime-evidence.yaml``). Tolerant: a malformed document
    is skipped, never raised (read-only observability must not crash the view).
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

    chains = load_chains(state) if state.is_dir() else None
    panes = load_panes(ledger) if ledger else None
    return fold_snapshot(
        panes=panes,
        scopes=load_scopes(state),
        chains=chains,
        observations=load_observations(observations) if observations else None,
        refusal_chain=load_refusal_chain(observations) if observations else None,
        envelopes=load_envelopes(panes),
        demo=demo,
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
    candidates = [
        Path(state_root),
        _resolve(ledger_root, env, LEDGER_ROOT_ENV),
        _resolve(observations_dir, env, OBSERVATIONS_DIR_ENV),
    ]
    return [str(p) for p in candidates if p is not None and p.is_dir()]
