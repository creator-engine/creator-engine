#!/usr/bin/env python3
"""Close explicitly referenced creator-engine/ce-ops issues from merged PRs.

Requires repository secret CE_OPS_TOKEN with least-privilege issues:write access
to creator-engine/ce-ops. This intentionally does not use GITHUB_TOKEN because
that token is scoped to the PR repository and cannot close cross-repo ce-ops
issues.
"""
from __future__ import annotations

import json
import os
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any


CE_OPS_REPO = "creator-engine/ce-ops"
GITHUB_API = "https://api.github.com"

_KEYWORD = r"(?:close[sd]?|fix(?:e[sd])?|resolve[sd]?)"
_REF = r"(?:creator-engine/)?ce-ops#\d+\b"
_CLOSING_CLAUSE_RE = re.compile(
    rf"^{_KEYWORD}(?:[ \t]+|[ \t]*:[ \t]*)(?P<refs>"
    rf"{_REF}(?:(?:[ \t]*(?:,|;)[ \t]*|[ \t]+and[ \t]+){_REF})*)",
    re.IGNORECASE,
)
_REF_RE = re.compile(r"(?:creator-engine/)?ce-ops#(\d+)\b", re.IGNORECASE)
_CLAUSE_SPLIT_RE = re.compile(r"(?<=[.!?])\s+|\n+")
_LIST_MARKER_RE = re.compile(r"^\s*(?:[-*+]\s+|\d+[.)]\s+)")


def parse_closing_ceops_refs(text: str) -> list[int]:
    """Return ce-ops issue numbers guarded by explicit closing keywords."""
    seen: set[int] = set()
    numbers: list[int] = []
    for raw_clause in _CLAUSE_SPLIT_RE.split(text):
        clause_text = _LIST_MARKER_RE.sub("", raw_clause).strip()
        clause = _CLOSING_CLAUSE_RE.match(clause_text)
        if not clause:
            continue
        for match in _REF_RE.finditer(clause.group("refs")):
            number = int(match.group(1))
            if number not in seen:
                seen.add(number)
                numbers.append(number)
    return numbers


def _api_json(method: str, path: str, token: str, payload: dict[str, Any] | None = None) -> Any:
    data = None
    headers = {
        "Accept": "application/vnd.github+json",
        "Authorization": f"Bearer {token}",
        "User-Agent": "creator-engine-ceops-autoclose",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"
    request = urllib.request.Request(
        f"{GITHUB_API}{path}", data=data, headers=headers, method=method
    )
    with urllib.request.urlopen(request, timeout=20) as response:
        body = response.read()
    if not body:
        return None
    return json.loads(body.decode("utf-8"))


def _load_pr_context() -> dict[str, Any]:
    event_path = os.environ.get("GITHUB_EVENT_PATH")
    if event_path:
        event = json.loads(Path(event_path).read_text(encoding="utf-8"))
        pr = event.get("pull_request") or {}
        repo = event.get("repository") or {}
        return {
            "merged": bool(pr.get("merged")),
            "number": pr.get("number"),
            "title": pr.get("title") or "",
            "body": pr.get("body") or "",
            "url": pr.get("html_url") or "",
            "merge_commit_sha": pr.get("merge_commit_sha") or "",
            "repository": repo.get("full_name") or os.environ.get("GITHUB_REPOSITORY", ""),
            "base_ref": ((pr.get("base") or {}).get("ref") or ""),
        }
    return {
        "merged": True,
        "number": os.environ.get("PR_NUMBER", ""),
        "title": os.environ.get("PR_TITLE", ""),
        "body": os.environ.get("PR_BODY", ""),
        "url": os.environ.get("PR_URL", ""),
        "merge_commit_sha": os.environ.get("PR_MERGE_SHA", ""),
        "repository": os.environ.get("GITHUB_REPOSITORY", ""),
        "base_ref": os.environ.get("PR_BASE_REF") or os.environ.get("GITHUB_BASE_REF", ""),
    }


def _provenance_comment(issue_number: int, context: dict[str, Any]) -> str:
    repo = context.get("repository") or "creator-engine/creator-engine"
    pr_number = context.get("number") or "unknown"
    title = context.get("title") or "(untitled PR)"
    url = context.get("url") or "(no URL available)"
    merge_sha = context.get("merge_commit_sha") or "(unknown merge SHA)"
    return (
        f"Auto-closing ce-ops#{issue_number} from merged PR {repo}#{pr_number}.\n\n"
        f"- PR: {title}\n"
        f"- URL: {url}\n"
        f"- Merge SHA: `{merge_sha}`\n\n"
        "Provenance: creator-engine/ce-ops#154 cross-repo autoclose. "
        "Authoring convention: use explicit `Closes ce-ops#N`, `Fixes ce-ops#N`, "
        "or `Resolves ce-ops#N` refs as tracked toward creator-engine/ce-ops#65."
    )


def close_issue_if_open(issue_number: int, token: str, context: dict[str, Any]) -> None:
    issue_path = f"/repos/{CE_OPS_REPO}/issues/{issue_number}"
    issue = _api_json("GET", issue_path, token)
    if issue.get("state") == "closed":
        print(f"ce-ops#{issue_number}: already closed, skipping")
        return

    _api_json(
        "POST",
        f"{issue_path}/comments",
        token,
        {"body": _provenance_comment(issue_number, context)},
    )
    _api_json("PATCH", issue_path, token, {"state": "closed", "state_reason": "completed"})
    print(f"ce-ops#{issue_number}: closed")


def main() -> int:
    context = _load_pr_context()
    if not context.get("merged"):
        print("PR was not merged; nothing to close")
        return 0

    base_ref = context.get("base_ref")
    if base_ref and base_ref != "main":
        print(f"PR base ref is {base_ref!r}, not main; nothing to close")
        return 0

    numbers = parse_closing_ceops_refs(f"{context.get('title', '')}\n{context.get('body', '')}")
    if not numbers:
        print("No explicit ce-ops closing refs found")
        return 0

    token = os.environ.get("CE_OPS_TOKEN")
    if not token:
        print("::warning::CE_OPS_TOKEN is not configured; skipping ce-ops autoclose")
        return 0

    for number in numbers:
        try:
            close_issue_if_open(number, token, context)
        except (OSError, urllib.error.URLError, urllib.error.HTTPError, json.JSONDecodeError) as exc:
            print(f"::warning::ce-ops#{number}: autoclose failed: {exc}", file=sys.stderr)
        except Exception as exc:  # pragma: no cover - defensive fail-soft boundary.
            print(f"::warning::ce-ops#{number}: unexpected autoclose failure: {exc}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
