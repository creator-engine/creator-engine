"""Pure-Python worktree dispatch core for claimed governed work.

The dispatch flow is intentionally small and injectable:

1. acquire the forge work claim;
2. allocate a governed worktree lane;
3. run the harness in a scrubbed worker environment;
4. push only after a successful harness exit;
5. release the PCO allocation first, then the forge claim.
"""
from __future__ import annotations

import hashlib
import subprocess
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from . import pco_allocator, work_claims, worker_spawn


ExecFn = Callable[..., Any]
PushFn = Callable[[Path, str], Any]


@dataclass(frozen=True)
class DispatchSpec:
    """Inputs for one governed worktree dispatch."""

    repo_root: Path
    ledger_root: Path
    worktree_root: Path
    controller_id: str
    work_key: work_claims.WorkKey
    branch: str
    brief_path: Path
    harness_cmd: Sequence[str]
    lease_seconds: int = 3600
    claim_reason: str = "implement"


@dataclass(frozen=True)
class DispatchOutcome:
    """Result of one dispatch attempt."""

    dispatched: bool
    stage: str
    reason: str | None
    branch: str
    worktree_path: Path
    pushed: bool
    exec_returncode: int | None
    lane_id: str
    claim_id: str | None = None


def _lane_id(spec: DispatchSpec) -> str:
    """Return a deterministic schema-valid lane id, bounded to 64 chars."""
    suffix = hashlib.sha256(spec.work_key.work_key.encode("utf-8")).hexdigest()[:8]
    prefix = _slug(
        f"dispatch-{spec.work_key.owner}-{spec.work_key.repo}-{spec.work_key.number}"
    )
    prefix = prefix[:55].rstrip("-") or "dispatch"
    return f"{prefix}-{suffix}"


def _worktree_path(spec: DispatchSpec, lane_id: str) -> Path:
    return spec.worktree_root / lane_id


def dispatch(
    spec: DispatchSpec,
    *,
    gh_runner: work_claims.GhRunner | None = None,
    exec_fn: ExecFn | None = None,
    push_fn: PushFn | None = None,
    now: datetime | Callable[[], datetime] | None = None,
) -> DispatchOutcome:
    """Claim, allocate, execute, push on success, and always release."""
    runner = gh_runner or work_claims.default_gh_runner
    executor = exec_fn or _default_exec
    pusher = push_fn or _default_push
    when = _coerce_now(now)

    lane_id = _lane_id(spec)
    worktree = _worktree_path(spec, lane_id)
    holder = spec.controller_id
    host = spec.controller_id

    try:
        claim_result = work_claims.acquire(
            spec.work_key,
            runner,
            holder=holder,
            host=host,
            reason=spec.claim_reason,
            now=when,
        )
    except Exception as exc:
        return _outcome(
            spec,
            lane_id=lane_id,
            worktree=worktree,
            stage="claim",
            reason=str(exc),
        )
    if not claim_result.ok:
        return _outcome(
            spec,
            lane_id=lane_id,
            worktree=worktree,
            stage="claim",
            reason=claim_result.refusal_reason or claim_result.note,
        )

    claim_id = claim_result.claim_id
    try:
        pco_allocator.allocate(
            repo_root=spec.repo_root,
            ledger_root=spec.ledger_root,
            lane_id=lane_id,
            worktree_path=worktree,
            envelope_ref=str(spec.brief_path),
            branch=spec.branch,
            controller_id=spec.controller_id,
            lease_seconds=spec.lease_seconds,
        )
    except pco_allocator.PcoAllocatorError as exc:
        _best_effort_claim_release(
            spec.work_key,
            runner,
            claim_id,
            holder=holder,
            host=host,
            reason="aborted",
            now=when,
        )
        return _outcome(
            spec,
            lane_id=lane_id,
            worktree=worktree,
            stage="allocate",
            reason=str(exc),
            claim_id=claim_id,
        )

    outcome: DispatchOutcome | None = None

    try:
        try:
            child_env, _scrubbed = worker_spawn.scrub_worker_environment(
                worker_id=lane_id,
                role="implementer",
                scope_id=spec.work_key.work_key,
                depth=1,
                parent_id=spec.controller_id,
                home_path=(
                    worktree / ".ce" / "state" / "workers" / lane_id / "home"
                ),
            )
            exec_result = executor(
                spec.harness_cmd,
                cwd=worktree,
                env=child_env,
                brief_path=spec.brief_path,
            )
            exec_rc = _returncode(exec_result)
        except Exception as exc:
            outcome = _outcome(
                spec,
                lane_id=lane_id,
                worktree=worktree,
                stage="exec",
                reason=f"exec failed: {exc}",
                claim_id=claim_id,
            )
        else:
            if exec_rc != 0:
                outcome = _outcome(
                    spec,
                    lane_id=lane_id,
                    worktree=worktree,
                    stage="exec",
                    reason=f"harness exited {exec_rc}",
                    claim_id=claim_id,
                    exec_returncode=exec_rc,
                )
            else:
                try:
                    push_result = pusher(worktree, spec.branch)
                    push_rc = _returncode(push_result)
                except Exception as exc:
                    outcome = _outcome(
                        spec,
                        lane_id=lane_id,
                        worktree=worktree,
                        stage="push",
                        reason=f"push failed: {exc}",
                        claim_id=claim_id,
                        exec_returncode=exec_rc,
                    )
                else:
                    pushed = push_rc == 0
                    outcome = _outcome(
                        spec,
                        lane_id=lane_id,
                        worktree=worktree,
                        dispatched=pushed,
                        stage="complete" if pushed else "push",
                        reason=None if pushed else f"push exited {push_rc}",
                        pushed=pushed,
                        claim_id=claim_id,
                        exec_returncode=exec_rc,
                    )
    finally:
        completed = bool(outcome and outcome.dispatched)
        try:
            pco_allocator.release(
                repo_root=spec.repo_root,
                ledger_root=spec.ledger_root,
                lane_id=lane_id,
                controller_id=spec.controller_id,
                release_reason="completed" if completed else "aborted",
            )
        except Exception:
            pass

        if completed and claim_id:
            try:
                work_claims.release(
                    spec.work_key,
                    runner,
                    holder=holder,
                    host=host,
                    claim_id=claim_id,
                    reason="completed",
                    now=when,
                )
            except Exception:
                _best_effort_claim_release(
                    spec.work_key,
                    runner,
                    claim_id,
                    holder=holder,
                    host=host,
                    reason="completed",
                    now=when,
                )
        else:
            _best_effort_claim_release(
                spec.work_key,
                runner,
                claim_id,
                holder=holder,
                host=host,
                reason="aborted",
                now=when,
            )

    if outcome is None:
        outcome = _outcome(
            spec,
            lane_id=lane_id,
            worktree=worktree,
            stage="exec",
            reason="dispatch stopped before execution completed",
            claim_id=claim_id,
        )
    return _outcome(
        spec,
        lane_id=lane_id,
        worktree=worktree,
        dispatched=outcome.dispatched,
        stage=outcome.stage,
        reason=outcome.reason,
        pushed=outcome.pushed,
        claim_id=outcome.claim_id,
        exec_returncode=outcome.exec_returncode,
    )


