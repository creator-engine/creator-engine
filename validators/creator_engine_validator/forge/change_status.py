"""CE v3 forge-native read-only change-status ops (G-3.2) — observe a change's merge-gates.

The §5.1 orchestrator lifecycle opens a PR (``open_change`` / G-3.0) and then, before it
may merge (step 6), must OBSERVE three forge-computed gates of the §8.3 PASS contract
WITHOUT mutating anything:

* :func:`review_state`     — is the change merge-blocked-until-reviewed (a required review
  decision satisfied)?  ``reviewDecision``.
* :func:`checks_state`     — are all required checks green?  the head commit's
  ``statusCheckRollup.state``.
* :func:`change_conflicts` — is the change up-to-date / conflict-free with base?
  ``mergeStateStatus`` (+ ``mergeable``); ``BEHIND`` is the not-up-to-date leg §5.1 step-6
  depends on.

These are **pure, read-only** observations — there is NO ``apply`` parameter; nothing here
ever mutates. Each takes a value-free :class:`~.change.ChangeRef` (the ``open_change``
output threads straight in) and reads through an injectable ``GhRunner``.

We read the **derived** gates GitHub itself computes (factoring in branch-protection /
required-reviews / required-checks) via a single GraphQL query per op — the same surface
``gh pr view`` uses — rather than re-deriving "required" from raw REST. The GraphQL call
still rides the injected ``GhRunner`` (it is just a different ``gh api graphql`` argv), so
auth lives ONLY in the runner's environment and tests inject a fake runner (zero live
network / subprocess).

Defensive invariants (deliberate, load-bearing):

* **Refuse a malformed / not-yet-opened change BEFORE any forge call**
  (refuse-before-side-effect): each op raises :class:`ChangeStatusRefused` (a
  ``ForgeConfigRefused``) on a malformed ``repo`` or a ``ChangeRef`` with no open PR
  (``pr_number is None`` — a plan-by-default change must be applied first). The injected
  runner is never called on a refusal.
* **Carries NO credential.** No op takes a token argument and no result type holds a token
  value; auth lives only in the injected ``gh_runner``'s environment (the established
  ``revoke_scoped_token`` pattern — the secret never appears in argv).
* **Read-only.** Every op issues a single GraphQL READ; a transport non-zero / unparseable
  response raises :class:`~.github_repo_config.ForgeConfigError` (a *transport* error,
  distinct from a *policy* refusal).

Like the rest of ``forge/`` this reuses ``GhRunner`` / ``ForgeConfigError`` /
``ForgeConfigRefused`` from the byte-unchanged ``github_repo_config`` module (and the
value-free :class:`~.change.ChangeRef`), imports ZERO doomed modules, performs no I/O on
import, and registers no validator check (so ``--list-checks`` stays byte-identical).

Defensive only — read-only observation of OUR OWN pipeline's PR to enforce the
no-self-merge / required-review / required-checks gates; never offensive (no bypass, no
self-merge, no detection evasion).
"""
from __future__ import annotations

import json
import re
import subprocess
from collections.abc import Sequence
from dataclasses import dataclass

from .change import ChangeRef
from ._redact import redact_gh_stderr
from .github_repo_config import ForgeConfigError, ForgeConfigRefused, GhRunner

# Re-defined LOCALLY (literal copied from ``scoped_token.py`` / ``change.py``) per the
# established forge convention, so the frozen sibling modules stay byte-unchanged.
_REPO_RE = re.compile(r"^[^/\s]+/[^/\s]+$")


class ChangeStatusRefused(ForgeConfigRefused):
    """A change-status read was refused on a precondition BEFORE any forge call.

    Raised when the request is malformed (bad ``repo``) or the change has no open PR to
    read (``pr_number is None`` — a plan-by-default :class:`~.change.ChangeRef` must be
    applied first). A *policy* refusal — distinct from a *transport*
    :class:`~.github_repo_config.ForgeConfigError`.
    """

    code = "V3-FORGE-CHANGESTATUS-REFUSED"


