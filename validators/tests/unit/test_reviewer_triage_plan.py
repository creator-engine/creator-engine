from __future__ import annotations

import copy
import json

from creator_engine_validator import ce_cli
from creator_engine_validator import reviewer_triage as rt


HEAD = "a" * 40
NON_AUTHORITY = (
    "Reviewer triage assigns review only; it does not approve, ratify, merge, or waive policy."
)


def _reviewer(
    reviewer_id: str,
    *,
    login: str | None = None,
    human_id: str | None = None,
    controller_id: str | None = None,
    venue_id: str | None = None,
    status: str = "available",
    active_reviews: int = 0,
    max_active_reviews: int = 2,
    teams: list[str] | None = None,
    paths: list[str] | None = None,
    mutation_classes: list[str] | None = None,
    risk_tiers: list[str] | None = None,
    isolation_tier: str = "tier-2",
    containment_status: str = "enforced",
    credential_domain_ref: str | None = None,
    os_user_ref: str | None = None,
    host_ref: str = "ce-pilot-1",
) -> dict:
    login = login or reviewer_id
    human_id = human_id or f"human-{reviewer_id}"
    controller_id = controller_id or f"controller-{reviewer_id}"
    venue_id = venue_id or f"venue-{reviewer_id}"
    return {
        "reviewer_id": reviewer_id,
        "human_id": human_id,
        "controller_id": controller_id,
        "venue_kind": "agentic",
        "allowed_harnesses": ["codex"],
        "source_host_identities": {
            "logins": [login],
            "teams": teams or ["ce-reviewers"],
            "app_installation_ids": [],
            "bot_slugs": [],
        },
        "identity_ref": f"tenants/creator-engine/reviewers/{reviewer_id}.yml",
        "allowed_repositories": ["creator-engine/creator-engine"],
        "capabilities": {
            "languages": ["python"],
            "mutation_classes": mutation_classes or ["code", "schema", "docs", "governance"],
            "risk_tiers": risk_tiers or ["low", "medium", "high", "privileged"],
            "security": True,
            "deploy": True,
            "schema": True,
            "readability": True,
        },
        "ownership": {
            "codeowners": [login],
            "teams": teams or ["ce-reviewers"],
            "path_globs": paths or ["validators/**", "schemas/**", "docs/**"],
            "area_owner_refs": [],
        },
        "availability": {
            "status": status,
            "time_zone": "UTC",
            "working_hours": "declared-durable",
            "max_active_reviews": max_active_reviews,
            "active_reviews": active_reviews,
            "backup_reviewer_ids": [],
        },
        "isolation_domain_attestation": {
            "forge_principal": login,
            "credential_domain_ref": credential_domain_ref or f"credential-{reviewer_id}",
            "os_user_ref": os_user_ref or f"os-user-{reviewer_id}",
            "controller_principal_ref": controller_id,
            "execution_sandbox_ref": f"sandbox-{reviewer_id}",
            "containment_ref": f"containment-{reviewer_id}",
            "host_ref": host_ref,
            "computed_tier": isolation_tier,
            "containment_status": containment_status,
            "evidence_timestamp": "2026-06-18T00:00:00Z",
            "source": "unit-test",
        },
        "policy_refs": ["ce-ops#120"],
    }


def _registry(reviewers: list[dict]) -> dict:
    return {
        "kind": "reviewer-registry",
        "schema_version": "1",
        "mutation_class": "governance",
        "reviewers": reviewers,
    }


def _base_kwargs(**overrides):
    kwargs = {
        "repo": "creator-engine/creator-engine",
        "pr_number": 120,
        "head_sha": HEAD,
        "expected_head_sha": HEAD,
        "author_run_id": "run-author-120",
        "author_identity": {
            "login": "chmod735",
            "human_id": "peer-operator",
            "controller_id": "ce-dev-1",
            "venue_id": "author-venue",
            "credential_domain_ref": "credential-author",
            "os_user_ref": "os-user-author",
            "host_ref": "ce-pilot-1",
        },
        "last_pusher": {"login": "chmod735", "human_id": "peer-operator"},
        "changed_paths": ["validators/creator_engine_validator/ce_cli.py"],
        "mutation_classes": ["code"],
        "risk_tier": "medium",
        "codeowners_text": "* @reviewer-z @reviewer-a\n",
        "coordination_policy": None,
        "registry": _registry([
            _reviewer("reviewer-z", login="reviewer-z"),
            _reviewer("reviewer-a", login="reviewer-a"),
        ]),
        "ruleset_required_teams": ["ce-reviewers"],
    }
    kwargs.update(overrides)
    return kwargs


