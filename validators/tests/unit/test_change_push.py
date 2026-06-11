"""v3.1-G2a — unit tests for the forge-native branch-push primitive (``forge.change_push``).

Every git/network edge is faked through the ``spawn=`` seam: ZERO live git / network. The
gate's heart is the secret-hygiene proof — a sentinel token value appears in NO argv and NO
:class:`PushResult` bytes, lands ONLY in the authenticated child env's ``GH_TOKEN``, and the
push is plan-by-default, HTTPS-URL-constructed, and NEVER force.
"""
from __future__ import annotations

import subprocess

import pytest

from creator_engine_validator.forge import change_push
from creator_engine_validator.forge.change_push import PushRefused, push_change
from creator_engine_validator.forge.github_repo_config import ForgeConfigError
from creator_engine_validator.forge.scoped_token import ScopedToken

# A recognizable sentinel — if this string ever appears in an argv or a PushResult, hygiene broke.
SENTINEL = "ghs_SENTINELtoken_DEADBEEFcafef00d"
REPO = "creator-engine/creator-engine"
BRANCH = "v31-g2-forge-join"
LOCAL = "a" * 40
REMOTE = "b" * 40


def _token(value: str = SENTINEL) -> ScopedToken:
    return ScopedToken(
        run_id="run-x", repo=REPO, policy_sha="c" * 64, secret_name="forge_pr",
        permissions=(("contents", "write"), ("pull_requests", "write")),
        expires_at="2026-06-11T10:00:00Z", token_ref=f"{REPO}@x", value=value,
    )


class ScriptedGit:
    """A fake ``spawn`` seam: routes by argv, records every (argv, input, env) call."""

    def __init__(
        self, *, local_head=LOCAL, remote_head=None, is_ancestor=True,
        local_rc=0, ls_remote_rc=0, push_rc=0,
    ):
        self.local_head = local_head
        self.remote_head = remote_head
        self.is_ancestor = is_ancestor
        self.local_rc = local_rc
        self.ls_remote_rc = ls_remote_rc
        self.push_rc = push_rc
        self.calls: list[dict] = []

    def __call__(self, argv, input_text, env):
        argv = list(argv)
        self.calls.append({"argv": argv, "input": input_text, "env": dict(env)})
        if "rev-parse" in argv:
            return subprocess.CompletedProcess(argv, self.local_rc, stdout=self.local_head + "\n", stderr="")
        if "ls-remote" in argv:
            if self.ls_remote_rc != 0:
                return subprocess.CompletedProcess(argv, self.ls_remote_rc, stdout="", stderr="ls-remote boom")
            out = f"{self.remote_head}\trefs/heads/{BRANCH}\n" if self.remote_head else ""
            return subprocess.CompletedProcess(argv, 0, stdout=out, stderr="")
        if "merge-base" in argv:
            return subprocess.CompletedProcess(argv, 0 if self.is_ancestor else 1, stdout="", stderr="")
        if "push" in argv:
            return subprocess.CompletedProcess(argv, self.push_rc, stdout="", stderr="push boom" if self.push_rc else "")
        raise AssertionError(f"unexpected git argv: {argv}")  # pragma: no cover

    def argv_for(self, verb: str) -> list[str] | None:
        for c in self.calls:
            if verb in c["argv"]:
                return c["argv"]
        return None

    def env_for(self, verb: str) -> dict | None:
        for c in self.calls:
            if verb in c["argv"]:
                return c["env"]
        return None


# ---------------------------------------------------------------------------
# Plan-by-default
# ---------------------------------------------------------------------------

def test_plan_by_default_creates_plan_and_mutates_nothing():
    git = ScriptedGit(remote_head=None)  # branch not yet on the remote
    res = push_change(REPO, BRANCH, source_dir="/wt", token=_token(), spawn=git)
    assert res.changed is True and res.up_to_date is False
    assert res.applied is False and res.pushed is False
    assert res.remote_head is None and res.local_head == LOCAL
    assert git.argv_for("push") is None  # plan mode never pushes


def test_plan_idempotent_when_remote_equals_local():
    git = ScriptedGit(remote_head=LOCAL)
    res = push_change(REPO, BRANCH, source_dir="/wt", token=_token(), spawn=git)
    assert res.up_to_date is True and res.changed is False and res.pushed is False
    assert git.argv_for("push") is None


# ---------------------------------------------------------------------------
# apply=True
# ---------------------------------------------------------------------------

def test_apply_pushes_when_branch_is_new():
    git = ScriptedGit(remote_head=None)
    res = push_change(REPO, BRANCH, source_dir="/wt", token=_token(), apply=True, spawn=git)
    assert res.applied is True and res.pushed is True and res.changed is True
    push = git.argv_for("push")
    assert push is not None
    assert f"refs/heads/{BRANCH}:refs/heads/{BRANCH}" in push


def test_apply_idempotent_noop_when_up_to_date():
    git = ScriptedGit(remote_head=LOCAL)
    res = push_change(REPO, BRANCH, source_dir="/wt", token=_token(), apply=True, spawn=git)
    assert res.applied is True and res.pushed is False and res.up_to_date is True
    assert git.argv_for("push") is None  # nothing to push


def test_apply_fast_forward_update_pushes():
    git = ScriptedGit(remote_head=REMOTE, is_ancestor=True)  # remote is an ancestor of local
    res = push_change(REPO, BRANCH, source_dir="/wt", token=_token(), apply=True, spawn=git)
    assert res.pushed is True
    assert git.argv_for("push") is not None


# ---------------------------------------------------------------------------
# Never force — non-fast-forward is refused
# ---------------------------------------------------------------------------

