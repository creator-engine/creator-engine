"""Unit tests for the v3 forge adapter — ``configure_repo`` / ``install_required_checks`` (G-iii).

Drives ``creator_engine_validator.forge.github_repo_config`` directly through an
injected in-memory fake GitHub (``FakeGh``). Asserts:

* both operations are **plan-by-default** (``apply=False`` mutates nothing);
* both are **idempotent** (already-desired state → ``changed=False``, no write);
* drift is detected and, with ``apply=True``, applied then re-read to verify;
* required-context registration is **non-destructive** (unions, never drops);
* ``configure_repo`` PUTs the correct classic-protection body (code-owner
  reviews on, ``enforce_admins`` on, ``restrictions: null``);
* **no live network** — the only runner ever invoked is the injected fake;
* read failure raises ``ForgeConfigError``; a post-apply verify mismatch is reported.
"""
from __future__ import annotations

import json
import subprocess

import pytest

from creator_engine_validator.forge import github_repo_config as grc
from creator_engine_validator.forge.github_repo_config import (
    DEFAULT_MAIN_PROTECTION,
    BranchProtectionPolicy,
    ForgeConfigError,
    configure_repo,
    install_required_checks,
)

REPO = "creator-engine/creator-engine"


def _get_shape(
    *,
    contexts=("Validate governance artifacts",),
    strict=True,
    review_count=1,
    dismiss_stale=True,
    code_owner=True,
    last_push=True,
    linear=True,
    enforce_admins=True,
    conversation=True,
    force_pushes=False,
    deletions=False,
) -> dict:
    """A classic-protection GET body (the shape the GitHub API returns)."""
    return {
        "required_status_checks": {"strict": strict, "contexts": list(contexts)},
        "required_pull_request_reviews": {
            "dismiss_stale_reviews": dismiss_stale,
            "require_code_owner_reviews": code_owner,
            "required_approving_review_count": review_count,
            "require_last_push_approval": last_push,
        },
        "enforce_admins": {"enabled": enforce_admins},
        "required_linear_history": {"enabled": linear},
        "allow_force_pushes": {"enabled": force_pushes},
        "allow_deletions": {"enabled": deletions},
        "required_conversation_resolution": {"enabled": conversation},
    }


class FakeGh:
    """An in-memory fake GitHub branch-protection store with a ``gh api`` surface.

    Callable with the project's ``GhRunner`` signature ``(argv, input_text)``;
    records every call and serves GET/PUT/PATCH against a mutable ``protection``
    state so the read -> apply -> re-read -> verify loop is exercised for real.
    """

    def __init__(self, protection: dict | None):
        self.protection = protection
        self.calls: list[tuple[list[str], str | None]] = []

    # -- argv parsing --
    @staticmethod
    def _parse(argv):
        method = "GET"
        path = None
        i = 2  # skip "gh", "api"
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

    def __call__(self, argv, input_text=None) -> subprocess.CompletedProcess:
        self.calls.append((list(argv), input_text))
        method, path = self._parse(argv)
        body = json.loads(input_text) if input_text else None

        if path == f"repos/{REPO}/branches/main/protection":
            if method == "GET":
                if self.protection is None:
                    return subprocess.CompletedProcess(argv, 1, stdout="", stderr="Not Found")
                return subprocess.CompletedProcess(argv, 0, stdout=json.dumps(self.protection))
            if method == "PUT":
                self.protection = self._put_to_get(body)
                return subprocess.CompletedProcess(argv, 0, stdout=json.dumps(self.protection))

        if path == f"repos/{REPO}/branches/main/protection/required_status_checks":
            if self.protection is None:
                return subprocess.CompletedProcess(argv, 1, stdout="", stderr="Not Found")
            rsc = self.protection["required_status_checks"]
            if method == "GET":
                return subprocess.CompletedProcess(argv, 0, stdout=json.dumps(rsc))
            if method == "PATCH":
                rsc["strict"] = body["strict"]
                rsc["contexts"] = list(body["contexts"])
                return subprocess.CompletedProcess(argv, 0, stdout=json.dumps(rsc))

        return subprocess.CompletedProcess(argv, 1, stdout="", stderr=f"unexpected {method} {path}")

    @staticmethod
    def _put_to_get(put_body: dict) -> dict:
        rpr = put_body["required_pull_request_reviews"]
        return {
            "required_status_checks": dict(put_body["required_status_checks"]),
            "required_pull_request_reviews": dict(rpr),
            "enforce_admins": {"enabled": put_body["enforce_admins"]},
            "required_linear_history": {"enabled": put_body["required_linear_history"]},
            "allow_force_pushes": {"enabled": put_body["allow_force_pushes"]},
            "allow_deletions": {"enabled": put_body["allow_deletions"]},
            "required_conversation_resolution": {
                "enabled": put_body["required_conversation_resolution"]
            },
        }

    def methods(self) -> list[str]:
        return [self._parse(argv)[0] for argv, _ in self.calls]


