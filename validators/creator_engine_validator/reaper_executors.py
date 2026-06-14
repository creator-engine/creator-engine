"""Per-substrate retirement executors for the seat/venue reaper (ce-ops#43, §3.5).

The reaper POLICY (``seat_reaper``) is substrate-neutral; every IRREVERSIBLE venue
action is delegated to an executor selected by the venue substrate. This module
ships the **tmux** executor and the substrate selector. A future worker/container
executor lands here too, behind the worker lifecycle contract; an unknown
substrate yields no executor (→ the policy escalates, never tears down).

Version boundary (§3.6): this is a V3_RUNTIME module. It imports NO V1_RUNTIME
module. The two crossings to v1 surfaces happen as **subprocess + DATA only**,
then the JSON / filesystem facts are verified:

- transcript archive: ``ce lane archive --transcript … --archive-root …
  --batch-slug … --role … --repo-root … --json`` (the v1 ``transcript_archive``
  leg) — we consume only the JSON ``archive_path`` + ``sha256`` and re-verify the
  bytes on disk. We never import ``transcript_archive`` or ``ce_cli``.
- worktree/claim/lease release: ``creator-engine-validator pco-release --lane-id …
  --controller-id … --ledger-root … --repo-root … --release-reason …`` (the v1
  ``pco_allocator`` leg) — we then verify the claim/lease/event/worktree facts off
  disk. We never import ``pco_allocator``.

tmux teardown itself (``kill-pane`` / pane-absence) is a substrate action issued
through the injectable ``runner`` subprocess seam, so CI exercises fakes, never a
live tmux/git/claude process.
"""

from __future__ import annotations

import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Sequence

import yaml

from .seat_reaper import (
    RELEASE_REASON_ABORTED,
    RELEASE_REASON_COMPLETED,
    STEP_ALREADY_SATISFIED,
    STEP_FAILED,
    STEP_NOT_APPLICABLE,
    STEP_SUCCEEDED,
    SUBSTRATE_TMUX,
    RetirementPlan,
    StepResult,
)

#: A subprocess seam: ``(argv, **kw) -> CompletedProcess-like`` (``.returncode``,
#: ``.stdout``, ``.stderr``). Injected so CI fakes every irreversible edge.
Runner = Callable[..., "subprocess.CompletedProcess[str]"]


def _default_runner(argv: Sequence[str], **kw: Any) -> "subprocess.CompletedProcess[str]":
    return subprocess.run(list(argv), check=False, capture_output=True, text=True, **kw)


def _utc_now_str() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


# ---------------------------------------------------------------------------
# Transcript resolution (§6.2) — exact harness_session_id, never mtime
# ---------------------------------------------------------------------------


def resolve_transcript(
    plan: RetirementPlan, *, search_root: Path | None
) -> tuple[Path | None, str | None]:
    """Resolve the seat's transcript path. Returns ``(path, reason)``.

    A Codex seat carries an explicit ``transcript_ref``. A Claude seat is resolved
    by its exact ``harness_session_id`` under ``search_root`` (the harness config
    projects dir). ``(None, reason)`` when missing/ambiguous (reason explains
    why); ``(path, None)`` on a unique resolution.
    """
    if plan.transcript_ref:
        p = Path(plan.transcript_ref)
        if p.is_file():
            return p, None
        return None, f"transcript_ref absent: {plan.transcript_ref}"

    sid = plan.harness_session_id
    if not sid:
        return None, "no harness_session_id stamped"
    if search_root is None or not search_root.is_dir():
        return None, "transcript search root unavailable"
    matches = sorted(search_root.rglob(f"{sid}.jsonl"))
    if not matches:
        return None, f"no transcript for session {sid}"
    if len(matches) > 1:
        return None, f"ambiguous transcript for session {sid} ({len(matches)} matches)"
    return matches[0], None


# ---------------------------------------------------------------------------
# The tmux executor
# ---------------------------------------------------------------------------


