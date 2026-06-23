"""Unit tests for repo ruleset plan/apply operations."""
from __future__ import annotations

import json
import subprocess

import pytest

from creator_engine_validator.forge import (
    CE_PROTECTION_RULESET_NAME,
    ForgeConfigError,
    RulesetBypassActor,
    RulesetPolicy,
    RulesetRefused,
    delete_ruleset,
    upsert_ruleset,
)
from creator_engine_validator.forge.ruleset import ruleset_satisfies_policy

REPO = "creator-engine/creator-engine"


def _policy() -> RulesetPolicy:
    return RulesetPolicy(
        name="ce-p1-devops",
        bypass_actors=(RulesetBypassActor(actor_id=4070181),),
    )


class FakeRulesetGh:
    def __init__(self, rulesets=None, *, fail_method=None, stderr="boom"):
        self.rulesets = list(rulesets or [])
        self.fail_method = fail_method
        self.stderr = stderr
        self.calls: list[tuple[list[str], str | None]] = []
        self.next_id = 100

    @staticmethod
    def _parse(argv):
        method = "GET"
        path = None
        i = 2
        while i < len(argv):
            tok = argv[i]
            if tok == "--method":
                method = argv[i + 1]
                i += 2
            elif tok == "--input":
                i += 2
            else:
                path = tok
                i += 1
        return method, path

    def __call__(self, argv, input_text=None):
        self.calls.append((list(argv), input_text))
        method, path = self._parse(argv)
        if method == self.fail_method:
            return subprocess.CompletedProcess(argv, 1, stdout="", stderr=self.stderr)
        body = json.loads(input_text) if input_text else None
        if path == f"repos/{REPO}/rulesets" and method == "GET":
            return subprocess.CompletedProcess(argv, 0, stdout=json.dumps(self.rulesets), stderr="")
        if path == f"repos/{REPO}/rulesets" and method == "POST":
            created = {"id": self.next_id, **body}
            self.rulesets.append(created)
            return subprocess.CompletedProcess(argv, 0, stdout=json.dumps(created), stderr="")
        if path and path.startswith(f"repos/{REPO}/rulesets/") and method == "PUT":
            rid = int(path.rsplit("/", 1)[1])
            updated = {"id": rid, **body}
            self.rulesets = [updated if r.get("id") == rid else r for r in self.rulesets]
            return subprocess.CompletedProcess(argv, 0, stdout=json.dumps(updated), stderr="")
        if path and path.startswith(f"repos/{REPO}/rulesets/") and method == "DELETE":
            rid = int(path.rsplit("/", 1)[1])
            self.rulesets = [r for r in self.rulesets if r.get("id") != rid]
            return subprocess.CompletedProcess(argv, 0, stdout="", stderr="")
        return subprocess.CompletedProcess(argv, 1, stdout="", stderr=f"unexpected {method} {path}")

    def methods(self):
        return [self._parse(argv)[0] for argv, _ in self.calls]

    def bodies(self, method):
        return [json.loads(body) for (argv, body) in self.calls if self._parse(argv)[0] == method]


def test_ruleset_payload_uses_required_review_count_without_code_owner_review():
    payload = _policy().to_put_payload()
    params = payload["rules"][0]["parameters"]
    assert params["required_approving_review_count"] == 1
    assert params["require_code_owner_review"] is False
    assert payload["bypass_actors"] == [
        {"actor_id": 4070181, "actor_type": "Integration", "bypass_mode": "pull_request"}
    ]


def test_reference_floor_ruleset_payload_has_required_check_strict_reviews_and_no_bypass():
    payload = RulesetPolicy(
        name=CE_PROTECTION_RULESET_NAME,
        required_status_check_contexts=("Validate governance artifacts",),
        required_approving_review_count=1,
        dismiss_stale_reviews_on_push=True,
        bypass_actors=(),
    ).to_put_payload()
    assert payload["bypass_actors"] == []
    status = next(rule for rule in payload["rules"] if rule["type"] == "required_status_checks")
    assert status["parameters"]["strict_required_status_checks_policy"] is True
    assert status["parameters"]["required_status_checks"] == [
        {"context": "Validate governance artifacts"}
    ]
    pull = next(rule for rule in payload["rules"] if rule["type"] == "pull_request")
    assert pull["parameters"]["required_approving_review_count"] == 1
    assert pull["parameters"]["dismiss_stale_reviews_on_push"] is True
    assert pull["parameters"]["require_code_owner_review"] is False