# --------------------------------------------------------------------------
# Policy serialization
# --------------------------------------------------------------------------
def test_put_payload_shape_is_classic_protection():
    payload = DEFAULT_MAIN_PROTECTION.to_put_payload()
    assert payload["restrictions"] is None  # required by the classic PUT endpoint
    assert payload["enforce_admins"] is True
    assert payload["required_status_checks"] == {
        "strict": True,
        "contexts": ["Validate governance artifacts"],
    }
    rpr = payload["required_pull_request_reviews"]
    assert rpr["require_code_owner_reviews"] is True
    assert rpr["required_approving_review_count"] == 1
    assert rpr["require_last_push_approval"] is True


def test_with_contexts_unions_and_sorts():
    pol = BranchProtectionPolicy(required_status_check_contexts=("b",))
    merged = pol.with_contexts(["a", "b"])
    assert merged.required_status_check_contexts == ("a", "b")


# --------------------------------------------------------------------------
# install_required_checks
# --------------------------------------------------------------------------
def test_install_required_checks_idempotent_no_write():
    fake = FakeGh(_get_shape(contexts=("Validate governance artifacts",)))
    res = install_required_checks(
        REPO, ["Validate governance artifacts"], apply=True, gh_runner=fake
    )
    assert res.changed is False
    assert res.applied is False
    assert res.verified is True
    assert "PATCH" not in fake.methods()  # idempotent: never mutated


def test_install_required_checks_plan_only_does_not_mutate():
    fake = FakeGh(_get_shape(contexts=("Validate governance artifacts",)))
    res = install_required_checks(REPO, ["pytest"], apply=False, gh_runner=fake)
    assert res.changed is True
    assert res.applied is False
    assert res.after["contexts"] == ["Validate governance artifacts", "pytest"]
    assert "PATCH" not in fake.methods()


def test_install_required_checks_apply_unions_and_verifies():
    fake = FakeGh(_get_shape(contexts=("Validate governance artifacts",)))
    res = install_required_checks(REPO, ["pytest"], apply=True, gh_runner=fake)
    assert res.changed is True and res.applied is True and res.verified is True
    # the PATCH carried the non-destructive union, sorted
    patch_calls = [body for (argv, body) in fake.calls if "--method" in argv and "PATCH" in argv]
    assert patch_calls and json.loads(patch_calls[0])["contexts"] == [
        "Validate governance artifacts",
        "pytest",
    ]


def test_install_required_checks_read_failure_raises():
    fake = FakeGh(None)  # 404 -> read fails
    with pytest.raises(ForgeConfigError):
        install_required_checks(REPO, ["pytest"], apply=True, gh_runner=fake)


# --------------------------------------------------------------------------
# configure_repo
# --------------------------------------------------------------------------
def test_configure_repo_idempotent_when_already_desired():
    # current already matches DEFAULT_MAIN_PROTECTION's observation
    fake = FakeGh(_get_shape(code_owner=True))
    res = configure_repo(REPO, apply=True, gh_runner=fake)
    assert res.changed is False
    assert res.applied is False
    assert res.verified is True
    assert "PUT" not in fake.methods()


def test_configure_repo_plan_detects_code_owner_drift_without_writing():
    fake = FakeGh(_get_shape(code_owner=False))  # the real pre-G-iii state
    res = configure_repo(REPO, apply=False, gh_runner=fake)
    assert res.changed is True
    assert res.applied is False
    assert res.before["require_code_owner_reviews"] is False
    assert res.after["require_code_owner_reviews"] is True
    assert "PUT" not in fake.methods()
    assert any("require_code_owner_reviews" in line for line in res.actions)


def test_configure_repo_apply_puts_desired_and_verifies():
    fake = FakeGh(_get_shape(code_owner=False))
    res = configure_repo(REPO, apply=True, gh_runner=fake)
    assert res.changed is True and res.applied is True and res.verified is True
    put_bodies = [body for (argv, body) in fake.calls if "--method" in argv and "PUT" in argv]
    assert put_bodies, "expected a PUT to protection"
    payload = json.loads(put_bodies[0])
    assert payload["required_pull_request_reviews"]["require_code_owner_reviews"] is True
    assert payload["enforce_admins"] is True
    assert payload["restrictions"] is None
    # live state now matches the policy
    assert fake.protection["required_pull_request_reviews"]["require_code_owner_reviews"] is True


