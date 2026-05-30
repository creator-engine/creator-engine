"""Gate 3 governed lane-launch runtime (`ce lane launch/status/verify`).

Implements the governed lane-launch primitive named in the v1.0 traceability
matrix:

* ``RV1-030`` — ``launch`` spawns/attaches a tmux pane, writes a Pane Registry
  record bound to a live Active-Work Ledger claim, and refuses any
  non-visible surface for a visibility-required role.
* ``RV1-031`` — ``launch`` verifies the consumed prompt/handoff pointer + SHA
  before launch and refuses on mismatch *before any side effect*.
* ``RV1-032`` — ``verify`` checks the stop line + optional completion report;
  ``status`` reads live lane state. (Transcript archiving lives in
  ``transcript_archive``.)

This module performs NO GitHub/tracker mutation, NO branch/worktree
allocation (that is ``pco_allocator``), and NO provider/model launch. It
reuses the existing Active-Work Ledger conflict guard (``pco_allocator.guard``)
and the existing Pane Registry schema/validator.

Prose contract: ``docs/operations/GOVERNED_LANE_LAUNCH_PROTOCOL.md``.
"""
from __future__ import annotations

import hashlib
import json
import os
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Sequence

import yaml

from . import claude_launch_spec
from .checks import operating_mode_policy as _omp
from .checks.active_work_ledger_schema import validate_active_work_ledger_record
from .checks.pane_registry import validate_pane_registry_record
from .loader import LoaderError, load_yaml
from .pco_allocator import guard
from .tmux_adapter import TmuxAdapter, TmuxPane, TmuxUnavailable

# Pane Registry role enum is exactly the visibility-required role set.
VISIBILITY_REQUIRED_ROLES = frozenset({"architect", "implementer", "reviewer", "verification"})
LIVE_STATUSES = frozenset({"active", "blocked", "closing"})

# G2.002.1 operating-mode runtime carriers. `strict` is the default; elevation
# fails closed unless an Operator-ratified tenant policy ratifies the mode.
OPERATING_MODES = frozenset({"strict", "auto", "transcendence"})
ELEVATED_MODES = frozenset({"auto", "transcendence"})
DEFAULT_OPERATING_MODE = "strict"
LANE_KINDS = frozenset({"read-only", "implementation", "review", "approval", "merge", "audit"})

DEFAULT_HOST_ID = "operator-host"
DEFAULT_SESSION = "ce-lane"
TMUX_TERMINAL_KIND = "tmux"

# Safe inert placeholder: keeps the visible pane alive without launching any
# provider, model, or credentialed surface.
INERT_PLACEHOLDER_COMMAND: list[str] = [
    "sh",
    "-c",
    "printf 'ce governed lane placeholder; awaiting operator-driven command\\n'; "
    'exec "${SHELL:-/bin/sh}"',
]


# ---------------------------------------------------------------------------
# Errors
# ---------------------------------------------------------------------------


class LaneError(Exception):
    """Base class for lane-runtime errors. Carries a stable ``code``."""

    code = "G3-LANE-ERROR"


class LaneLaunchError(LaneError):
    code = "G3-LAUNCH-ERROR"


class PromptMissing(LaneLaunchError):
    code = "G3-PROMPT-MISSING"


class PromptShaMismatch(LaneLaunchError):
    code = "G3-PROMPT-SHA-MISMATCH"


class HandoffMissing(LaneLaunchError):
    code = "G3-HANDOFF-MISSING"


class HandoffShaMismatch(LaneLaunchError):
    code = "G3-HANDOFF-SHA-MISMATCH"


class VisibilityRefused(LaneLaunchError):
    code = "G3-VISIBILITY-REFUSED"


class ClaimMissing(LaneLaunchError):
    code = "G3-CLAIM-MISSING"


class ClaimInvalid(LaneLaunchError):
    code = "G3-CLAIM-INVALID"


class ClaimMismatch(LaneLaunchError):
    code = "G3-CLAIM-MISMATCH"


class ClaimReleased(LaneLaunchError):
    code = "G3-CLAIM-RELEASED"


