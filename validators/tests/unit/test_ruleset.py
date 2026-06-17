"""Unit tests for repo ruleset plan/apply operations."""
from __future__ import annotations

import json
import subprocess

import pytest

from creator_engine_validator.forge import (
    ForgeConfigError,
    RulesetBypassActor,
    RulesetPolicy,
    RulesetRefused,
    delete_ruleset,
    upsert_ruleset,
)

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
    assert "require_code_owner_review" not in params
    assert payload["bypass_actors"] == [
        {"actor_id": 4070181, "actor_type": "Integration", "bypass_mode": "pull_request"}
    ]


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
