"""Rebase-aware re-review reconciliation (ce-ops#151 — the reviews-automation
half of the #188 belt reviews-pickup).

Deterministically resolves stale-review churn so the controller no longer
dismisses superseded reviews by hand (the recurring #309 toil: two stale
``CHANGES_REQUESTED`` reviews on superseded commits while a distinct reviewer
had independently approved the fixed head).

Conservative auto-dismiss rule (the ONLY case that dismisses):

    A ``CHANGES_REQUESTED`` review is dismissed iff
      (a) its ``commit_id`` is no longer the PR head (it reviewed an older
          commit), AND
      (b) the current head carries a fresh ``APPROVED`` review from a
          DIFFERENT reviewer login (the objection is objectively superseded
          by an independent approval on the live head).

Every other stale review — a force-push with no fresh approval, an approval
that simply aged — is classified ``RE_REQUEST_SCOPED`` (re-request the right
reviewer with a scoped reason) and is NEVER auto-dismissed. A live objection on
the current head is ``CURRENT`` and untouched. Every dismissal posts an audit
comment naming the superseding approval.

All GitHub I/O flows through an injectable :data:`GhRunner` (``gh api`` by
default); the pure classification core (:func:`classify_reviews`) takes plain
data and is exhaustively unit-testable with zero I/O.
"""
from __future__ import annotations

import json
import subprocess
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, field

from .github_repo_config import ForgeConfigError, ForgeConfigRefused, GhRunner, _default_gh_runner

#: Verdicts a stale/current review can resolve to.
CURRENT = "current"  # review is on the live head — a standing signal, untouched
DISMISS_SUPERSEDED = "dismiss_superseded"  # stale CR superseded by a fresh independent approval
RE_REQUEST_SCOPED = "re_request_scoped"  # stale, but no fresh approval — re-request, do NOT dismiss


@dataclass(frozen=True)
class Review:
    """One GitHub PR review (latest-per-reviewer is computed by the caller)."""

    review_id: int
    state: str  # APPROVED | CHANGES_REQUESTED | COMMENTED | DISMISSED | ...
    commit_id: str
    reviewer: str


@dataclass(frozen=True)
class ReviewVerdict:
    review: Review
    verdict: str
    reason: str
    superseded_by: str | None = None  # reviewer login of the fresh approval, when DISMISS_SUPERSEDED


@dataclass(frozen=True)
class ReconcileReport:
    pr_number: int
    head_sha: str
    verdicts: tuple[ReviewVerdict, ...] = field(default_factory=tuple)
    dismissed: tuple[int, ...] = field(default_factory=tuple)  # review ids actually dismissed

    @property
    def re_request_needed(self) -> tuple[ReviewVerdict, ...]:
        return tuple(v for v in self.verdicts if v.verdict == RE_REQUEST_SCOPED)


def _latest_per_reviewer(reviews: Sequence[Review]) -> list[Review]:
    """Reduce to each reviewer's LAST decisioning review (input order = chronological).

    Only APPROVED / CHANGES_REQUESTED carry a decision; COMMENTED / DISMISSED do
    not change a reviewer's effective state, so they are ignored for the latest
    decision but a later DISMISSED clears a prior decision.
    """
    latest: dict[str, Review] = {}
    for r in reviews:
        state = (r.state or "").upper()
        if state in ("APPROVED", "CHANGES_REQUESTED"):
            latest[r.reviewer] = r
        elif state == "DISMISSED":
            latest.pop(r.reviewer, None)
    return list(latest.values())


