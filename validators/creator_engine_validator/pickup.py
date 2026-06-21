"""CE ce-ops#55/#182 — the autonomous forge work-pickup poller (the "conveyor belt").

A per-seat **read-only** poller that lets a dev-seat pick up its OWN GitHub
review-requests / assigned-issues / labeled / @mention work with no human relay.

Adopted design (ce-ops#55, amended by ce-ops#182):

* Poll the GitHub **Search API** (``GET /search/issues``) instead of
  ``GET /notifications`` so fine-grained read-only PATs can drive the feed.
  The query set is deterministic and explicitly typed: PR-only
  ``is:pull-request review-requested:@me`` → ``review_requested``; PR + issue
  ``assignee:@me`` → ``assigned``; PR + issue ``mentions:@me`` → ``mention``;
  and optionally PR + issue ``label:"…"`` → ``labeled`` for team-label pickup.
* Per-identity auth via ``~/.ce-keys/ce-dev-N.pat`` (or ``CE_PICKUP_TOKEN``).
  Ambient ``gh auth token`` is used only when explicitly opted into by the local
  convention (``--allow-ambient-gh`` or ``CE_PICKUP_ALLOW_AMBIENT_GH=1``).
* Resolve each Search hit → a normalized work-item
  ``{repo, kind, number, url, reason, thread_id}``. Search has no notification
  thread id, so the thread id is stable and synthetic:
  ``search:{reason}:{repo}:{kind}:{number}``.
* Honor Search API rate limiting by failing closed on HTTP ``403``/``429`` and
  carrying ``Retry-After`` / ``X-RateLimit-Reset`` metadata to the CLI. The
  default poll interval is five minutes, which is within the Search API budget.

**Hard Ring-0 constraint (verified in code):** CE refuses headless authoring —
``claude_launch_spec.CLAUSE_PRINT`` (``CC-D-2``: ``-p``/``--print``) and
``codex_launch_spec.CLAUSE_HEADLESS`` (``CDX-D-1``: ``exec``/``review``/``apply``).
So this poller is **read-only and NEVER authors**. Actual work runs as a fresh
governed lane via ``ce lane launch`` (S3), fed a seed-file; the poller only
observes (S1), claims via the forge (S2), and triggers the lane (S3, gated OFF
by default).

The live network touch lives behind an injectable ``transport`` seam (a stdlib
``urllib`` HTTPS call by default), mirroring ``forge/app_jwt_runner.py``; tests
inject fakes and perform ZERO live network / subprocess. Importing this module
performs no I/O and registers no validator check.

Defensive only — it picks up the Creator Engine's own work; never offensive.
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from . import work_claims

#: HTTPS transport: ``(method, url, headers, body) -> (status, headers, body_text)``.
Transport = Callable[[str, str, "dict[str, str]", "str | None"], "tuple[int, dict[str, str], str]"]

_API_ROOT = "https://api.github.com"
_API_VERSION = "2022-11-28"
_ACCEPT = "application/vnd.github+json"

#: The default seat PAT location (per-identity, one file per dev).
DEFAULT_KEYS_DIR = Path.home() / ".ce-keys"
#: The env override for the seat token (takes precedence over the PAT file).
TOKEN_ENV = "CE_PICKUP_TOKEN"
#: Explicit opt-in for falling back to the local ``gh auth token`` store.
AMBIENT_GH_TOKEN_ENV = "CE_PICKUP_ALLOW_AMBIENT_GH"

#: Search API pickup cadence. Three queries plus optional labels every five
#: minutes stays within the documented Search API budget for one seat.
DEFAULT_POLL_INTERVAL = 300
DEFAULT_SEARCH_PER_PAGE = 100

_PR_SEARCH_TYPE = "is:pull-request"
_ISSUE_SEARCH_TYPE = "is:issue"

_REPO_SCOPE_RE = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")
_ORG_SCOPE_RE = re.compile(r"^[A-Za-z0-9_.-]+$")


class PickupError(Exception):
    """Bad local input / missing credential / unreachable forge (CLI exit 2)."""

    code = "PICKUP-INPUT"


class PickupRateLimited(PickupError):
    """Search API refused the poll with a rate-limit/backoff response."""

    code = "PICKUP-RATE-LIMITED"

    def __init__(
        self,
        message: str,
        *,
        status: int,
        retry_after_seconds: int | None = None,
        rate_limit_reset: str | None = None,
    ) -> None:
        super().__init__(message)
        self.status = status
        self.retry_after_seconds = retry_after_seconds
        self.rate_limit_reset = rate_limit_reset

    def to_payload(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "status": self.status,
            "retry_after_seconds": self.retry_after_seconds,
            "rate_limit_reset": self.rate_limit_reset,
        }
        return {k: v for k, v in payload.items() if v is not None}


@dataclass(frozen=True)
class SearchQuery:
    """One GitHub Search query and the pickup reason assigned to its hits."""

    reason: str
    query: str


@dataclass(frozen=True)
class PollResult:
    """The outcome of one read-only Search API poll (PURE value).

    Search API has no notification cursor. ``last_modified`` and
    ``not_modified`` are retained as output fields for the existing belt JSON
    contract, but they are always ``None`` / ``False`` for Search-backed polls.
    """

    items: tuple[dict[str, Any], ...] = ()
    last_modified: str | None = None
    poll_interval: int = DEFAULT_POLL_INTERVAL
    not_modified: bool = False
    rate_limit: Mapping[str, Any] | None = None


def _default_transport(  # pragma: no cover - the lone live HTTPS shell; tests inject a fake
    method: str, url: str, headers: dict[str, str], body: str | None
) -> tuple[int, dict[str, str], str]:
    data = body.encode("utf-8") if body is not None else None
    request = urllib.request.Request(url, data=data, method=method, headers=headers)
    try:
        with urllib.request.urlopen(request, timeout=60) as resp:
            return resp.status, dict(resp.headers), resp.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as exc:
        return exc.code, dict(exc.headers or {}), exc.read().decode("utf-8", "replace")


def resolve_token(
    *,
    keys_dir: Path | str | None = None,
    identity: str,
    environ: Mapping[str, str] | None = None,
    allow_ambient_gh: bool = False,
    gh_token_runner: Callable[[], subprocess.CompletedProcess] | None = None,
) -> str:
    """Resolve the per-identity PAT without ever logging its value.

    Order:

    1. ``$CE_PICKUP_TOKEN``.
    2. ``<keys_dir>/<identity>.pat`` (default ``~/.ce-keys/<identity>.pat``).
    3. Ambient ``gh auth token`` only when explicitly enabled by local convention
       (``allow_ambient_gh`` or ``CE_PICKUP_ALLOW_AMBIENT_GH=1``).

    Per-identity auth keeps the pickup loop running as the dev's OWN account (the
    #137 identity model), never a shared/overwatch token. A missing credential
    raises :class:`PickupError` (fail-closed).
    """
    env = os.environ if environ is None else environ
    env_token = env.get(TOKEN_ENV)
    if env_token and env_token.strip():
        return env_token.strip()
    base = Path(keys_dir) if keys_dir is not None else DEFAULT_KEYS_DIR
    pat = base / f"{identity}.pat"
    if pat.is_file():
        text = pat.read_text(encoding="utf-8").strip()
        if text:
            return text
    if allow_ambient_gh or _truthy(env.get(AMBIENT_GH_TOKEN_ENV)):
        ambient_env = env.get("GH_TOKEN") or env.get("GITHUB_TOKEN")
        if ambient_env and ambient_env.strip():
            return ambient_env.strip()
        ambient = _ambient_gh_token(gh_token_runner)
        if ambient:
            return ambient
    raise PickupError(
        f"no pickup token for identity {identity!r}: set ${TOKEN_ENV}, write {pat}, "
        f"or opt into ambient gh auth with ${AMBIENT_GH_TOKEN_ENV}=1"
    )


def _truthy(value: str | None) -> bool:
    return str(value or "").strip().lower() in {"1", "true", "yes", "on"}


def _ambient_gh_token(
    gh_token_runner: Callable[[], subprocess.CompletedProcess] | None = None,
) -> str | None:
    runner = gh_token_runner or _default_gh_token_runner
    try:
        proc = runner()
    except Exception:
        return None
    if getattr(proc, "returncode", 1) != 0:
        return None
    token = (getattr(proc, "stdout", "") or "").strip()
    return token or None


def _default_gh_token_runner() -> subprocess.CompletedProcess:  # pragma: no cover - local gh seam
    return subprocess.run(["gh", "auth", "token"], check=False, capture_output=True, text=True, timeout=30)


def _header(headers: Mapping[str, str], name: str) -> str | None:
    """Case-insensitive header lookup (HTTP header names are case-insensitive)."""
    for key, value in headers.items():
        if key.lower() == name.lower():
            return value
    return None


def build_queries(
    *,
    labels: Sequence[str] = (),
    repo: str | None = None,
    org: str | None = None,
) -> tuple[SearchQuery, ...]:
    """Build the deterministic Search API query set for one poll."""
    if repo and org:
        raise PickupError("--repo and --org are mutually exclusive search scopes")
    normalized_labels = _normalize_labels(labels)
    if normalized_labels and not (repo or org):
        raise PickupError("--label requires an explicit Search scope: supply --repo owner/name or --org slug")
    scope_terms: list[str] = []
    if repo:
        if not _REPO_SCOPE_RE.match(repo):
            raise PickupError(f"--repo must be owner/name, got {repo!r}")
        scope_terms.append(f"repo:{repo}")
    if org:
        if not _ORG_SCOPE_RE.match(org):
            raise PickupError(f"--org must be a GitHub organization/user slug, got {org!r}")
        scope_terms.append(f"org:{org}")

    specs = [
        SearchQuery(
            "review_requested",
            " ".join(["is:open", _PR_SEARCH_TYPE, "review-requested:@me", *scope_terms]),
        ),
    ]
    for reason, selector in (
        ("assigned", "assignee:@me"),
        ("mention", "mentions:@me"),
    ):
        specs.extend(
            SearchQuery(reason, " ".join(["is:open", search_type, selector, *scope_terms]))
            for search_type in (_PR_SEARCH_TYPE, _ISSUE_SEARCH_TYPE)
        )
    for label in normalized_labels:
        specs.extend(
            SearchQuery("labeled", " ".join(["is:open", search_type, _label_term(label), *scope_terms]))
            for search_type in (_PR_SEARCH_TYPE, _ISSUE_SEARCH_TYPE)
        )
    return tuple(specs)


def _normalize_labels(labels: Sequence[str]) -> tuple[str, ...]:
    out: list[str] = []
    seen: set[str] = set()
    for raw in labels or ():
        for part in str(raw).split(","):
            label = part.strip()
            if label and label not in seen:
                seen.add(label)
                out.append(label)
    return tuple(out)


def _label_term(label: str) -> str:
    escaped = label.replace("\\", "\\\\").replace('"', '\\"')
    return f'label:"{escaped}"'


def poll(
    *,
    token: str,
    transport: Transport | None = None,
    labels: Sequence[str] = (),
    repo: str | None = None,
    org: str | None = None,
    per_page: int = DEFAULT_SEARCH_PER_PAGE,
) -> PollResult:
    """One READ-ONLY Search API poll → a :class:`PollResult` (observe-only).

    This issues one ``GET /search/issues`` request per configured reason query,
    normalizes hits to the belt work-item shape, de-duplicates overlapping query
    hits by ``(repo, number)``, and NEVER mutates the forge.
    """
    if not token or not token.strip():
        raise PickupError("poll requires a non-empty token")
    _transport = transport or _default_transport
    queries = build_queries(labels=labels, repo=repo, org=org)
    items: list[dict[str, Any]] = []
    rate_limit: dict[str, Any] = {}

    for query in queries:
        page_items, rate_limit = _search_once(
            token=token.strip(),
            transport=_transport,
            query=query,
            per_page=per_page,
        )
        items.extend(page_items)

    return PollResult(
        items=tuple(_dedupe_items(items)),
        last_modified=None,
        poll_interval=DEFAULT_POLL_INTERVAL,
        not_modified=False,
        rate_limit=rate_limit or None,
    )


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
    url = f"{_API_ROOT}/search/issues?{params}"
    status, resp_headers, body = transport("GET", url, headers, None)

    if status in (403, 429):
        raise _rate_limited(status, resp_headers)
    if not (200 <= status < 300):
        raise PickupError(f"search poll failed (HTTP {status})")

    try:
        payload = json.loads(body) if body and body.strip() else {}
    except (ValueError, TypeError) as exc:
        raise PickupError(f"unparseable search payload: {exc}") from exc
    hits = payload.get("items", []) if isinstance(payload, Mapping) else []

    items: list[dict[str, Any]] = []
    for raw in hits if isinstance(hits, list) else []:
        item = resolve_search_hit(raw, query.reason) if isinstance(raw, Mapping) else None
        if item is not None:
            items.append(item)
    return items, _rate_limit_payload(resp_headers)


def _rate_limited(status: int, headers: Mapping[str, str]) -> PickupRateLimited:
    retry_after = _parse_positive_int(_header(headers, "Retry-After"))
    reset = _header(headers, "X-RateLimit-Reset")
    return PickupRateLimited(
        f"search poll failed closed (HTTP {status}); retry later",
        status=status,
        retry_after_seconds=retry_after,
        rate_limit_reset=reset,
    )


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
    except (ValueError, TypeError):
        return None
    return value if value > 0 else None


def resolve_search_hit(raw: Mapping[str, Any], reason: str) -> dict[str, Any] | None:
    """Normalize one Search API issue/PR hit into the belt work-item shape."""
    repo = _repo_from_search_hit(raw)
    number = _issue_number(raw.get("number"))
    if not repo or number is None:
        return None
    is_pr = isinstance(raw.get("pull_request"), Mapping)
    subject_type = "PullRequest" if is_pr else "Issue"
    url = str(raw.get("html_url") or "").strip()
    if not url:
        web_kind = "pull" if is_pr else "issues"
        url = f"https://github.com/{repo}/{web_kind}/{number}"
    kind = reason
    return {
        "repo": repo,
        "kind": kind,
        "number": number,
        "url": url,
        "reason": reason,
        "thread_id": f"search:{reason}:{repo}:{kind}:{number}",
        "title": raw.get("title"),
        "subject_type": subject_type,
        "updated_at": raw.get("updated_at"),
    }


def _repo_from_search_hit(raw: Mapping[str, Any]) -> str | None:
    repo_url = str(raw.get("repository_url") or "")
    marker = "/repos/"
    if marker in repo_url:
        slug = repo_url.split(marker, 1)[1].strip("/")
        parts = slug.split("/")
        if len(parts) >= 2:
            return f"{parts[0]}/{parts[1]}"
    html = str(raw.get("html_url") or "")
    marker = "github.com/"
    if marker in html:
        slug = html.split(marker, 1)[1].split("/")
        if len(slug) >= 2:
            return f"{slug[0]}/{slug[1]}"
    return None


def _issue_number(value: Any) -> int | None:
    try:
        number = int(value)
    except (TypeError, ValueError):
        return None
    return number if number > 0 else None


def _dedupe_items(items: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    seen: set[tuple[str, int]] = set()
    for item in items:
        key = (str(item.get("repo") or ""), int(item.get("number") or 0))
        if not key[0] or key[1] <= 0 or key in seen:
            continue
        seen.add(key)
        out.append(item)
    return out


# ===========================================================================
# S2 — claim + idempotency (forge-arbitrated claim + an append-only dedup ledger).
# ===========================================================================

#: The append-only dedup ledger (NDJSON), mirroring ``runner/notify_feed.py``'s
#: pure-fold pattern: the dedup key is ``(thread_id, item_id, action)`` and carries
#: ONLY GitHub server timestamps — NO wall-clock diffing — so it is idempotent
#: across restarts and re-polls by construction.
DEFAULT_LEDGER_NAME = "ledger.ndjson"

#: The single pickup ``action`` recorded today (one per picked-up thread).
ACTION_CLAIM = "claim"

#: A GhRunner runs a ``gh`` invocation (argv incl. the leading "gh") with an
#: optional stdin body — the same shape as ``work_claims.GhRunner``.
GhRunner = Callable[[Sequence[str], "str | None"], "subprocess.CompletedProcess"]

#: A PR-author lookup: ``(item, gh_runner) -> author_login`` (the independent-
#: reviewer fence input). Injectable so tests perform zero live forge reads.
PrAuthorLookup = Callable[[Mapping[str, Any], GhRunner], "str | None"]


@dataclass(frozen=True)
class ClaimOutcome:
    """The outcome of attempting to claim one work-item (PURE value).

    ``claimed`` is the gate for an S3 launch. ``reason`` is one of: ``claimed`` /
    ``already_seen`` (dedup) / ``own_pr_review_refused`` (independent-reviewer) /
    ``active_foreign_claim`` / ``stale_foreign_claim`` / ``lost_after_reread`` /
    ``no_number``. ``would_launch`` / ``launched`` are set by the S3 caller.
    """

    item: Mapping[str, Any]
    claimed: bool
    reason: str
    claim_id: str | None = None
    posted_url: str | None = None
    would_launch: bool = False
    launched: bool = False
    seed_path: str | None = None
    note: str | None = None


def ledger_key(thread_id: str, item_id: str, action: str) -> tuple[str, str, str]:
    """The dedup identity ``(thread_id, item_id, action)`` — NO clock term."""
    return (str(thread_id), str(item_id), str(action))


def _ledger_path(path: Path | str) -> Path:
    return Path(path)


def load_ledger(path: Path | str) -> list[dict[str, Any]]:
    """Read the dedup ledger (NDJSON, tolerant). Missing file ⇒ ``[]`` (I/O edge).

    A malformed line is skipped (at worst a benign re-claim attempt that the
    forge-arbitrated acquire then fails closed on — never a lost pickup).
    """
    p = _ledger_path(path)
    if not p.is_file():
        return []
    out: list[dict[str, Any]] = []
    try:
        text = p.read_text(encoding="utf-8")
    except OSError:
        return out
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            record = json.loads(line)
        except (ValueError, TypeError):
            continue
        if isinstance(record, dict):
            out.append(record)
    return out


def ledger_keys(records: Iterable[Mapping[str, Any]]) -> set[tuple[str, str, str]]:
    """Fold ledger records → the set of seen dedup keys (PURE)."""
    keys: set[tuple[str, str, str]] = set()
    for r in records:
        if not isinstance(r, Mapping):
            continue
        keys.add(ledger_key(
            str(r.get("thread_id") or ""),
            str(r.get("item_id") or ""),
            str(r.get("action") or ""),
        ))
    return keys


def append_ledger(path: Path | str, record: Mapping[str, Any]) -> None:
    """Append one dedup record to the ledger (I/O edge, the only governance-free write)."""
    p = _ledger_path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, "a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, sort_keys=True) + "\n")


def _item_id(item: Mapping[str, Any]) -> str:
    """The stable per-item dedup component: ``<repo>:<number>``."""
    return f"{item.get('repo')}:{item.get('number')}"


def default_pr_author_lookup(item: Mapping[str, Any], gh_runner: GhRunner) -> str | None:
    """Resolve a PR's author login via ``GET repos/{repo}/pulls/{n}`` (live read).

    Returns ``None`` when the item is not a PR or the read does not yield an
    author. For ``review_requested`` items, the caller treats ``None`` as
    indeterminate and refuses before claiming; the no-self-review fence must
    prove the author is foreign, not merely fail to prove it is us. Never raises.
    """
    repo = str(item.get("repo") or "")
    number = item.get("number")
    if not repo or number is None or str(item.get("subject_type")) != "PullRequest":
        return None
    try:
        proc = gh_runner(["gh", "api", "--method", "GET", f"repos/{repo}/pulls/{number}"], None)
    except Exception:
        return None
    out = (getattr(proc, "stdout", "") or "").strip()
    if not out:
        return None
    try:
        payload = json.loads(out)
    except (ValueError, TypeError):
        return None
    user = payload.get("user") if isinstance(payload, Mapping) else None
    return user.get("login") if isinstance(user, Mapping) else None


def _self_assign(work_key: work_claims.WorkKey, identity: str, gh_runner: GhRunner) -> bool:
    """Self-assign the issue/PR to ``identity`` (best-effort; never raises).

    Returns ``ok``. The structured claim comment is the AUTHORITATIVE lock (the
    #38 work-claim shape); the assignee is the human-visible forge signal.
    """
    try:
        proc = gh_runner(
            ["gh", "api", "--method", "POST",
             f"repos/{work_key.repo_slug}/issues/{work_key.number}/assignees",
             "--input", "-"],
            json.dumps({"assignees": [identity]}),
        )
    except Exception:
        return False
    return getattr(proc, "returncode", 1) == 0


def claim_item(
    item: Mapping[str, Any],
    *,
    identity: str,
    gh_runner: GhRunner,
    ledger_path: Path | str,
    run_id: str,
    pr_author_lookup: PrAuthorLookup | None = None,
    backoff_seconds: float = 1.0,
) -> ClaimOutcome:
    """Forge-arbitrate a claim on one work-item (fail-closed), with dedup + the
    independent-reviewer fence.

    Order (each gate fails closed before any side effect):

    1. **Independent-reviewer refusal** — for a ``review_requested`` item whose PR
       author IS this identity, refuse (we never review our own PR). NO post.
    2. **Dedup** — if ``(thread_id, <repo>:<number>, claim)`` is already in the
       ledger, short-circuit (``already_seen``); NO post.
    3. **Forge-arbitrated claim** — ``work_claims.acquire`` reads → refuses on a
       foreign active claim → posts the structured ``ce-work-claim`` marker (the
       #38 shape) → re-reads after a bounded backoff → proceeds only if our claim
       wins, else posts a void release and fails closed.
    4. **Self-assign** the issue/PR to ``identity`` (human-visible forge signal).
    5. **Append** the dedup record (server timestamps only; no wall-clock).
    """
    number = item.get("number")
    repo = str(item.get("repo") or "")
    if not repo or number is None:
        return ClaimOutcome(item=item, claimed=False, reason="no_number")

    thread_id = str(item.get("thread_id") or "")
    item_id = _item_id(item)
    key_tuple = ledger_key(thread_id, item_id, ACTION_CLAIM)

    # 1. Independent-reviewer refusal (own-PR review) — before any side effect.
    if item.get("kind") == "review_requested":
        lookup = pr_author_lookup or default_pr_author_lookup
        author = lookup(item, gh_runner)
        if not author:
            return ClaimOutcome(
                item=item,
                claimed=False,
                reason="pr_author_unknown_refused",
                note="PR author lookup was unavailable — refusing review claim fail-closed",
            )
        if author and author == identity:
            return ClaimOutcome(item=item, claimed=False, reason="own_pr_review_refused",
                                note=f"PR author {author!r} is this identity — refusing self-review")

    # 2. Dedup — a server-keyed short-circuit (no wall-clock).
    if key_tuple in ledger_keys(load_ledger(ledger_path)):
        return ClaimOutcome(item=item, claimed=False, reason="already_seen")

    # 3. Forge-arbitrated claim (fail-closed, race-tested in work_claims.acquire).
    work_key = work_claims.WorkKey(*repo.split("/", 1), int(number))
    result = work_claims.acquire(
        work_key, gh_runner,
        holder=identity, host=identity, reason="manual",
        backoff_seconds=backoff_seconds,
    )
    if not result.ok:
        return ClaimOutcome(item=item, claimed=False,
                            reason=result.refusal_reason or "claim_refused",
                            note=result.note)

    # 4. Self-assign (human-visible; the comment marker is the authoritative lock).
    _self_assign(work_key, identity, gh_runner)

    # 5. Append the dedup record (GitHub server-time stamp from the marker).
    append_ledger(ledger_path, {
        "kind": "ce-pickup-dedup",
        "schema_version": 1,
        "thread_id": thread_id,
        "item_id": item_id,
        "action": ACTION_CLAIM,
        "repo": repo,
        "number": int(number),
        "work_kind": item.get("kind"),
        "identity": identity,
        "run_id": run_id,
        "claim_id": result.claim_id,
        "claimed_at": _claim_marker_time(result),
    })
    return ClaimOutcome(item=item, claimed=True, reason="claimed",
                        claim_id=result.claim_id, posted_url=result.posted_url)


def _claim_marker_time(result: work_claims.ClaimResult) -> str | None:
    """The GitHub server-time of the winning claim marker (never the local clock)."""
    active = result.state.active if result.state else None
    return active.claimed_at if active else None


#: Ambient auth env vars dropped from the child ``gh`` env so the per-identity
#: ``GH_TOKEN`` is unambiguous (``GH_TOKEN`` already wins by precedence; dropping
#: these is defense-in-depth — the same hygiene the v3 credential_runner applies).
_AMBIENT_AUTH_ENV = ("GITHUB_TOKEN", "GH_CONFIG_DIR", "GH_HOST")


def make_gh_runner(token: str) -> GhRunner:
    """Return a :data:`GhRunner` that runs ``gh`` AS ``identity`` (token in the child env ONLY).

    The per-identity PAT lands in a per-call child ``GH_TOKEN`` env — never the
    argv, a log, the returned process, or disk — so the pickup loop authenticates
    as the dev's OWN account (the #137 identity model), never ambient/overwatch auth.
    """
    def runner(argv: Sequence[str], input_text: str | None = None) -> subprocess.CompletedProcess:
        env = dict(os.environ)
        for var in _AMBIENT_AUTH_ENV:
            env.pop(var, None)
        env["GH_TOKEN"] = token
        return subprocess.run(
            list(argv), check=False, capture_output=True, text=True,
            input=input_text, env=env, timeout=60,
        )
    return runner


# ===========================================================================
# S3 — `ce lane launch` wiring (canary, gated behind --enable-launch).
# ===========================================================================

import hashlib  # noqa: E402  (kept local to the S3 leg)

#: The spawn seam: ``(argv) -> CompletedProcess``. Defaults to a real subprocess
#: ``ce lane launch`` (the v1→v1 SUBPROCESS + DATA cross to the launcher — keeps
#: ALL tmux coupling behind the lane primitive, the one seam). Tests inject a fake.
Spawn = Callable[[Sequence[str]], "subprocess.CompletedProcess"]

#: Work-item ``kind`` → the governed lane ``--role`` / ``--lane-kind``. A review
#: request drives a reviewer/review lane; everything else an implementer lane.
_KIND_TO_ROLE = {"review_requested": "reviewer"}
_KIND_TO_LANE_KIND = {"review_requested": "review"}
_DEFAULT_ROLE = "implementer"
_DEFAULT_LANE_KIND = "implementation"

#: The lane-launch sentinel that confirms the seat is live (the lane runtime's
#: registered lifecycle state). Search-backed work has no read-state API; this
#: sentinel still gates launch success and seed bookkeeping.
LAUNCHED_STATE = "launched"


@dataclass(frozen=True)
class Seed:
    """A written seed file + its byte-level SHA256 (the SHA-binding pointer shape)."""

    path: str
    sha256: str


@dataclass(frozen=True)
class LaunchResult:
    """The outcome of an S3 lane launch (PURE value)."""

    launched: bool
    seed_path: str | None = None
    lane_id: str | None = None
    note: str | None = None


def _default_spawn(argv: Sequence[str]) -> subprocess.CompletedProcess:  # pragma: no cover - live subprocess shell
    return subprocess.run(list(argv), check=False, capture_output=True, text=True, timeout=120)


def _lane_id(item: Mapping[str, Any], run_id: str) -> str:
    repo = str(item.get("repo") or "").replace("/", "-")
    return f"pickup-{repo}-{item.get('number')}-{run_id}"


def build_seed(
    item: Mapping[str, Any], *, identity: str, run_id: str, claim_id: str | None,
    seed_root: Path | str,
) -> Seed:
    """Write a per-item seed file and return its path + byte-level SHA256 (the
    do_not_replan SHA-binding pointer shape; [[ce-seat-dispatch-prompt-pointer-sha]]).

    The seed is a self-contained brief (it must not reference a private ticket a
    contained seat cannot read; [[ce-no-egress-seat-self-contained-briefs]]) — it
    embeds the work-item the lane is to act on.
    """
    root = Path(seed_root)
    root.mkdir(parents=True, exist_ok=True)
    role = _KIND_TO_ROLE.get(str(item.get("kind")), _DEFAULT_ROLE)
    body = (
        f"# CE work-pickup seed — {item.get('repo')}#{item.get('number')}\n\n"
        f"You are picking up auto-detected forge work as **{identity}** ({role} lane).\n\n"
        f"- repo: {item.get('repo')}\n"
        f"- item: #{item.get('number')} ({item.get('subject_type')})\n"
        f"- kind: {item.get('kind')} (pickup reason: {item.get('reason')})\n"
        f"- url: {item.get('url')}\n"
        f"- title: {item.get('title')}\n"
        f"- claim_id: {claim_id}\n"
        f"- run_id: {run_id}\n\n"
        f"The work-claim lock is already held by this identity. Do the {role} work "
        f"for the item above; reach green, commit locally, then hand off push/merge "
        f"to the controller (a §7-governed seat cannot push).\n"
    )
    path = root / f"{_lane_id(item, run_id)}.seed.md"
    path.write_text(body, encoding="utf-8")
    return Seed(path=str(path), sha256=hashlib.sha256(body.encode("utf-8")).hexdigest())


def build_lane_argv(
    item: Mapping[str, Any], *, identity: str, run_id: str, harness: str,
    seed: Seed, repo_root: str, ledger_root: str,
) -> list[str]:
    """Build the ``ce lane launch`` argv binding the seed as the prompt pointer + SHA (PURE).

    The seed file IS the ``--prompt`` pointer and its SHA the ``--prompt-sha`` (the
    lane primitive's existing SHA-binding gate). The harness rides ``--command``
    (the lane runtime's harness seam); a review item launches a ``reviewer`` lane.
    """
    role = _KIND_TO_ROLE.get(str(item.get("kind")), _DEFAULT_ROLE)
    lane_kind = _KIND_TO_LANE_KIND.get(str(item.get("kind")), _DEFAULT_LANE_KIND)
    return [
        "ce", "lane", "launch",
        "--controller-id", identity,
        "--lane-id", _lane_id(item, run_id),
        "--role", role,
        "--lane-kind", lane_kind,
        "--prompt", seed.path,
        "--prompt-sha", seed.sha256,
        "--repo-root", repo_root,
        "--ledger-root", ledger_root,
        "--command", harness,
        "--json",
    ]


def launch_lane(
    item: Mapping[str, Any], *, identity: str, run_id: str, claim_id: str | None,
    harness: str, seed_root: Path | str, repo_root: str, ledger_root: str,
    spawn: Spawn | None = None,
) -> LaunchResult:
    """Write a seed and spawn a fresh governed ``ce lane launch`` for a claimed item.

    Returns ``launched=True`` ONLY when the spawn exits 0 AND its JSON reports the
    lane's :data:`LAUNCHED_STATE` sentinel. Search-backed pickup has no
    notification read marker; the claim ledger remains the idempotency gate.
    """
    runner = spawn or _default_spawn
    seed = build_seed(item, identity=identity, run_id=run_id, claim_id=claim_id, seed_root=seed_root)
    argv = build_lane_argv(
        item, identity=identity, run_id=run_id, harness=harness,
        seed=seed, repo_root=repo_root, ledger_root=ledger_root,
    )
    try:
        proc = runner(argv)
    except Exception as exc:
        return LaunchResult(launched=False, seed_path=seed.path, note=f"spawn error: {exc}")
    if getattr(proc, "returncode", 1) != 0:
        return LaunchResult(launched=False, seed_path=seed.path,
                            note=f"lane launch exited {getattr(proc, 'returncode', '?')}")
    state = None
    out = (getattr(proc, "stdout", "") or "").strip()
    if out:
        try:
            state = json.loads(out).get("seat_lifecycle_state")
        except (ValueError, TypeError, AttributeError):
            state = None
    launched = state == LAUNCHED_STATE
    return LaunchResult(
        launched=launched, seed_path=seed.path, lane_id=_lane_id(item, run_id),
        note=None if launched else f"lane did not confirm '{LAUNCHED_STATE}' (state={state!r})",
    )


def mark_thread_read(thread_id: str, *, gh_runner: GhRunner) -> bool:
    """Best-effort notification read marker for legacy thread ids.

    Search-backed pickup thread ids are synthetic (``search:…``) and cannot be
    marked read through GitHub. For those, this is an explicit no-op. Legacy
    notification ids are retained for backward compatibility and are marked only
    after a launch confirms :data:`LAUNCHED_STATE`.
    """
    if not thread_id or str(thread_id).startswith("search:"):
        return False
    try:
        proc = gh_runner(
            ["gh", "api", "--method", "PATCH", f"notifications/threads/{thread_id}"], None
        )
    except Exception:
        return False
    return getattr(proc, "returncode", 1) == 0
