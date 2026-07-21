from __future__ import annotations

from pathlib import Path

import pytest

from creator_engine_validator.forge.review_submission_receipt import (
    REVIEW_SUBMISSION_RECEIPT_SECRET_PURPOSE, ReviewReceiptRefused, ReviewSubmissionReceiptAuthority,
    receipt_key_supplier_from_secret_identity_backend,
)
from creator_engine_validator.forge.reviewer_terminal import require_reviewed_terminal
from creator_engine_validator.secret_identity import SecretRef, SecretRequest


_FIXTURES = Path(__file__).parents[1] / "fixtures" / "ce639"


def _terminal():
    return require_reviewed_terminal({
        "version": 2, "state": "REVIEWED", "repository": "owner/repo", "pr_number": 7,
        "head_sha": "a" * 40, "base": "main", "range": "main...head", "reviewer": "reviewer",
        "author": "author", "review_id": "dispatch-7", "verdict": "APPROVE",
        "verified": [{"claim": "diff", "evidence": "git diff: clean"}], "findings": [],
        "summary": "inspected", "timestamp": "2026-07-21T00:00:00Z",
    })


def test_receipt_tamper_expiry_and_replay_refuse_before_reuse(tmp_path):
    clock = [1000]
    authority = ReviewSubmissionReceiptAuthority(state_root=tmp_path / "state", key_supplier=lambda: b"k" * 32,
                                                  now=lambda: clock[0])
    terminal = _terminal()
    receipt = authority.issue(terminal, ttl_seconds=60)
    authority.consume(receipt, terminal=terminal, repository="owner/repo", pr_number=7,
                      head_sha="a" * 40, event="APPROVE")
    with pytest.raises(ReviewReceiptRefused, match="replay"):
        authority.consume(receipt, terminal=terminal, repository="owner/repo", pr_number=7,
                          head_sha="a" * 40, event="APPROVE")
    clock[0] = 2000
    expired = authority.issue(terminal, ttl_seconds=1)
    clock[0] = 2002
    with pytest.raises(ReviewReceiptRefused, match="expired"):
        authority.consume(expired, terminal=terminal, repository="owner/repo", pr_number=7,
                          head_sha="a" * 40, event="APPROVE")


def test_receipt_unavailable_key_refuses(tmp_path):
    authority = ReviewSubmissionReceiptAuthority(state_root=tmp_path / "state", key_supplier=lambda: None)
    with pytest.raises(ReviewReceiptRefused, match="backend unavailable"):
        authority.issue(_terminal(), ttl_seconds=60)


def test_invalid_v2_audit_legacy_never_issues_a_receipt(tmp_path):
    authority = ReviewSubmissionReceiptAuthority(state_root=tmp_path / "state", key_supplier=lambda: b"k" * 32)
    malformed = {
        "version": 2, "state": "REVIEWED", "repository": "owner/repo", "pr_number": 7,
        "head_sha": "a" * 40, "base": "main", "range": "main...head", "reviewer": "reviewer",
        "author": "author", "review_id": "dispatch-7", "verdict": "APPROVE", "verified": [],
        "findings": [], "summary": "inspected", "timestamp": "2026-07-21T00:00:00Z",
    }
    with pytest.raises(ReviewReceiptRefused, match="not receipt-eligible"):
        authority.issue(malformed, ttl_seconds=60)


@pytest.mark.parametrize("fixture", [
    "ce637_gate_review_refusal.md",
    "ce637_gate_review_retry_refusal.md",
])
def test_real_ce637_refusal_fixtures_never_issue_receipts(tmp_path, fixture):
    authority = ReviewSubmissionReceiptAuthority(state_root=tmp_path / "state", key_supplier=lambda: b"k" * 32)
    raw = (_FIXTURES / fixture).read_text(encoding="utf-8")
    with pytest.raises(ReviewReceiptRefused, match="not receipt-eligible"):
        authority.issue(raw, ttl_seconds=60)


def test_receipt_key_supplier_refuses_the_approval_wall_purpose_before_backend_use():
    request = SecretRequest(
        run_id="run-1", seat_id="dev-2", repo="owner/repo", ttl_seconds=60, delivery="file",
        requested_capabilities=("read",),
        secret_ref=SecretRef(
            backend="openbao", mount="ce-kv", path="approval-wall", field="key", version=None,
            purpose="approval_capability", owner_ref="controller", policy_sha="a" * 64,
        ),
    )
    with pytest.raises(ReviewReceiptRefused, match="dedicated secret purpose"):
        receipt_key_supplier_from_secret_identity_backend(
            backend=object(), request=request, target_ref="file:/tmp/receipt-key", value_reader=lambda _: None,
        )
    assert REVIEW_SUBMISSION_RECEIPT_SECRET_PURPOSE == "review_submission_receipt"
