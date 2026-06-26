"""Read-only controller awaiting-decision inbox (ce-ops#253).

The inbox is a deterministic view over scoped open pull requests. It does not
enqueue, rebase, review, or mutate anything; live I/O is limited to one GraphQL
read behind an injectable ``gh_runner``.
"""
from __future__ import annotations

import json
import os
import re
import subprocess
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from typing import Any

GhRunner = Callable[[Sequence[str], str | None], subprocess.CompletedProcess]

DEFAULT_CONTROLLER_LOGIN = "ce-dev-2"
DEFAULT_TOKEN_ENV = "GH_TOKEN"
DEFAULT_FIRST = 100
BUCKET_ORDER = ("needs_review", "stranded", "needs_rebase", "awaiting_operator")
REBASE_MERGE_STATES = {"BEHIND", "DIRTY"}
AWAITING_OPERATOR_LABELS = {"awaiting-operator", "hold", "awaiting-operator/hold"}
_HOLD_MARKER_RE = re.compile(r"awaiting[-\s]*operator|⏸", re.IGNORECASE)
_REDACTED = "<redacted>"
_GH_TOKEN_RE = re.compile(r"\b(?:gh[opusr]_|github_pat_)[A-Za-z0-9_.\-]+")
_JWT_RE = re.compile(r"\beyJ[A-Za-z0-9_-]+(?:\.[A-Za-z0-9_-]+){2}")
_AUTH_HEADER_RE = re.compile(r"(?i)\bauthorization\s*:\s*[^\r\n]+")
_BEARER_RE = re.compile(r"(?i)\bbearer\s+[A-Za-z0-9._~+/=\-]{16,}")


class ControllerInboxError(Exception):
    """Bad input or failed read-only inbox discovery."""


@dataclass(frozen=True)
class InboxScope:
    kind: str
    value: str

    def to_dict(self) -> dict[str, str]:
        return {"kind": self.kind, "value": self.value}


@dataclass(frozen=True)
class InboxPullRequest:
    repo: str
    number: int
    title: str
    url: str
    author: str
    review_decision: str | None
    merge_state_status: str | None
    rollup_state: str | None
    is_draft: bool
    labels: tuple[str, ...]
    requested_reviewers: tuple[str, ...]
    queued: bool
    hold_marker: bool

    def to_item(self, *, bucket: str) -> dict[str, Any]:
        return {
            "bucket": bucket,
            "repo": self.repo,
            "number": self.number,
            "title": self.title,
            "url": self.url,
            "author": self.author,
            "review_decision": self.review_decision,
            "merge_state_status": self.merge_state_status,
            "rollup_state": self.rollup_state,
            "is_draft": self.is_draft,
            "labels": list(self.labels),
            "requested_reviewers": list(self.requested_reviewers),
            "queued": self.queued,
            "hold_marker": self.hold_marker,
        }


@dataclass(frozen=True)
class ControllerInboxResult:
    scope: InboxScope
    controller_login: str
    buckets: Mapping[str, tuple[InboxPullRequest, ...]]

    @property
    def counts(self) -> dict[str, int]:
        return {bucket: len(self.buckets.get(bucket, ())) for bucket in BUCKET_ORDER}

    @property
    def total_count(self) -> int:
        return sum(self.counts.values())

    def to_dict(self) -> dict[str, Any]:
        return {
            "action": "controller_inbox",
            "scope": self.scope.to_dict(),
            "controller_login": self.controller_login,
            "counts": self.counts,
            "total_count": self.total_count,
            "buckets": {
                bucket: [pr.to_item(bucket=bucket) for pr in self.buckets.get(bucket, ())]
                for bucket in BUCKET_ORDER
            },
        }


def resolve_scope(*, repo: str | None = None, org: str | None = None) -> InboxScope:
    if repo and org:
        raise ControllerInboxError("repo and org are mutually exclusive")
    if repo:
        owner, name = _split_repo(repo)
        return InboxScope("repo", f"{owner}/{name}")
    if org:
        value = org.strip()
        if not value or any(ch.isspace() for ch in value):
            raise ControllerInboxError(f"org scope is malformed: {org!r}")
        return InboxScope("org", value)
    raise ControllerInboxError("controller inbox refuses an unscoped search")


