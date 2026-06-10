"""Unit tests for the v3.5-C A-C3 ``peer_authority`` check + the generalized
forge-side ``plan_approved`` authority path."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import yaml

from creator_engine_validator.checks import peer_authority as chk
from creator_engine_validator.checks import registered_checks
from creator_engine_validator.checks.mutation_class import PRIVILEGED_NAMES
from creator_engine_validator.forge.plan_approval import ApprovalQuery, plan_approved

FIXTURES = Path(__file__).resolve().parents[2] / "examples" / "peer-authority"
REPO_ROOT = Path(__file__).resolve().parents[3]


def _fixture(name: str) -> Path:
    return FIXTURES / name


def _policy(**overrides):
    base = {
        "kind": "coordination-policy", "schema_version": "1",
        "mutation_class": "governance",
        "ratification_authority": {
            "defer_to_codeowners": False,
            "area_owners": {
                "runner/**": ["alice"],
                "forge/**": ["bob"],
                "docs/decisions/**": ["alice", "bob"],
            },
            "quorum_by_tier": {"non_privileged": 1, "privileged": 2},
            "no_self_approval": True,
        },
        "identity_map": {
            "humans": [
                {"human_id": "alice", "github_logins": ["alice-gh"],
                 "seats": ["seat-alpha"], "app_installations": ["12345678"]},
                {"human_id": "bob", "github_logins": ["bob-gh", "bob-work-gh"],
                 "seats": ["seat-beta"], "app_installations": ["87654321"]},
                {"human_id": "carol", "github_logins": ["carol-gh"],
                 "seats": ["seat-gamma"], "app_installations": []},
            ]
        },
    }
    base.update(overrides)
    return base


def _codes(policy):
    return sorted({e.code for e in chk.validate_policy(policy, Path("coordination.yml"))})


# --- registration -------------------------------------------------------------
def test_registered_in_check_surface():
    reg = registered_checks()
    assert chk.CHECK_NAME in reg
    assert chk.CODE_QUORUM in reg[chk.CHECK_NAME].frs


# --- fixtures (the gate's green-def) -------------------------------------------
def test_valid_coordination_fixture_passes():
    result = chk.run([_fixture("valid-coordination.yml")])
    assert result.ok, [e.format() for e in result.errors]


def test_privileged_single_ratifier_fixture_rejected():
    result = chk.run([_fixture("invalid-privileged-single-ratifier.yml")])
    assert any(e.code == chk.CODE_QUORUM for e in result.errors)


def test_crossarea_missing_owner_fixture_rejected():
    result = chk.run([_fixture("invalid-crossarea-missing-owner.yml")])
    assert any(e.code == chk.CODE_AREA_OWNER_MISSING for e in result.errors)


def test_repo_coordination_policy_validates_and_is_governance_classed():
    policy_path = REPO_ROOT / ".ce" / "coordination.yml"
    assert policy_path.is_file()
    result = chk.run([policy_path])
    assert result.ok, [e.format() for e in result.errors]
    policy = yaml.safe_load(policy_path.read_text(encoding="utf-8"))
    # recognized governance-class: changing the authority map is privileged.
    assert policy["mutation_class"] == "governance"
    assert "governance" in PRIVILEGED_NAMES


# --- identity resolution (the §11.5 resolver, shipped honestly) -----------------
def test_resolver_distinguishes_the_two_peers_across_all_axes():
    policy = _policy()
    # {git author / PR approver login, running seat, App installation} -> human
    assert chk.resolve_actor("alice-gh", policy) == "alice"
    assert chk.resolve_actor("seat-alpha", policy) == "alice"
    assert chk.resolve_actor("12345678", policy) == "alice"
    assert chk.resolve_actor("bob-gh", policy) == "bob"
    assert chk.resolve_actor("bob-work-gh", policy) == "bob"
    assert chk.resolve_actor("seat-beta", policy) == "bob"
    assert chk.resolve_actor("87654321", policy) == "bob"
    assert chk.resolve_actor("alice-gh", policy) != chk.resolve_actor("bob-gh", policy)


def test_unresolved_actor_fails_closed():
    ok, reasons = chk.authority_satisfied(
        _policy(), author="alice-gh", approvers=["stranger-gh", "bob-gh"],
        mutation_class="code", changed_paths=["forge/x.py"],
    )
    # bob still satisfies quorum+area, but the unresolved actor is SURFACED.
    assert not ok
    assert any("does not resolve" in r for r in reasons)


def test_two_accounts_of_one_human_count_once_toward_quorum():
    ok, reasons = chk.authority_satisfied(
        _policy(), author="alice-gh", approvers=["bob-gh", "bob-work-gh"],
        mutation_class="security", changed_paths=[],
    )
    assert not ok
    assert any("quorum not met" in r for r in reasons)


# --- quorum / self-approval / area invariants ------------------------------------
def test_privileged_with_both_peers_passes():
    ok, reasons = chk.authority_satisfied(
        _policy(), author="seat-gamma", approvers=["alice-gh", "bob-gh"],
        mutation_class="governance", changed_paths=["docs/decisions/ADR-0002-x.md"],
    )
    assert ok, reasons


def test_unmapped_author_is_surfaced_fail_closed():
    ok, reasons = chk.authority_satisfied(
        _policy(), author="seat-omega-unmapped", approvers=["alice-gh", "bob-gh"],
        mutation_class="governance", changed_paths=["docs/decisions/ADR-0002-x.md"],
    )
    assert not ok and any("author" in r and "does not resolve" in r for r in reasons)


def test_resolved_author_with_one_independent_ratifier_passes_non_privileged():
    ok, reasons = chk.authority_satisfied(
        _policy(), author="seat-alpha", approvers=["bob-gh"],
        mutation_class="code", changed_paths=["runner/spend_gate.py"],
    )
    # a resolved author covering their own area + 1 independent passes.
    assert ok, reasons


def test_privileged_quorum_of_one_fails_for_every_privileged_class():
    for cls in sorted(PRIVILEGED_NAMES):
        ok, reasons = chk.authority_satisfied(
            _policy(), author="alice-gh", approvers=["bob-gh"],
            mutation_class=cls, changed_paths=[],
        )
        assert not ok and any("quorum not met" in r for r in reasons), cls


def test_approver_resolving_to_author_human_is_self_approval():
    # alice's SEAT authored; alice's login approving = same human = self-approval.
    ok, reasons = chk.authority_satisfied(
        _policy(), author="seat-alpha", approvers=["alice-gh"],
        mutation_class="code", changed_paths=[],
    )
    assert not ok
    assert any("no self-approval" in r for r in reasons)


def test_approver_resolving_to_seat_human_is_self_approval():
    ok, reasons = chk.authority_satisfied(
        _policy(), author="bob-gh", seat="seat-alpha", approvers=["alice-gh", "bob-work-gh"],
        mutation_class="code", changed_paths=[],
    )
    assert not ok
    assert any("no self-approval" in r for r in reasons)
    assert any("bob-work-gh" in r for r in reasons)  # author's other login too


def test_crossarea_change_requires_owning_peer():
    ok, reasons = chk.authority_satisfied(
        _policy(), author="bob-gh", approvers=["alice-gh"],
        mutation_class="code", changed_paths=["runner/audit.py", "forge/merge.py"],
    )
    # alice covers runner/**, author bob covers his own forge/** -> ok
    assert ok, reasons


def test_authors_own_area_is_covered_by_authorship():
    ok, reasons = chk.authority_satisfied(
        _policy(), author="alice-gh", approvers=["bob-gh"],
        mutation_class="code", changed_paths=["runner/spend_gate.py"],
    )
    assert ok, reasons


# --- policy shape invariants -------------------------------------------------------
def test_privileged_quorum_below_two_rejected_by_schema():
    p = _policy()
    p["ratification_authority"]["quorum_by_tier"]["privileged"] = 1
    assert chk.CODE_SCHEMA in _codes(p)


def test_no_self_approval_false_rejected_by_schema():
    p = _policy()
    p["ratification_authority"]["no_self_approval"] = False
    assert chk.CODE_SCHEMA in _codes(p)


def test_non_governance_self_classification_rejected_by_schema():
    assert chk.CODE_SCHEMA in _codes(_policy(mutation_class="docs"))


def test_missing_area_configuration_rejected():
    p = _policy()
    p["ratification_authority"]["defer_to_codeowners"] = False
    p["ratification_authority"]["area_owners"] = {}
    assert chk.CODE_AREA_CONFIG in _codes(p)


def test_room_for_future_coordination_fields_is_left_open():
    # §9.9: unknown top-level blocks are allowed (the declared blocks stay strict).
    assert _codes(_policy(future_block={"anything": True})) == []


# --- the generalized plan_approved (the live forge-side enforcement) ----------------
_POLICY_SHA = "a" * 64
_REPO = "creator-engine/creator-engine"
_HEAD = "f" * 40


def _pr(author="alice-gh", run_id="run-1"):
    return {
        "user": {"login": author}, "head": {"sha": _HEAD},
        "body": f"plan PR\n\nce-run-id: {run_id}\nce-policy-sha: {_POLICY_SHA}\n",
    }


def _review(login, state="APPROVED", commit_id=_HEAD):
    return {"state": state, "commit_id": commit_id, "user": {"login": login}}


def _fake_runner(pr_obj, reviews):
    def run(argv, input_text=None):
        path = argv[-1]
        payload = reviews if path.endswith("/reviews") else pr_obj
        return subprocess.CompletedProcess(argv, 0, stdout=json.dumps(payload), stderr="")
    return run


def _query():
    return ApprovalQuery(repo=_REPO, pr_number=7, run_id="run-1", policy_sha=_POLICY_SHA)


def test_plan_approved_authority_privileged_needs_both_peers():
    runner = _fake_runner(_pr(author="seat-gamma"), [_review("bob-gh")])
    plan = plan_approved(
        _query(), seat_identity="seat-gamma", gh_runner=runner,
        authority=_policy(), mutation_class="governance",
        changed_paths=["docs/decisions/ADR-0002-x.md"],
    )
    assert plan is None  # one peer < privileged quorum 2


def test_plan_approved_authority_both_peers_resolves_plan():
    runner = _fake_runner(_pr(author="seat-gamma"),
                          [_review("alice-gh"), _review("bob-gh")])
    plan = plan_approved(
        _query(), seat_identity="seat-gamma", gh_runner=runner,
        authority=_policy(), mutation_class="governance",
        changed_paths=["docs/decisions/ADR-0002-x.md"],
    )
    assert plan is not None
    assert plan.approved_by == "alice-gh,bob-gh"


def test_plan_approved_authority_still_rejects_author_and_seat():
    # approver == author (same human via another login) and approver == seat
    # keep failing under the authority path: no_self_approval end-to-end.
    runner = _fake_runner(_pr(author="bob-gh"),
                          [_review("bob-work-gh"), _review("seat-beta")])
    plan = plan_approved(
        _query(), seat_identity="seat-beta", gh_runner=runner,
        authority=_policy(), mutation_class="code", changed_paths=["forge/x.py"],
    )
    assert plan is None


def test_plan_approved_authority_crossarea_requires_owner():
    runner = _fake_runner(_pr(author="bob-gh"), [_review("carol-gh")])
    plan = plan_approved(
        _query(), seat_identity="seat-x", gh_runner=runner,
        authority=_policy(), mutation_class="code",
        changed_paths=["runner/spend_gate.py"],
    )
    assert plan is None  # quorum met via carol, but alice's area is uncovered


def test_plan_approved_authority_unmapped_approver_fails_closed():
    runner = _fake_runner(_pr(author="bob-gh"), [_review("dora-unmapped")])
    plan = plan_approved(
        _query(), seat_identity="seat-x", gh_runner=runner,
        authority=_policy(), mutation_class="code", changed_paths=[],
    )
    assert plan is None  # an unresolved approver never counts toward quorum


def test_plan_approved_without_authority_is_byte_compatible():
    # the pre-A-C3 single-approver path is unchanged when no authority is passed.
    runner = _fake_runner(_pr(author="author-alice"), [_review("reviewer-bob")])
    plan = plan_approved(_query(), seat_identity="seat-x", gh_runner=runner)
    assert plan is not None and plan.approved_by == "reviewer-bob"


def test_plan_approved_authority_stale_reviews_do_not_count():
    runner = _fake_runner(
        _pr(author="seat-gamma"),
        [_review("alice-gh", commit_id="0" * 40), _review("bob-gh")],
    )
    plan = plan_approved(
        _query(), seat_identity="seat-gamma", gh_runner=runner,
        authority=_policy(), mutation_class="governance", changed_paths=[],
    )
    assert plan is None  # alice's approval is off-head -> only bob counts


def test_plan_approved_authority_changes_requested_supersedes_approval():
    runner = _fake_runner(
        _pr(author="seat-gamma"),
        [_review("alice-gh"), _review("bob-gh"),
         _review("alice-gh", state="CHANGES_REQUESTED")],
    )
    plan = plan_approved(
        _query(), seat_identity="seat-gamma", gh_runner=runner,
        authority=_policy(), mutation_class="governance", changed_paths=[],
    )
    assert plan is None  # alice's latest pinned review is not APPROVED
