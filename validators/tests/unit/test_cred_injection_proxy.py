"""Unit tests for the contained-agent credential-injection proxy.

The proxy evaluates transport policy before minting, injects the minted token
only into the trusted outbound transport request, and keeps worker launch facts
plus durable audit projections token-free.
"""

from creator_engine_validator.forge.cred_injection_proxy import (
    ContainedDispatch,
    CredentialBinding,
    OutboundTransportRequest,
    dispatch_with_credential_injection,
)
from creator_engine_validator.forge.scoped_token import ScopedToken, TokenRequest
from creator_engine_validator.forge.transport_deputy_policy import TransportRequest, evaluate

_REPO = "creator-engine/creator-engine"
_HEAD = "a" * 40
_SECRET = "ghs_abcdefghijklmnopqrstuvwxyz1234567890"


def _request(**overrides) -> TransportRequest:
    base = dict(
        seat_id="seat-reviewer-1",
        role_profile="reviewer",
        host="api.github.com",
        method="POST",
        path=f"/repos/{_REPO}/pulls/7/reviews",
        repo=_REPO,
        pr=7,
        head_sha=_HEAD,
        headers={"Accept": "application/vnd.github+json"},
        body='{"event":"COMMENT","body":"review"}',
    )
    base.update(overrides)
    return TransportRequest(**base)


def _binding(**overrides) -> CredentialBinding:
    base = dict(
        installation_id=123,
        run_id="run-1",
        policy_sha="0" * 64,
        permissions={"metadata": "read", "pull_requests": "write"},
        requested_ttl_seconds=300,
    )
    base.update(overrides)
    return CredentialBinding(**base)


def _token(value: str = _SECRET, *, token_ref: str = "creator-engine/creator-engine@2026") -> ScopedToken:
    return ScopedToken(
        run_id="run-1",
        repo=_REPO,
        policy_sha="0" * 64,
        secret_name="github_installation_access_token",
        permissions=(("metadata", "read"), ("pull_requests", "write")),
        expires_at="2026-06-25T12:00:00Z",
        token_ref=token_ref,
        value=value,
    )


class FakeMinter:
    def __init__(self, token: ScopedToken, events: list[str] | None = None):
        self.token = token
        self.events = events if events is not None else []
        self.calls: list[TokenRequest] = []

    def __call__(self, request: TokenRequest) -> ScopedToken:
        self.events.append("mint")
        self.calls.append(request)
        return self.token


class FakeTransport:
    def __init__(self, events: list[str] | None = None):
        self.events = events if events is not None else []
        self.calls: list[OutboundTransportRequest] = []

    def __call__(self, request: OutboundTransportRequest) -> dict:
        self.events.append("transport")
        self.calls.append(request)
        return {"status_code": 200}


def test_allowed_request_mints_then_injects_only_into_outbound_transport():
    events: list[str] = []

    def evaluator(request: TransportRequest):
        events.append("policy")
        return evaluate(request)

    minter = FakeMinter(_token(), events)
    transport = FakeTransport(events)
    worker_env = {"PATH": "/usr/bin", "CE_SEAT": "seat-reviewer-1"}
    worker_argv = ("codex", "exec", "--json")
    result = dispatch_with_credential_injection(
        ContainedDispatch(
            request=_request(),
            binding=_binding(),
            worker_env=worker_env,
            worker_argv=worker_argv,
            durable_metadata={"dispatch_id": "dispatch-1"},
        ),
        minter=minter,
        transport=transport,
        evaluator=evaluator,
    )

    assert events == ["policy", "mint", "transport"]
    assert result.allowed is True
    assert minter.calls[0].repo == _REPO
    assert minter.calls[0].permissions == {"metadata": "read", "pull_requests": "write"}
    assert transport.calls[0].headers["Authorization"] == f"Bearer {_SECRET}"
    assert "Authorization" not in _request().headers
    assert worker_env == {"PATH": "/usr/bin", "CE_SEAT": "seat-reviewer-1"}
    assert worker_argv == ("codex", "exec", "--json")

    rendered = repr(result.audit_record)
    assert _SECRET not in rendered
    assert f"Bearer {_SECRET}" not in rendered
    assert "Authorization" in rendered  # header name only is attestable
    assert "pull_requests" in rendered
    assert result.audit_record["outcome"] == "transport_dispatched"


def test_policy_denial_refuses_before_mint_or_transport():
    minter = FakeMinter(_token())
    transport = FakeTransport()
    result = dispatch_with_credential_injection(
        ContainedDispatch(
            request=_request(method="POST", path=f"/repos/{_REPO}/dispatches"),
            binding=_binding(),
        ),
        minter=minter,
        transport=transport,
    )

    assert result.allowed is False
    assert result.decision.allowed is False
    assert minter.calls == []
    assert transport.calls == []
    assert result.audit_record["outcome"] == "policy_denied"


def test_policy_request_metadata_secret_denies_before_mint():
    minter = FakeMinter(_token())
    transport = FakeTransport()
    result = dispatch_with_credential_injection(
        ContainedDispatch(
            request=_request(headers={"Authorization": f"Bearer {_SECRET}"}),
            binding=_binding(),
        ),
        minter=minter,
        transport=transport,
    )

    assert result.allowed is False
    assert minter.calls == []
    assert transport.calls == []
    rendered = repr(result.audit_record)
    assert _SECRET not in rendered
    assert "Authorization" in rendered


def test_secret_bearing_launch_context_refuses_after_policy_before_mint():
    minter = FakeMinter(_token())
    transport = FakeTransport()
    result = dispatch_with_credential_injection(
        ContainedDispatch(
            request=_request(),
            binding=_binding(),
            worker_env={"GH_TOKEN": _SECRET},
            worker_argv=("codex", "exec"),
            durable_metadata={"dispatch_id": "dispatch-1"},
        ),
        minter=minter,
        transport=transport,
    )

    assert result.decision.allowed is True
    assert result.allowed is False
    assert minter.calls == []
    assert transport.calls == []
    assert result.audit_record["outcome"] == "launch_context_secret_denied"
    assert "worker_env:GH_TOKEN" in repr(result.audit_record)
    assert _SECRET not in repr(result.audit_record)


def test_token_shaped_ref_is_redacted_from_audit_but_value_still_in_transport():
    minter = FakeMinter(_token(token_ref=f"ref-{_SECRET}"))
    transport = FakeTransport()
    result = dispatch_with_credential_injection(
        ContainedDispatch(request=_request(), binding=_binding()),
        minter=minter,
        transport=transport,
    )

    assert result.allowed is True
    assert transport.calls[0].headers["Authorization"] == f"Bearer {_SECRET}"
    rendered = repr(result.audit_record)
    assert _SECRET not in rendered
    assert "<redacted-token-shaped-ref>" in rendered