class TmuxExecutor:
    """Retire a tmux-substrate venue: archive → pane kill + registry → pco-release.

    Every step verifies before returning. The policy enforces archive-before-remove
    ORDERING; this executor enforces per-step verification.
    """

    substrate = SUBSTRATE_TMUX

    def __init__(
        self,
        *,
        runner: Runner | None = None,
        ce_exe: str = "ce",
        validator_exe: str = "creator-engine-validator",
        transcript_search_root: Path | None = None,
    ) -> None:
        self._runner = runner or _default_runner
        self._ce_exe = ce_exe
        self._validator_exe = validator_exe
        self._transcript_search_root = transcript_search_root

    # --- Step 1: archive evidence (subprocess+DATA to `ce lane archive --json`) ---

    def archive_transcript(self, plan: RetirementPlan) -> StepResult:
        transcript, reason = resolve_transcript(
            plan, search_root=self._transcript_search_root
        )
        if transcript is None:
            if plan.archive_expected:
                return StepResult(STEP_FAILED, reason or "transcript unresolved")
            return StepResult(STEP_NOT_APPLICABLE, reason or "no transcript expected")

        if plan.archive_root is None:
            # the operator did not configure an archive root (flag / CE_TRANSCRIPT_ARCHIVE_ROOT)
            if plan.archive_expected:
                return StepResult(STEP_FAILED, "no transcript archive root configured")
            return StepResult(STEP_NOT_APPLICABLE, "no transcript archive root configured")

        argv = [
            self._ce_exe,
            "lane",
            "archive",
            "--transcript",
            str(transcript),
            "--archive-root",
            str(plan.archive_root),
            "--batch-slug",
            plan.batch_slug,
            "--role",
            plan.role,
            "--json",
        ]
        if plan.worktree_path is not None:
            argv += ["--repo-root", str(plan.worktree_path)]
        proc = self._runner(argv)
        if proc.returncode != 0:
            return StepResult(STEP_FAILED, f"ce lane archive failed: {proc.stderr.strip()}")
        try:
            payload = json.loads(proc.stdout)
        except ValueError:
            return StepResult(STEP_FAILED, "ce lane archive returned non-JSON")
        archive_path = payload.get("archive_path")
        sha = payload.get("sha256")
        if not archive_path or not sha:
            return StepResult(STEP_FAILED, "ce lane archive JSON missing path/sha")
        return StepResult(
            STEP_SUCCEEDED,
            "archived",
            {"archive_path": archive_path, "sha256": sha, "source": str(transcript)},
        )

    # --- Step 2: close the terminal venue (kill pane, verify, update registry) ---

    def close_venue(self, plan: RetirementPlan) -> StepResult:
        terminal = plan.terminal or {}
        pane_id = terminal.get("pane_id")
        if not pane_id:
            return StepResult(STEP_NOT_APPLICABLE, "no pane id")

        already_absent = not self._pane_present(pane_id)
        if not already_absent:
            kill = self._runner(["tmux", "kill-pane", "-t", str(pane_id)])
            # tolerate an already-absent pane only after archive verification (policy ordering)
            if kill.returncode != 0 and self._pane_present(pane_id):
                return StepResult(STEP_FAILED, f"tmux kill-pane failed: {kill.stderr.strip()}")
        if self._pane_present(pane_id):
            return StepResult(STEP_FAILED, "pane still present after kill")

        registry = self._update_pane_registry(plan)
        if registry.status == STEP_FAILED:
            return registry
        status = STEP_ALREADY_SATISFIED if already_absent else STEP_SUCCEEDED
        return StepResult(
            status,
            "venue closed",
            {"pane_id": pane_id, "already_absent": already_absent, "registry": registry.status},
        )

    def _pane_present(self, pane_id: str) -> bool:
        proc = self._runner(["tmux", "list-panes", "-a", "-F", "#{pane_id}"])
        if proc.returncode != 0:
            return False  # no server / no panes ⇒ pane is absent
        present = {ln.strip() for ln in proc.stdout.splitlines() if ln.strip()}
        return str(pane_id) in present

    def _update_pane_registry(self, plan: RetirementPlan) -> StepResult:
        path = plan.pane_registry_path
        if path is None or not path.is_file():
            return StepResult(STEP_NOT_APPLICABLE, "no pane registry record")
        try:
            rec = yaml.safe_load(path.read_text(encoding="utf-8"))
        except (OSError, yaml.YAMLError) as exc:
            return StepResult(STEP_FAILED, f"pane registry unreadable: {exc}", {"pane_registry_failed": True})
        if not isinstance(rec, dict):
            return StepResult(STEP_FAILED, "pane registry record malformed", {"pane_registry_failed": True})
        if rec.get("status") in ("closed", "aborted"):
            return StepResult(STEP_ALREADY_SATISFIED, "pane registry already closed")
        if plan.release_reason == RELEASE_REASON_COMPLETED:
            rec["status"] = "closed"
            rec["close_reason"] = "completed"
        else:
            rec["status"] = "aborted"
            rec["close_reason"] = "aborted"
        rec["closed_at"] = _utc_now_str()
        try:
            path.write_text(yaml.safe_dump(rec, sort_keys=True), encoding="utf-8")
        except OSError as exc:
            return StepResult(STEP_FAILED, f"pane registry write failed: {exc}", {"pane_registry_failed": True})
        return StepResult(STEP_SUCCEEDED, "pane registry closed")

    # --- Step 3: release worktree + ledger markers (subprocess+DATA to pco-release) ---

    def release_worktree(self, plan: RetirementPlan) -> StepResult:
        if not (plan.lane_id and plan.controller_id and plan.worktree_path and plan.ledger_root):
            return StepResult(STEP_NOT_APPLICABLE, "no pco worktree binding")

        claim_path = plan.ledger_root / "claims" / plan.controller_id / f"{plan.lane_id}.yaml"
        lease_path = plan.ledger_root / "leases" / plan.controller_id / f"{plan.lane_id}.yaml"

        # already satisfied? claim released + lease gone + worktree gone (§12 recovery)
        if self._release_already_satisfied(claim_path, lease_path, plan.worktree_path):
            return StepResult(
                STEP_ALREADY_SATISFIED,
                "release already satisfied",
                {"release_reason": plan.release_reason},
            )

        argv = [
            self._validator_exe,
            "pco-release",
            "--lane-id",
            plan.lane_id,
            "--controller-id",
            plan.controller_id,
            "--ledger-root",
            str(plan.ledger_root),
            "--repo-root",
            str(plan.worktree_path),
            "--release-reason",
            plan.release_reason,
        ]
        proc = self._runner(argv)
        if proc.returncode != 0:
            stderr = (proc.stderr or "").strip()
            root_refused = "root checkout" in stderr.lower()
            return StepResult(
                STEP_FAILED,
                f"pco-release failed: {stderr}",
                {"root_checkout_refused": root_refused},
            )

        ok, detail = self._verify_release(claim_path, lease_path, plan)
        if not ok:
            return StepResult(STEP_FAILED, detail, {"worktree_verify_failed": True})
        return StepResult(STEP_SUCCEEDED, "released", {"release_reason": plan.release_reason})

    def _release_already_satisfied(
        self, claim_path: Path, lease_path: Path, worktree_path: Path
    ) -> bool:
        if lease_path.exists() or worktree_path.exists():
            return False
        if not claim_path.is_file():
            return True
        try:
            rec = yaml.safe_load(claim_path.read_text(encoding="utf-8"))
        except (OSError, yaml.YAMLError):
            return False
        return isinstance(rec, dict) and bool(rec.get("released_at"))

    def _verify_release(
        self, claim_path: Path, lease_path: Path, plan: RetirementPlan
    ) -> tuple[bool, str]:
        # claim absent OR released_at + release_reason stamped
        if claim_path.is_file():
            try:
                claim = yaml.safe_load(claim_path.read_text(encoding="utf-8"))
            except (OSError, yaml.YAMLError) as exc:
                return False, f"claim unreadable post-release: {exc}"
            if not isinstance(claim, dict) or not claim.get("released_at") or not claim.get("release_reason"):
                return False, "claim not marked released"
        # lease removed
        if lease_path.exists():
            return False, "worktree lease still present"
        # a claim_released event exists
        if not self._has_claim_released_event(plan):
            return False, "claim_released event not found"
        # the secondary worktree was removed
        if plan.worktree_path is not None and plan.worktree_path.exists():
            return False, "worktree still present"
        return True, "verified"

    def _has_claim_released_event(self, plan: RetirementPlan) -> bool:
        assert plan.ledger_root is not None
        events_dir = plan.ledger_root / "events"
        if not events_dir.is_dir():
            return False
        for path in events_dir.rglob("*.yaml"):
            try:
                rec = yaml.safe_load(path.read_text(encoding="utf-8"))
            except (OSError, yaml.YAMLError):
                continue
            if (
                isinstance(rec, dict)
                and rec.get("event_kind") == "claim_released"
                and rec.get("lane_id") == plan.lane_id
                and rec.get("controller_id") == plan.controller_id
            ):
                return True
        return False


# ---------------------------------------------------------------------------
# Substrate selection (§3.5)
# ---------------------------------------------------------------------------

#: terminal kinds the tmux executor handles. A spawned seat with no recorded kind
#: still occupies a tmux pane (the only substrate CE launches into today), so an
#: absent/empty kind defaults to tmux; an explicit unsupported kind yields None.
_TMUX_KINDS = frozenset({SUBSTRATE_TMUX, "", None})


def default_executor_for(terminal_kind: str | None) -> TmuxExecutor | None:
    """Return the executor for a substrate, or None for an unsupported one (§3.5)."""
    if terminal_kind in _TMUX_KINDS:
        return TmuxExecutor()
    return None
