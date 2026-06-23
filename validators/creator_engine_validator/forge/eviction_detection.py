"""CE ce-ops#216 Unit 1 — read-only integrator eviction detection.

This module is the control-plane poll step for APPROVED + green PRs that stop
being directly mergeable while waiting for integration. It reuses the belt's
bounded Search API polling shape, then reads GitHub's computed PR gate state
through the existing v3 forge GraphQL helper.

No daemon and no executor behavior lives here. Callers run this ephemerally,
receive deterministic ``repair-needed`` events, and decide separately what to do.
"""
from __future__ import annotations

import json
import re
import subprocess
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from .change import ChangeRef
from .change_status import PullRequestState, pr_state
from .github_repo_config import GhRunner

Transport = Callable[[str, str, "dict[str, str]", "str | None"], "tuple[int, dict[str, str], str]"]

_API_ROOT = "https://api.github.com"
_API_VERSION = "2022-11-28"
_ACCEPT = "application/vnd.github+json"
_REPO_SCOPE_RE = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")
_ORG_SCOPE_RE = re.compile(r"^[A-Za-z0-9_.-]+$")

REPAIR_NEEDED_EVENT_TYPE = "repair-needed"
REPAIRABLE_MERGE_STATE_STATUSES = frozenset({"BEHIND", "DIRTY"})
REPAIRABLE_MERGEABLE_STATES = frozenset({"CONFLICTING"})
DEFAULT_SEARCH_PER_PAGE = 100


class EvictionDetectionError(Exception):
    """Bad input or failed read while detecting repair-needed events."""


@dataclass(frozen=True)
class SearchQuery:
    """One GitHub Search API query used to discover PR candidates."""

    reason: str
    query: str


@dataclass(frozen=True)
class RepairNeededEvent:
    """Structured event emitted for an approved, green PR that needs repair."""

    repo: str
    pr_number: int
    head_sha: str
    merge_state_status: str
    mergeable: str | None
    reason: str
    review_decision: str | None
    rollup_state: str
    detected_at: str | None = None
    event_type: str = REPAIR_NEEDED_EVENT_TYPE

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "event_type": self.event_type,
            "repo": self.repo,
            "pr_number": self.pr_number,
            "head_sha": self.head_sha,
            "merge_state_status": self.merge_state_status,
            "mergeable": self.mergeable,
            "reason": self.reason,
        }
        if self.detected_at is not None:
            payload["detected_at"] = self.detected_at
        payload["evidence"] = {
            "review_decision": self.review_decision,
            "approved": self.review_decision == "APPROVED",
            "rollup_state": self.rollup_state,
            "all_green": self.rollup_state == "SUCCESS",
        }
        return payload


@dataclass(frozen=True)
class RepairPollResult:
    """The result of one bounded Search API poll plus PR-state read pass."""

    events: tuple[RepairNeededEvent, ...] = ()
    rate_limit: Mapping[str, Any] | None = None


def _default_transport(  # pragma: no cover - live HTTPS edge; tests inject a fake
    method: str, url: str, headers: dict[str, str], body: str | None
) -> tuple[int, dict[str, str], str]:
    data = body.encode("utf-8") if body is not None else None
    request = urllib.request.Request(url, data=data, method=method, headers=headers)
    try:
        with urllib.request.urlopen(request, timeout=60) as resp:
            return resp.status, dict(resp.headers), resp.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as exc:
        return exc.code, dict(exc.headers or {}), exc.read().decode("utf-8", "replace")


def _default_gh_runner(
    argv: Sequence[str], input_text: str | None = None
) -> subprocess.CompletedProcess:  # pragma: no cover - requires live gh auth
    return subprocess.run(
        list(argv), check=False, capture_output=True, text=True, input=input_text, timeout=60
    )


def build_candidate_queries(*, repo: str | None = None, org: str | None = None) -> tuple[SearchQuery, ...]:
    """Build deterministic Search API queries for approved + green PR candidates."""
    if repo and org:
        raise EvictionDetectionError("repo and org are mutually exclusive search scopes")
    scope_terms: list[str] = []
    if repo:
        if not _REPO_SCOPE_RE.match(repo):
            raise EvictionDetectionError(f"repo must be owner/name, got {repo!r}")
        scope_terms.append(f"repo:{repo}")
    if org:
        if not _ORG_SCOPE_RE.match(org):
            raise EvictionDetectionError(f"org must be a GitHub organization/user slug, got {org!r}")
        scope_terms.append(f"org:{org}")
    return (
        SearchQuery(
            "approved_green_pr",
            " ".join(["is:open", "is:pull-request", "review:approved", "status:success", *scope_terms]),
        ),
    )


def detect_repair_needed(
    *, repo: str, state: PullRequestState, detected_at: str | None = None
) -> RepairNeededEvent | None:
    """Return a ``repair-needed`` event iff PR state is approved, green, and repairable."""
    if not state.approved or not state.all_green:
        return None
    reason = _repair_reason(state)
    if reason is None:
        return None
    return RepairNeededEvent(
        repo=repo,
        pr_number=state.pr_number,
        head_sha=state.head_sha,
        merge_state_status=state.merge_state_status,
        mergeable=state.mergeable,
        reason=reason,
        review_decision=state.review_decision,
        rollup_state=state.rollup_state,
        detected_at=detected_at,
    )