class ConflictGuardRefused(LaneLaunchError):
    code = "G3-CONFLICT-GUARD"


class WorktreePathInvalid(LaneLaunchError):
    code = "G3-WORKTREE-INVALID"


class TmuxUnavailableError(LaneLaunchError):
    code = "G3-TMUX-UNAVAILABLE"


class ClaudeLaunchRefused(LaneLaunchError):
    """CC-G-D Ring 0: a governed Claude lane surface is refused before side effects."""

    code = "G3-CLAUDE-REFUSED"


# G2.002.1 operating-mode runtime-carrier refusals. Each is raised before any
# side effect (no tmux spawn, no Pane Registry write, no ledger write), mirroring
# the G3-* ordering. They preserve — never relax — the Operator-only floor.


class OperatingModeInvalid(LaneLaunchError):
    code = "G2-OPERATING-MODE-INVALID"


class AutonomyClassInvalid(LaneLaunchError):
    code = "G2-AUTONOMY-CLASS-INVALID"


class LaneKindInvalid(LaneLaunchError):
    code = "G2-LANE-KIND-INVALID"


class ReservedAutonomyActive(LaneLaunchError):
    code = "G2-RESERVED-AUTONOMY-ACTIVE"


class AutoWithoutOperatorPolicy(LaneLaunchError):
    code = "G2-AUTO-WITHOUT-OPERATOR-POLICY"


class TranscendenceWithoutOperatorPolicy(LaneLaunchError):
    code = "G2-TRANSCENDENCE-WITHOUT-OPERATOR-POLICY"


class PrivilegedRatifierInvalid(LaneLaunchError):
    code = "G2-PRIVILEGED-RATIFIER-INVALID"


class AgentRatifierActive(LaneLaunchError):
    code = "G2-AGENT-RATIFIER-ACTIVE"


class LaneStatusError(LaneError):
    code = "G3-STATUS-ERROR"


class LaneVerifyError(LaneError):
    code = "G3-VERIFY-ERROR"


# ---------------------------------------------------------------------------
# Results
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class LaunchResult:
    pane_path: Path
    record: dict[str, Any]
    pane: TmuxPane
    claim_path: Path
    # CC-G-D: governed-Claude audit + deterministic closeout pointers. ``None``
    # for non-Claude lanes. These ride the LaunchResult and an ignored sidecar —
    # they are deliberately NOT written into the schema-validated pane record,
    # because ``schemas/pane-registry.schema.yaml`` pins ``unevaluatedProperties:
    # false`` and is outside the CC-G-D allowlist.
    claude_governance: dict[str, Any] | None = None
    # G2.002.1: resolved operating-mode posture for this launch. Carried in-memory
    # for observability; NOT written into the schema-validated pane record (whose
    # schema pins unevaluatedProperties: false and is outside this gate's surface).
    operating_mode: str = DEFAULT_OPERATING_MODE
    autonomy_class: str | None = None
    lane_kind: str | None = None


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _atomic_write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.parent / f"{path.name}.tmp.{os.getpid()}.{uuid.uuid4().hex[:8]}"
    tmp.write_text(content, encoding="utf-8")
    tmp.rename(path)


def _utc_now_str(now: datetime | None) -> str:
    return (now or datetime.now(UTC)).strftime("%Y-%m-%dT%H:%M:%SZ")


def _claim_path(ledger_root: Path, controller_id: str, lane_id: str) -> Path:
    return ledger_root / "claims" / controller_id / f"{lane_id}.yaml"


def _pane_path(ledger_root: Path, controller_id: str, lane_id: str) -> Path:
    return ledger_root / "panes" / controller_id / f"{lane_id}.yaml"


def _governance_sidecar_path(ledger_root: Path, controller_id: str, lane_id: str) -> Path:
    """Ignored sidecar holding CC-G-D governed-Claude audit + closeout pointers.

    Lives next to the Pane Registry record under ignored ``.hermes`` state. The
    pointers are kept here (and on :class:`LaunchResult`) rather than in the
    schema-validated pane record, which pins ``unevaluatedProperties: false``.
    """
    return ledger_root / "panes" / controller_id / f"{lane_id}.claude-governance.json"