def classify_reviews(reviews: Sequence[Review], head_sha: str) -> list[ReviewVerdict]:
    """Pure classifier (no I/O). Apply the conservative auto-dismiss rule.

    ``reviews`` is the raw chronological review list; ``head_sha`` the current PR
    head. Returns one verdict per effective (latest-per-reviewer) decision.
    """
    if not head_sha:
        raise ForgeConfigRefused("classify_reviews requires a non-empty head_sha (fail-closed)")
    effective = _latest_per_reviewer(reviews)
    # Fresh independent approvals: APPROVED on the live head.
    fresh_approvers = {
        r.reviewer for r in effective
        if r.state.upper() == "APPROVED" and r.commit_id == head_sha
    }
    verdicts: list[ReviewVerdict] = []
    for r in effective:
        state = r.state.upper()
        on_head = r.commit_id == head_sha
        if on_head:
            verdicts.append(ReviewVerdict(r, CURRENT, "review is on the live head"))
            continue
        if state == "CHANGES_REQUESTED":
            superseding = sorted(a for a in fresh_approvers if a != r.reviewer)
            if superseding:
                verdicts.append(ReviewVerdict(
                    r, DISMISS_SUPERSEDED,
                    f"CHANGES_REQUESTED on superseded commit {r.commit_id[:8]}; "
                    f"head {head_sha[:8]} independently APPROVED by {superseding[0]}",
                    superseded_by=superseding[0],
                ))
            else:
                verdicts.append(ReviewVerdict(
                    r, RE_REQUEST_SCOPED,
                    f"CHANGES_REQUESTED on superseded commit {r.commit_id[:8]}; "
                    f"no fresh independent approval on {head_sha[:8]} — re-request, do not dismiss",
                ))
        else:  # a stale APPROVED (or other) — never auto-dismiss; re-request if it gates merge
            verdicts.append(ReviewVerdict(
                r, RE_REQUEST_SCOPED,
                f"{state} on superseded commit {r.commit_id[:8]} — stale; re-request on {head_sha[:8]}",
            ))
    return verdicts


def _gh_json(runner: GhRunner, method: str, path: str, body: Mapping | None = None) -> object:
    argv = ["gh", "api", "-X", method, path]
    input_text = None
    if body is not None:
        argv += ["--input", "-"]
        input_text = json.dumps(body)
    proc = runner(argv, input_text)
    if proc.returncode != 0:
        raise ForgeConfigError(f"gh api {method} {path} failed: {(proc.stderr or '').strip()[:200]}")
    out = (proc.stdout or "").strip()
    return json.loads(out) if out else None


def list_reviews(repo: str, pr_number: int, *, gh_runner: GhRunner | None = None) -> list[Review]:
    """Read all reviews on a PR (read-only). Chronological as GitHub returns them."""
    runner = gh_runner or _default_gh_runner
    raw = _gh_json(runner, "GET", f"repos/{repo}/pulls/{pr_number}/reviews")
    reviews: list[Review] = []
    for item in raw or []:
        if not isinstance(item, Mapping):
            continue
        rid = item.get("id")
        if rid is None:
            continue
        reviews.append(Review(
            review_id=int(rid),
            state=str(item.get("state") or ""),
            commit_id=str(item.get("commit_id") or ""),
            reviewer=str(((item.get("user") or {}) if isinstance(item.get("user"), Mapping) else {}).get("login") or ""),
        ))
    return reviews


def dismiss_review(repo: str, pr_number: int, review_id: int, message: str,
                   *, gh_runner: GhRunner | None = None) -> None:
    """Dismiss one review with an audit ``message`` (the GitHub dismissal endpoint)."""
    if not message.strip():
        raise ForgeConfigRefused("dismiss_review requires a non-empty audit message (fail-closed)")
    runner = gh_runner or _default_gh_runner
    _gh_json(runner, "PUT", f"repos/{repo}/pulls/{pr_number}/reviews/{review_id}/dismissals",
             {"message": message, "event": "DISMISS"})


def reconcile_reviews(repo: str, pr_number: int, head_sha: str, *,
                      gh_runner: GhRunner | None = None, apply: bool = False) -> ReconcileReport:
    """Classify a PR's reviews and (when ``apply``) auto-dismiss the objectively
    superseded ``CHANGES_REQUESTED`` ones with an audit trail.

    Read-only when ``apply=False`` (the dry-run the belt/controller inspects).
    Returns the verdicts + the ids actually dismissed.
    """
    runner = gh_runner or _default_gh_runner
    reviews = list_reviews(repo, pr_number, gh_runner=runner)
    verdicts = classify_reviews(reviews, head_sha)
    dismissed: list[int] = []
    if apply:
        for v in verdicts:
            if v.verdict == DISMISS_SUPERSEDED:
                dismiss_review(
                    repo, pr_number, v.review.review_id,
                    f"Auto-dismissed (ce-ops#151): {v.reason}. The reviewed commit is "
                    f"no longer the head and a distinct reviewer has approved the current "
                    f"head; re-request if you still have a concern on {head_sha[:8]}.",
                    gh_runner=runner,
                )
                dismissed.append(v.review.review_id)
    return ReconcileReport(
        pr_number=pr_number, head_sha=head_sha,
        verdicts=tuple(verdicts), dismissed=tuple(dismissed),
    )
