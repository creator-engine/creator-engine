"""Request-time credential injection proxy for contained sub-agent forge traffic.

This module is the contained-agent counterpart to ``authenticated_gh_runner``:
the worker/container never receives a token in its env, argv, or durable launch
record. Instead, each outbound request is evaluated by the transport deputy
policy first; only an allowed request triggers a scoped-token mint, and the live
token is attached only to the proxy's outbound transport request.

Tests inject the token minter and transport adapter. Importing this module does
not perform network I/O, spawn subprocesses, or read ambient credentials.
"""
from __future__ import annotations

import json
import re
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any

from ._redact import redact_gh_stderr
from .credential_runner import authenticated_gh_runner
from .github_repo_config import ForgeConfigRefused
from .scoped_token import ScopedToken, TokenRequest
from .transport_deputy_policy import Decision, TransportRequest, evaluate

CredentialMinter = Callable[[TokenRequest], ScopedToken]
TransportAdapter = Callable[["OutboundTransportRequest"], Any]
PolicyEvaluator = Callable[[TransportRequest], Decision]

_SECRET_KEY_RE = re.compile(
    r"(?:authorization|cookie|credential|password|private[-_]?key|secret|token|api[-_]?key)",
    re.IGNORECASE,
)
_TOKEN_VALUE_RE = re.compile(
    r"(?:gh[pousr]_[A-Za-z0-9_]{20,}|github_pat_[A-Za-z0-9_]{20,}|"
    r"Bearer\s+[A-Za-z0-9._~+/=-]{20,}|[A-Za-z0-9_-]{40,})"
)
_AUDIT_TOKEN_VALUE_RE = re.compile(
    r"(?:gh[pousr]_[A-Za-z0-9_]{20,}|github_pat_[A-Za-z0-9_]{20,}|"
    r"Bearer\s+[A-Za-z0-9._~+/=-]{20,})"
)
_REPO_RE = re.compile(r"^[^/\s]+/[^/\s]+$")
_HEAD_SHA_RE = re.compile(r"^[0-9a-fA-F]{40,64}$")
_CONTAINED_REVIEW_EVENTS = frozenset({"COMMENT", "REQUEST_CHANGES"})


class CredentialProxyRefused(ForgeConfigRefused):
    """The proxy refused before minting or before outbound transport."""

    code = "V3-FORGE-CRED-PROXY-REFUSED"


@dataclass(frozen=True)
class CredentialBinding:
    """Non-secret minting context for the request-time proxy.

    ``repo`` is deliberately absent: the proxy binds the mint request to
    ``TransportRequest.repo`` so a caller cannot mint for a different repository
    than the policy-evaluated request.
    """

    installation_id: int
    run_id: str
    policy_sha: str
    permissions: Mapping[str, str]
    secret_name: str = "github_installation_access_token"
    requested_ttl_seconds: int = 600
    escalation_authority: tuple[tuple[str, str], ...] = ()


@dataclass(frozen=True)
class ContainedDispatch:
    """One contained sub-agent outbound request plus token-free launch facts."""

    request: TransportRequest
    binding: CredentialBinding
    worker_env: Mapping[str, str] = field(default_factory=dict)
    worker_argv: Sequence[str] = ()
    durable_metadata: Mapping[str, object] = field(default_factory=dict)


@dataclass(frozen=True)
class OutboundTransportRequest:
    """The request handed to the trusted transport adapter after injection."""

    host: str
    method: str
    path: str
    headers: Mapping[str, str] = field(repr=False)
    body: str | None = None
    repo: str | None = None
    pr: int | None = None
    head_sha: str | None = None
    credential: ScopedToken | None = field(default=None, repr=False, compare=False)

    def as_record(self) -> dict[str, object]:
        """Return a value-free projection; never include header values or body."""

        return {
            "host": self.host,
            "method": self.method,
            "path": self.path,
            "repo": self.repo,
            "pr": self.pr,
            "head_sha": self.head_sha,
            "header_names": sorted(str(k) for k in self.headers),
            "body_present": self.body is not None,
        }