def test_deterministic_ranking_selects_concrete_reviewer_identity():
    first = rt.plan_reviewer_triage(**_base_kwargs())
    second = rt.plan_reviewer_triage(**_base_kwargs())

    assert first == second
    assert first["assignment"]["selected_reviewers"] == ["reviewer-a"]
    assert first["assignment"]["selected_identity_refs"] == [
        "tenants/creator-engine/reviewers/reviewer-a.yml"
    ]
    assert first["assignment"]["review_request_action"] == "request_review"
    assert first["non_authority_statement"] == NON_AUTHORITY
    assert first["candidate_generation"]["git_history_scoring"] is False
    assert first["eligibility_results"][0]["isolation_domain_attestation"]["computed_tier"] == "tier-2"
    assert first["eligibility_results"][0]["containment_status"] == "enforced"


def test_same_host_tier2_peer_is_valid_when_domains_are_disjoint():
    registry = _registry([
        _reviewer("same-host-peer", login="reviewer-a", host_ref="ce-pilot-1"),
    ])
    decision = rt.plan_reviewer_triage(
        **_base_kwargs(registry=registry, codeowners_text="* @reviewer-a\n")
    )

    assert decision["assignment"]["selected_reviewers"] == ["same-host-peer"]
    result = decision["eligibility_results"][0]
    assert result["eligible"] is True
    assert result["isolation_domain_attestation"]["host_ref"] == "ce-pilot-1"
    assert result["isolation_domain_attestation"]["computed_tier"] == "tier-2"


def test_same_user_and_same_controller_with_different_login_is_tier1_invalid():
    registry = _registry([
        _reviewer(
            "same-controller",
            login="reviewer-a",
            human_id="peer-operator",
            controller_id="ce-dev-1",
            isolation_tier="tier-1",
        ),
    ])
    decision = rt.plan_reviewer_triage(
        **_base_kwargs(registry=registry, codeowners_text="* @reviewer-a\n")
    )

    assert decision["assignment"]["selected_reviewers"] == []
    reasons = set(decision["eligibility_results"][0]["reasons"])
    assert "same_human_as_author" in reasons
    assert "same_controller_as_author" in reasons
    assert "isolation_tier_below_floor" in reasons


def test_unresolved_controller_mapping_fails_closed():
    reviewer = _reviewer("unresolved-controller", login="reviewer-a")
    reviewer["controller_id"] = ""
    reviewer["isolation_domain_attestation"]["controller_principal_ref"] = ""
    decision = rt.plan_reviewer_triage(
        **_base_kwargs(registry=_registry([reviewer]), codeowners_text="* @reviewer-a\n")
    )

    assert decision["assignment"]["selected_reviewers"] == []
    assert "unresolved_controller_identity" in decision["eligibility_results"][0]["reasons"]


def test_uncontained_real_reviewer_venue_is_ineligible():
    registry = _registry([
        _reviewer("uncontained", login="reviewer-a", containment_status="uncontained"),
    ])
    decision = rt.plan_reviewer_triage(
        **_base_kwargs(registry=registry, codeowners_text="* @reviewer-a\n")
    )

    assert decision["assignment"]["selected_reviewers"] == []
    assert "runtime_uncontained" in decision["eligibility_results"][0]["reasons"]


def test_tier4_reviewer_can_be_selected_for_high_consequence_release_class():
    registry = _registry([
        _reviewer(
            "tier4-reviewer",
            login="reviewer-a",
            isolation_tier="tier-4",
            mutation_classes=["code", "release", "root-key", "signing"],
        )
    ])
    decision = rt.plan_reviewer_triage(
        **_base_kwargs(
            registry=registry,
            codeowners_text="* @reviewer-a\n",
            mutation_classes=["release"],
            risk_tier="privileged",
        )
    )

    assert decision["assignment"]["selected_reviewers"] == ["tier4-reviewer"]
    assert decision["eligibility_results"][0]["isolation_domain_attestation"]["computed_tier"] == "tier-4"


def test_unresolved_identity_fails_closed_for_codeowners_candidate():
    decision = rt.plan_reviewer_triage(**_base_kwargs(registry=_registry([])))

    assert decision["assignment"]["selected_reviewers"] == []
    assert decision["escalation"]["status"] == "operator"
    assert any(
        result["reviewer_id"] == "reviewer-a"
        and "missing_ratified_reviewer_identity" in result["reasons"]
        for result in decision["eligibility_results"]
    )


