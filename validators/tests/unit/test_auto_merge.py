"""Unit tests for per-PR GraphQL auto-merge enablement."""
from __future__ import annotations

import json
import socket
import subprocess
from dataclasses import fields

import pytest

from creator_engine_validator.forge import (
    AutoMergeRefused,
    ChangeRef,
    ForgeConfigError,
    enable_auto_merge,
)

REPO = "creator-engine/creator-engine"
HEAD = "d" * 40


def _change(**overrides) -> ChangeRef:
    base = dict(
        repo=REPO,
        branch="ce/run-1",
        base="main",
        pr_number=7,
        head_sha=HEAD,
        manifest_paths=("x.py",),
        plan_ref="a" * 64,
        changed=True,
        applied=True,
        verified=True,
    )
    base.update(overrides)
    return ChangeRef(**base)


class FakeAutoMergeGh:
    def __init__(self, *, enabled=False, method="SQUASH", rc=0, stderr="boom"):
        self.enabled = enabled
        self.method = method
        self.rc = rc
        self.stderr = stderr
        self.calls: list[list[str]] = []

    def __call__(self, argv, input_text=None):
        self.calls.append(list(argv))
        query = next((str(a) for a in argv if str(a).startswith("query=")), "")
        if self.rc != 0:
            return subprocess.CompletedProcess(argv, self.rc, stdout="", stderr=self.stderr)
        if "enablePullRequestAutoMerge" in query:
            self.enabled = True
            merge_method = next(str(a).split("=", 1)[1] for a in argv if str(a).startswith("mergeMethod="))
            self.method = merge_method
            payload = {"data": {"enablePullRequestAutoMerge": {
                "pullRequest": {"autoMergeRequest": {"enabledAt": "now", "mergeMethod": merge_method}}
            }}}
            return subprocess.CompletedProcess(argv, 0, stdout=json.dumps(payload), stderr="")
        auto = {"enabledAt": "then", "mergeMethod": self.method} if self.enabled else None
        payload = {"data": {"repository": {"pullRequest": {"id": "PR_kwDO", "autoMergeRequest": auto}}}}
        return subprocess.CompletedProcess(argv, 0, stdout=json.dumps(payload), stderr="")

    def mutation_calls(self):
        return [c for c in self.calls if any("enablePullRequestAutoMerge" in str(a) for a in c)]


def test_auto_merge_plan_reads_node_id_without_mutation():
    fake = FakeAutoMergeGh()
    result = enable_auto_merge(_change(), apply=False, gh_runner=fake)
    assert result.changed is True
    assert result.applied is False
    assert result.pull_request_id == "PR_kwDO"
    assert fake.mutation_calls() == []


def test_auto_merge_refuses_sec7_governed_context_before_call():
    fake = FakeAutoMergeGh()
    with pytest.raises(AutoMergeRefused) as ei:
        enable_auto_merge(_change(), apply=True, gh_runner=fake, sec7_context={"posture": "governed"})
    assert "§7 governed-seat context" in str(ei.value)
    assert fake.calls == []


def test_auto_merge_allows_non_governed_context():
    fake = FakeAutoMergeGh()
    result = enable_auto_merge(_change(), apply=True, gh_runner=fake, sec7_context={"posture": "ungoverned"})
    assert result.enabled is True
    assert fake.calls


def test_auto_merge_apply_mutates_exact_node_and_method():
    fake = FakeAutoMergeGh()
    result = enable_auto_merge(_change(), apply=True, gh_runner=fake)
    assert result.applied is True and result.enabled is True
    mutations = fake.mutation_calls()
    assert len(mutations) == 1
    assert "pullRequestId=PR_kwDO" in mutations[0]
    assert "mergeMethod=SQUASH" in mutations[0]


def test_auto_merge_idempotent_when_already_enabled():
    fake = FakeAutoMergeGh(enabled=True, method="SQUASH")
    result = enable_auto_merge(_change(), apply=True, gh_runner=fake)
    assert result.changed is False
    assert result.enabled is True
    assert fake.mutation_calls() == []


def test_auto_merge_refuses_malformed_change_before_call():
    fake = FakeAutoMergeGh()
    with pytest.raises(AutoMergeRefused):
        enable_auto_merge(_change(repo="not-a-repo"), apply=True, gh_runner=fake)
    assert fake.calls == []


def test_auto_merge_transport_error_redacts_token():
    token = "ghs_leak_secret_0123456789ABCDEFGHIJKLMNOP"
    fake = FakeAutoMergeGh(rc=1, stderr=f"token {token}")
    with pytest.raises(ForgeConfigError) as ei:
        enable_auto_merge(_change(), apply=True, gh_runner=fake)
    assert token not in str(ei.value)
    assert "<redacted>" in str(ei.value)


def test_auto_merge_result_carries_no_secret():
    result = enable_auto_merge(_change(), gh_runner=FakeAutoMergeGh())
    names = {f.name for f in fields(result)}
    assert "token" not in names and "value" not in names


def test_auto_merge_zero_live(monkeypatch):
    def explode(*a, **k):  # pragma: no cover
        raise AssertionError("auto_merge must use injected fake runner")

    monkeypatch.setattr(subprocess, "run", explode)
    monkeypatch.setattr(socket, "socket", explode)
    result = enable_auto_merge(_change(), apply=True, gh_runner=FakeAutoMergeGh())
    assert result.enabled is True