@dataclass(frozen=True)
class ProxyDispatchResult:
    """Result of one proxy dispatch; ``audit_record`` is durable and secret-free."""

    allowed: bool
    decision: Decision
    audit_record: Mapping[str, object]
    response: Any = None


@dataclass(frozen=True)
class ContainedSeatReview:
    """A contained seat's value-only PR review intent.

    This is intentionally narrower than GitHub's review API. Contained seats may
    submit only opinionated non-approval reviews through this seam; gate-valid
    approvals remain controller-only approval-wall work.
    """

    seat_id: str
    repo: str
    pr_number: int
    head_sha: str
    event: str
    body: str = ""
    role_profile: str = "reviewer"
    host: str = "api.github.com"


@dataclass(frozen=True)
class ContainedSeatReviewResult:
    """Submitted contained-seat review result plus secret-free proxy audit."""

    repo: str
    pr_number: int
    head_sha: str
    event: str
    changed: bool
    applied: bool
    review_id: int | None
    audit_record: Mapping[str, object]

    def to_dict(self) -> dict[str, object]:
        return {
            "repo": self.repo,
            "pr_number": self.pr_number,
            "head_sha": self.head_sha,
            "event": self.event,
            "changed": self.changed,
            "applied": self.applied,
            "review_id": self.review_id,
            "audit_record": dict(self.audit_record),
        }


def dispatch_with_credential_injection(
    dispatch: ContainedDispatch,
    *,
    minter: CredentialMinter,
    transport: TransportAdapter,
    evaluator: PolicyEvaluator = evaluate,
) -> ProxyDispatchResult:
    """Evaluate, mint, inject, and dispatch one contained-agent transport request.

    Ordering is load-bearing:
    1. evaluate policy against the token-free request facts;
    2. refuse without mint/transport on policy denial or secret-bearing launch
       context;
    3. mint a scoped token bound to the evaluated repo;
    4. inject the bearer only into the trusted outbound transport request.
    """

    decision = evaluator(dispatch.request)
    audit = _base_audit(dispatch, decision)
    if not decision.allowed:
        return ProxyDispatchResult(
            allowed=False,
            decision=decision,
            audit_record=_finalize_audit(audit, "policy_denied"),
        )

    context_leaks = _secret_context_findings(dispatch)
    if context_leaks:
        audit["proxy_refusal"] = {
            "reason": "contained launch context carries credential material",
            "findings": context_leaks,
        }
        return ProxyDispatchResult(
            allowed=False,
            decision=decision,
            audit_record=_finalize_audit(audit, "launch_context_secret_denied"),
        )

    if not dispatch.request.repo:
        audit["proxy_refusal"] = {
            "reason": "allowed request is not bound to a repository; refusing mint",
        }
        return ProxyDispatchResult(
            allowed=False,
            decision=decision,
            audit_record=_finalize_audit(audit, "repo_context_missing"),
        )

    token_request = _token_request(dispatch)
    token = minter(token_request)
    if not token.value:
        audit["token"] = _token_record(token)
        audit["proxy_refusal"] = {"reason": "minted token carried no credential value"}
        return ProxyDispatchResult(
            allowed=False,
            decision=decision,
            audit_record=_finalize_audit(audit, "empty_token_denied"),
        )

    outbound = _outbound_request(dispatch.request, token)
    response = transport(outbound)
    audit["token"] = _token_record(token)
    audit["outbound"] = outbound.as_record()
    return ProxyDispatchResult(
        allowed=True,
        decision=decision,
        response=response,
        audit_record=_finalize_audit(audit, "transport_dispatched"),
    )