def _is_claude_command(command: Sequence[str]) -> bool:
    """True when ``command`` invokes the Claude harness (basename ``claude``)."""
    if not command:
        return False
    head = str(command[0])
    return head == "claude" or head.rsplit("/", 1)[-1] == "claude"


def _confirm_pack(repo_root: Path | str | None) -> bool:
    """Seam: confirm the committed hook-pack is loaded (monkeypatchable in tests).

    Delegates to :func:`hook_pack_confirm.confirm_hook_pack`. Never launches
    Claude and never makes a network call.
    """
    from . import hook_pack_confirm

    return hook_pack_confirm.confirm_hook_pack(Path(repo_root or ".")).confirmed


@dataclass(frozen=True)
class OperatingModeResolution:
    operating_mode: str
    autonomy_class: str | None
    lane_kind: str | None
    ratification_evidence_ref: str | None


def _evaluate_operating_mode(
    *,
    operating_mode: str | None,
    autonomy_class: str | None,
    lane_kind: str | None,
    tenant_policy: Path | str | None,
    ratification_evidence_ref: str | None,
) -> OperatingModeResolution:
    """Evaluate the G2.002.1 operating-mode floor for a lane launch.

    Raises a typed ``G2-*`` refusal (subclass of :class:`LaneLaunchError`) when a
    floor is breached. Returns the resolved posture otherwise. Pure evaluation:
    performs no side effect, so callers raise this before any tmux spawn / Pane
    Registry write / ledger write. ``strict`` is the default; ``auto`` /
    ``transcendence`` are refused unless an Operator-ratified tenant policy
    ratifies the requested mode.
    """
    mode = (str(operating_mode).strip().lower() if operating_mode else DEFAULT_OPERATING_MODE)
    if mode not in OPERATING_MODES:
        raise OperatingModeInvalid(
            f"operating_mode {operating_mode!r} is not one of {sorted(OPERATING_MODES)}"
        )

    autonomy_norm: str | None = None
    if autonomy_class is not None:
        autonomy_norm = _omp._normalize_token(autonomy_class)
        if autonomy_norm not in _omp.AUTONOMY_CLASSES:
            raise AutonomyClassInvalid(
                f"autonomy_class {autonomy_class!r} is not a recognized G2.002.0 value"
            )
        if autonomy_norm == "reserved_future_agent_ratification":
            raise ReservedAutonomyActive(
                "reserved_future_agent_ratification is reserved-inactive and MUST NOT be an active lane autonomy"
            )

    lane_kind_norm: str | None = None
    if lane_kind is not None:
        lane_kind_norm = str(lane_kind).strip().lower()
        if lane_kind_norm not in LANE_KINDS:
            raise LaneKindInvalid(
                f"lane_kind {lane_kind!r} is not one of {sorted(LANE_KINDS)}"
            )

    # When a tenant policy is supplied, the Operator-only floor is enforced in
    # every mode (including strict): a policy that binds an active agent_ratifier
    # or names an advisory/agent role as the privileged ratifier is refused.
    policy: dict[str, Any] | None = None
    policy_codes: set[str] = set()
    if tenant_policy is not None:
        try:
            data = load_yaml(Path(tenant_policy))
        except LoaderError:
            data = None
        policy = data.get("operating_mode_policy") if isinstance(data, dict) else None
        if isinstance(policy, dict):
            policy_codes = {e.code for e in _omp._validate_policy(policy, Path(tenant_policy))}
            if _omp.CODE_AGENT_RATIFIER_ACTIVE in policy_codes:
                raise AgentRatifierActive(
                    f"tenant policy {str(tenant_policy)!r} binds an active agent_ratifier; the reserved-inactive floor holds in every mode"
                )
            if _omp.CODE_PRIVILEGED_FLOOR_AGENT in policy_codes:
                raise PrivilegedRatifierInvalid(
                    f"tenant policy {str(tenant_policy)!r} names an agent/advisory role as a privileged ratifier; privileged classes require required_ratifier_role: operator"
                )

    if mode in ELEVATED_MODES:
        refusal = (
            AutoWithoutOperatorPolicy if mode == "auto" else TranscendenceWithoutOperatorPolicy
        )
        if policy is None:
            raise refusal(
                f"operating_mode {mode!r} requires an Operator-ratified tenant policy (--tenant-policy) that ratifies {mode!r}"
            )
        if policy_codes:
            raise refusal(
                f"tenant policy for {mode!r} fails operating_mode_policy validation; refusing elevation"
            )
        policy_mode = _omp._normalize_token(policy.get("operating_mode", ""))
        if policy_mode != mode or not _omp._operator_policy_pointer_present(policy):
            raise refusal(
                f"tenant policy does not ratify operating_mode {mode!r} with an Operator policy pointer"
            )

    return OperatingModeResolution(
        operating_mode=mode,
        autonomy_class=autonomy_norm,
        lane_kind=lane_kind_norm,
        ratification_evidence_ref=ratification_evidence_ref,
    )


