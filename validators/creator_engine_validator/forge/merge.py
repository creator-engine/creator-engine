"""CE v3 forge-native gated merge op (G-3.3) — squash-merge a reviewed, green, up-to-date PR.

The §5.1 orchestrator lifecycle opens a PR (``open_change`` / G-3.0), OBSERVES its merge-gates
(``review_state`` / ``checks_state`` / ``change_conflicts`` / G-3.2), and then — step 6 — may
merge it. :func:`merge` is that step: it squash-merges the change's PR through an injectable
``GhRunner``, **gated** on the three G-3.2 reads composed inline:

    eligible  ==  review.approved  and  checks.all_green  and  conflict.mergeable == "MERGEABLE"

(The conflict leg gates on the GitHub-computed ``mergeable == "MERGEABLE"`` — NOT
``ConflictState.up_to_date`` alone, which covers only the behind-base leg and would let a
``DIRTY``/conflicted-but-not-behind PR through; per the PR #128 review advisory.)

Like the rest of ``forge/`` it talks to a live forge ONLY through the injectable ``GhRunner``
(``gh api`` by default) and is **plan-by-default**:

* ``apply=False`` (default) reads the gate and RETURNS a :class:`MergeResult` reporting whether
  the PR ``would_merge`` (and the gate snapshot) WITHOUT mutating anything.
* ``apply=True`` (never run against a live forge in CI) re-reads the gate and, only when it is
  eligible, issues **exactly one** head-pinned squash merge
  (``PUT /repos/{owner}/{repo}/pulls/{n}/merge`` with ``{"merge_method":"squash","sha":<head>}``),
  then returns the resulting squash commit. A gate-ineligible PR is REFUSED before the merge.

Defensive invariants (deliberate, load-bearing):

* **Refuse a malformed / ungated request BEFORE any forge call** (refuse-before-side-effect):
  :func:`merge` raises :class:`MergeRefused` (a ``ForgeConfigRefused``) on a malformed ``repo``,
  a :class:`~.change.ChangeRef` with no open PR (``pr_number is None``), an ``apply=True`` with
  no ``head_sha`` to head-pin, or — under ``apply=True`` — a gate-ineligible PR (never merge an
  ungated PR). The injected runner is never called on the malformed/no-PR/no-head refusals.
* **Carries NO credential.** :func:`merge` takes no token argument and :class:`MergeResult`
  holds no token value; auth lives only in the injected ``gh_runner``'s environment (the secret
  never appears in argv).
* **Server-side gates still rule.** This merges OUR OWN already-reviewed, already-green PR; it
  is NOT a bypass — GitHub's branch-protection still enforces the gates, so a merge the server
  rejects (``405`` not mergeable / ``409`` head moved) surfaces as a transport
  :class:`~.github_repo_config.ForgeConfigError`.

Like the rest of ``forge/`` this reuses ``GhRunner`` / ``ForgeConfigError`` /
``ForgeConfigRefused`` from the byte-unchanged ``github_repo_config`` module, the value-free
:class:`~.change.ChangeRef`, and the G-3.2 read ops by import; imports ZERO doomed modules
(in particular NOT the unrelated PCL-ledger ``pcl_runtime.MergeResult``), performs no I/O on
import, and registers no validator check (so ``--list-checks`` stays byte-identical).

Defensive only — merging our own pipeline's gated PR; never offensive (no branch-protection
bypass, no self-merge of an unreviewed change, no detection evasion).
"""
from __future__ import annotations

import json
import re
import subprocess
from collections.abc import Sequence
from dataclasses import dataclass

from .change import ChangeRef
from .change_status import change_conflicts, checks_state, review_state
from .github_repo_config import ForgeConfigError, ForgeConfigRefused, GhRunner

# Re-defined LOCALLY (literal copied from ``scoped_token.py`` / ``change.py``) per the
# established forge convention, so the frozen sibling modules stay byte-unchanged.
_REPO_RE = re.compile(r"^[^/\s]+/[^/\s]+$")


class MergeRefused(ForgeConfigRefused):
    """A merge request was refused on a precondition BEFORE the merge call.

    Raised when the request is malformed (bad ``repo``), the change has no open PR to merge
    (``pr_number is None`` — a plan-by-default :class:`~.change.ChangeRef` must be applied
    first), an ``apply=True`` carries no ``head_sha`` to head-pin the squash, or — under
    ``apply=True`` — the merge gate is not satisfied (review not approved / checks not green /
    not ``MERGEABLE``). A *policy* refusal — distinct from a *transport*
    :class:`~.github_repo_config.ForgeConfigError`.
    """

    code = "V3-FORGE-MERGE-REFUSED"


@dataclass(frozen=True)
class MergeResult:
    """The result of a (planned or applied) gated squash-merge — secret-free.

    ``eligible`` is the composed gate (``review.approved and checks.all_green and
    conflict.mergeable == "MERGEABLE"``); ``would_merge`` echoes it (in plan mode, whether a
    merge WOULD be attempted). ``merged`` / ``merge_commit_sha`` are populated only on an
    applied merge. The remaining fields are the value-free gate snapshot. Holds NO token.
    """

    pr_number: int
    head_sha: str | None
    eligible: bool
    would_merge: bool
    merged: bool
    merge_commit_sha: str | None
    review_decision: str | None
    rollup_state: str
    merge_state_status: str
    mergeable: str | None
    applied: bool

    def to_dict(self) -> dict:
        return {
            "pr_number": self.pr_number,
            "head_sha": self.head_sha,
            "eligible": self.eligible,
            "would_merge": self.would_merge,
            "merged": self.merged,
            "merge_commit_sha": self.merge_commit_sha,
            "review_decision": self.review_decision,
            "rollup_state": self.rollup_state,
            "merge_state_status": self.merge_state_status,
            "mergeable": self.mergeable,
            "applied": self.applied,
        }


