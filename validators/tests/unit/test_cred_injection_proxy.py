"""Unit tests for the contained-agent credential-injection proxy.

The proxy evaluates transport policy before minting, injects the minted token
only into the trusted outbound transport request, and keeps worker launch facts
plus durable audit projections token-free.
"""

import json
import subprocess

import pytest

from creator_engine_validator.forge.cred_injection_proxy import (
    ContainedDispatch,
    ContainedSeatReview,
    CredentialBinding,
    CredentialProxyRefused,
    OutboundTransportRequest,
    dispatch_with_credential_injection,
    gh_api_transport_adapter,
    submit_contained_seat_pr_review,
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


def _reviewer_authority_envelope(**overrides):
    envelope = {
        "envelope_id": "rva-test-reviewer-approve",
        "mechanic": "pr_review",
        "pr_number": 7,
        "head_sha": _HEAD,
        "actor": "reviewer-1",
        "ratified_prompt_sha": "b" * 64,
        "emitting_role": "reviewer",
        "operating_mode": "transcendence",
        "recorded_at": "2026-06-28T00:00:00Z",
    }
    envelope.update(overrides)
    return {"reviewer_authority_envelope": envelope}


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
    assert _SECRET not in repr(transport.calls[0])
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


def test_contained_seat_review_smoke_uses_trusted_gh_runner_outside_seat_env(tmp_path):
    spawned: list[tuple[list[str], str | None, dict[str, str]]] = []
    seat_fs = tmp_path / "seat-fs"
    seat_fs.mkdir()
    (seat_fs / "review.log").write_text("seat review workspace\n", encoding="utf-8")

    def token_spawn(argv, input_text, env):
        spawned.append((list(argv), input_text, dict(env)))
        return subprocess.CompletedProcess(argv, 0, stdout=json.dumps({"id": 987}), stderr="")

    minter = FakeMinter(_token())
    worker_env = {"PATH": "/usr/bin", "CE_SEAT": "seat-reviewer-1", "PWD": str(seat_fs)}
    worker_argv = ("gh", "pr", "review", "7", "--request-changes", "--body-file", "-")
    result = submit_contained_seat_pr_review(
        ContainedSeatReview(
            seat_id="seat-reviewer-1",
            repo=_REPO,
            pr_number=7,
            head_sha=_HEAD,
            event="REQUEST_CHANGES",
            body="Needs a fix before merge.",
        ),
        binding=_binding(),
        minter=minter,
        worker_env=worker_env,
        worker_argv=worker_argv,
        durable_metadata={"dispatch_id": "dispatch-1"},
        token_spawn=token_spawn,
    )

    assert result.applied is True
    assert result.review_id == 987
    assert result.event == "REQUEST_CHANGES"
    assert minter.calls[0].permissions == {"metadata": "read", "pull_requests": "write"}
    argv, input_text, child_env = spawned[0]
    assert argv == ["gh", "api", "-X", "POST", f"repos/{_REPO}/pulls/7/reviews", "--input", "-"]
    assert json.loads(input_text or "") == {
        "body": "Needs a fix before merge.",
        "commit_id": _HEAD,
        "event": "REQUEST_CHANGES",
    }
    assert child_env["GH_TOKEN"] == _SECRET
    log_projection = json.dumps(result.to_dict(), sort_keys=True) + repr(argv) + (input_text or "")
    assert _SECRET not in log_projection
    assert _SECRET not in repr(worker_env)
    assert _SECRET not in repr(worker_argv)
    for path in seat_fs.rglob("*"):
        if path.is_file():
            assert _SECRET not in path.read_text(encoding="utf-8")
    assert worker_env == {"PATH": "/usr/bin", "CE_SEAT": "seat-reviewer-1", "PWD": str(seat_fs)}


def test_contained_seat_review_fails_closed_without_valid_injected_credential():
    spawned: list[object] = []

    def token_spawn(*args):
        spawned.append(args)
        raise AssertionError("transport must not run without a credential")

    with pytest.raises(CredentialProxyRefused):
        submit_contained_seat_pr_review(
            ContainedSeatReview(
                seat_id="seat-reviewer-1",
                repo=_REPO,
                pr_number=7,
                head_sha=_HEAD,
                event="COMMENT",
                body="Read-only opinion.",
            ),
            binding=_binding(),
            minter=FakeMinter(_token(value="")),
            token_spawn=token_spawn,
        )

    assert spawned == []


def test_contained_seat_review_refuses_approve_without_permitting_run_mode_before_mint():
    minter = FakeMinter(_token())
    transport = FakeTransport()

    with pytest.raises(CredentialProxyRefused) as exc:
        submit_contained_seat_pr_review(
            ContainedSeatReview(
                seat_id="seat-reviewer-1",
                repo=_REPO,
                pr_number=7,
                head_sha=_HEAD,
                event="APPROVE",
                body="seat approval must not be gate-valid",
                run_mode="solo",
                reviewer_authority_envelope=_reviewer_authority_envelope(),
            ),
            binding=_binding(),
            minter=minter,
            transport=transport,
        )

    assert "autonomous APPROVE is disabled" in str(exc.value)
    assert minter.calls == []
    assert transport.calls == []


def test_contained_seat_review_approve_refuses_missing_envelope_before_mint():
    minter = FakeMinter(_token())
    transport = FakeTransport()

    with pytest.raises(CredentialProxyRefused) as exc:
        submit_contained_seat_pr_review(
            ContainedSeatReview(
                seat_id="seat-reviewer-1",
                repo=_REPO,
                pr_number=7,
                head_sha=_HEAD,
                event="APPROVE",
                run_mode="strangeLoop",
            ),
            binding=_binding(),
            minter=minter,
            transport=transport,
        )

    assert "missing reviewer-authority-envelope" in str(exc.value)
    assert minter.calls == []
    assert transport.calls == []


def test_contained_seat_review_approve_refuses_invalid_envelope_before_mint():
    minter = FakeMinter(_token())
    transport = FakeTransport()

    with pytest.raises(CredentialProxyRefused) as exc:
        submit_contained_seat_pr_review(
            ContainedSeatReview(
                seat_id="seat-reviewer-1",
                repo=_REPO,
                pr_number=7,
                head_sha=_HEAD,
                event="APPROVE",
                run_mode="strangeLoop",
                reviewer_authority_envelope=_reviewer_authority_envelope(pr_number=8),
            ),
            binding=_binding(),
            minter=minter,
            transport=transport,
        )

    assert "PR does not match request" in str(exc.value)
    assert minter.calls == []
    assert transport.calls == []


@pytest.mark.parametrize("substrate", ["contained", "non-contained"])
def test_approve_allowed_for_independent_valid_envelope_and_permitting_mode(substrate):
    minter = FakeMinter(_token())
    transport = FakeTransport()

    result = submit_contained_seat_pr_review(
        ContainedSeatReview(
            seat_id="seat-reviewer-1",
            repo=_REPO,
            pr_number=7,
            head_sha=_HEAD,
            event="APPROVE",
            body="Independent reviewer approval.",
            run_mode="strangeLoop",
            reviewer_authority_envelope=_reviewer_authority_envelope(),
            containment_substrate=substrate,
        ),
        binding=_binding(),
        minter=minter,
        transport=transport,
    )

    assert result.applied is True
    assert result.event == "APPROVE"
    assert result.audit_record["outcome"] == "transport_dispatched"
    assert result.audit_record["decision"]["request"]["approve_authority_checked"] is True
    assert any(
        check["name"] == "review_event_allowed" and check["passed"]
        for check in result.audit_record["decision"]["checks"]
    )
    assert minter.calls[0].repo == _REPO
    assert transport.calls[0].repo == _REPO
    assert json.loads(transport.calls[0].body or "") == {
        "body": "Independent reviewer approval.",
        "commit_id": _HEAD,
        "event": "APPROVE",
    }


def test_contained_seat_review_refuses_wall_secret_in_launch_context_before_mint():
    minter = FakeMinter(_token())
    transport = FakeTransport()

    with pytest.raises(CredentialProxyRefused) as exc:
        submit_contained_seat_pr_review(
            ContainedSeatReview(
                seat_id="seat-reviewer-1",
                repo=_REPO,
                pr_number=7,
                head_sha=_HEAD,
                event="COMMENT",
                body="not a wall-capable approval",
            ),
            binding=_binding(),
            minter=minter,
            worker_env={"CE_APPROVAL_CAPABILITY_SECRET": "wall-signing-secret"},
            transport=transport,
        )

    assert "launch_context_secret_denied" in str(exc.value)
    assert minter.calls == []
    assert transport.calls == []


def test_trusted_gh_transport_requires_proxy_injected_credential():
    transport = gh_api_transport_adapter(spawn=lambda *args: None)

    with pytest.raises(CredentialProxyRefused):
        transport(
            OutboundTransportRequest(
                host="api.github.com",
                method="POST",
                path=f"/repos/{_REPO}/pulls/7/reviews",
                headers={},
                body='{"event":"COMMENT"}',
                repo=_REPO,
                pr=7,
                head_sha=_HEAD,
            )
        )