# ---------------------------------------------------------------------------
# ce lane launch
# ---------------------------------------------------------------------------


def launch(
    *,
    controller_id: str,
    lane_id: str,
    role: str,
    prompt: Path | str,
    prompt_sha: str,
    repo_root: Path | str,
    ledger_root: Path | str,
    handoff: Path | str | None = None,
    handoff_sha: str | None = None,
    command: Sequence[str] | None = None,
    terminal_kind: str = TMUX_TERMINAL_KIND,
    host_id: str = DEFAULT_HOST_ID,
    pane_id: str | None = None,
    session: str | None = None,
    window: str | None = None,
    worktree_path: str | None = None,
    branch: str | None = None,
    envelope_ref: str | None = None,
    tmux_adapter: Any | None = None,
    now: datetime | None = None,
    mcp_config_path: str | None = None,
    closeout_file: str | None = None,
    completion_report_ref: str | None = None,
    operating_mode: str | None = None,
    autonomy_class: str | None = None,
    lane_kind: str | None = None,
    tenant_policy: Path | str | None = None,
    ratification_evidence_ref: str | None = None,
) -> LaunchResult:
    """Launch a governed visible lane and write its Pane Registry record.

    All refusals raise before any side effect (no tmux spawn, no Pane Registry
    write). See module docstring for the requirement mapping.
    """
    prompt = Path(prompt)
    ledger_root = Path(ledger_root)

    # 0. G2.002.1 operating-mode floor. `strict` is the default; auto/transcendence
    #    are refused without an Operator-ratified tenant policy, and a tenant policy
    #    that names agent_ratifier / an advisory role as ratifier is refused. All of
    #    this raises before any side effect.
    mode_resolution = _evaluate_operating_mode(
        operating_mode=operating_mode,
        autonomy_class=autonomy_class,
        lane_kind=lane_kind,
        tenant_policy=tenant_policy,
        ratification_evidence_ref=ratification_evidence_ref,
    )

    # 1. Prompt pointer must exist and match its SHA (RV1-031) — before side effects.
    if not prompt.is_file():
        raise PromptMissing(f"prompt pointer not found: {prompt}")
    actual_prompt_sha = _sha256_file(prompt)
    if actual_prompt_sha.lower() != str(prompt_sha).lower():
        raise PromptShaMismatch(
            f"prompt SHA256 mismatch for {prompt}: expected {prompt_sha}, got {actual_prompt_sha}"
        )

    # 2. Optional handoff pointer + SHA (RV1-031).
    if handoff is not None:
        handoff = Path(handoff)
        if not handoff.is_file():
            raise HandoffMissing(f"handoff pointer not found: {handoff}")
        actual_handoff_sha = _sha256_file(handoff)
        if handoff_sha is None or actual_handoff_sha.lower() != str(handoff_sha).lower():
            raise HandoffShaMismatch(
                f"handoff SHA256 mismatch for {handoff}: expected {handoff_sha}, got {actual_handoff_sha}"
            )

    # 3. Visibility: a visibility-required role must use tmux (RV1-030).
    if role in VISIBILITY_REQUIRED_ROLES and terminal_kind != TMUX_TERMINAL_KIND:
        raise VisibilityRefused(
            f"role {role!r} requires an operator-visible tmux lane; "
            f"terminal {terminal_kind!r} is not permitted"
        )

    # 4. Require a live, unreleased, matching Active-Work claim (RV1-030).
    claim_path = _claim_path(ledger_root, controller_id, lane_id)
    if not claim_path.is_file():
        raise ClaimMissing(
            f"no Active-Work claim at {claim_path}; allocate a lane before launch"
        )
    try:
        claim = load_yaml(claim_path)
    except LoaderError as exc:
        raise ClaimInvalid(f"claim at {claim_path} is unreadable: {exc}") from exc
    if not isinstance(claim, dict):
        raise ClaimInvalid(f"claim at {claim_path} is not a YAML mapping")
    claim_errors = validate_active_work_ledger_record(claim, claim_path)
    if claim_errors:
        raise ClaimInvalid(
            f"claim at {claim_path} fails schema validation: "
            + "; ".join(e.format() for e in claim_errors)
        )
    if claim.get("controller_id") != controller_id or claim.get("lane_id") != lane_id:
        raise ClaimMismatch(
            f"claim at {claim_path} names "
            f"{claim.get('controller_id')!r}/{claim.get('lane_id')!r}, "
            f"expected {controller_id!r}/{lane_id!r}"
        )
    if claim.get("released_at"):
        raise ClaimReleased(f"claim at {claim_path} is released; allocate a fresh lane")

    # 5. Reuse the Active-Work Ledger conflict guard (PCO-030) — before pane write.
    guard_result = guard(ledger_root, now=now)
    if not guard_result.ok:
        codes = ", ".join(e.code for e in guard_result.errors)
        raise ConflictGuardRefused(
            f"Active-Work Ledger conflict guard refuses launch: {codes}"
        )

    # 5b. When an explicit ``--worktree-path`` is supplied, refuse a missing /
    #     non-directory path BEFORE any side effect and enforce it as the pane cwd
    #     (tmux ``-c``) so the lane runs in its allocated worktree, not the
    #     controller's cwd. The claim's own ``worktree_path`` stays record metadata
    #     only (it may name a host-agnostic path that need not exist here).
    if worktree_path and not Path(worktree_path).is_dir():
        raise WorktreePathInvalid(
            f"worktree path {str(worktree_path)!r} is not an existing directory; "
            "refusing lane launch before any side effect"
        )

    # 6. CC-G-D Ring 0: when the command is a Claude invocation, refuse prohibited
    #    surfaces and pin the governed command BEFORE any side effect (no tmux
    #    spawn, no Pane Registry write). Non-Claude lanes are untouched.
    launch_command = list(command) if command else list(INERT_PLACEHOLDER_COMMAND)
    claude_governance: dict[str, Any] | None = None
    if _is_claude_command(launch_command):
        requested = list(launch_command[1:])
        spec = claude_launch_spec.parse_claude_argv(requested)
        confirmed = _confirm_pack(repo_root) if spec.skip_permissions else False
        spec_result = claude_launch_spec.evaluate_claude_launch(
            spec, hook_pack_confirmed=confirmed
        )
        if not spec_result.ok:
            codes = ", ".join(r.clause for r in spec_result.refusals)
            surfaces = ", ".join(r.surface for r in spec_result.refusals)
            raise ClaudeLaunchRefused(
                f"refusing governed Claude lane launch: {codes} ({surfaces}) — "
                "Ring 0 refuses before any side effect"
            )
        resolved_mcp = mcp_config_path or f".hermes/{lane_id}/mcp/ce-mcp.json"
        try:
            launch_command = claude_launch_spec.build_governed_claude_command(
                base_argv=requested,
                mcp_config_path=resolved_mcp,
                closeout_file=closeout_file,
                completion_report_ref=completion_report_ref,
            )
        except claude_launch_spec.GovernedCommandError as exc:
            clause = (
                claude_launch_spec.CLAUSE_MCP
                if "MCP config" in str(exc)
                else claude_launch_spec.CLAUSE_LOCAL_SETTINGS
            )
            raise ClaudeLaunchRefused(
                f"refusing governed Claude lane launch: {clause} — {exc}"
            ) from exc
        claude_governance = {
            "harness": "claude",
            "hook_pack_confirmed": bool(confirmed) if spec.skip_permissions else None,
            "setting_sources_pinned": True,
            "strict_mcp_config": True,
            "mcp_config_path": resolved_mcp,
            "closeout_ref": closeout_file,
            "completion_report_ref": completion_report_ref,
        }

    # 6b. tmux must be available for a tmux lane — before pane write (RV1-030).
    adapter = tmux_adapter if tmux_adapter is not None else TmuxAdapter()
    if terminal_kind == TMUX_TERMINAL_KIND and not adapter.is_available():
        raise TmuxUnavailableError(
            "tmux is unavailable; refusing visible lane launch before any side effect"
        )

    # --- Side effects begin here ---

    # 7. Spawn/attach the tmux pane running the (possibly governed) command.
    session_name = session or DEFAULT_SESSION
    window_name = window or lane_id
    try:
        pane = adapter.ensure_pane(
            session=session_name,
            window=window_name,
            command=launch_command,
            cwd=worktree_path or None,
        )
    except TmuxUnavailable as exc:
        raise TmuxUnavailableError(str(exc)) from exc

    # 8. Build + write the Pane Registry record bound to the claim (PCO-050).
    timestamp = _utc_now_str(now)
    record: dict[str, Any] = {
        "kind": "pane-registry-record",
        "record_type": "pane_identity",
        "schema_version": "1",
        "controller_id": controller_id,
        "lane_id": lane_id,
        "claim_ref": f"claims/{controller_id}/{lane_id}.yaml",
        "host_id": host_id,
        "pane_id": pane_id or f"pane-{uuid.uuid4().hex[:8]}",
        "role": role,
        "status": "active",
        "record_timestamp": timestamp,
        "registered_at": timestamp,
        "last_seen_at": timestamp,
        "visibility": "operator_visible",
        "terminal": {
            "kind": TMUX_TERMINAL_KIND,
            "session_id": pane.session_id,
            "window_id": pane.window_id,
            "pane_id": pane.pane_id,
        },
        "claim_record_sha256": _sha256_file(claim_path),
    }
    if pane.pane_tty:
        record["terminal"]["pane_tty"] = pane.pane_tty
    if pane.pane_pid is not None:
        record["terminal"]["pane_pid"] = pane.pane_pid

    # Bind worktree_path/branch/envelope_ref from the claim when not overridden.
    resolved_worktree = worktree_path or claim.get("worktree_path")
    if resolved_worktree:
        record["worktree_path"] = str(resolved_worktree)
    resolved_branch = branch or claim.get("branch")
    if resolved_branch:
        record["branch"] = str(resolved_branch)
    resolved_envelope = envelope_ref or claim.get("envelope_ref")
    if resolved_envelope and resolved_envelope != "none":
        record["envelope_ref"] = str(resolved_envelope)

    pane_path = _pane_path(ledger_root, controller_id, lane_id)
    schema_errors = validate_pane_registry_record(record, pane_path)
    if schema_errors:
        raise LaneLaunchError(
            "internal error: generated Pane Registry record is invalid: "
            + "; ".join(e.format() for e in schema_errors)
        )
    _atomic_write(pane_path, yaml.safe_dump(record, sort_keys=True))

    # 9. CC-G-D: persist the governed-Claude audit + deterministic closeout
    #    pointers to an ignored sidecar (never the tracked-shape pane record).
    if claude_governance is not None:
        sidecar = _governance_sidecar_path(ledger_root, controller_id, lane_id)
        _atomic_write(sidecar, json.dumps(claude_governance, indent=2, sort_keys=True))

    return LaunchResult(
        pane_path=pane_path,
        record=record,
        pane=pane,
        claim_path=claim_path,
        claude_governance=claude_governance,
        operating_mode=mode_resolution.operating_mode,
        autonomy_class=mode_resolution.autonomy_class,
        lane_kind=mode_resolution.lane_kind,
    )


