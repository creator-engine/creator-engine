"""Offline transport-deputy policy for rules-before-credential-injection.

This module models the deterministic decision seam only. It performs no network I/O,
does not mint or inject credentials, and never starts a OneCLI process. A caller supplies
already-observed request facts; :func:`evaluate` returns a fail-closed, secret-free verdict
that can be audited before any credential material is decrypted or attached.
"""
from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass, field

READ_METHODS = frozenset({"GET", "HEAD", "OPTIONS"})
WRITE_METHODS = frozenset({"POST", "PUT", "PATCH", "DELETE"})
DEFAULT_GITHUB_HOSTS = ("api.github.com", "github.com")

_REVIEW_POST_RE = re.compile(
    r"^/repos/(?P<owner>[^/]+)/(?P<repo>[^/]+)/pulls/(?P<pr>[0-9]+)/reviews/?$"
)
_REPO_PATH_RE = re.compile(r"^/repos/(?P<owner>[^/]+)/(?P<repo>[^/?#]+)(?:[/?#]|$)")
_GRAPHQL_RE = re.compile(r"^/(?:api/)?graphql/?$")
_GRAPHQL_MUTATION_RE = re.compile(r"\bmutation\b", re.IGNORECASE)
_GIT_SMART_WRITE_RE = re.compile(r"(?:git-receive-pack|service=git-receive-pack)")
_SECRET_KEY_RE = re.compile(
    r"(?:authorization|cookie|credential|password|secret|token|api[-_]?key)",
    re.IGNORECASE,
)
_TOKEN_VALUE_RE = re.compile(
    r"(?:gh[pousr]_[A-Za-z0-9_]{20,}|github_pat_[A-Za-z0-9_]{20,}|"
    r"Bearer\s+[A-Za-z0-9._~+/=-]{20,}|[A-Za-z0-9_-]{40,})"
)


@dataclass(frozen=True)
class TransportRequest:
    """Value facts for one outbound transport request before credential injection."""

    seat_id: str
    role_profile: str
    host: str
    path: str
    method: str
    repo: str | None = None
    pr: int | None = None
    head_sha: str | None = None
    headers: Mapping[str, str] = field(default_factory=dict)
    env: Mapping[str, str] = field(default_factory=dict)
    body: str | None = None
    contains_secret_material: bool = False


@dataclass(frozen=True)
class PolicyRule:
    """One explicit write allowance inside a profile."""

    name: str
    methods: frozenset[str]
    path_regex: re.Pattern[str]
    require_repo: bool = True
    require_pr: bool = False


@dataclass(frozen=True)
class PolicyProfile:
    """Rules for a role profile. Reads are explicit profile policy, not ambient allow."""

    name: str
    hosts: tuple[str, ...] = DEFAULT_GITHUB_HOSTS
    allow_reads: bool = True
    write_rules: tuple[PolicyRule, ...] = ()


@dataclass(frozen=True)
class CheckResult:
    """One gate outcome. Detail must be value-free and safe for durable audit."""

    name: str
    passed: bool
    detail: str

    def as_record(self) -> dict:
        return {"name": self.name, "passed": self.passed, "detail": self.detail}


@dataclass(frozen=True)
class Decision:
    """Fail-closed verdict for a request before any credential injection."""

    allowed: bool
    verdict: str
    checks: tuple[CheckResult, ...]
    request: TransportRequest
    matched_rule: str | None = None

    @property
    def reasons(self) -> tuple[str, ...]:
        return tuple(check.detail for check in self.checks if not check.passed)

    def as_record(self) -> dict:
        """Return a durable audit projection with no header/env/body values."""

        return {
            "verdict": self.verdict,
            "allowed": self.allowed,
            "matched_rule": self.matched_rule,
            "reasons": list(self.reasons),
            "request": {
                "seat_id": self.request.seat_id,
                "role_profile": self.request.role_profile,
                "host": self.request.host,
                "method": _norm_method(self.request.method),
                "path": _norm_path(self.request.path),
                "repo": self.request.repo,
                "pr": self.request.pr,
                "head_sha": self.request.head_sha,
                "header_names": sorted(str(k) for k in self.request.headers),
                "env_names": sorted(str(k) for k in self.request.env),
                "body_present": self.request.body is not None,
            },
            "checks": [check.as_record() for check in self.checks],
        }


REVIEWER_REVIEW_SUBMIT = PolicyRule(
    name="github.pull_request.review.submit",
    methods=frozenset({"POST"}),
    path_regex=_REVIEW_POST_RE,
    require_pr=True,
)

DEFAULT_PROFILES: Mapping[str, PolicyProfile] = {
    "reader": PolicyProfile(name="reader"),
    "builder": PolicyProfile(name="builder"),
    "controller": PolicyProfile(name="controller"),
    "reviewer": PolicyProfile(
        name="reviewer",
        write_rules=(REVIEWER_REVIEW_SUBMIT,),
    ),
}