@dataclass(frozen=True)
class ReviewState:
    """The review-gate observation for a change — secret-free.

    ``review_decision`` is GitHub's computed ``reviewDecision`` (``APPROVED`` /
    ``CHANGES_REQUESTED`` / ``REVIEW_REQUIRED`` / ``None``); ``approved`` is the single
    convenience bool the merge-gate (G-3.3) reads.
    """

    pr_number: int
    review_decision: str | None
    approved: bool

    def to_dict(self) -> dict:
        return {
            "pr_number": self.pr_number,
            "review_decision": self.review_decision,
            "approved": self.approved,
        }


@dataclass(frozen=True)
class ChecksState:
    """The required-checks-green observation for a change — secret-free.

    ``rollup_state`` is the head commit's computed ``statusCheckRollup.state``
    (``SUCCESS`` / ``PENDING`` / ``FAILURE`` / ``ERROR`` / ``EXPECTED``); ``all_green`` is
    ``rollup_state == "SUCCESS"`` (a null rollup — no checks — is conservatively NOT green).
    """

    pr_number: int
    head_sha: str
    rollup_state: str
    all_green: bool

    def to_dict(self) -> dict:
        return {
            "pr_number": self.pr_number,
            "head_sha": self.head_sha,
            "rollup_state": self.rollup_state,
            "all_green": self.all_green,
        }


@dataclass(frozen=True)
class ConflictState:
    """The up-to-date / conflict observation for a change — secret-free.

    ``merge_state_status`` is GitHub's computed ``mergeStateStatus`` (``CLEAN`` / ``BEHIND``
    / ``BLOCKED`` / ``DIRTY`` / ``UNSTABLE`` / ``UNKNOWN`` / ``DRAFT`` / ``HAS_HOOKS``);
    ``mergeable`` is ``MERGEABLE`` / ``CONFLICTING`` / ``UNKNOWN`` / ``None``; ``up_to_date``
    is ``merge_state_status != "BEHIND"`` (the §5.1 step-6 up-to-date leg).
    """

    pr_number: int
    merge_state_status: str
    mergeable: str | None
    up_to_date: bool

    def to_dict(self) -> dict:
        return {
            "pr_number": self.pr_number,
            "merge_state_status": self.merge_state_status,
            "mergeable": self.mergeable,
            "up_to_date": self.up_to_date,
        }


def _default_gh_runner(
    argv: Sequence[str], input_text: str | None = None
) -> subprocess.CompletedProcess:  # pragma: no cover - requires a live gh + GitHub App
    return subprocess.run(
        list(argv), check=False, capture_output=True, text=True, input=input_text, timeout=60
    )


def _gh_graphql(
    runner: GhRunner, query: str, variables: dict[str, object]
) -> tuple[int, object, str]:
    """Invoke ``gh api graphql -f query=<q> [-f|-F k=v ...]`` through the injected runner.

    String variables are passed with ``-f`` (raw string), non-string (int/bool) with
    ``-F`` (typed) so the GraphQL ``Int!``/``String!`` parameters bind correctly. Returns
    ``(returncode, parsed_json|None, stderr)``; never raises on a non-zero exit or
    unparseable stdout (mirrors ``change.py`` ``_gh_api_method``).
    """
    argv = ["gh", "api", "graphql", "-f", f"query={query}"]
    for key, value in variables.items():
        flag = "-f" if isinstance(value, str) else "-F"
        argv += [flag, f"{key}={value}"]
    proc = runner(argv, None)
    parsed: object = None
    out = (proc.stdout or "").strip()
    if out:
        try:
            parsed = json.loads(out)
        except (json.JSONDecodeError, ValueError):
            parsed = None
    return proc.returncode, parsed, proc.stderr or ""


