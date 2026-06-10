"""CE v3 forge-native plan approval — resolve the ``ApprovedPlan`` from the forge (G-2.1).

The G-2.0 orchestrator gate refuses to provision unless a valid :class:`ApprovedPlan`
is present. G-2.0 took that record as a caller-supplied literal; G-2.1 makes the
**forge the source-of-truth** for it: :func:`plan_approved` resolves the record from
a plan-PR's review state so the approval authority lives outside-and-below the agent
and the seat cannot mint its own approval.

The resolved approval is bound, defensively, on four axes:

* **Run + policy binding.** The plan-PR body MUST carry ``ce-run-id`` and
  ``ce-policy-sha`` markers that equal the requested run and the runtime-policy in
  force — an unbound approval is not a ratification (mirrors our SHA-pinned
  ratification lines).
* **Commit pin.** The APPROVED review's ``commit_id`` MUST equal the PR head SHA.
  GitHub marks a review stale when the reviewed commit changes; we re-assert that
  pin so an approval cannot survive a post-approval edit of the plan.
* **Independence.** The approver is NEITHER the PR author NOR the running seat —
  no self-approval (the gate also re-checks ``approved_by`` != seat as a second,
  load-bearing guardrail).
* **APPROVED state.** Only an ``APPROVED`` review counts; ``COMMENTED`` /
  ``CHANGES_REQUESTED`` do not.

Like the rest of ``forge/``, every GitHub call goes through an injectable
:data:`GhRunner` (``gh api`` by default); tests inject a fake runner and perform
**zero** live network/subprocess, and importing this module performs no I/O and
registers no validator check. A transport failure (the PR/reviews read errors)
raises :class:`ForgeConfigError`; a clean "no valid approval" is a ``None`` return.

This is a pure resolver — it never provisions, mints a token, or merges. It depends
on the orchestrator's :class:`ApprovedPlan` *port type* (adapter-depends-on-core);
the orchestrator stays forge-free and consumes this only through an injected
resolver callable. Defensive only — authorization + accountability for our own
agent runtime; never offensive.
"""
from __future__ import annotations

import json
import re
import subprocess
from collections.abc import Sequence
from dataclasses import dataclass

from ..orchestrator import ApprovedPlan
from ._redact import redact_gh_stderr
from .github_repo_config import ForgeConfigError, GhRunner

_MARKER_RE = re.compile(r"\s*(ce-run-id|ce-policy-sha)\s*:\s*(\S+)\s*$", re.IGNORECASE)


@dataclass(frozen=True)
class ApprovalQuery:
    """What we ask the forge to ratify: a plan-PR bound to an exact run + policy.

    ``repo`` is ``owner/name``; ``pr_number`` the plan-PR; ``run_id`` the run being
    authorized; ``policy_sha`` the 64-hex digest of the runtime-policy in force. The
    PR body's ``ce-run-id`` / ``ce-policy-sha`` markers MUST equal ``run_id`` /
    ``policy_sha`` for the approval to bind.
    """

    repo: str
    pr_number: int
    run_id: str
    policy_sha: str


def _default_gh_runner(
    argv: Sequence[str], input_text: str | None = None
) -> subprocess.CompletedProcess:
    return subprocess.run(
        list(argv), check=False, capture_output=True, text=True, input=input_text, timeout=60
    )


def _gh_api(runner: GhRunner, path: str) -> tuple[int, object, str]:
    """Invoke ``gh api <path>`` (read-only GET). Returns ``(returncode, parsed_json|None, stderr)``.

    Mirrors the ``github_repo_config`` idiom locally so that frozen G-iii module
    stays byte-unchanged. Never raises on a non-zero exit or unparseable stdout.
    """
    proc = runner(["gh", "api", path], None)
    parsed: object = None
    out = (proc.stdout or "").strip()
    if out:
        try:
            parsed = json.loads(out)
        except (json.JSONDecodeError, ValueError):
            parsed = None
    return proc.returncode, parsed, proc.stderr or ""


def _parse_markers(body: str) -> dict[str, str]:
    """Extract ``ce-run-id`` / ``ce-policy-sha`` binding markers from a PR body."""
    markers: dict[str, str] = {}
    for line in (body or "").splitlines():
        m = _MARKER_RE.match(line)
        if m:
            markers[m.group(1).lower()] = m.group(2)
    return markers