def evaluate(
    request: TransportRequest,
    *,
    profiles: Mapping[str, PolicyProfile] = DEFAULT_PROFILES,
) -> Decision:
    """Evaluate ``request`` against deterministic transport-deputy policy.

    A single failed check denies the request. Write allowances are opt-in and profile
    scoped; unmatched writes fail closed.
    """

    checks: list[CheckResult] = []
    matched_rule: str | None = None
    method = _norm_method(request.method)
    path = _norm_path(request.path)
    host = (request.host or "").strip().lower()
    role = (request.role_profile or "").strip().lower()

    checks.append(_present("seat_present", request.seat_id, "request has no seat_id"))
    profile = profiles.get(role)
    checks.append(
        CheckResult(
            "known_role_profile",
            profile is not None,
            f"unknown role_profile {request.role_profile!r}",
        )
    )
    if profile is not None:
        checks.append(
            CheckResult(
                "host_allowed",
                host in {h.lower() for h in profile.hosts},
                f"host {request.host!r} is not allowed for {profile.name}",
            )
        )

    secret_fields = _secret_field_names(request.headers, request.env)
    checks.append(
        CheckResult(
            "no_secret_material",
            not request.contains_secret_material and not secret_fields,
            "secret material present in request metadata: "
            + ", ".join(secret_fields)
            if secret_fields or request.contains_secret_material
            else "request metadata contains no credential material",
        )
    )

    if _is_graphql_mutation(method, path, request.body):
        checks.append(
            CheckResult(
                "not_opaque_graphql_mutation",
                False,
                "opaque GraphQL mutation denied before credential injection",
            )
        )
    else:
        checks.append(
            CheckResult(
                "not_opaque_graphql_mutation",
                True,
                "request is not an opaque GraphQL mutation",
            )
        )

    if _is_git_smart_write(method, path):
        checks.append(
            CheckResult(
                "not_unknown_git_smart_http_write",
                False,
                "unknown git smart-HTTP write denied before credential injection",
            )
        )
    else:
        checks.append(
            CheckResult(
                "not_unknown_git_smart_http_write",
                True,
                "request is not a git smart-HTTP write",
            )
        )

    if method in READ_METHODS:
        checks.append(
            CheckResult(
                "read_allowed",
                bool(profile and profile.allow_reads),
                "read method allowed by profile" if profile else "read denied without profile",
            )
        )
    elif method in WRITE_METHODS:
        checks.append(_write_has_repo_context(request, path))
        destructive = _destructive_write(method, path)
        checks.append(
            CheckResult(
                "not_destructive_repo_write",
                not destructive,
                destructive or "request is not on the destructive write deny-list",
            )
        )
        if profile is not None and not destructive and not _is_graphql_mutation(method, path, request.body):
            matched_rule = _matching_rule(profile, request, method, path)
        checks.append(
            CheckResult(
                "write_rule_matched",
                matched_rule is not None,
                f"matched write rule {matched_rule}"
                if matched_rule
                else "unmatched write path denied before credential injection",
            )
        )
    else:
        checks.append(
            CheckResult(
                "known_method",
                False,
                f"unknown HTTP method {request.method!r} denied before credential injection",
            )
        )

    allowed = all(check.passed for check in checks)
    return Decision(
        allowed=allowed,
        verdict="allow" if allowed else "deny",
        checks=tuple(checks),
        request=request,
        matched_rule=matched_rule if allowed else None,
    )


def _present(name: str, value: object, detail: str) -> CheckResult:
    return CheckResult(name, bool(str(value or "").strip()), detail)


def _norm_method(method: str) -> str:
    return (method or "").strip().upper()


def _norm_path(path: str) -> str:
    raw = (path or "").strip()
    if not raw:
        return "/"
    return raw if raw.startswith("/") else f"/{raw}"


def _secret_field_names(headers: Mapping[str, str], env: Mapping[str, str]) -> tuple[str, ...]:
    names: list[str] = []
    for prefix, values in (("header", headers), ("env", env)):
        for key, value in values.items():
            key_s = str(key)
            value_s = str(value)
            if _SECRET_KEY_RE.search(key_s) or _TOKEN_VALUE_RE.search(value_s):
                names.append(f"{prefix}:{key_s}")
    return tuple(sorted(names))


def _is_graphql_mutation(method: str, path: str, body: str | None) -> bool:
    return method in WRITE_METHODS and bool(_GRAPHQL_RE.match(path)) and (
        body is None or bool(_GRAPHQL_MUTATION_RE.search(body))
    )


def _is_git_smart_write(method: str, path: str) -> bool:
    return method in WRITE_METHODS and bool(_GIT_SMART_WRITE_RE.search(path))


def _write_has_repo_context(request: TransportRequest, path: str) -> CheckResult:
    if not request.repo:
        return CheckResult("write_has_repo_context", False, "write request is missing repo context")
    path_repo = _repo_from_path(path)
    if path_repo and path_repo != request.repo:
        return CheckResult(
            "write_has_repo_context",
            False,
            f"path repo {path_repo!r} does not match request repo {request.repo!r}",
        )
    return CheckResult("write_has_repo_context", True, "write request is bound to repo context")


def _repo_from_path(path: str) -> str | None:
    match = _REPO_PATH_RE.match(path)
    if not match:
        return None
    return f"{match.group('owner')}/{match.group('repo')}"


def _destructive_write(method: str, path: str) -> str:
    if method == "PATCH" and _repo_from_path(path) and path.count("/") == 3:
        return "destructive repo settings PATCH denied before credential injection"
    if method == "DELETE" and re.search(r"/repos/[^/]+/[^/]+/(?:hooks|actions/secrets|actions/workflows|git/refs)", path):
        return "destructive repo DELETE denied before credential injection"
    if method in {"PATCH", "PUT", "DELETE"} and re.search(
        r"/repos/[^/]+/[^/]+/(?:hooks|actions/secrets|actions/workflows|branches/.+/protection|git/refs)",
        path,
    ):
        return "destructive repo administration write denied before credential injection"
    return ""


def _matching_rule(
    profile: PolicyProfile,
    request: TransportRequest,
    method: str,
    path: str,
) -> str | None:
    for rule in profile.write_rules:
        if method not in rule.methods:
            continue
        match = rule.path_regex.match(path)
        if not match:
            continue
        if rule.require_repo and _repo_from_path(path) != request.repo:
            continue
        if rule.require_pr:
            pr = match.groupdict().get("pr")
            if request.pr is None or str(request.pr) != pr:
                continue
        return rule.name
    return None
