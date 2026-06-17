"""Enable per-PR GitHub auto-merge through GraphQL (plan-by-default)."""
from __future__ import annotations

import json
import re
import subprocess
from collections.abc import Sequence
from dataclasses import dataclass

from ._redact import redact_gh_stderr
from .change import ChangeRef
from .github_repo_config import ForgeConfigError, ForgeConfigRefused, GhRunner

_REPO_RE = re.compile(r"^[^/\s]+/[^/\s]+$")
_METHODS = {"merge": "MERGE", "squash": "SQUASH", "rebase": "REBASE"}

_PR_ID_QUERY = (
    "query($owner:String!,$name:String!,$number:Int!)"
    "{repository(owner:$owner,name:$name){pullRequest(number:$number)"
    "{id autoMergeRequest{enabledAt mergeMethod}}}}"
)
_ENABLE_MUTATION = (
    "mutation($pullRequestId:ID!,$mergeMethod:PullRequestMergeMethod!)"
    "{enablePullRequestAutoMerge(input:{pullRequestId:$pullRequestId,mergeMethod:$mergeMethod})"
    "{pullRequest{autoMergeRequest{enabledAt mergeMethod}}}}"
)


class AutoMergeRefused(ForgeConfigRefused):
    """An auto-merge request was refused before any forge side effect."""

    code = "V3-FORGE-AUTO-MERGE-REFUSED"


@dataclass(frozen=True)
class AutoMergeResult:
    """Outcome of a planned or applied per-PR auto-merge enablement."""

    repo: str
    pr_number: int
    pull_request_id: str
    merge_method: str
    changed: bool
    applied: bool
    enabled: bool

    def to_dict(self) -> dict:
        return {
            "repo": self.repo,
            "pr_number": self.pr_number,
            "pull_request_id": self.pull_request_id,
            "merge_method": self.merge_method,
            "changed": self.changed,
            "applied": self.applied,
            "enabled": self.enabled,
        }


def _default_gh_runner(
    argv: Sequence[str], input_text: str | None = None
) -> subprocess.CompletedProcess:  # pragma: no cover - live gh
    return subprocess.run(
        list(argv), check=False, capture_output=True, text=True, input=input_text, timeout=60
    )


def _gh_graphql(
    runner: GhRunner, query: str, variables: dict[str, object]
) -> tuple[int, object, str]:
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


def _validate(change: ChangeRef, method: str) -> tuple[int, str]:
    repo = getattr(change, "repo", "") or ""
    if not _REPO_RE.match(repo):
        raise AutoMergeRefused(f"repo {repo!r} is not in owner/name form")
    number = getattr(change, "pr_number", None)
    if not isinstance(number, int) or isinstance(number, bool) or number <= 0:
        raise AutoMergeRefused(f"change has no open PR for auto-merge (pr_number={number!r})")
    normalized = _METHODS.get((method or "").lower())
    if normalized is None:
        raise AutoMergeRefused("auto-merge method must be one of merge, squash, rebase")
    return number, normalized


def _read_pr(runner: GhRunner, change: ChangeRef) -> dict:
    owner, name = change.repo.split("/", 1)
    code, parsed, stderr = _gh_graphql(
        runner, _PR_ID_QUERY, {"owner": owner, "name": name, "number": change.pr_number}
    )
    if code != 0 or not isinstance(parsed, dict):
        raise ForgeConfigError(
            f"could not read PR node id for {change.repo}#{change.pr_number}: "
            f"{redact_gh_stderr(stderr) or 'unknown error'}"
        )
    pr = ((parsed.get("data") or {}).get("repository") or {}).get("pullRequest")
    if not isinstance(pr, dict) or not pr.get("id"):
        raise ForgeConfigError(f"unexpected auto-merge read response for {change.repo}#{change.pr_number}")
    return pr


def enable_auto_merge(
    change: ChangeRef,
    *,
    method: str = "squash",
    apply: bool = False,
    gh_runner: GhRunner | None = None,
) -> AutoMergeResult:
    """Enable GitHub auto-merge for ``change`` via GraphQL (plan-by-default)."""
    pr_number, merge_method = _validate(change, method)
    runner = gh_runner or _default_gh_runner
    pr = _read_pr(runner, change)
    node_id = str(pr["id"])
    current = pr.get("autoMergeRequest")
    already_enabled = isinstance(current, dict) and current.get("mergeMethod") == merge_method
    if already_enabled:
        return AutoMergeResult(
            repo=change.repo, pr_number=pr_number, pull_request_id=node_id,
            merge_method=merge_method, changed=False, applied=False, enabled=True,
        )
    if not apply:
        return AutoMergeResult(
            repo=change.repo, pr_number=pr_number, pull_request_id=node_id,
            merge_method=merge_method, changed=True, applied=False, enabled=False,
        )
    code, parsed, stderr = _gh_graphql(
        runner, _ENABLE_MUTATION, {"pullRequestId": node_id, "mergeMethod": merge_method}
    )
    if code != 0 or not isinstance(parsed, dict):
        raise ForgeConfigError(
            f"could not enable auto-merge for {change.repo}#{pr_number}: "
            f"{redact_gh_stderr(stderr) or 'unknown error'}"
        )
    return AutoMergeResult(
        repo=change.repo, pr_number=pr_number, pull_request_id=node_id,
        merge_method=merge_method, changed=True, applied=True, enabled=True,
    )
