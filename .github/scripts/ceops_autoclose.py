#!/usr/bin/env python3
"""Close creator-engine/ce-ops issues referenced by a merged PR.

Issue numbers are extracted via two paths (ce-ops#262):

1. **Title scan** — every ``ce-ops#N`` token in the PR title (no keyword
   required; CE PR titles embed the issue, e.g. ``feat(ce-ops#262): ...``).
2. **Body closing-keyword scan** — lines starting with ``Closes``, ``Fixes``,
   or ``Resolves`` (and common inflections) followed by ``ce-ops#N`` refs.

Parsing logic lives in ``tools/ce-ops-autoclose/parse_issue_refs.py`` so it
can be unit-tested independently of this workflow driver.

Required repository secret:
  CE_CROSS_REPO_TOKEN — fine-grained PAT or GitHub App token with
  ``issues:write`` on ``creator-engine/ce-ops`` **only**.  The built-in
  ``GITHUB_TOKEN`` is scoped to this repository and cannot close cross-repo
  issues; never substitute it here.

Fail-closed token contract: if the token is absent or empty, a workflow error is
emitted and the step exits nonzero. The workflow step may still be configured
continue-on-error so merges are not blocked silently.
"""
# Acceptance-Evidence enforcement (P2)
# Issues labeled exactly `directive` require proof in the closing PR body before
# this bot may close them. The PR body field is line-based:
#
#     Acceptance-Evidence: <check-name or test path>
#
# Unlabeled issues, and issues without the `directive` label, keep the normal
# autoclose behavior. A directive issue without evidence is left open and gets a
# structured bot comment pointing back to the closing PR. Missing cross-repo
# token configuration is fail-closed: the script exits nonzero and emits a
# GitHub Actions error instead of silently skipping closures.
from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Import shared parser (stdlib-only; no install required)
# ---------------------------------------------------------------------------
_REPO_ROOT = Path(__file__).resolve().parents[2]
_PARSER_PATH = _REPO_ROOT / "tools" / "ce-ops-autoclose" / "parse_issue_refs.py"

if _PARSER_PATH.exists():
    import importlib.util as _ilu

    _spec = _ilu.spec_from_file_location("parse_issue_refs", _PARSER_PATH)
    assert _spec is not None and _spec.loader is not None
    _parser_mod = _ilu.module_from_spec(_spec)
    _spec.loader.exec_module(_parser_mod)
    _parse_all_refs = _parser_mod.parse_all_refs
    _parse_acceptance_evidence = _parser_mod.parse_acceptance_evidence
else:
    # Fallback: inline minimal parser so the workflow still runs if the tools
    # directory is somehow absent (should not happen in CI).
    import re as _re

    def _parse_all_refs(title: str, body: str) -> list[int]:  # type: ignore[misc]
        """Minimal fallback parser (bare title refs + body closing-keyword refs)."""
        _bare = _re.compile(r"(?:creator-engine/)?ce-ops#(\d+)\b", _re.IGNORECASE)
        _kw = _re.compile(
            r"^(?:close[sd]?|fix(?:e[sd])?|resolve[sd]?)"
            r"(?:[ \t]+|[ \t]*:[ \t]*)(?P<refs>(?:(?:creator-engine/)?ce-ops#\d+\b)"
            r"(?:(?:[ \t]*(?:,|;)[ \t]*|[ \t]+and[ \t]+)(?:creator-engine/)?ce-ops#\d+\b)*)",
            _re.IGNORECASE,
        )
        _split = _re.compile(r"(?<=[.!?])\s+|\n+")
        _lm = _re.compile(r"^\s*(?:[-*+]\s+|\d+[.)]\s+)")
        seen: set[int] = set()
        numbers: list[int] = []
        for m in _bare.finditer(title):
            n = int(m.group(1))
            if n not in seen:
                seen.add(n)
                numbers.append(n)
        for clause in _split.split(body):
            stripped = _lm.sub("", clause).strip()
            cm = _kw.match(stripped)
            if cm:
                for rm in _bare.finditer(cm.group("refs")):
                    n = int(rm.group(1))
                    if n not in seen:
                        seen.add(n)
                        numbers.append(n)
        return numbers

    def _parse_acceptance_evidence(body: str) -> str | None:  # type: ignore[misc]
        for line in body.splitlines():
            stripped = line.strip()
            if not stripped.startswith("Acceptance-Evidence"):
                continue
            field, separator, value = stripped.partition(":")
            if field == "Acceptance-Evidence" and separator:
                evidence = value.strip()
                if evidence:
                    return evidence
        return None


# ---------------------------------------------------------------------------
# Backward-compatibility shim
# ---------------------------------------------------------------------------
# The original ce154 implementation exposed `parse_closing_ceops_refs` at
# module level; existing tests reference it.  Delegate to the shared parser
# so the interface remains stable.