def _quorum_approvers(
    reviews: list,
    *,
    head_sha: str,
    author: str,
    seat_identity: str,
    authority: dict,
    mutation_class: str | None,
    changed_paths: Sequence[str],
) -> str | None:
    """Grade the commit-pinned APPROVED set against the area+tier authority map.

    v3.5-C A-C3: the per-area × risk-tiered quorum (design §A.5). The latest
    commit-pinned review state per login decides whether that login approves
    (a later CHANGES_REQUESTED supersedes an earlier approval, mirroring
    GitHub's own dismissal semantics). The surviving set is graded by the
    SHARED ``peer_authority`` helpers — quorum of distinct resolved humans
    per tier, area-owner coverage for the changed paths, no self-approval at
    the HUMAN level (two accounts of one human never sum), unresolved actors
    fail closed. Returns the comma-joined approver logins, or ``None``.
    """
    latest: dict[str, str] = {}
    for review in reviews:
        if not isinstance(review, dict):
            continue
        if review.get("commit_id") != head_sha:  # stale: not pinned to head
            continue
        login = ((review.get("user") or {}).get("login")) or ""
        if not login:
            continue
        latest[login] = review.get("state") or ""
    approvers = sorted(
        login for login, state in latest.items()
        if state == "APPROVED" and login != author and login != seat_identity
    )
    if not approvers:
        return None
    # Lazy import: the authority grading lives in the SHARED peer_authority
    # check module (a v3->shared edge, allowed). Imported at CALL time so that
    # importing forge/ still registers no validator check (--list-checks
    # byte-identical, the package invariant).
    from ..checks.peer_authority import authority_satisfied

    ok, _reasons = authority_satisfied(
        authority,
        author=author,
        seat=seat_identity,
        approvers=approvers,
        mutation_class=mutation_class,
        changed_paths=changed_paths,
    )
    return ",".join(approvers) if ok else None


def plan_approved(
    query: ApprovalQuery,
    *,
    seat_identity: str,
    gh_runner: GhRunner | None = None,
    authority: dict | None = None,
    mutation_class: str | None = None,
    changed_paths: Sequence[str] = (),
) -> ApprovedPlan | None:
    """Resolve an :class:`ApprovedPlan` from the forge, or ``None`` if not ratified.

    Reads the plan-PR and its reviews through the injected ``gh_runner`` and returns
    a bound :class:`ApprovedPlan` only when a run/policy-bound, commit-pinned,
    independent (non-author, non-seat) ``APPROVED`` review exists. Returns ``None``
    for any clean "not ratified" condition; raises :class:`ForgeConfigError` only on
    a transport failure (the PR or reviews read errored).

    **v3.5-C A-C3 — peer authority.** When ``authority`` (the parsed
    ``.ce/coordination.yml`` policy) is supplied, the approval bar generalizes
    from one-independent-reviewer to the per-area × risk-tiered quorum:
    ``mutation_class`` picks the tier (privileged → both peers),
    ``changed_paths`` drives area-owner coverage, and quorum counts DISTINCT
    resolved humans (identity_map; fail-closed on unresolved actors). The
    ``approver != author != seat`` rule is preserved on both paths.
    Without ``authority`` the pre-A-C3 single-approver behaviour is unchanged.
    """
    runner = gh_runner or _default_gh_runner
    repo, pr = query.repo, query.pr_number

    code, pr_obj, stderr = _gh_api(runner, f"repos/{repo}/pulls/{pr}")
    if code != 0 or not isinstance(pr_obj, dict):
        raise ForgeConfigError(
            f"could not read PR {repo}#{pr}: {redact_gh_stderr(stderr) or 'unknown error'}"
        )
    author = ((pr_obj.get("user") or {}).get("login")) or ""
    head_sha = ((pr_obj.get("head") or {}).get("sha")) or ""
    body = pr_obj.get("body") or ""

    # Binding: the approval must name the exact run + runtime-policy in force.
    markers = _parse_markers(body)
    if markers.get("ce-run-id") != query.run_id or markers.get("ce-policy-sha") != query.policy_sha:
        return None
    if not head_sha:
        return None

    rcode, reviews, rstderr = _gh_api(runner, f"repos/{repo}/pulls/{pr}/reviews")
    if rcode != 0:
        raise ForgeConfigError(
            f"could not read reviews for {repo}#{pr}: {redact_gh_stderr(rstderr) or 'unknown error'}"
        )
    if not isinstance(reviews, list):
        return None

    if authority is not None:
        approved_by = _quorum_approvers(
            reviews,
            head_sha=head_sha,
            author=author,
            seat_identity=seat_identity,
            authority=authority,
            mutation_class=mutation_class,
            changed_paths=changed_paths,
        )
        if approved_by is None:
            return None
        return ApprovedPlan(
            run_id=query.run_id,
            policy_sha=query.policy_sha,
            approved_by=approved_by,
            approval_ref=f"{repo}#{pr}@{head_sha}",
        )

    # Latest independent, commit-pinned APPROVED review wins (reviews are chronological).
    approver: str | None = None
    for review in reviews:
        if not isinstance(review, dict):
            continue
        if review.get("state") != "APPROVED":
            continue
        if review.get("commit_id") != head_sha:  # stale: not pinned to the reviewed head
            continue
        login = ((review.get("user") or {}).get("login")) or ""
        if not login or login == author or login == seat_identity:  # no self-approval
            continue
        approver = login
    if approver is None:
        return None

    return ApprovedPlan(
        run_id=query.run_id,
        policy_sha=query.policy_sha,
        approved_by=approver,
        approval_ref=f"{repo}#{pr}@{head_sha}",
    )