# ---------------------------------------------------------------------------
# ce lane status
# ---------------------------------------------------------------------------


def status(*, controller_id: str, lane_id: str, ledger_root: Path | str) -> dict[str, Any]:
    """Read the Pane Registry record for ``controller_id``/``lane_id``."""
    ledger_root = Path(ledger_root)
    pane_path = _pane_path(ledger_root, controller_id, lane_id)
    if not pane_path.is_file():
        raise LaneStatusError(f"no Pane Registry record at {pane_path}")
    try:
        record = load_yaml(pane_path)
    except LoaderError as exc:
        raise LaneStatusError(f"Pane Registry record at {pane_path} is unreadable: {exc}") from exc
    if not isinstance(record, dict):
        raise LaneStatusError(f"Pane Registry record at {pane_path} is not a YAML mapping")
    terminal = record.get("terminal") or {}
    summary = (
        f"lane {controller_id}/{lane_id}: role={record.get('role')} "
        f"status={record.get('status')} terminal={terminal.get('kind')} "
        f"session={terminal.get('session_id')} pane={terminal.get('pane_id')}"
    )
    return {"pane_path": str(pane_path), "record": record, "summary": summary}


# ---------------------------------------------------------------------------
# ce lane verify
# ---------------------------------------------------------------------------


def verify(
    *,
    controller_id: str,
    lane_id: str,
    ledger_root: Path | str,
    transcript: Path | str,
    stop_line: str,
    completion_report: Path | str | None = None,
) -> dict[str, Any]:
    """Verify a lane closeout without mutating tracked files (RV1-032)."""
    ledger_root = Path(ledger_root)
    transcript = Path(transcript)

    pane_path = _pane_path(ledger_root, controller_id, lane_id)
    if not pane_path.is_file():
        raise LaneVerifyError(f"no Pane Registry record at {pane_path}")

    if not transcript.is_file():
        raise LaneVerifyError(f"transcript not found: {transcript}")
    transcript_text = transcript.read_text(encoding="utf-8", errors="replace")
    if stop_line not in transcript_text:
        raise LaneVerifyError(
            f"transcript {transcript} does not contain the required stop line {stop_line!r}"
        )

    completion_report_ok = None
    if completion_report is not None:
        report_path = Path(completion_report)
        if not report_path.is_file():
            raise LaneVerifyError(f"completion report not found: {report_path}")
        report_text = report_path.read_text(encoding="utf-8", errors="replace")
        if stop_line not in report_text:
            raise LaneVerifyError(
                f"completion report {report_path} does not declare the stop line {stop_line!r}"
            )
        completion_report_ok = True

    return {
        "ok": True,
        "pane_path": str(pane_path),
        "transcript": str(transcript),
        "stop_line": stop_line,
        "completion_report_ok": completion_report_ok,
    }


# ---------------------------------------------------------------------------
# CC-G-D — Ring 0 closeout verification (Ring 2 Stop logic; committed hook stays advisory)
# ---------------------------------------------------------------------------


def verify_closeout(
    *,
    closeout_file: str | None = None,
    completion_report: str | None = None,
    posture: str = "governed",
) -> dict[str, Any]:
    """Evaluate a deterministic closeout against the Ring 2 Stop logic.

    CC-G-D injects the deterministic closeout / ``completion_report_ref``
    pointers (Ring 0 facts) and feeds them to the existing
    :mod:`hook_check` Stop decision so post-hoc verification and the in-band hook
    never diverge. This is a Ring 0 *fact* only: it returns the Claude-hook Stop
    decision shape (``{"decision": "block", ...}`` when a governed closeout is
    incomplete) but **does not** modify or arm the committed advisory Stop hook
    ``.claude/hooks/ce-stop.sh`` — arming hard Stop blocking is a separate gate.
    """
    from . import hook_check

    event = {"hook_event_name": "Stop"}
    context = hook_check.build_context(
        event,
        posture=posture,
        closeout_file=closeout_file,
        completion_report=completion_report,
    )
    decision = hook_check.evaluate(event, context)
    return decision.to_claude_hook_dict()
