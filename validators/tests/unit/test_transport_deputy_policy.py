"""Unit tests for the offline transport-deputy policy seam."""

from creator_engine_validator.forge.transport_deputy_policy import (
    TransportRequest,
    evaluate,
)

_REPO = "creator-engine/creator-engine"
_HEAD = "a" * 40


def _request(**overrides) -> TransportRequest:
    base = dict(
        seat_id="seat-reviewer-1",
        role_profile="reviewer",
        host="api.github.com",
        method="GET",
        path=f"/repos/{_REPO}/pulls/7",
        repo=_REPO,
        pr=7,
        head_sha=_HEAD,
    )
    base.update(overrides)
    return TransportRequest(**base)


def test_reviewer_can_submit_review_to_matching_pr():
    decision = evaluate(
        _request(
            method="POST",
            path=f"/repos/{_REPO}/pulls/7/reviews",
            body=f'{{"event":"COMMENT","commit_id":"{_HEAD}"}}',
            review_receipt_checked=True,
        )
    )

    assert decision.allowed is True
    assert decision.as_record()["verdict"] == "allow"


def test_reviewer_review_submit_denies_approve_without_prior_authority_check():
    decision = evaluate(
        _request(
            method="POST",
            path=f"/repos/{_REPO}/pulls/7/reviews",
            body='{"event":"APPROVE","body":"not gate-valid"}',
            review_receipt_checked=True,
        )
    )

    assert decision.allowed is False
    assert "lacks prior role/run-mode/envelope authority check" in " ".join(decision.reasons)


def test_reviewer_review_submit_allows_approve_after_prior_authority_check():
    decision = evaluate(
        _request(
            method="POST",
            path=f"/repos/{_REPO}/pulls/7/reviews",
            body=f'{{"event":"APPROVE","commit_id":"{_HEAD}"}}',
            approve_authority_checked=True,
            review_receipt_checked=True,
        )
    )

    assert decision.allowed is True
    assert decision.as_record()["request"]["approve_authority_checked"] is True


def test_reviewer_review_submit_requires_explicit_event():
    decision = evaluate(
        _request(method="POST", path=f"/repos/{_REPO}/pulls/7/reviews", review_receipt_checked=True)
    )

    assert decision.allowed is False
    assert "missing an explicit review event" in " ".join(decision.reasons)


def test_reviewer_review_submit_refuses_without_receipt_check():
    decision = evaluate(_request(
        method="POST", path=f"/repos/{_REPO}/pulls/7/reviews",
        body='{"event":"COMMENT"}',
    ))
    assert decision.allowed is False
    assert "parser-issued exact-payload receipt" in " ".join(decision.reasons)


def test_destructive_delete_is_blocked_before_injection():
    decision = evaluate(
        _request(method="DELETE", path=f"/repos/{_REPO}/hooks/42")
    )

    assert decision.allowed is False
    assert decision.verdict == "deny"
    assert "destructive" in " ".join(decision.reasons)


def test_unknown_write_is_denied():
    decision = evaluate(
        _request(method="POST", path=f"/repos/{_REPO}/dispatches")
    )

    assert decision.allowed is False
    assert "unmatched write" in " ".join(decision.reasons)


def test_missing_seat_or_unknown_role_denies():
    assert evaluate(_request(seat_id="")).allowed is False
    assert evaluate(_request(role_profile="operator")).allowed is False


def test_secret_bearing_header_and_env_denies_without_echoing_secret():
    decision = evaluate(
        _request(
            headers={"Authorization": "Bearer ghs_abcdefghijklmnopqrstuvwxyz123456"},
            env={"GH_TOKEN": "github_pat_secretvalue1234567890"},
        )
    )

    assert decision.allowed is False
    record = decision.as_record()
    rendered = repr(record)
    assert "ghs_abcdefghijklmnopqrstuvwxyz123456" not in rendered
    assert "github_pat_secretvalue1234567890" not in rendered
    assert "Authorization" in rendered
    assert "GH_TOKEN" in rendered


def test_graphql_mutation_is_denied_as_opaque_write():
    decision = evaluate(
        _request(
            method="POST",
            path="/graphql",
            body='mutation { deleteRepository(input: {repositoryId: "R_123"}) { clientMutationId } }',
        )
    )

    assert decision.allowed is False
    assert "GraphQL mutation" in " ".join(decision.reasons)


def test_reviewer_read_path_is_allowed():
    decision = evaluate(_request(method="GET", path=f"/repos/{_REPO}/pulls/7/files"))

    assert decision.allowed is True