def parse_closing_ceops_refs(text: str) -> list[int]:
    """Return ce-ops issue numbers guarded by explicit closing keywords.

    Backward-compatible wrapper around parse_body_closing_refs from
    tools/ce-ops-autoclose/parse_issue_refs.py.  New callers should use
    _parse_all_refs (which also picks up title refs) or import the
    parse_issue_refs module directly.
    """
    if _PARSER_PATH.exists():
        return _parser_mod.parse_body_closing_refs(text)  # type: ignore[return-value]
    # Fallback: re-use _parse_all_refs with empty title
    return _parse_all_refs("", text)


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
CE_OPS_REPO = "creator-engine/ce-ops"
GITHUB_API = "https://api.github.com"

# Primary secret name (ce-ops#262).  CE_OPS_TOKEN is the legacy name kept for
# backwards-compatibility with any existing secret configuration.
_TOKEN_ENVVAR_PRIMARY = "CE_CROSS_REPO_TOKEN"
_TOKEN_ENVVAR_LEGACY = "CE_OPS_TOKEN"


# ---------------------------------------------------------------------------
# GitHub API helper
# ---------------------------------------------------------------------------

def _api_json(
    method: str,
    path: str,
    token: str,
    payload: dict[str, Any] | None = None,
) -> Any:
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


# ---------------------------------------------------------------------------
# PR context loader
# ---------------------------------------------------------------------------

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
    # Env-var fallback for local testing / manual workflow dispatch
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


# ---------------------------------------------------------------------------
# Issue closing
# ---------------------------------------------------------------------------

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
        "Provenance: ce-ops#262 cross-repo autoclose bot. "
        "Title refs (``feat(ce-ops#N): ...``) are closed automatically; "
        "body ``Closes ce-ops#N`` refs are also honoured. "
        "Token: CE_CROSS_REPO_TOKEN (issues:write on creator-engine/ce-ops only)."
    )


def _acceptance_evidence_required_comment(context: dict[str, Any]) -> str:
    url = context.get("url") or "(no URL available)"
    return (
        "**Autoclose blocked — Acceptance-Evidence required.**\n\n"
        "This issue carries the `directive` label. The closing PR did not supply\n"
        "an `Acceptance-Evidence:` field in its body. Add a line of the form:\n\n"
        "    Acceptance-Evidence: <check-name or test path>\n\n"
        "to the PR body and the bot will close this issue on the next merge.\n\n"
        f"Closing PR: {url}"
    )


def _is_directive_issue(issue: dict[str, Any]) -> bool:
    return any(label.get("name") == "directive" for label in issue.get("labels", []))


def close_issue_if_open(issue_number: int, token: str, context: dict[str, Any]) -> None:
    issue_path = f"/repos/{CE_OPS_REPO}/issues/{issue_number}"
    issue = _api_json("GET", issue_path, token)
    if issue.get("state") == "closed":
        print(f"ce-ops#{issue_number}: already closed, skipping")
        return

    if _is_directive_issue(issue) and not _parse_acceptance_evidence(context.get("body") or ""):
        _api_json(
            "POST",
            f"{issue_path}/comments",
            token,
            {"body": _acceptance_evidence_required_comment(context)},
        )
        print(f"ce-ops#{issue_number}: Acceptance-Evidence required, leaving open")
        return

    _api_json(
        "POST",
        f"{issue_path}/comments",
        token,
        {"body": _provenance_comment(issue_number, context)},
    )
    _api_json("PATCH", issue_path, token, {"state": "closed", "state_reason": "completed"})
    print(f"ce-ops#{issue_number}: closed")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> int:
    context = _load_pr_context()
    if not context.get("merged"):
        print("PR was not merged; nothing to close")
        return 0

    base_ref = context.get("base_ref")
    if base_ref and base_ref != "main":
        print(f"PR base ref is {base_ref!r}, not main; nothing to close")
        return 0

    title = context.get("title") or ""
    body = context.get("body") or ""
    numbers = _parse_all_refs(title, body)
    if not numbers:
        print("No ce-ops refs found in PR title or body")
        return 0

    # Accept primary token name; fall back to legacy name transparently
    token = os.environ.get(_TOKEN_ENVVAR_PRIMARY) or os.environ.get(_TOKEN_ENVVAR_LEGACY)
    if not token:
        print(
            f"::error::{_TOKEN_ENVVAR_PRIMARY} (and legacy {_TOKEN_ENVVAR_LEGACY}) "
            "are not configured; skipping ce-ops autoclose. "
            "Provision a fine-grained token with issues:write on creator-engine/ce-ops."
        )
        return 1

    print(f"ce-ops refs to close: {numbers}")
    for number in numbers:
        try:
            close_issue_if_open(number, token, context)
        except (OSError, urllib.error.URLError, urllib.error.HTTPError, json.JSONDecodeError) as exc:
            print(f"::warning::ce-ops#{number}: autoclose failed: {exc}", file=sys.stderr)
        except Exception as exc:  # pragma: no cover - defensive fail-soft boundary
            print(f"::warning::ce-ops#{number}: unexpected autoclose failure: {exc}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