def submit_contained_seat_pr_review(
    review: ContainedSeatReview,
    *,
    binding: CredentialBinding,
    minter: CredentialMinter,
    worker_env: Mapping[str, str] | None = None,
    worker_argv: Sequence[str] = (),
    durable_metadata: Mapping[str, object] | None = None,
    transport: TransportAdapter | None = None,
    token_spawn: Any = None,
    evaluator: PolicyEvaluator = evaluate,
) -> ContainedSeatReviewResult:
    """Submit a contained seat COMMENT/REQUEST_CHANGES review through the proxy.

    The contained seat supplies only value facts. The trusted caller owns
    ``minter`` and either supplies ``transport`` or lets this function build the
    default trusted ``gh api`` transport outside the sandbox. ``APPROVE`` is
    deliberately refused before policy evaluation or token minting.
    """

    event = _validate_contained_review(review)
    payload: dict[str, object] = {"event": event, "commit_id": review.head_sha}
    if review.body:
        payload["body"] = review.body

    request = TransportRequest(
        seat_id=review.seat_id,
        role_profile=review.role_profile,
        host=review.host,
        method="POST",
        path=f"/repos/{review.repo}/pulls/{review.pr_number}/reviews",
        repo=review.repo,
        pr=review.pr_number,
        head_sha=review.head_sha,
        headers={"Accept": "application/vnd.github+json"},
        body=json.dumps(payload, sort_keys=True),
    )
    metadata = dict(durable_metadata or {})
    metadata.setdefault("contained_review_event", event)
    result = dispatch_with_credential_injection(
        ContainedDispatch(
            request=request,
            binding=binding,
            worker_env=dict(worker_env or {}),
            worker_argv=tuple(worker_argv),
            durable_metadata=metadata,
        ),
        minter=minter,
        transport=transport or gh_api_transport_adapter(spawn=token_spawn),
        evaluator=evaluator,
    )
    if not result.allowed:
        raise CredentialProxyRefused(
            f"contained seat review refused before forge side effect: {result.audit_record.get('outcome')}"
        )
    response = result.response if isinstance(result.response, Mapping) else {}
    review_id = response.get("id")
    return ContainedSeatReviewResult(
        repo=review.repo,
        pr_number=review.pr_number,
        head_sha=review.head_sha,
        event=event,
        changed=True,
        applied=True,
        review_id=(int(review_id) if review_id is not None else None),
        audit_record=result.audit_record,
    )


def gh_api_transport_adapter(*, spawn: Any = None) -> TransportAdapter:
    """Return the trusted outside-sandbox ``gh api`` transport adapter.

    The adapter requires the proxy-injected :class:`ScopedToken` object and
    turns it into an authenticated ``GhRunner`` via ``authenticated_gh_runner``.
    The token goes only into the child ``gh`` env outside the seat sandbox; it is
    never copied into argv, stdin, worker env, worker argv, or durable audit.
    """

    def transport(request: OutboundTransportRequest) -> object:
        token = request.credential
        if token is None or not token.value:
            raise CredentialProxyRefused("trusted gh transport missing injected credential")
        runner = authenticated_gh_runner(token, spawn=spawn)
        path = request.path.lstrip("/")
        argv = ["gh", "api", "-X", request.method.upper(), path]
        input_text = request.body
        if input_text is not None:
            argv += ["--input", "-"]
        proc = runner(argv, input_text)
        parsed: object = None
        out = (proc.stdout or "").strip()
        if out:
            try:
                parsed = json.loads(out)
            except (json.JSONDecodeError, ValueError):
                parsed = None
        if proc.returncode != 0 or not isinstance(parsed, Mapping):
            raise CredentialProxyRefused(
                "trusted gh transport failed for contained review: "
                f"{redact_gh_stderr(proc.stderr or '') or 'unknown error'}"
            )
        return parsed

    return transport


def _token_request(dispatch: ContainedDispatch) -> TokenRequest:
    request = dispatch.request
    binding = dispatch.binding
    return TokenRequest(
        repo=request.repo or "",
        installation_id=binding.installation_id,
        run_id=binding.run_id,
        policy_sha=binding.policy_sha,
        permissions=dict(binding.permissions),
        secret_name=binding.secret_name,
        requested_ttl_seconds=binding.requested_ttl_seconds,
        escalation_authority=binding.escalation_authority,
    )


