"""Submit an independent approving PR review through an injected GitHub runner."""
from __future__ import annotations

import json
import re
import subprocess
from collections.abc import Sequence
from dataclasses import dataclass

from ..sec7_forge_guard import sec7_forge_refusal
from ._redact import redact_gh_stderr
from .change import ChangeRef
from .github_repo_config import ForgeConfigError, ForgeConfigRefused, GhRunner

_REPO_RE = re.compile(r"^[^/\s]+/[^/\s]+$")


class ReviewSubmitRefused(ForgeConfigRefused):
    """A review submission was refused before any forge side effect."""

    code = "V3-FORGE-REVIEW-SUBMIT-REFUSED"


@dataclass(frozen=True)
class ReviewResult:
    """Outcome of a planned or submitted approving review."""

    repo: str
    pr_number: int
    head_sha: str
    event: str
    changed: bool
    applied: bool
    review_id: int | None = None

    def to_dict(self) -> dict:
        return {
            "repo": self.repo,
            "pr_number": self.pr_number,
            "head_sha": self.head_sha,
            "event": self.event,
            "changed": self.changed,
            "applied": self.applied,
            "review_id": self.review_id,
        }


def _default_gh_runner(
    argv: Sequence[str], input_text: str | None = None
) -> subprocess.CompletedProcess:  # pragma: no cover - live gh
    return subprocess.run(
        list(argv), check=False, capture_output=True, text=True, input=input_text, timeout=60
    )


def _gh_api_method(
    runner: GhRunner, method: str, path: str, body: dict | None = None
) -> tuple[int, object, str]:
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


def _validate(change: ChangeRef) -> tuple[int, str]:
    repo = getattr(change, "repo", "") or ""
    if not _REPO_RE.match(repo):
        raise ReviewSubmitRefused(f"repo {repo!r} is not in owner/name form")
    number = getattr(change, "pr_number", None)
    if not isinstance(number, int) or isinstance(number, bool) or number <= 0:
        raise ReviewSubmitRefused(
            f"change has no open PR to approve (pr_number={number!r})"
        )
    head_sha = (getattr(change, "head_sha", None) or "").strip()
    if not head_sha:
        raise ReviewSubmitRefused("review submission requires change.head_sha for commit_id binding")
    return number, head_sha


def submit_review(
    change: ChangeRef,
    *,
    body: str = "",
    apply: bool = False,
    gh_runner: GhRunner | None = None,
    sec7_context: object | None = None,
) -> ReviewResult:
    """Submit an ``APPROVE`` review for ``change`` (plan-by-default)."""
    refusal = sec7_forge_refusal("review-submit", sec7_context)
    if refusal is not None:
        raise ReviewSubmitRefused(refusal)
    pr_number, head_sha = _validate(change)
    if not apply:
        return ReviewResult(
            repo=change.repo, pr_number=pr_number, head_sha=head_sha,
            event="APPROVE", changed=True, applied=False, review_id=None,
        )
    runner = gh_runner or _default_gh_runner
    payload = {"event": "APPROVE", "commit_id": head_sha}
    if body:
        payload["body"] = body
    code, parsed, stderr = _gh_api_method(
        runner, "POST", f"repos/{change.repo}/pulls/{pr_number}/reviews", payload
    )
    if code != 0 or not isinstance(parsed, dict):
        raise ForgeConfigError(
            f"could not submit approving review for {change.repo}#{pr_number}: "
            f"{redact_gh_stderr(stderr) or 'unknown error'}"
        )
    review_id = parsed.get("id")
    return ReviewResult(
        repo=change.repo, pr_number=pr_number, head_sha=head_sha,
        event="APPROVE", changed=True, applied=True,
        review_id=(int(review_id) if review_id is not None else None),
    )