def search_query(scope: InboxScope) -> str:
    if scope.kind == "repo":
        return f"repo:{scope.value} is:pr is:open"
    if scope.kind == "org":
        return f"org:{scope.value} is:pr is:open"
    raise ControllerInboxError(f"unsupported scope kind: {scope.kind!r}")


def token_from_env(name: str = DEFAULT_TOKEN_ENV) -> str:
    token = os.environ.get(name, "").strip()
    if not token:
        raise ControllerInboxError(f"{name} is required for controller inbox")
    return token


def gh_runner_with_token(token: str, runner: GhRunner | None = None) -> GhRunner:
    base = runner or _default_gh_runner

    def run(argv: Sequence[str], input_text: str | None = None) -> subprocess.CompletedProcess:
        old = os.environ.get("GH_TOKEN")
        os.environ["GH_TOKEN"] = token
        try:
            return base(argv, input_text)
        finally:
            if old is None:
                os.environ.pop("GH_TOKEN", None)
            else:
                os.environ["GH_TOKEN"] = old

    return run


def collect_controller_inbox(
    *,
    repo: str | None = None,
    org: str | None = None,
    controller_login: str = DEFAULT_CONTROLLER_LOGIN,
    gh_runner: GhRunner | None = None,
    first: int = DEFAULT_FIRST,
) -> ControllerInboxResult:
    scope = resolve_scope(repo=repo, org=org)
    controller = controller_login.strip()
    if not controller:
        raise ControllerInboxError("controller login is required")
    if first < 1 or first > 100:
        raise ControllerInboxError("first must be between 1 and 100")

    runner = gh_runner or _default_gh_runner
    parsed = _gh_graphql(
        runner,
        _INBOX_QUERY,
        {"searchQuery": search_query(scope), "first": first},
        purpose="read controller inbox",
    )
    prs = _parse_prs(parsed)
    buckets = classify_pull_requests(prs, controller_login=controller)
    return ControllerInboxResult(scope=scope, controller_login=controller, buckets=buckets)


def classify_pull_requests(
    prs: Sequence[InboxPullRequest],
    *,
    controller_login: str = DEFAULT_CONTROLLER_LOGIN,
) -> dict[str, tuple[InboxPullRequest, ...]]:
    controller = controller_login.strip().lower()
    out: dict[str, list[InboxPullRequest]] = {bucket: [] for bucket in BUCKET_ORDER}
    for pr in sorted(prs, key=lambda item: (item.repo, item.number)):
        if _needs_review(pr, controller):
            out["needs_review"].append(pr)
        if _is_stranded(pr):
            out["stranded"].append(pr)
        if _needs_rebase(pr):
            out["needs_rebase"].append(pr)
        if _awaiting_operator(pr):
            out["awaiting_operator"].append(pr)
    return {bucket: tuple(out[bucket]) for bucket in BUCKET_ORDER}


def format_table(result: ControllerInboxResult) -> str:
    rows: list[dict[str, str]] = []
    for bucket in BUCKET_ORDER:
        for pr in result.buckets.get(bucket, ()):
            rows.append(
                {
                    "bucket": bucket,
                    "pr": f"{pr.repo}#{pr.number}",
                    "author": pr.author,
                    "review": pr.review_decision or "-",
                    "merge": pr.merge_state_status or "-",
                    "checks": pr.rollup_state or "-",
                    "queued": "yes" if pr.queued else "no",
                    "title": _one_line(pr.title),
                }
            )
    headers = {
        "bucket": "BUCKET",
        "pr": "PR",
        "author": "AUTHOR",
        "review": "REVIEW",
        "merge": "MERGE",
        "checks": "CHECKS",
        "queued": "QUEUED",
        "title": "TITLE",
    }
    columns = tuple(headers)
    widths = {
        col: max(len(headers[col]), *(len(row[col]) for row in rows)) if rows else len(headers[col])
        for col in columns
    }
    lines = [
        " ".join(headers[col].ljust(widths[col]) for col in columns),
        " ".join("-" * widths[col] for col in columns),
    ]
    lines.extend(" ".join(row[col].ljust(widths[col]) for col in columns) for row in rows)
    if not rows:
        lines.append("(empty)")
    return "\n".join(lines)


