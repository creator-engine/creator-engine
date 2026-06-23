"""ce-ops#216 Unit 3 - deterministic integrator executor with race guard.

The resolver leg is intentionally read-only: it returns deterministic content
and evidence, but never writes. This module owns the write boundary. It accepts
Unit 1 ``repair-needed`` events plus Unit 2 resolver output, re-checks the live
PR/base refs through an injected adapter, applies only already-resolved content,
then re-checks refs again before push/requeue.

No live forge or git operation is performed here directly. Production callers
provide an adapter with the write authority; tests provide a fake adapter.
"""

from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import PurePosixPath
from typing import Any, Protocol

from ._redact import redact_gh_stderr
from .deterministic_resolvers import ResolverResult
from .eviction_detection import RepairNeededEvent

_REPO_RE = re.compile(r"^[^/\s]+/[^/\s]+$")
_SHA_RE = re.compile(r"^[0-9a-fA-F]{40}$")


@dataclass(frozen=True)
class ExecutorRefs:
    """Current refs used by the executor's pre-write and pre-push race guards."""

    pr_head_sha: str
    base_sha: str


@dataclass(frozen=True)
class ExecutorPublishResult:
    """Adapter-owned push/requeue outcome, kept secret-free by the executor."""

    pushed: bool
    requeued: bool
    evidence: tuple[str, ...] = ()


@dataclass(frozen=True)
class ResolutionPlan:
    """Resolved deterministic content plus the base SHA observed while resolving."""

    resolver_result: ResolverResult
    expected_base_sha: str
    files: Mapping[str, str] | None = None


class ExecutorAdapter(Protocol):
    """Write-authority seam for integrator repair execution."""

    def current_refs(self, repo: str, pr_number: int) -> ExecutorRefs:
        """Return the current PR head and base/main SHA."""

    def apply_resolved_content(self, repo: str, pr_number: int, files: dict[str, str]) -> tuple[str, ...]:
        """Write the deterministic file contents and return applied paths."""

    def push_and_requeue(self, repo: str, pr_number: int) -> ExecutorPublishResult:
        """Push the repaired branch and re-enqueue it for integration."""


@dataclass(frozen=True)
class IntegratorExecutionResult:
    """Structured, secret-free executor outcome."""

    repo: str
    pr_number: int
    resolver: str | None
    accepted: bool
    applied_paths: tuple[str, ...]
    pushed: bool
    requeued: bool
    refusal_reason: str | None
    evidence: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "repo": self.repo,
            "pr_number": self.pr_number,
            "resolver": self.resolver,
            "accepted": self.accepted,
            "applied_paths": list(self.applied_paths),
            "pushed": self.pushed,
            "requeued": self.requeued,
            "refusal_reason": self.refusal_reason,
            "evidence": [_redact(item) for item in self.evidence],
        }


def execute_integrator_repair(
    event: RepairNeededEvent | Mapping[str, Any],
    resolution: ResolverResult | ResolutionPlan,
    *,
    adapter: ExecutorAdapter,
    expected_base_sha: str | None = None,
) -> IntegratorExecutionResult:
    """Apply deterministic repair content, guarded against PR/base races.

    The function refuses before touching the adapter's write methods unless the
    resolver output is resolved, non-semantic, and contains concrete file
    content. It checks the live PR head/base immediately before writing and
    again immediately before push/requeue; either movement aborts the next side
    effect.
    """

    parsed_event = _parse_event(event)
    if parsed_event["refusal_reason"]:
        return _refused(
            repo=parsed_event["repo"],
            pr_number=parsed_event["pr_number"],
            resolver=None,
            reason=parsed_event["refusal_reason"],
            evidence=parsed_event["evidence"],
        )

    plan = _coerce_plan(resolution, expected_base_sha=expected_base_sha)
    result = plan.resolver_result
    repo = parsed_event["repo"]
    pr_number = parsed_event["pr_number"]
    expected_head = parsed_event["head_sha"]
    expected_base = (plan.expected_base_sha or "").strip()

    if not _valid_sha(expected_base):
        return _refused(
            repo=repo,
            pr_number=pr_number,
            resolver=result.resolver,
            reason="missing_expected_base_sha",
            evidence=("expected_base_sha must be a 40-character git SHA",),
        )

    files_or_reason = _resolved_files(plan)
    if isinstance(files_or_reason, str):
        return _refused(
            repo=repo,
            pr_number=pr_number,
            resolver=result.resolver,
            reason=files_or_reason,
            evidence=result.evidence,
        )
    files = files_or_reason

    first_guard = _race_refusal(
        adapter.current_refs(repo, pr_number),
        expected_head=expected_head,
        expected_base=expected_base,
        suffix="",
    )
    if first_guard is not None:
        return _refused(repo=repo, pr_number=pr_number, resolver=result.resolver, **first_guard)

    applied_paths = tuple(adapter.apply_resolved_content(repo, pr_number, dict(files)))

    second_guard = _race_refusal(
        adapter.current_refs(repo, pr_number),
        expected_head=expected_head,
        expected_base=expected_base,
        suffix="_before_push",
    )
    if second_guard is not None:
        return _refused(
            repo=repo,
            pr_number=pr_number,
            resolver=result.resolver,
            applied_paths=applied_paths,
            **second_guard,
        )

    published = adapter.push_and_requeue(repo, pr_number)
    return IntegratorExecutionResult(
        repo=repo,
        pr_number=pr_number,
        resolver=result.resolver,
        accepted=True,
        applied_paths=tuple(sorted(applied_paths)),
        pushed=bool(published.pushed),
        requeued=bool(published.requeued),
        refusal_reason=None,
        evidence=_evidence(
            (
                f"resolver={result.resolver}",
                *result.evidence,
                "race_guard=passed_before_write",
                "race_guard=passed_before_push",
                *published.evidence,
            )
        ),
    )


