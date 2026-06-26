"""Unit tests for independent App review submission."""
from __future__ import annotations

import json
import socket
import subprocess
from dataclasses import fields
from pathlib import Path

import pytest
import yaml

from creator_engine_validator import v3_forge_join
from creator_engine_validator.forge import (
    ChangeRef,
    ForgeConfigError,
    ReviewSubmitRefused,
    submit_review,
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


class FakeReviewGh:
    def __init__(self, *, rc=0, stderr="boom"):
        self.rc = rc
        self.stderr = stderr
        self.calls: list[tuple[list[str], str | None]] = []

    def __call__(self, argv, input_text=None):
        self.calls.append((list(argv), input_text))
        if self.rc != 0:
            return subprocess.CompletedProcess(argv, self.rc, stdout="", stderr=self.stderr)
        return subprocess.CompletedProcess(argv, 0, stdout=json.dumps({"id": 123}), stderr="")


def test_review_submit_plan_does_not_post():
    fake = FakeReviewGh()
    result = submit_review(_change(), apply=False, gh_runner=fake)
    assert result.changed is True
    assert result.applied is False
    assert fake.calls == []


def test_review_submit_refuses_sec7_governed_context_before_call():
    fake = FakeReviewGh()
    with pytest.raises(ReviewSubmitRefused) as ei:
        submit_review(_change(), apply=True, gh_runner=fake, sec7_context={"posture": "governed"})
    assert "§7 governed-seat context" in str(ei.value)
    assert fake.calls == []


def test_review_submit_allows_non_governed_context():
    fake = FakeReviewGh()
    result = submit_review(_change(), apply=True, gh_runner=fake, sec7_context={"posture": "ungoverned"})
    assert result.applied is True
    assert fake.calls


def test_review_submit_apply_posts_approve_with_commit_id():
    fake = FakeReviewGh()
    result = submit_review(_change(), apply=True, body="LGTM", gh_runner=fake)
    assert result.applied is True and result.review_id == 123
    argv, body = fake.calls[0]
    assert argv[:5] == ["gh", "api", "-X", "POST", f"repos/{REPO}/pulls/7/reviews"]
    assert json.loads(body) == {"event": "APPROVE", "commit_id": HEAD, "body": "LGTM"}


def test_review_submit_self_approve_422_fails_closed():
    fake = FakeReviewGh(rc=1, stderr="HTTP 422: Can not approve your own pull request")
    with pytest.raises(ForgeConfigError) as ei:
        submit_review(_change(), apply=True, gh_runner=fake)
    assert "422" in str(ei.value)


def test_review_submit_refuses_malformed_before_call():
    fake = FakeReviewGh()
    with pytest.raises(ReviewSubmitRefused):
        submit_review(_change(pr_number=None), apply=True, gh_runner=fake)
    assert fake.calls == []


def test_review_submit_error_redacts_token():
    token = "ghs_leak_secret_0123456789ABCDEFGHIJKLMNOP"
    fake = FakeReviewGh(rc=1, stderr=f"Authorization: Bearer {token}")
    with pytest.raises(ForgeConfigError) as ei:
        submit_review(_change(), apply=True, gh_runner=fake)
    assert token not in str(ei.value)
    assert "<redacted>" in str(ei.value)


def test_review_result_carries_no_secret():
    result = submit_review(_change(), gh_runner=FakeReviewGh())
    names = {f.name for f in fields(result)}
    assert "token" not in names and "value" not in names


def test_review_submit_zero_live(monkeypatch):
    def explode(*a, **k):  # pragma: no cover
        raise AssertionError("review_submit must use injected fake runner")

    monkeypatch.setattr(subprocess, "run", explode)
    monkeypatch.setattr(socket, "socket", explode)
    result = submit_review(_change(), apply=True, gh_runner=FakeReviewGh())
    assert result.applied is True


def _stage_dispatch(root: Path) -> None:
    ddir = root / "dispatches" / "run-1"
    ddir.mkdir(parents=True)
    (ddir / "dispatch.yaml").write_text(yaml.safe_dump({
        "scope_id": "scope-1",
        "spawned_at": "2026-06-16T00:00:00Z",
        "change": {
            "branch": "ce/run-1",
            "base": "main",
            "pr_number": 7,
            "head_sha": HEAD,
            "manifest_paths": ["x.py"],
        },
    }), encoding="utf-8")


def test_submit_review_for_run_mints_reviewer_pull_requests_only(tmp_path):
    _stage_dispatch(tmp_path)
    mint_calls: list[dict] = []
    spawned: list[tuple[list[str], dict[str, str]]] = []

    def mint_runner(argv, input_text=None):
        mint_calls.append(json.loads(input_text))
        payload = {"token": "ghs_review_secret", "expires_at": "2026-06-16T01:00:00Z"}
        return subprocess.CompletedProcess(argv, 0, stdout=json.dumps(payload), stderr="")

    def token_spawn(argv, input_text, env):
        spawned.append((list(argv), dict(env)))
        if "DELETE" in argv:
            return subprocess.CompletedProcess(argv, 0, stdout="", stderr="")
        return subprocess.CompletedProcess(argv, 0, stdout=json.dumps({"id": 321}), stderr="")

    cfg = v3_forge_join.AppConfig("client", 42, "/pem", REPO, ())
    result = v3_forge_join.submit_review_for_run(
        tmp_path,
        "run-1",
        reviewer_app_config=cfg,
        apply=True,
        mint_gh_runner=mint_runner,
        token_spawn=token_spawn,
    )
    assert result.review_id == 321
    assert mint_calls[0]["permissions"] == {"pull_requests": "write"}
    assert "contents" not in mint_calls[0]["permissions"]
    assert v3_forge_join.REVIEWER_TOKEN_ESCALATION_AUTHORITY == ()
    assert spawned[0][1]["GH_TOKEN"] == "ghs_review_secret"