def test_configure_repo_is_non_destructive_about_existing_contexts():
    fake = FakeGh(_get_shape(contexts=("Validate governance artifacts", "extra-check"), code_owner=False))
    res = configure_repo(REPO, apply=True, gh_runner=fake)
    assert res.applied is True
    assert "extra-check" in res.after["contexts"]
    put_bodies = [body for (argv, body) in fake.calls if "--method" in argv and "PUT" in argv]
    assert "extra-check" in json.loads(put_bodies[0])["required_status_checks"]["contexts"]


def test_configure_repo_applies_to_unprotected_branch():
    fake = FakeGh(None)  # no protection yet -> 404 on read
    res = configure_repo(REPO, apply=True, gh_runner=fake)
    assert res.before == {}  # observed nothing
    assert res.changed is True and res.applied is True and res.verified is True
    assert fake.protection is not None


def test_configure_repo_reports_verify_mismatch():
    fake = FakeGh(_get_shape(code_owner=False))

    # A runner that applies the PUT but then lies on re-read (returns stale state).
    class LyingGh(FakeGh):
        def __call__(self, argv, input_text=None):
            out = super().__call__(argv, input_text)
            method, path = self._parse(argv)
            if method == "PUT":
                # roll the live state back so the verify re-read disagrees
                self.protection = _get_shape(code_owner=False)
            return out

    lying = LyingGh(_get_shape(code_owner=False))
    res = configure_repo(REPO, apply=True, gh_runner=lying)
    assert res.applied is True
    assert res.verified is False
    assert any("VERIFY MISMATCH" in line for line in res.actions)


# --------------------------------------------------------------------------
# G-3.7.0b — a leaked credential in gh stderr is masked in the raised exception
# --------------------------------------------------------------------------
_LEAK_TOKEN = "ghs_leak_secret_0123456789ABCDEFGHIJKLMNOP"
_LEAK_STDERR = f"HTTP 401: Bad credentials (token {_LEAK_TOKEN})"


class _TokenLeakingGh(FakeGh):
    """A FakeGh that fails the chosen HTTP method with a token-bearing stderr."""

    def __init__(self, protection, *, fail_method):
        super().__init__(protection)
        self._fail_method = fail_method

    def __call__(self, argv, input_text=None):
        method, _path = self._parse(argv)
        if method == self._fail_method:
            self.calls.append((list(argv), input_text))
            return subprocess.CompletedProcess(argv, 1, stdout="", stderr=_LEAK_STDERR)
        return super().__call__(argv, input_text)


def test_read_required_checks_error_redacts_leaked_token():
    fake = _TokenLeakingGh(_get_shape(contexts=("Validate governance artifacts",)), fail_method="GET")
    with pytest.raises(ForgeConfigError) as ei:
        install_required_checks(REPO, ["pytest"], apply=True, gh_runner=fake)
    msg = str(ei.value)
    assert _LEAK_TOKEN not in msg and "<redacted>" in msg


def test_patch_required_checks_error_redacts_leaked_token():
    fake = _TokenLeakingGh(_get_shape(contexts=("Validate governance artifacts",)), fail_method="PATCH")
    with pytest.raises(ForgeConfigError) as ei:
        install_required_checks(REPO, ["pytest"], apply=True, gh_runner=fake)
    msg = str(ei.value)
    assert _LEAK_TOKEN not in msg and "<redacted>" in msg


def test_put_protection_error_redacts_leaked_token():
    fake = _TokenLeakingGh(_get_shape(code_owner=False), fail_method="PUT")
    with pytest.raises(ForgeConfigError) as ei:
        configure_repo(REPO, apply=True, gh_runner=fake)
    msg = str(ei.value)
    assert _LEAK_TOKEN not in msg and "<redacted>" in msg


# --------------------------------------------------------------------------
# No live network
# --------------------------------------------------------------------------
def test_no_live_network_default_runner_never_invoked(monkeypatch):
    # If any code path fell through to the real subprocess runner, this explodes.
    def explode(*a, **k):  # pragma: no cover - must never run
        raise AssertionError("live subprocess invoked — forge adapter must use the injected runner")

    monkeypatch.setattr(grc.subprocess, "run", explode)
    fake = FakeGh(_get_shape(code_owner=False))
    configure_repo(REPO, apply=True, gh_runner=fake)
    install_required_checks(REPO, ["pytest"], apply=True, gh_runner=fake)
    assert fake.calls  # the injected runner did all the work
