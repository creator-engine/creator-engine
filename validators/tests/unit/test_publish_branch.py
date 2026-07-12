"""Unit tests for the host-side ``ce publish-branch`` gate."""

from __future__ import annotations

import json
import subprocess

from creator_engine_validator import ce_cli
from creator_engine_validator.forge.publish_branch import SeatIdentityExpectation, publish_branch

REPO = "creator-engine/creator-engine"
BRANCH = "worker-a/publish-branch-gate"
LOCAL = "a" * 40
REMOTE = "b" * 40
AUTHOR_NAME = "ce-dev-1"
AUTHOR_EMAIL = "ce-dev-1@example.invalid"


class ScriptedGit:
    """Fake git runner for publish-branch; records argv/env and returns scripted facts."""

    def __init__(
        self,
        *,
        remote_head: str | None = None,
        is_ancestor: bool = True,
        push_rc: int = 0,
        status: str = "",
        author_name: str = AUTHOR_NAME,
        author_email: str = AUTHOR_EMAIL,
    ):
        self.remote_head = remote_head
        self.is_ancestor = is_ancestor
        self.push_rc = push_rc
        self.status = status
        self.author_name = author_name
        self.author_email = author_email
        self.calls: list[dict] = []
        self.pushed = False

    def __call__(self, argv, input_text, env):
        argv = list(argv)
        self.calls.append({"argv": argv, "input": input_text, "env": dict(env)})
        if "remote" in argv and "get-url" in argv:
            return subprocess.CompletedProcess(
                argv, 0, stdout=f"https://github.com/{REPO}.git\n", stderr=""
            )
        if "rev-parse" in argv:
            if argv[-1] == "HEAD":
                return subprocess.CompletedProcess(argv, 0, stdout=f"{LOCAL}\n", stderr="")
            if argv[-1] == f"refs/heads/{BRANCH}":
                return subprocess.CompletedProcess(argv, 0, stdout=f"{LOCAL}\n", stderr="")
        if "status" in argv:
            return subprocess.CompletedProcess(argv, 0, stdout=self.status, stderr="")
        if "show" in argv:
            out = "\x00".join([LOCAL, self.author_name, self.author_email, self.author_name, self.author_email])
            return subprocess.CompletedProcess(argv, 0, stdout=out + "\n", stderr="")
        if "ls-remote" in argv:
            head = LOCAL if self.pushed else self.remote_head
            out = f"{head}\trefs/heads/{BRANCH}\n" if head else ""
            return subprocess.CompletedProcess(argv, 0, stdout=out, stderr="")
        if "merge-base" in argv and "--is-ancestor" in argv:
            return subprocess.CompletedProcess(argv, 0 if self.is_ancestor else 1, stdout="", stderr="")
        if "push" in argv:
            self.pushed = self.push_rc == 0
            err = "non-fast-forward" if self.push_rc else ""
            return subprocess.CompletedProcess(argv, self.push_rc, stdout="", stderr=err)
        raise AssertionError(f"unexpected git argv: {argv}")  # pragma: no cover

    def argv_for(self, verb: str) -> list[str] | None:
        for call in self.calls:
            if verb in call["argv"]:
                return call["argv"]
        return None

    def env_for(self, verb: str) -> dict | None:
        for call in self.calls:
            if verb in call["argv"]:
                return call["env"]
        return None


def _expected(**overrides) -> SeatIdentityExpectation:
    data = {"author_email": AUTHOR_EMAIL}
    data.update(overrides)
    return SeatIdentityExpectation(**data)


def test_dry_run_verifies_new_branch_without_push():
    git = ScriptedGit(remote_head=None)

    result = publish_branch(
        BRANCH,
        repo=REPO,
        source_dir="/wt",
        expected_identity=_expected(),
        apply=False,
        spawn=git,
    )

    assert result.ok is True
    assert result.verified is True
    assert result.changed is True
    assert result.applied is False
    assert result.pushed is False
    assert git.argv_for("push") is None


def test_apply_pushes_fast_forward_or_new_branch_through_host_gh_credential_helper(monkeypatch):
    monkeypatch.delenv("GH_TOKEN", raising=False)
    git = ScriptedGit(remote_head=REMOTE, is_ancestor=True)

    result = publish_branch(
        BRANCH,
        repo=REPO,
        source_dir="/wt",
        expected_identity=_expected(),
        apply=True,
        spawn=git,
    )

    assert result.ok is True
    assert result.pushed is True
    push = git.argv_for("push")
    assert push is not None
    assert "credential.helper=" in push
    assert "credential.helper=!gh auth git-credential" in push
    assert f"refs/heads/{BRANCH}:refs/heads/{BRANCH}" in push
    assert "--force" not in push and "--force-with-lease" not in push
    assert git.env_for("push") is not None
    assert "GH_TOKEN" not in git.env_for("push")


def test_refuses_non_fast_forward_before_push():
    git = ScriptedGit(remote_head=REMOTE, is_ancestor=False)

    result = publish_branch(
        BRANCH,
        repo=REPO,
        source_dir="/wt",
        expected_identity=_expected(),
        apply=True,
        spawn=git,
    )

    assert result.ok is False
    assert result.refusal_reason == "non_fast_forward"
    assert result.pushed is False
    assert git.argv_for("push") is None


def test_refuses_head_identity_mismatch_before_remote_read_or_push():
    git = ScriptedGit(remote_head=None, author_email="intruder@example.invalid")

    result = publish_branch(
        BRANCH,
        repo=REPO,
        source_dir="/wt",
        expected_identity=_expected(),
        apply=True,
        spawn=git,
    )

    assert result.ok is False
    assert result.refusal_reason == "head_identity_mismatch"
    assert git.argv_for("ls-remote") is None
    assert git.argv_for("push") is None


def test_refuses_missing_identity_expectation_before_git_calls():
    git = ScriptedGit()

    result = publish_branch(
        BRANCH,
        repo=REPO,
        source_dir="/wt",
        expected_identity=SeatIdentityExpectation(),
        spawn=git,
    )

    assert result.refusal_reason == "missing_identity_expectation"
    assert git.calls == []


def test_cli_json_reports_machine_readable_refusal(monkeypatch, capsys):
    git = ScriptedGit(remote_head=REMOTE, is_ancestor=False)
    monkeypatch.setattr(ce_cli, "_make_publish_branch_runner", lambda: git)

    rc = ce_cli.main(
        [
            "publish-branch",
            BRANCH,
            "--repo",
            REPO,
            "--repo-root",
            "/wt",
            "--expect-author-email",
            AUTHOR_EMAIL,
            "--json",
        ]
    )

    payload = json.loads(capsys.readouterr().out)
    assert rc == 1
    assert payload["ok"] is False
    assert payload["refusal_reason"] == "non_fast_forward"
    assert payload["branch"] == BRANCH