def test_refuses_non_fast_forward_and_never_pushes():
    git = ScriptedGit(remote_head=REMOTE, is_ancestor=False)
    with pytest.raises(PushRefused):
        push_change(REPO, BRANCH, source_dir="/wt", token=_token(), apply=True, spawn=git)
    # the refusal happens BEFORE any push — never force-push
    assert git.argv_for("push") is None
    # and the argv NEVER carries a force flag anywhere
    for c in git.calls:
        assert "--force" not in c["argv"] and "--force-with-lease" not in c["argv"]


# ---------------------------------------------------------------------------
# The HTTPS URL is CONSTRUCTED — never the configured (SSH) origin
# ---------------------------------------------------------------------------

def test_https_remote_url_constructed_not_origin():
    git = ScriptedGit(remote_head=None)
    res = push_change(REPO, BRANCH, source_dir="/wt", token=_token(), apply=True, spawn=git)
    assert res.remote_url == f"https://github.com/{REPO}"
    for verb in ("ls-remote", "push"):
        argv = git.argv_for(verb)
        assert argv is not None
        assert f"https://github.com/{REPO}" in argv
        # never an SSH origin, never the bare word "origin"
        assert not any(a.startswith("git@") or a.startswith("ssh://") for a in argv)
        assert "origin" not in argv


# ---------------------------------------------------------------------------
# Refuse-before-side-effect
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("repo,branch", [("not-a-repo", BRANCH), (REPO, "")])
def test_refuses_malformed_request_before_any_git_call(repo, branch):
    git = ScriptedGit()
    with pytest.raises(PushRefused):
        push_change(repo, branch, source_dir="/wt", token=_token(), spawn=git)
    assert git.calls == []  # spawn never invoked


def test_refuses_credential_less_token_before_any_git_call():
    git = ScriptedGit()
    with pytest.raises(PushRefused):
        push_change(REPO, BRANCH, source_dir="/wt", token=_token(value=""), spawn=git)
    assert git.calls == []


def test_refuses_missing_local_branch():
    git = ScriptedGit(local_rc=1, local_head="")
    with pytest.raises(PushRefused):
        push_change(REPO, BRANCH, source_dir="/wt", token=_token(), spawn=git)
    assert git.argv_for("ls-remote") is None  # refused at local-head resolution


# ---------------------------------------------------------------------------
# Transport failures surface as ForgeConfigError
# ---------------------------------------------------------------------------

def test_ls_remote_failure_is_transport_error():
    git = ScriptedGit(ls_remote_rc=1)
    with pytest.raises(ForgeConfigError):
        push_change(REPO, BRANCH, source_dir="/wt", token=_token(), spawn=git)


def test_push_failure_is_transport_error():
    git = ScriptedGit(remote_head=None, push_rc=1)
    with pytest.raises(ForgeConfigError):
        push_change(REPO, BRANCH, source_dir="/wt", token=_token(), apply=True, spawn=git)


# ---------------------------------------------------------------------------
# Secret hygiene — the gate's heart
# ---------------------------------------------------------------------------

def test_token_value_appears_in_no_argv_across_plan_and_apply():
    for apply in (False, True):
        git = ScriptedGit(remote_head=None)
        push_change(REPO, BRANCH, source_dir="/wt", token=_token(), apply=apply, spawn=git)
        for c in git.calls:
            assert SENTINEL not in c["argv"], f"token leaked into argv: {c['argv']}"
            assert SENTINEL not in " ".join(c["argv"])


def test_token_value_appears_in_no_pushresult_bytes():
    git = ScriptedGit(remote_head=None)
    res = push_change(REPO, BRANCH, source_dir="/wt", token=_token(), apply=True, spawn=git)
    assert SENTINEL not in repr(res)
    assert SENTINEL not in str(res.to_dict())


def test_token_value_only_in_authenticated_call_env():
    git = ScriptedGit(remote_head=REMOTE, is_ancestor=True)
    push_change(REPO, BRANCH, source_dir="/wt", token=_token(), apply=True, spawn=git)
    # GH_TOKEN carries the value ONLY in the authenticated (ls-remote / push) call envs
    for verb in ("ls-remote", "push"):
        env = git.env_for(verb)
        assert env is not None and env.get("GH_TOKEN") == SENTINEL
    # local read-only calls (rev-parse / merge-base) carry NO credential
    for verb in ("rev-parse", "merge-base"):
        env = git.env_for(verb)
        assert env is not None and "GH_TOKEN" not in env


def test_authenticated_argv_routes_through_gh_credential_helper():
    git = ScriptedGit(remote_head=None)
    push_change(REPO, BRANCH, source_dir="/wt", token=_token(), apply=True, spawn=git)
    for verb in ("ls-remote", "push"):
        argv = git.argv_for(verb)
        assert "credential.helper=" in argv
        assert "credential.helper=!gh auth git-credential" in argv


def test_competing_auth_and_app_key_vars_scrubbed_from_child_env(monkeypatch):
    monkeypatch.setenv("GITHUB_TOKEN", "competing-ambient")
    monkeypatch.setenv("CE_FORGE_APP_PEM", "-----BEGIN PRIVATE KEY-----")
    monkeypatch.setenv("GH_DEBUG", "api")
    git = ScriptedGit(remote_head=None)
    push_change(REPO, BRANCH, source_dir="/wt", token=_token(), apply=True, spawn=git)
    env = git.env_for("push")
    assert "GITHUB_TOKEN" not in env  # competing ambient auth dropped
    assert "CE_FORGE_APP_PEM" not in env  # App-private-key var dropped
    assert "GH_DEBUG" not in env  # debug/redirect var dropped
    assert env.get("GH_TOKEN") == SENTINEL


def test_module_registers_no_check_and_imports_cleanly():
    # forge siblings perform no I/O on import and register no validator check.
    assert change_push._https_remote_url(REPO) == f"https://github.com/{REPO}"