# --- creator-engine#368: rebase must NOT dismiss a standing approval -----------
#
# Root cause: the CE-emitted ``ce-reference-protection-floor`` ruleset carried
# GitHub's blunt ``dismiss_stale_reviews_on_push: true``, which wipes EVERY
# standing review on ANY head-changing push — including a pure mechanical rebase
# with no net content delta — and silently overrides branch-protection
# ``dismiss_stale_reviews=false`` (rulesets layer on top, most-restrictive wins).
# The fix: CE no longer emits the blunt flag by default; re-review-on-content-
# change is a CE-owned, diff-aware concern (forge.re_review / ce-ops#151).


def test_default_policy_does_not_emit_blanket_dismiss_on_push():
    """REGRESSION (creator-engine#368): the default ruleset must NOT carry GitHub's
    blunt ``dismiss_stale_reviews_on_push`` flag, so a head-changing push (incl. a
    pure rebase) does not wipe a standing approval via GitHub's non-diff-aware path."""
    pull = next(
        rule for rule in _policy().to_put_payload()["rules"] if rule["type"] == "pull_request"
    )
    assert pull["parameters"]["dismiss_stale_reviews_on_push"] is False


def test_default_ruleset_does_not_require_dismiss_on_a_live_floor():
    """A live ruleset with ``dismiss_stale_reviews_on_push: false`` (the rebase-safe
    posture) still SATISFIES the default policy — CE no longer mandates the blunt
    flag, so a mechanical-rebase push leaves the live approval standing."""
    policy = RulesetPolicy(
        name=CE_PROTECTION_RULESET_NAME,
        required_status_check_contexts=("Validate governance artifacts",),
        bypass_actors=(),
    )
    rebase_safe_live = {
        "target": "branch",
        "enforcement": "active",
        "conditions": {"ref_name": {"include": ["refs/heads/main"], "exclude": []}},
        "bypass_actors": [],
        "rules": [
            {
                "type": "required_status_checks",
                "parameters": {
                    "strict_required_status_checks_policy": True,
                    "required_status_checks": [{"context": "Validate governance artifacts"}],
                },
            },
            {
                "type": "pull_request",
                "parameters": {
                    "required_approving_review_count": 1,
                    "dismiss_stale_reviews_on_push": False,  # rebase-safe
                    "require_code_owner_review": False,
                    "require_last_push_approval": True,
                    "required_review_thread_resolution": True,
                    "allowed_merge_methods": ["squash"],
                },
            },
        ],
    }
    assert ruleset_satisfies_policy(rebase_safe_live, policy) is True


def test_explicit_dismiss_true_still_emits_blunt_flag_for_callers_that_want_it():
    """A caller may still OPT IN to GitHub's blunt dismissal by passing True —
    content-change re-review strictness is preserved for those who choose it."""
    pull = next(
        rule
        for rule in RulesetPolicy(
            name=CE_PROTECTION_RULESET_NAME, dismiss_stale_reviews_on_push=True
        ).to_put_payload()["rules"]
        if rule["type"] == "pull_request"
    )
    assert pull["parameters"]["dismiss_stale_reviews_on_push"] is True


def test_merge_queue_rule_absent_by_default():
    """A policy without merge-queue config emits no merge_queue rule (opt-in only)."""
    payload = _policy().to_put_payload()
    assert all(rule["type"] != "merge_queue" for rule in payload["rules"])