def _parse_event(event: RepairNeededEvent | Mapping[str, Any]) -> dict[str, Any]:
    payload: Mapping[str, Any]
    if isinstance(event, RepairNeededEvent):
        payload = event.to_dict()
    elif isinstance(event, Mapping):
        payload = event
    else:
        return {
            "repo": "",
            "pr_number": 0,
            "head_sha": "",
            "refusal_reason": "malformed_event",
            "evidence": ("event must be RepairNeededEvent or mapping",),
        }

    repo = str(payload.get("repo") or "").strip()
    pr_number = payload.get("pr_number")
    head_sha = str(payload.get("head_sha") or "").strip()
    if payload.get("event_type") != "repair-needed":
        return {
            "repo": repo,
            "pr_number": pr_number if isinstance(pr_number, int) else 0,
            "head_sha": head_sha,
            "refusal_reason": "malformed_event",
            "evidence": ("event_type must be repair-needed",),
        }
    if not _REPO_RE.match(repo):
        return {
            "repo": repo,
            "pr_number": pr_number if isinstance(pr_number, int) else 0,
            "head_sha": head_sha,
            "refusal_reason": "malformed_event",
            "evidence": (f"repo={repo!r} is not owner/name",),
        }
    if not isinstance(pr_number, int) or isinstance(pr_number, bool) or pr_number <= 0:
        return {
            "repo": repo,
            "pr_number": 0,
            "head_sha": head_sha,
            "refusal_reason": "malformed_event",
            "evidence": ("pr_number must be a positive integer",),
        }
    if not _valid_sha(head_sha):
        return {
            "repo": repo,
            "pr_number": pr_number,
            "head_sha": head_sha,
            "refusal_reason": "malformed_event",
            "evidence": ("head_sha must be a 40-character git SHA",),
        }
    return {
        "repo": repo,
        "pr_number": pr_number,
        "head_sha": head_sha.lower(),
        "refusal_reason": None,
        "evidence": (),
    }


def _coerce_plan(
    resolution: ResolverResult | ResolutionPlan, *, expected_base_sha: str | None
) -> ResolutionPlan:
    if isinstance(resolution, ResolutionPlan):
        return resolution
    return ResolutionPlan(resolver_result=resolution, expected_base_sha=expected_base_sha or "")


def _resolved_files(plan: ResolutionPlan) -> dict[str, str] | str:
    result = plan.resolver_result
    if not result.applicable:
        return "resolver_not_applicable"
    if result.unresolved or not result.resolved:
        return "resolver_unresolved"
    changed_paths = tuple(result.changed_paths)
    if not changed_paths:
        return "missing_changed_paths"
    for path in changed_paths:
        if not _safe_repo_path(path):
            return "unsafe_resolved_path"

    if plan.files is not None:
        files = dict(plan.files)
        if set(files) != set(changed_paths):
            return "resolved_content_path_mismatch"
        if any(not isinstance(content, str) for content in files.values()):
            return "missing_resolved_content"
        return {path: files[path] for path in sorted(files)}

    if result.content is None:
        return "missing_resolved_content"
    if len(changed_paths) != 1:
        return "missing_resolved_content"
    return {changed_paths[0]: result.content}


def _race_refusal(
    refs: ExecutorRefs, *, expected_head: str, expected_base: str, suffix: str
) -> dict[str, Any] | None:
    actual_head = (refs.pr_head_sha or "").strip().lower()
    actual_base = (refs.base_sha or "").strip().lower()
    expected_head = expected_head.lower()
    expected_base = expected_base.lower()
    if actual_head != expected_head:
        return {
            "reason": f"race_guard_head_moved{suffix}",
            "evidence": (f"expected_head={expected_head}", f"actual_head={actual_head}"),
        }
    if actual_base != expected_base:
        return {
            "reason": f"race_guard_base_moved{suffix}",
            "evidence": (f"expected_base={expected_base}", f"actual_base={actual_base}"),
        }
    return None


def _refused(
    *,
    repo: str,
    pr_number: int,
    resolver: str | None,
    reason: str,
    evidence: tuple[str, ...],
    applied_paths: tuple[str, ...] = (),
) -> IntegratorExecutionResult:
    return IntegratorExecutionResult(
        repo=repo,
        pr_number=pr_number,
        resolver=resolver,
        accepted=False,
        applied_paths=tuple(sorted(applied_paths)),
        pushed=False,
        requeued=False,
        refusal_reason=reason,
        evidence=_evidence(evidence),
    )


def _valid_sha(value: str) -> bool:
    return bool(_SHA_RE.fullmatch((value or "").strip()))


def _safe_repo_path(path: str) -> bool:
    if not isinstance(path, str) or not path.strip():
        return False
    pure = PurePosixPath(path)
    return not pure.is_absolute() and ".." not in pure.parts


def _evidence(items: tuple[str, ...]) -> tuple[str, ...]:
    return tuple(_redact(str(item)) for item in items)


def _redact(value: str) -> str:
    return redact_gh_stderr(value)