def redact_gh_stderr(text: str) -> str:
    if not text:
        return ""
    masked = text.strip()
    masked = _AUTH_HEADER_RE.sub(f"Authorization: {_REDACTED}", masked)
    masked = _GH_TOKEN_RE.sub(_REDACTED, masked)
    masked = _JWT_RE.sub(_REDACTED, masked)
    masked = _BEARER_RE.sub(_REDACTED, masked)
    return masked


def _needs_review(pr: InboxPullRequest, controller: str) -> bool:
    return (
        not pr.is_draft
        and pr.author.lower() != controller
        and (pr.review_decision or "") != "APPROVED"
        and controller in {reviewer.lower() for reviewer in pr.requested_reviewers}
    )


def _is_stranded(pr: InboxPullRequest) -> bool:
    return (
        not pr.is_draft
        and pr.review_decision == "APPROVED"
        and pr.rollup_state == "SUCCESS"
        and pr.merge_state_status == "CLEAN"
        and not pr.queued
    )


def _needs_rebase(pr: InboxPullRequest) -> bool:
    return not pr.is_draft and (pr.merge_state_status or "") in REBASE_MERGE_STATES


def _awaiting_operator(pr: InboxPullRequest) -> bool:
    labels = {label.lower() for label in pr.labels}
    return pr.hold_marker or bool(labels & AWAITING_OPERATOR_LABELS)


def _parse_prs(parsed: Mapping[str, Any]) -> tuple[InboxPullRequest, ...]:
    search = ((parsed.get("data") or {}).get("search") or {})
    if not isinstance(search, Mapping):
        raise ControllerInboxError("unexpected controller inbox response")
    if ((search.get("pageInfo") or {}).get("hasNextPage")) is True:
        raise ControllerInboxError("controller inbox search returned more than one page; narrow scope")

    raw_nodes = search.get("nodes")
    if not isinstance(raw_nodes, list):
        raise ControllerInboxError("controller inbox response missing nodes")

    queued_numbers = _queued_numbers(raw_nodes)
    prs: list[InboxPullRequest] = []
    for node in raw_nodes:
        if isinstance(node, Mapping):
            prs.append(_parse_pr(node, queued_numbers))
    return tuple(prs)


def _queued_numbers(nodes: Sequence[Any]) -> set[tuple[str, int]]:
    queued: set[tuple[str, int]] = set()
    for node in nodes:
        if not isinstance(node, Mapping):
            continue
        repository = node.get("repository") if isinstance(node.get("repository"), Mapping) else {}
        queue = repository.get("mergeQueue") if isinstance(repository.get("mergeQueue"), Mapping) else {}
        entries = queue.get("entries") if isinstance(queue, Mapping) else {}
        if not isinstance(entries, Mapping):
            continue
        if ((entries.get("pageInfo") or {}).get("hasNextPage")) is True:
            raise ControllerInboxError("merge queue entries returned more than one page; narrow scope")
        for entry in entries.get("nodes") or ():
            if not isinstance(entry, Mapping):
                continue
            pr = entry.get("pullRequest")
            if not isinstance(pr, Mapping):
                continue
            repo = str(((pr.get("repository") or {}).get("nameWithOwner") or "")).strip()
            number = pr.get("number")
            if repo and isinstance(number, int):
                queued.add((repo, number))
    return queued