def _validate_change(change: ChangeRef) -> None:
    """Refuse a malformed / not-yet-opened change BEFORE any forge call."""
    repo = getattr(change, "repo", "") or ""
    if not _REPO_RE.match(repo):
        raise ChangeStatusRefused(f"repo {repo!r} is not in owner/name form")
    number = getattr(change, "pr_number", None)
    if not isinstance(number, int) or isinstance(number, bool) or number <= 0:
        raise ChangeStatusRefused(
            f"change has no open PR to read (pr_number={number!r}); a plan-by-default "
            f"ChangeRef must be applied (a PR opened) before its status can be read"
        )


def _read_pr_node(runner: GhRunner, change: ChangeRef, query: str) -> dict:
    """Run one GraphQL read for ``change`` and return its ``pullRequest`` node dict."""
    owner, name = change.repo.split("/", 1)
    code, parsed, stderr = _gh_graphql(
        runner, query, {"owner": owner, "name": name, "number": change.pr_number}
    )
    if code != 0 or not isinstance(parsed, dict):
        raise ForgeConfigError(
            f"could not read change status for {change.repo}#{change.pr_number}: "
            f"{redact_gh_stderr(stderr) or 'unknown error'}"
        )
    pr = ((parsed.get("data") or {}).get("repository") or {}).get("pullRequest")
    if not isinstance(pr, dict):
        raise ForgeConfigError(
            f"unexpected change-status response for {change.repo}#{change.pr_number}"
        )
    return pr


_REVIEW_QUERY = (
    "query($owner:String!,$name:String!,$number:Int!)"
    "{repository(owner:$owner,name:$name){pullRequest(number:$number){reviewDecision}}}"
)
_CHECKS_QUERY = (
    "query($owner:String!,$name:String!,$number:Int!)"
    "{repository(owner:$owner,name:$name){pullRequest(number:$number)"
    "{headRefOid commits(last:1){nodes{commit{statusCheckRollup{state}}}}}}}"
)
_CONFLICT_QUERY = (
    "query($owner:String!,$name:String!,$number:Int!)"
    "{repository(owner:$owner,name:$name){pullRequest(number:$number)"
    "{mergeStateStatus mergeable}}}"
)


def review_state(change: ChangeRef, *, gh_runner: GhRunner | None = None) -> ReviewState:
    """Read the change's review decision (read-only; refuses a change with no open PR)."""
    _validate_change(change)
    runner = gh_runner or _default_gh_runner
    pr = _read_pr_node(runner, change, _REVIEW_QUERY)
    decision = pr.get("reviewDecision")
    return ReviewState(
        pr_number=change.pr_number,  # type: ignore[arg-type]
        review_decision=decision,
        approved=(decision == "APPROVED"),
    )


def checks_state(change: ChangeRef, *, gh_runner: GhRunner | None = None) -> ChecksState:
    """Read the change head's required-check rollup (read-only)."""
    _validate_change(change)
    runner = gh_runner or _default_gh_runner
    pr = _read_pr_node(runner, change, _CHECKS_QUERY)
    head_sha = pr.get("headRefOid") or ""
    nodes = (pr.get("commits") or {}).get("nodes") or []
    rollup = None
    if nodes and isinstance(nodes[0], dict):
        rollup = (nodes[0].get("commit") or {}).get("statusCheckRollup")
    state = (rollup or {}).get("state") or "EXPECTED"  # null rollup (no checks) -> not green
    return ChecksState(
        pr_number=change.pr_number,  # type: ignore[arg-type]
        head_sha=head_sha,
        rollup_state=state,
        all_green=(state == "SUCCESS"),
    )


def change_conflicts(change: ChangeRef, *, gh_runner: GhRunner | None = None) -> ConflictState:
    """Read the change's up-to-date / conflict state (read-only)."""
    _validate_change(change)
    runner = gh_runner or _default_gh_runner
    pr = _read_pr_node(runner, change, _CONFLICT_QUERY)
    merge_state_status = pr.get("mergeStateStatus") or "UNKNOWN"
    mergeable = pr.get("mergeable")
    return ConflictState(
        pr_number=change.pr_number,  # type: ignore[arg-type]
        merge_state_status=merge_state_status,
        mergeable=mergeable,
        up_to_date=(merge_state_status != "BEHIND"),
    )