def test_merge_queue_rule_payload_shape():
    """require_merge_queue=True emits a GitHub merge_queue rule with the queue params."""
    payload = RulesetPolicy(
        name=CE_PROTECTION_RULESET_NAME,
        required_status_check_contexts=("Validate governance artifacts",),
        require_merge_queue=True,
        merge_queue_merge_method="SQUASH",
        merge_queue_max_entries_to_build=5,
        merge_queue_max_entries_to_merge=5,
        merge_queue_min_entries_to_merge=1,
        merge_queue_min_entries_to_merge_wait_minutes=5,
        merge_queue_grouping_strategy="ALLGREEN",
        merge_queue_check_response_timeout_minutes=60,
    ).to_put_payload()
    mq = next(rule for rule in payload["rules"] if rule["type"] == "merge_queue")
    params = mq["parameters"]
    assert params == {
        "merge_method": "SQUASH",
        "grouping_strategy": "ALLGREEN",
        "max_entries_to_build": 5,
        "max_entries_to_merge": 5,
        "min_entries_to_merge": 1,
        "min_entries_to_merge_wait_minutes": 5,
        "check_response_timeout_minutes": 60,
    }
    # The squash-only floor and the queue merge method must agree.
    pull = next(rule for rule in payload["rules"] if rule["type"] == "pull_request")
    assert pull["parameters"]["allowed_merge_methods"] == ["squash"]


def test_merge_queue_refuses_unknown_merge_method():
    policy = RulesetPolicy(
        name=CE_PROTECTION_RULESET_NAME,
        require_merge_queue=True,
        merge_queue_merge_method="FASTFORWARD",
    )
    with pytest.raises(RulesetRefused):
        policy.to_put_payload()


def test_merge_queue_refuses_grouping_strategy_other_than_allgreen_headgreen():
    policy = RulesetPolicy(
        name=CE_PROTECTION_RULESET_NAME,
        require_merge_queue=True,
        merge_queue_grouping_strategy="WHATEVER",
    )
    with pytest.raises(RulesetRefused):
        policy.to_put_payload()


def test_merge_queue_method_must_match_allowed_pull_methods():
    """A merge_queue method outside the policy's allowed PR merge methods is refused."""
    policy = RulesetPolicy(
        name=CE_PROTECTION_RULESET_NAME,
        allowed_merge_methods=("squash",),
        require_merge_queue=True,
        merge_queue_merge_method="MERGE",
    )
    with pytest.raises(RulesetRefused):
        policy.to_put_payload()


@pytest.mark.parametrize(
    "kwargs",
    [
        {"merge_queue_max_entries_to_build": 0},
        {"merge_queue_max_entries_to_merge": 0},
        {"merge_queue_min_entries_to_merge": 0},
        {"merge_queue_max_entries_to_build": 101},
        {"merge_queue_max_entries_to_merge": 101},
        {"merge_queue_min_entries_to_merge": 101},
        {"merge_queue_min_entries_to_merge": 6, "merge_queue_max_entries_to_merge": 5},
        {"merge_queue_min_entries_to_merge_wait_minutes": -1},
        {"merge_queue_min_entries_to_merge_wait_minutes": 361},
        {"merge_queue_check_response_timeout_minutes": 0},
        {"merge_queue_check_response_timeout_minutes": 361},
    ],
)
def test_merge_queue_refuses_impossible_limits_before_any_call(kwargs):
    """Impossible queue limits fail closed before a live upsert can call GitHub."""
    fake = FakeRulesetGh([])
    policy = RulesetPolicy(
        name=CE_PROTECTION_RULESET_NAME,
        require_merge_queue=True,
        **kwargs,
    )
    with pytest.raises(RulesetRefused):
        upsert_ruleset(REPO, policy, apply=True, gh_runner=fake)
    assert fake.calls == []


def test_merge_queue_satisfies_policy_round_trips():
    """A live ruleset built from the policy's own payload satisfies the policy."""
    policy = RulesetPolicy(
        name=CE_PROTECTION_RULESET_NAME,
        required_status_check_contexts=("Validate governance artifacts",),
        require_merge_queue=True,
    )
    live = {"id": 9, **policy.to_put_payload()}
    assert ruleset_satisfies_policy(live, policy) is True
    # A live ruleset missing the merge_queue rule does NOT satisfy a queue policy.
    no_queue = RulesetPolicy(
        name=CE_PROTECTION_RULESET_NAME,
        required_status_check_contexts=("Validate governance artifacts",),
    )
    live_no_queue = {"id": 9, **no_queue.to_put_payload()}
    assert ruleset_satisfies_policy(live_no_queue, policy) is False