def _repair_reason(state: PullRequestState) -> str | None:
    mergeable = state.mergeable or ""
    if mergeable in REPAIRABLE_MERGEABLE_STATES:
        return "conflicting"
    status = state.merge_state_status
    if status == "BEHIND":
        return "behind"
    if status == "DIRTY":
        return "dirty"
    return None


def poll_repair_needed(
    *,
    token: str,
    transport: Transport | None = None,
    gh_runner: GhRunner | None = None,
    repo: str | None = None,
    org: str | None = None,
    per_page: int = DEFAULT_SEARCH_PER_PAGE,
    detected_at: str | None = None,
) -> RepairPollResult:
    """Run one read-only Search API poll and emit deterministic repair-needed events."""
    if not token or not token.strip():
        raise EvictionDetectionError("poll_repair_needed requires a non-empty token")
    _transport = transport or _default_transport
    _gh_runner = gh_runner or _default_gh_runner
    events: list[RepairNeededEvent] = []
    rate_limit: dict[str, Any] = {}

    for query in build_candidate_queries(repo=repo, org=org):
        candidates, rate_limit = _search_once(
            token=token.strip(),
            transport=_transport,
            query=query,
            per_page=per_page,
        )
        for item in _dedupe_candidates(candidates):
            state = pr_state(_change_ref_for_candidate(item), gh_runner=_gh_runner)
            event = detect_repair_needed(repo=item["repo"], state=state, detected_at=detected_at)
            if event is not None:
                events.append(event)

    return RepairPollResult(events=tuple(events), rate_limit=rate_limit or None)


def _search_once(
    *,
    token: str,
    transport: Transport,
    query: SearchQuery,
    per_page: int,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": _ACCEPT,
        "X-GitHub-Api-Version": _API_VERSION,
    }
    params = urllib.parse.urlencode({
        "q": query.query,
        "per_page": str(per_page),
        "sort": "updated",
        "order": "desc",
    })
    status, resp_headers, body = transport("GET", f"{_API_ROOT}/search/issues?{params}", headers, None)
    if not (200 <= status < 300):
        raise EvictionDetectionError(f"repair-needed candidate search failed (HTTP {status})")
    try:
        payload = json.loads(body) if body and body.strip() else {}
    except (ValueError, TypeError) as exc:
        raise EvictionDetectionError(f"unparseable repair-needed candidate search payload: {exc}") from exc
    hits = payload.get("items", []) if isinstance(payload, Mapping) else []
    items: list[dict[str, Any]] = []
    for raw in hits if isinstance(hits, list) else []:
        item = _resolve_search_hit(raw) if isinstance(raw, Mapping) else None
        if item is not None:
            items.append(item)
    return items, _rate_limit_payload(resp_headers)


def _resolve_search_hit(raw: Mapping[str, Any]) -> dict[str, Any] | None:
    if not isinstance(raw.get("pull_request"), Mapping):
        return None
    repo = _repo_from_search_hit(raw)
    number = _positive_int(raw.get("number"))
    if repo is None or number is None:
        return None
    return {"repo": repo, "number": number}


def _repo_from_search_hit(raw: Mapping[str, Any]) -> str | None:
    repo_url = str(raw.get("repository_url") or "")
    marker = "/repos/"
    if marker in repo_url:
        parts = repo_url.split(marker, 1)[1].strip("/").split("/")
        if len(parts) >= 2:
            return f"{parts[0]}/{parts[1]}"
    html = str(raw.get("html_url") or "")
    marker = "github.com/"
    if marker in html:
        parts = html.split(marker, 1)[1].split("/")
        if len(parts) >= 2:
            return f"{parts[0]}/{parts[1]}"
    return None


def _positive_int(value: Any) -> int | None:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return None
    return parsed if parsed > 0 else None


def _dedupe_candidates(candidates: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    seen: set[tuple[str, int]] = set()
    for item in candidates:
        repo = str(item.get("repo") or "")
        number = _positive_int(item.get("number"))
        if not repo or number is None:
            continue
        key = (repo, number)
        if key in seen:
            continue
        seen.add(key)
        out.append({"repo": repo, "number": number})
    return out


def _change_ref_for_candidate(item: Mapping[str, Any]) -> ChangeRef:
    return ChangeRef(
        repo=str(item["repo"]),
        branch="",
        base="",
        pr_number=int(item["number"]),
        head_sha=None,
        manifest_paths=(),
        plan_ref="",
        changed=False,
        applied=True,
        verified=True,
    )


def _header(headers: Mapping[str, str], name: str) -> str | None:
    for key, value in headers.items():
        if key.lower() == name.lower():
            return value
    return None


def _rate_limit_payload(headers: Mapping[str, str]) -> dict[str, Any]:
    payload: dict[str, Any] = {}
    for header, key in (
        ("X-RateLimit-Limit", "limit"),
        ("X-RateLimit-Remaining", "remaining"),
        ("X-RateLimit-Reset", "reset"),
        ("Retry-After", "retry_after_seconds"),
    ):
        value = _header(headers, header)
        if value is not None:
            payload[key] = _parse_positive_int(value) if key != "reset" else value
    return payload


def _parse_positive_int(raw: str | None) -> int | None:
    if raw is None:
        return None
    try:
        value = int(str(raw).strip())
    except (TypeError, ValueError):
        return None
    return value if value > 0 else None