def _default_exec(
    harness_cmd: Sequence[str],
    *,
    cwd: Path | str,
    env: Mapping[str, str],
    brief_path: Path | str,
) -> subprocess.CompletedProcess[str]:  # pragma: no cover - live subprocess edge
    """Default harness executor used when no test seam is injected."""
    child_env = dict(env)
    child_env["CE_DISPATCH_BRIEF_PATH"] = str(brief_path)
    return subprocess.run(
        [str(part) for part in harness_cmd],
        cwd=str(cwd),
        env=child_env,
        check=False,
        capture_output=True,
        text=True,
    )


def _default_push(
    worktree: Path,
    branch: str,
) -> subprocess.CompletedProcess[str]:  # pragma: no cover - live git edge
    """Default push seam: push the dispatched branch from the worktree."""
    return subprocess.run(
        ["git", "push", "-u", "origin", branch],
        cwd=str(worktree),
        check=False,
        capture_output=True,
        text=True,
    )


def _outcome(
    spec: DispatchSpec,
    *,
    lane_id: str,
    worktree: Path,
    stage: str,
    reason: str | None,
    dispatched: bool = False,
    pushed: bool = False,
    claim_id: str | None = None,
    exec_returncode: int | None = None,
) -> DispatchOutcome:
    return DispatchOutcome(
        dispatched=dispatched,
        stage=stage,
        reason=reason,
        branch=spec.branch,
        worktree_path=worktree,
        pushed=pushed,
        exec_returncode=exec_returncode,
        lane_id=lane_id,
        claim_id=claim_id,
    )


def _coerce_now(now: datetime | Callable[[], datetime] | None) -> datetime:
    value = now() if callable(now) else now
    if value is None:
        return datetime.now(timezone.utc)
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _returncode(result: Any) -> int:
    if isinstance(result, int):
        return result
    rc = getattr(result, "returncode", None)
    if rc is None:
        return 0
    return int(rc)


def _best_effort_claim_release(
    work_key: work_claims.WorkKey,
    runner: work_claims.GhRunner,
    claim_id: str | None,
    *,
    holder: str,
    host: str,
    reason: str,
    now: datetime,
) -> bool:
    if not claim_id:
        return False
    return work_claims.best_effort_release(
        work_key,
        runner,
        claim_id,
        holder=holder,
        host=host,
        reason=reason,
        now=now,
    )


def _slug(value: str) -> str:
    text = "".join(ch.lower() if ch.isalnum() else "-" for ch in str(value))
    text = "-".join(part for part in text.split("-") if part)
    return text or "dispatch"