def _parse_pr(node: Mapping[str, Any], queued_numbers: set[tuple[str, int]]) -> InboxPullRequest:
    repo = str(((node.get("repository") or {}).get("nameWithOwner") or "")).strip()
    number = node.get("number")
    if not repo or not isinstance(number, int):
        raise ControllerInboxError("controller inbox PR missing repo or number")
    labels = tuple(
        sorted(
            str(item.get("name"))
            for item in (((node.get("labels") or {}).get("nodes")) or ())
            if isinstance(item, Mapping) and isinstance(item.get("name"), str)
        )
    )
    requested = tuple(
        sorted(
            str(item.get("login"))
            for item in (((node.get("requestedReviewers") or {}).get("nodes")) or ())
            if isinstance(item, Mapping) and isinstance(item.get("login"), str)
        )
    )
    commit = _latest_commit_node(node)
    rollup = commit.get("statusCheckRollup") if isinstance(commit, Mapping) else None
    author = str(((node.get("author") or {}).get("login") or "")).strip()
    body = str(node.get("body") or "")
    return InboxPullRequest(
        repo=repo,
        number=number,
        title=str(node.get("title") or ""),
        url=str(node.get("url") or ""),
        author=author,
        review_decision=node.get("reviewDecision") if isinstance(node.get("reviewDecision"), str) else None,
        merge_state_status=(
            node.get("mergeStateStatus") if isinstance(node.get("mergeStateStatus"), str) else None
        ),
        rollup_state=(
            rollup.get("state") if isinstance(rollup, Mapping) and isinstance(rollup.get("state"), str) else None
        ),
        is_draft=bool(node.get("isDraft")),
        labels=labels,
        requested_reviewers=requested,
        queued=(repo, number) in queued_numbers,
        hold_marker=bool(_HOLD_MARKER_RE.search(body)),
    )


def _latest_commit_node(node: Mapping[str, Any]) -> Mapping[str, Any]:
    commits = node.get("commits") if isinstance(node.get("commits"), Mapping) else {}
    commit_nodes = commits.get("nodes") if isinstance(commits, Mapping) else None
    if not isinstance(commit_nodes, list) or not commit_nodes:
        return {}
    wrapper = commit_nodes[-1]
    if not isinstance(wrapper, Mapping):
        return {}
    commit = wrapper.get("commit")
    return commit if isinstance(commit, Mapping) else {}


def _gh_graphql(runner: GhRunner, query: str, variables: dict[str, object], *, purpose: str) -> dict[str, Any]:
    argv = ["gh", "api", "graphql", "-f", f"query={query}"]
    for key, value in variables.items():
        flag = "-f" if isinstance(value, str) else "-F"
        argv += [flag, f"{key}={value}"]
    proc = runner(argv, None)
    if proc.returncode != 0:
        stderr = redact_gh_stderr(proc.stderr or "")
        raise ControllerInboxError(f"could not {purpose}: {stderr or 'unknown error'}")
    try:
        parsed = json.loads((proc.stdout or "").strip() or "{}")
    except (TypeError, ValueError) as exc:
        raise ControllerInboxError(f"could not {purpose}: unparseable JSON response") from exc
    if not isinstance(parsed, dict):
        raise ControllerInboxError(f"could not {purpose}: unexpected JSON response")
    return parsed


def _default_gh_runner(
    argv: Sequence[str], input_text: str | None = None
) -> subprocess.CompletedProcess:  # pragma: no cover - live gh edge
    return subprocess.run(
        list(argv), check=False, capture_output=True, text=True, input=input_text, timeout=60
    )


def _split_repo(repo: str) -> tuple[str, str]:
    parts = (repo or "").split("/", 1)
    if len(parts) != 2 or not all(part.strip() for part in parts):
        raise ControllerInboxError(f"repo must be owner/name, got {repo!r}")
    return parts[0].strip(), parts[1].strip()


def _one_line(text: str) -> str:
    return " ".join(str(text).split())


_INBOX_QUERY = (
    "query($searchQuery:String!,$first:Int!){"
    "search(type:ISSUE,query:$searchQuery,first:$first){pageInfo{hasNextPage endCursor}nodes{"
    "... on PullRequest{"
    "number title url body isDraft reviewDecision mergeStateStatus mergeable "
    "author{login} repository{nameWithOwner "
    "mergeQueue{entries(first:100){pageInfo{hasNextPage}nodes{pullRequest{number repository{nameWithOwner}}}}}} "
    "labels(first:50){nodes{name}} "
    "requestedReviewers(first:50){nodes{... on User{login}}} "
    "commits(last:1){nodes{commit{oid statusCheckRollup{state}}}} "
    "}}}}"
)
