"""Shared GitHub Search-API pickup core (ce-ops#55/#182/#188).

The deterministic, **read-only** GitHub Search primitives shared by BOTH the v1
per-seat work-poller (``pickup.py``) and the v3 controller review-pickup
(``forge/review_pickup.py``): the Search query/transport seam, per-identity token
resolution, the ``gh`` runner factory, rate-limit handling, and search-hit
normalization.

This module is deliberately classified **shared** (it is in neither
``V1_RUNTIME`` nor ``V3_RUNTIME`` in ``_versions.py``), so it may be imported by
both runtimes without crossing the v1⊥v3 boundary. It imports no v1 or v3 module
— only the stdlib. Importing it performs no I/O and registers no validator check.

The live network touch lives behind an injectable ``transport`` seam (a stdlib
``urllib`` HTTPS call by default); tests inject fakes and perform ZERO live
network / subprocess. Defensive only.
"""
from __future__ import annotations

import json
import os
import subprocess
import re
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

#: HTTPS transport: ``(method, url, headers, body) -> (status, headers, body_text)``.
Transport = Callable[[str, str, "dict[str, str]", "str | None"], "tuple[int, dict[str, str], str]"]

#: A GhRunner runs a ``gh`` invocation (argv incl. the leading "gh") with an
#: optional stdin body — the same shape as ``work_claims.GhRunner``.
GhRunner = Callable[[Sequence[str], "str | None"], "subprocess.CompletedProcess"]

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

#: Ambient auth env vars dropped from the child ``gh`` env so the per-identity
#: ``GH_TOKEN`` is unambiguous (``GH_TOKEN`` already wins by precedence; dropping
#: these is defense-in-depth — the same hygiene the v3 credential_runner applies).
_AMBIENT_AUTH_ENV = ("GITHUB_TOKEN", "GH_CONFIG_DIR", "GH_HOST")


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
class SearchScope:
    """Explicit Search API blast-radius declaration for a query builder."""

    kind: str
    value: str | None = None
    query_terms: tuple[str, ...] = ()

    @classmethod
    def repo(cls, repo: str) -> "SearchScope":
        if not _REPO_SCOPE_RE.match(repo):
            raise PickupError(f"--repo must be owner/name, got {repo!r}")
        return cls("repo", repo, (f"repo:{repo}",))

    @classmethod
    def org(cls, org: str) -> "SearchScope":
        if not _ORG_SCOPE_RE.match(org):
            raise PickupError(f"--org must be a GitHub organization/user slug, got {org!r}")
        return cls("org", org, (f"org:{org}",))

    @classmethod
    def viewer(cls) -> "SearchScope":
        """Declare a query bounded by GitHub's authenticated-user ``@me`` selector."""
        return cls("viewer", "@me", ())

    def validate_query(self, query: str) -> None:
        if self.kind == "repo":
            if not self.value or not _REPO_SCOPE_RE.match(self.value):
                raise PickupError("repo search scope requires a valid owner/name value")
            expected = f"repo:{self.value}"
            if expected not in self.query_terms:
                raise PickupError(f"repo search scope requires matching query term {expected!r}")
            terms = set(query.split())
            if expected not in terms:
                raise PickupError(
                    "search query declared a scope but did not include its scope term(s): "
                    + expected
                )
            return
        if self.kind == "org":
            if not self.value or not _ORG_SCOPE_RE.match(self.value):
                raise PickupError("org search scope requires a valid organization/user slug value")
            expected = f"org:{self.value}"
            if expected not in self.query_terms:
                raise PickupError(f"org search scope requires matching query term {expected!r}")
            terms = set(query.split())
            if expected not in terms:
                raise PickupError(
                    "search query declared a scope but did not include its scope term(s): "
                    + expected
                )
            return
        if self.kind == "viewer":
            if self.value != "@me" or self.query_terms:
                raise PickupError("viewer search scope must use value '@me' and no query terms")
            if "@me" not in query:
                raise PickupError("viewer-scoped search query must include an @me qualifier")
            return
        raise PickupError(f"unknown search scope kind {self.kind!r}")


def declared_search_scope(
    *,
    repo: str | None = None,
    org: str | None = None,
    default: SearchScope | None = None,
    error_factory: Callable[[str], Exception] = PickupError,
) -> SearchScope:
    """Resolve an explicit Search API scope or fail closed.

    ``default`` is intentionally an explicit :class:`SearchScope`, not a string
    fallback. Callers that permit current-user ``@me`` queries must say so with
    ``SearchScope.viewer()``; callers that need repo/org blast-radius bounds
    leave it unset and receive a fail-closed error when no scope is supplied.
    """
    if repo and org:
        raise error_factory("repo and org are mutually exclusive search scopes")
    if repo:
        try:
            return SearchScope.repo(repo)
        except PickupError as exc:
            raise error_factory(str(exc)) from exc
    if org:
        try:
            return SearchScope.org(org)
        except PickupError as exc:
            raise error_factory(str(exc)) from exc
    if default is not None:
        if not isinstance(default, SearchScope):
            raise error_factory("default search scope must be a SearchScope declaration")
        return default
    raise error_factory("search query requires an explicit repo or org scope declaration")


def build_scoped_search_query(
    reason: str,
    terms: Sequence[str],
    *,
    scope: SearchScope,
) -> "SearchQuery":
    """Build a Search API query through the scope-declaration chokepoint."""
    if not isinstance(scope, SearchScope):
        raise PickupError("search query requires an explicit SearchScope declaration")
    return SearchQuery(reason, " ".join([*terms, *scope.query_terms]), scope=scope)


@dataclass(frozen=True)
class SearchQuery:
    """One GitHub Search query and the pickup reason assigned to its hits."""

    reason: str
    query: str
    scope: SearchScope

    def __post_init__(self) -> None:
        if not self.reason or not self.reason.strip():
            raise PickupError("search query requires a non-empty reason")
        if not self.query or not self.query.strip():
            raise PickupError("search query requires a non-empty query")
        if not isinstance(self.scope, SearchScope):
            raise PickupError("search query requires an explicit SearchScope declaration")
        self.scope.validate_query(self.query)


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


def make_gh_runner(token: str) -> GhRunner:
    """Return a :data:`GhRunner` that runs ``gh`` with ``token`` in the child env ONLY.

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


def _header(headers: Mapping[str, str], name: str) -> str | None:
    """Case-insensitive header lookup (HTTP header names are case-insensitive)."""
    for key, value in headers.items():
        if key.lower() == name.lower():
            return value
    return None


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
