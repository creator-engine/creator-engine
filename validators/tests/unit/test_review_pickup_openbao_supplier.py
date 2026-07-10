"""Smoke coverage for review-pickup SecretIdentity token supply."""

from __future__ import annotations

import json
import subprocess
from argparse import Namespace
from dataclasses import replace

import pytest

from creator_engine_validator import pickup_search, v3_cli
from creator_engine_validator.forge import review_pickup


def _pickup_secret_args(**overrides) -> Namespace:
    values = {
        "repo": "owner/repo",
        "org": None,
        "pickup_token_secret_backend": None,
        "pickup_token_secret_mount": None,
        "pickup_token_secret_path": None,
        "pickup_token_secret_field": None,
        "pickup_token_secret_version": None,
        "pickup_token_secret_purpose": None,
        "pickup_token_secret_owner_ref": None,
        "pickup_token_secret_ref_policy_sha": None,
        "pickup_token_secret_target_ref": None,
        "pickup_token_secret_run_id": "review-pickup-daemon",
        "pickup_token_secret_seat_id": "dev-2",
        "pickup_token_secret_ttl_seconds": (
            v3_cli.secret_identity.DEFAULT_REVIEW_PICKUP_TOKEN_SECRET_TTL_SECONDS
        ),
    }
    values.update(overrides)
    return Namespace(**values)


class _RecordingPickupTokenBackend:
    backend_key = "openbao"

    def __init__(self) -> None:
        self.requests = []
        self.materialized_targets = []
        self.revoked = []

    def validate_config(self) -> None:
        return None

    def resolve_identity(self, seat_id):
        raise AssertionError("resolve_identity is not used by review-pickup token supply")

    def issue(self, request):
        self.requests.append(request)
        return v3_cli.secret_identity.SecretGrant(
            grant_id="grant-review-pickup-token-001",
            run_id=request.run_id,
            seat_id=request.seat_id,
            secret_ref=request.secret_ref,
            lease_id=None,
            token_accessor_ref="accessor:review-pickup",
            issued_at="2026-07-05T00:00:00Z",
            expires_at="2026-07-05T00:05:00Z",
            delivery_ref=None,
            audit_ref="audit:review-pickup",
        )

    def issue_secret_zero(self, request):
        raise AssertionError("issue_secret_zero is not used by review-pickup token supply")

    def materialize(self, grant, target_ref):
        self.materialized_targets.append(target_ref)
        return replace(grant, delivery_ref=target_ref)

    def revoke(self, grant):
        self.revoked.append(grant.grant_id)
        return replace(grant, revoked_at="2026-07-05T00:00:01Z")

    def collect_audit(self, grant):
        return {"grant_id": grant.grant_id, "audit_ref": grant.audit_ref}


def test_review_pickup_token_supplier_unconfigured_preserves_static_path() -> None:
    assert v3_cli._review_pickup_token_supplier_from_args(_pickup_secret_args()) is None


def test_review_pickup_token_supplier_rejects_env_target_ref() -> None:
    args = _pickup_secret_args(
        pickup_token_secret_ref_policy_sha="a" * 64,
        pickup_token_secret_target_ref="env:CE_PICKUP_TOKEN",
    )

    with pytest.raises(pickup_search.PickupError, match="env: targets are fork-unsafe"):
        v3_cli._review_pickup_token_supplier_from_args(args)


def test_review_pickup_token_supplier_uses_backend_defaults(monkeypatch) -> None:
    backend = _RecordingPickupTokenBackend()
    monkeypatch.setattr(v3_cli.secret_identity, "get_backend", lambda key: backend)
    monkeypatch.setattr(
        v3_cli,
        "_approval_wall_materialized_value_reader",
        lambda target_ref: "ghp_backend_review_token",
    )

    supplier = v3_cli._review_pickup_token_supplier_from_args(
        _pickup_secret_args(
            pickup_token_secret_ref_policy_sha="a" * 64,
            pickup_token_secret_target_ref="file:/run/ce/review-pickup-token",
        )
    )

    assert supplier is not None
    assert supplier() == "ghp_backend_review_token"
    assert backend.materialized_targets == ["file:/run/ce/review-pickup-token"]
    assert backend.revoked == ["grant-review-pickup-token-001"]
    request = backend.requests[0]
    assert request.run_id == "review-pickup-daemon"
    assert request.seat_id == "dev-2"
    assert request.ttl_seconds == 300
    assert request.secret_ref.backend == "openbao"
    assert request.secret_ref.mount == "ce-kv"
    assert request.secret_ref.path == "forge/reviewer/gh-token"
    assert request.secret_ref.field == "token"
    assert request.secret_ref.purpose == "review-pickup-token"
    assert request.secret_ref.owner_ref == "controller:reviewer"


def test_review_pickup_loop_refreshes_supplier_token_each_pass() -> None:
    supplied_tokens = iter(("tok-pass-1", "tok-pass-2"))
    runner_tokens = []
    auth_headers = []

    def token_supplier() -> str:
        return next(supplied_tokens)

    def gh_runner_factory(token: str):
        runner_tokens.append(token)

        def runner(argv, input_text=None):
            return subprocess.CompletedProcess(argv, 1, stdout="", stderr="unexpected gh call")

        return runner

    def transport(method, url, headers, body):
        auth_headers.append(headers.get("Authorization"))
        return 200, {}, json.dumps({"total_count": 0, "items": []})

    result = review_pickup.run_review_pickup_loop(
        token="static-token",
        reviewer_seats=("reviewer-b",),
        gh_runner=lambda argv, input_text=None: subprocess.CompletedProcess(argv, 1),
        token_supplier=token_supplier,
        gh_runner_factory=gh_runner_factory,
        transport=transport,
        repo="owner/repo",
        iterations=2,
        interval=0,
        sleep=lambda seconds: None,
    )

    assert len(result.passes) == 2
    assert all(not review_pass.incomplete for review_pass in result.passes)
    assert runner_tokens == ["tok-pass-1", "tok-pass-2"]
    assert auth_headers == ["Bearer tok-pass-1", "Bearer tok-pass-2"]


def test_review_pickup_loop_exits_after_bounded_supplier_failures() -> None:
    events = []
    sleeps = []

    def token_supplier() -> str:
        raise RuntimeError("backend unavailable")

    with pytest.raises(review_pickup.PickupError, match="2 consecutive"):
        review_pickup.run_review_pickup_loop(
            token="",
            reviewer_seats=("reviewer-b",),
            gh_runner=lambda argv, input_text=None: subprocess.CompletedProcess(argv, 1),
            token_supplier=token_supplier,
            gh_runner_factory=lambda token: (
                lambda argv, input_text=None: subprocess.CompletedProcess(argv, 1)
            ),
            transport=lambda method, url, headers, body: (200, {}, "{}"),
            repo="owner/repo",
            iterations=3,
            interval=0,
            sleep=lambda seconds: sleeps.append(seconds),
            log_sink=events.append,
            max_consecutive_failures=2,
        )

    incomplete = [event for event in events if event["event"] == "review_pickup_pass_incomplete"]
    assert [event["reason"] for event in incomplete] == [
        "token_supplier_failed",
        "token_supplier_failed",
    ]
    assert sleeps == [0]