def _outbound_request(request: TransportRequest, token: ScopedToken) -> OutboundTransportRequest:
    headers = dict(request.headers)
    headers["Authorization"] = f"Bearer {token.value}"
    return OutboundTransportRequest(
        host=request.host,
        method=request.method,
        path=request.path,
        headers=headers,
        body=request.body,
        repo=request.repo,
        pr=request.pr,
        head_sha=request.head_sha,
        credential=token,
    )


def _validate_contained_review(review: ContainedSeatReview) -> str:
    event = (review.event or "").strip().upper().replace("-", "_")
    if event not in _CONTAINED_REVIEW_EVENTS:
        raise CredentialProxyRefused(
            "contained seat review event must be COMMENT or REQUEST_CHANGES; "
            "APPROVE is controller approval-wall only"
        )
    if not review.seat_id.strip():
        raise CredentialProxyRefused("contained seat review requires a seat_id")
    if not _REPO_RE.match(review.repo or ""):
        raise CredentialProxyRefused(f"repo {review.repo!r} is not in owner/name form")
    if (
        not isinstance(review.pr_number, int)
        or isinstance(review.pr_number, bool)
        or review.pr_number <= 0
    ):
        raise CredentialProxyRefused(f"pr_number {review.pr_number!r} must be a positive integer")
    if not _HEAD_SHA_RE.match(review.head_sha or ""):
        raise CredentialProxyRefused("contained seat review requires a 40-64 hex head_sha")
    return event


def _base_audit(dispatch: ContainedDispatch, decision: Decision) -> dict[str, object]:
    return {
        "decision": decision.as_record(),
        "contained_launch": {
            "env_names": sorted(str(k) for k in dispatch.worker_env),
            "argv_count": len(tuple(dispatch.worker_argv)),
            "durable_metadata_keys": sorted(str(k) for k in dispatch.durable_metadata),
        },
    }


def _token_record(token: ScopedToken) -> dict[str, object]:
    return {
        "run_id": token.run_id,
        "repo": token.repo,
        "policy_sha": token.policy_sha,
        "secret_name": token.secret_name,
        "permissions": [{"scope": scope, "level": level} for scope, level in token.permissions],
        "expires_at": token.expires_at,
        "token_ref": _value_free(token.token_ref),
    }


def _finalize_audit(record: dict[str, object], outcome: str) -> dict[str, object]:
    record["outcome"] = outcome
    rendered = repr(record)
    if _AUDIT_TOKEN_VALUE_RE.search(rendered):
        raise CredentialProxyRefused(
            "credential proxy audit record contains token-shaped material; refusing durable record"
        )
    return record


def _secret_context_findings(dispatch: ContainedDispatch) -> tuple[str, ...]:
    findings: list[str] = []
    for key, value in dispatch.worker_env.items():
        if _SECRET_KEY_RE.search(str(key)) or _TOKEN_VALUE_RE.search(str(value)):
            findings.append(f"worker_env:{key}")
    for idx, value in enumerate(dispatch.worker_argv):
        if _TOKEN_VALUE_RE.search(str(value)):
            findings.append(f"worker_argv:{idx}")
    for key, value in dispatch.durable_metadata.items():
        if _SECRET_KEY_RE.search(str(key)) or _TOKEN_VALUE_RE.search(str(value)):
            findings.append(f"durable_metadata:{key}")
    return tuple(sorted(findings))


def _value_free(value: str) -> str:
    return "<redacted-token-shaped-ref>" if _AUDIT_TOKEN_VALUE_RE.search(value or "") else value


__all__ = [
    "ContainedDispatch",
    "ContainedSeatReview",
    "ContainedSeatReviewResult",
    "CredentialBinding",
    "CredentialMinter",
    "CredentialProxyRefused",
    "OutboundTransportRequest",
    "PolicyEvaluator",
    "ProxyDispatchResult",
    "TransportAdapter",
    "dispatch_with_credential_injection",
    "gh_api_transport_adapter",
    "submit_contained_seat_pr_review",
]
