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

import re
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any

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
    headers: Mapping[str, str]
    body: str | None = None
    repo: str | None = None
    pr: int | None = None
    head_sha: str | None = None

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
    )


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
    "CredentialBinding",
    "CredentialMinter",
    "CredentialProxyRefused",
    "OutboundTransportRequest",
    "PolicyEvaluator",
    "ProxyDispatchResult",
    "TransportAdapter",
    "dispatch_with_credential_injection",
]