def test_no_self_and_last_pusher_exclusions_use_human_identity():
    registry = _registry([
        _reviewer("same-human", login="reviewer-a", human_id="peer-operator"),
        _reviewer("last-pusher", login="reviewer-z", human_id="human-last-pusher"),
    ])
    decision = rt.plan_reviewer_triage(
        **_base_kwargs(
            registry=registry,
            last_pusher={"login": "pushbot", "human_id": "human-last-pusher"},
        )
    )

    reasons = {r["reviewer_id"]: set(r["reasons"]) for r in decision["eligibility_results"]}
    assert "same_human_as_author" in reasons["same-human"]
    assert "same_human_as_last_pusher" in reasons["last-pusher"]
    assert decision["assignment"]["selected_reviewers"] == []


def test_retired_and_busy_reviewers_are_not_available():
    registry = _registry([
        _reviewer("retired", login="reviewer-a", status="retired"),
        _reviewer("busy", login="reviewer-z", active_reviews=2, max_active_reviews=2),
    ])
    decision = rt.plan_reviewer_triage(**_base_kwargs(registry=registry))

    availability = {r["reviewer_id"]: set(r["reasons"]) for r in decision["availability_results"]}
    assert "availability_status_retired" in availability["retired"]
    assert "max_active_reviews_reached" in availability["busy"]
    assert decision["assignment"]["selected_reviewers"] == []


def test_codeowners_path_and_ruleset_team_match_are_required():
    registry = _registry([
        _reviewer("wrong-path", login="reviewer-a", paths=["docs/**"]),
        _reviewer("wrong-team", login="reviewer-z", teams=["not-codeowners"]),
    ])
    decision = rt.plan_reviewer_triage(**_base_kwargs(registry=registry))

    reasons = {r["reviewer_id"]: set(r["reasons"]) for r in decision["eligibility_results"]}
    assert "not_owner_for_changed_paths" in reasons["wrong-path"]
    assert "missing_required_ruleset_team" in reasons["wrong-team"]
    assert decision["assignment"]["selected_reviewers"] == []


def test_head_sha_mismatch_fails_closed_without_assignment():
    decision = rt.plan_reviewer_triage(**_base_kwargs(expected_head_sha="b" * 40))

    assert decision["assignment"]["selected_reviewers"] == []
    assert decision["assignment"]["review_request_action"] == "none"
    assert decision["escalation"]["status"] == "operator"
    assert decision["escalation"]["reason"] == "head_sha_mismatch"


def test_privileged_class_routes_to_source():
    registry = _registry([_reviewer("source-reviewer", login="reviewer-a")])
    decision = rt.plan_reviewer_triage(
        **_base_kwargs(
            registry=registry,
            mutation_classes=["governance"],
            risk_tier="privileged",
        )
    )

    assert decision["assignment"]["selected_reviewers"] == []
    assert decision["escalation"]["status"] == "operator"
    assert decision["escalation"]["reason"] == "privileged_requires_source"


def test_cli_plan_outputs_json_decision(tmp_path, capsys):
    registry = tmp_path / "reviewer-registry.yml"
    registry.write_text(
        rt.dump_yaml(_registry([_reviewer("reviewer-a", login="reviewer-a")])),
        encoding="utf-8",
    )

    rc = ce_cli.main([
        "reviewer-triage",
        "plan",
        "--pr",
        "120",
        "--json",
        "--repo",
        "creator-engine/creator-engine",
        "--head-sha",
        HEAD,
        "--author-login",
        "chmod735",
        "--author-human-id",
        "peer-operator",
        "--author-controller-id",
        "ce-dev-1",
        "--author-credential-domain-ref",
        "credential-author",
        "--author-os-user-ref",
        "os-user-author",
        "--author-host-ref",
        "ce-pilot-1",
        "--changed-path",
        "validators/creator_engine_validator/ce_cli.py",
        "--mutation-class",
        "code",
        "--risk-tier",
        "medium",
        "--codeowners-text",
        "* @reviewer-a\n",
        "--registry",
        str(registry),
        "--required-team",
        "ce-reviewers",
    ])

    assert rc == 0
    out = json.loads(capsys.readouterr().out)
    assert out["work_ref"]["pr_number"] == 120
    assert out["assignment"]["selected_reviewers"] == ["reviewer-a"]