def _default_gh_runner(
    argv: Sequence[str], input_text: str | None = None
) -> subprocess.CompletedProcess:  # pragma: no cover - requires a live gh + GitHub App
    return subprocess.run(
        list(argv), check=False, capture_output=True, text=True, input=input_text, timeout=60
    )


def _gh_api_method(
    runner: GhRunner, method: str, path: str, body: dict | None = None
) -> tuple[int, object, str]:
    """Invoke ``gh api -X <METHOD> <path>`` (JSON body via ``--input -``).

    Returns ``(returncode, parsed_json|None, stderr)``. Never raises on a non-zero exit or
    unparseable stdout. Mirrors the ``change.py`` ``gh api`` idiom locally so that frozen
    module stays byte-unchanged.
    """
    argv = ["gh", "api", "-X", method, path]
    input_text: str | None = None
    if body is not None:
        argv += ["--input", "-"]
        input_text = json.dumps(body)
    proc = runner(argv, input_text)
    parsed: object = None
    out = (proc.stdout or "").strip()
    if out:
        try:
            parsed = json.loads(out)
        except (json.JSONDecodeError, ValueError):
            parsed = None
    return proc.returncode, parsed, proc.stderr or ""


def _validate_merge(change: ChangeRef) -> None:
    """Refuse a malformed / not-yet-opened change BEFORE any forge call."""
    repo = getattr(change, "repo", "") or ""
    if not _REPO_RE.match(repo):
        raise MergeRefused(f"repo {repo!r} is not in owner/name form")
    number = getattr(change, "pr_number", None)
    if not isinstance(number, int) or isinstance(number, bool) or number <= 0:
        raise MergeRefused(
            f"change has no open PR to merge (pr_number={number!r}); a plan-by-default "
            f"ChangeRef must be applied (a PR opened) before it can be merged"
        )


def merge(
    change: ChangeRef, *, apply: bool = False, gh_runner: GhRunner | None = None
) -> MergeResult:
    """Squash-merge the change's PR, gated on review + checks + up-to-date (plan-by-default).

    Validates the request FIRST (raising :class:`MergeRefused` before any forge call), then
    composes the three G-3.2 reads through the injected ``gh_runner`` to compute the merge
    gate. With ``apply=False`` (default) it returns a non-mutating :class:`MergeResult`
    reporting whether the PR ``would_merge``. With ``apply=True`` it refuses a gate-ineligible
    PR (``MergeRefused``) and otherwise issues exactly one head-pinned squash merge, then
    returns the resulting squash commit. A transport failure raises :class:`ForgeConfigError`.
    """
    _validate_merge(change)
    if apply and not (change.head_sha or "").strip():
        raise MergeRefused(
            "apply=True requires change.head_sha to head-pin the squash merge "
            "(the server-side --match-head-commit guard); refusing an unpinned merge"
        )
    runner = gh_runner or _default_gh_runner

    review = review_state(change, gh_runner=runner)
    checks = checks_state(change, gh_runner=runner)
    conflict = change_conflicts(change, gh_runner=runner)
    eligible = review.approved and checks.all_green and (conflict.mergeable == "MERGEABLE")

    if not apply:
        return MergeResult(
            pr_number=change.pr_number,  # type: ignore[arg-type]
            head_sha=change.head_sha,
            eligible=eligible,
            would_merge=eligible,
            merged=False,
            merge_commit_sha=None,
            review_decision=review.review_decision,
            rollup_state=checks.rollup_state,
            merge_state_status=conflict.merge_state_status,
            mergeable=conflict.mergeable,
            applied=False,
        )

    if not eligible:
        raise MergeRefused(
            f"merge gate not satisfied for {change.repo}#{change.pr_number} "
            f"(review_decision={review.review_decision!r}, rollup_state={checks.rollup_state!r}, "
            f"mergeable={conflict.mergeable!r}); refusing to merge an ungated PR"
        )

    code, parsed, stderr = _gh_api_method(
        runner,
        "PUT",
        f"repos/{change.repo}/pulls/{change.pr_number}/merge",
        {"merge_method": "squash", "sha": change.head_sha},
    )
    if code != 0 or not isinstance(parsed, dict):
        raise ForgeConfigError(
            f"could not squash-merge {change.repo}#{change.pr_number}: "
            f"{stderr.strip() or 'unknown error'}"
        )
    return MergeResult(
        pr_number=change.pr_number,  # type: ignore[arg-type]
        head_sha=change.head_sha,
        eligible=True,
        would_merge=True,
        merged=bool(parsed.get("merged")),
        merge_commit_sha=parsed.get("sha"),
        review_decision=review.review_decision,
        rollup_state=checks.rollup_state,
        merge_state_status=conflict.merge_state_status,
        mergeable=conflict.mergeable,
        applied=True,
    )
