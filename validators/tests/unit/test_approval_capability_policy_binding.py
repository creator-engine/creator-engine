from creator_engine_validator.forge.approval_capability import (
    ApprovalCapabilityClaims,
    ApprovalCapabilityVerifier,
    approval_capability_policy_sha,
    issue_approval_capability,
)


def test_policy_sha_mode_tier_binding_rejects_permissive_replay():
    secret = "approval-secret"
    permissive_sha = approval_capability_policy_sha(
        run_mode="dev",
        risk_tier="low",
        policy_material={"policy": "approval-wall-v1"},
    )
    strict_sha = approval_capability_policy_sha(
        run_mode="strangeLoop",
        risk_tier="medium",
        policy_material={"policy": "approval-wall-v1"},
    )
    marker = issue_approval_capability(
        ApprovalCapabilityClaims(
            repo="owner/repo",
            pr_number=42,
            head_sha="a" * 40,
            approved_by="reviewer",
            issued_at=100,
            expires_at=200,
            policy_sha=permissive_sha,
        ),
        secret,
    )

    result = ApprovalCapabilityVerifier(
        lambda: secret,
        now=lambda: 150,
        policy_sha=strict_sha,
    ).verify(
        marker,
        repo="owner/repo",
        pr_number=42,
        head_sha="a" * 40,
        approved_by_candidates=("reviewer",),
    )

    assert result.valid is False
    assert result.reason == "policy_mismatch"