@pytest.mark.parametrize(
    ("key", "value"),
    [
        ("merge_method", "MERGE"),
        ("grouping_strategy", "HEADGREEN"),
        ("max_entries_to_build", 4),
        ("max_entries_to_merge", 4),
        ("min_entries_to_merge", 2),
        ("min_entries_to_merge_wait_minutes", 6),
        ("check_response_timeout_minutes", 61),
    ],
)
def test_merge_queue_satisfies_policy_rejects_parameter_drift(key, value):
    """Live merge_queue params must match the policy, not only carry a queue rule."""
    policy = RulesetPolicy(
        name=CE_PROTECTION_RULESET_NAME,
        required_status_check_contexts=("Validate governance artifacts",),
        require_merge_queue=True,
    )
    live = {"id": 9, **policy.to_put_payload()}
    queue_rule = next(rule for rule in live["rules"] if rule["type"] == "merge_queue")
    queue_rule["parameters"][key] = value
    assert ruleset_satisfies_policy(live, policy) is False


def test_ruleset_plan_does_not_mutate():
    fake = FakeRulesetGh([])
    result = upsert_ruleset(REPO, _policy(), apply=False, gh_runner=fake)
    assert result.changed is True and result.applied is False
    assert fake.methods() == ["GET"]


def test_ruleset_apply_creates_and_verifies():
    fake = FakeRulesetGh([])
    result = upsert_ruleset(REPO, _policy(), apply=True, gh_runner=fake)
    assert result.changed is True and result.applied is True and result.verified is True
    assert fake.methods() == ["GET", "POST", "GET"]
    body = fake.bodies("POST")[0]
    assert body["bypass_actors"][0]["bypass_mode"] == "pull_request"
    assert body["rules"][0]["parameters"]["required_approving_review_count"] == 1


def test_ruleset_apply_updates_by_name():
    existing = {"id": 7, **RulesetPolicy(name="ce-p1-devops", branch="dev").to_put_payload()}
    fake = FakeRulesetGh([existing])
    result = upsert_ruleset(REPO, _policy(), apply=True, gh_runner=fake)
    assert result.ruleset_id == 7
    assert "PUT" in fake.methods()
    assert fake.bodies("PUT")[0]["conditions"]["ref_name"]["include"] == ["refs/heads/main"]


def test_ruleset_idempotent_no_write():
    existing = {"id": 7, **_policy().to_put_payload()}
    fake = FakeRulesetGh([existing])
    result = upsert_ruleset(REPO, _policy(), apply=True, gh_runner=fake)
    assert result.changed is False and result.verified is True
    assert fake.methods() == ["GET"]


def test_delete_ruleset_plan_and_apply():
    existing = {"id": 7, **_policy().to_put_payload()}
    fake = FakeRulesetGh([existing])
    plan = delete_ruleset(REPO, "ce-p1-devops", apply=False, gh_runner=fake)
    assert plan.changed is True and "DELETE" not in fake.methods()
    result = delete_ruleset(REPO, "ce-p1-devops", apply=True, gh_runner=fake)
    assert result.changed is True and result.verified is True
    assert "DELETE" in fake.methods()


def test_ruleset_refuses_always_bypass_before_any_call():
    fake = FakeRulesetGh([])
    policy = RulesetPolicy(
        name="ce-p1-devops",
        bypass_actors=(RulesetBypassActor(actor_id=4070181, bypass_mode="always"),),
    )
    with pytest.raises(RulesetRefused):
        upsert_ruleset(REPO, policy, apply=True, gh_runner=fake)
    assert fake.calls == []


def test_ruleset_refuses_non_repo_scope_before_any_call():
    fake = FakeRulesetGh([])
    with pytest.raises(RulesetRefused):
        upsert_ruleset("creator-engine", _policy(), apply=True, gh_runner=fake)
    assert fake.calls == []


def test_ruleset_transport_error_redacts_token():
    token = "ghs_leak_secret_0123456789ABCDEFGHIJKLMNOP"
    fake = FakeRulesetGh([], fail_method="GET", stderr=f"Authorization: Bearer {token}")
    with pytest.raises(ForgeConfigError) as ei:
        upsert_ruleset(REPO, _policy(), apply=True, gh_runner=fake)
    assert token not in str(ei.value)
    assert "<redacted>" in str(ei.value)
