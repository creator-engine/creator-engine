"""Unit tests for the v3 G-3.4 forge-native credential value-injection seam.

``authenticated_gh_runner`` takes a JIT-minted ``ScopedToken`` and returns a ``GhRunner``
whose CHILD ``gh`` subprocess env carries the live token value (``GH_TOKEN``), so the forge
ops authenticate AS the scoped per-run credential. The secret lands in the child env ONLY —
never argv, never input_text, never logged, never persisted, never the parent ``os.environ``.
These tests inject a fake ``spawn`` capturing ``(argv, input_text, env)`` and perform ZERO
live ``gh`` / network / subprocess.
"""

import os
import socket
import subprocess

import pytest

from creator_engine_validator.forge import authenticated_gh_runner
from creator_engine_validator.forge.github_repo_config import ForgeConfigRefused
from creator_engine_validator.forge.scoped_token import ScopedToken

_SECRET = "ghs_SCOPED_SECRET"


def _token(value: str = _SECRET) -> ScopedToken:
    return ScopedToken(
        run_id="run-1",
        repo="o/n",
        policy_sha="0" * 64,
        secret_name="forge_pat",
        permissions=(("contents", "read"), ("pull_requests", "write")),
        expires_at="2026-06-04T16:00:00Z",
        token_ref="o/n@2026-06-04T16:00:00Z",
        value=value,
    )


def _fake_spawn(*, rc: int = 0, stdout: str = "{}", stderr: str = ""):
    """A spawn seam capturing every (argv, input_text, env); the sole transport in tests."""
    calls: list[dict] = []

    def spawn(argv, input_text, env):
        calls.append({"argv": list(argv), "input_text": input_text, "env": dict(env)})
        return subprocess.CompletedProcess(list(argv), rc, stdout=stdout, stderr=stderr)

    spawn.calls = calls  # type: ignore[attr-defined]
    return spawn


# ---------------------------------------------------------------------------
# Env-injection — the scoped token value reaches the child env as GH_TOKEN
# ---------------------------------------------------------------------------
def test_injects_scoped_token_into_child_env():
    spawn = _fake_spawn()
    runner = authenticated_gh_runner(_token(), spawn=spawn)
    runner(["gh", "api", "repos/o/n/pulls/1"])
    assert spawn.calls[0]["env"]["GH_TOKEN"] == _SECRET


# ---------------------------------------------------------------------------
# Secret hygiene (the core) — value in env ONLY, never argv / input_text
# ---------------------------------------------------------------------------
def test_value_never_in_argv_or_input():
    spawn = _fake_spawn()
    runner = authenticated_gh_runner(_token(), spawn=spawn)
    runner(["gh", "api", "repos/o/n/pulls/1"])  # bodyless
    runner(["gh", "api", "-X", "PUT", "repos/o/n/pulls/1/merge"], '{"merge_method":"squash"}')  # body
    assert len(spawn.calls) == 2
    for call in spawn.calls:
        assert all(_SECRET not in a for a in call["argv"]), "secret must never appear in argv"
        assert call["input_text"] is None or _SECRET not in call["input_text"]
        assert call["env"]["GH_TOKEN"] == _SECRET  # it IS in the env, and only the env


# ---------------------------------------------------------------------------
# Ambient auth — the scoped token wins; competing auth vars are neutralized
# ---------------------------------------------------------------------------
def test_scoped_token_wins_and_competing_auth_neutralized(monkeypatch):
    monkeypatch.setenv("GH_TOKEN", "ambient-default")
    monkeypatch.setenv("GITHUB_TOKEN", "ambient-competing")
    monkeypatch.setenv("GH_ENTERPRISE_TOKEN", "ambient-ghe")
    monkeypatch.setenv("GITHUB_ENTERPRISE_TOKEN", "ambient-ghe2")
    spawn = _fake_spawn()
    runner = authenticated_gh_runner(_token(), spawn=spawn)
    runner(["gh", "api", "x"])
    env = spawn.calls[0]["env"]
    assert env["GH_TOKEN"] == _SECRET  # scoped token overrides the ambient default
    assert "GITHUB_TOKEN" not in env
    assert "GH_ENTERPRISE_TOKEN" not in env
    assert "GITHUB_ENTERPRISE_TOKEN" not in env


# ---------------------------------------------------------------------------
# Child-env scrubber (G-3.7.0a) — debug/redirect/app-key host vars never reach the child
# ---------------------------------------------------------------------------
def test_scrubs_debug_redirect_and_appkey_vars_from_child_env(monkeypatch):
    # Host vars inherited from os.environ that could echo the token (GH_DEBUG), redirect the
    # Authorization header to a non-github host (GH_HOST / GITHUB_API_URL / GH_CONFIG_DIR), or
    # leak the App private key (any *_PEM / PRIVATE_KEY / APP_KEY var) must NEVER reach the child
    # gh env — even though they live in the parent environment.
    monkeypatch.setenv("GH_DEBUG", "api")
    monkeypatch.setenv("GH_HOST", "evil.example")
    monkeypatch.setenv("GITHUB_API_URL", "https://evil.example")
    monkeypatch.setenv("GH_CONFIG_DIR", "/tmp/evil")
    monkeypatch.setenv("CE_APP_PEM", "-----BEGIN RSA PRIVATE KEY-----\nMIIE\n-----END RSA PRIVATE KEY-----")
    monkeypatch.setenv("CE_GITHUB_APP_PRIVATE_KEY", "secret-key-material")
    monkeypatch.setenv("CE_KEEP_ME", "ok")  # an unrelated var must pass through unharmed
    spawn = _fake_spawn()
    runner = authenticated_gh_runner(_token(), spawn=spawn)
    runner(["gh", "api", "x"])
    env = spawn.calls[0]["env"]
    assert env["GH_TOKEN"] == _SECRET
    for scrubbed in (
        "GH_DEBUG",
        "GH_HOST",
        "GITHUB_API_URL",
        "GH_CONFIG_DIR",
        "CE_APP_PEM",
        "CE_GITHUB_APP_PRIVATE_KEY",
    ):
        assert scrubbed not in env, f"{scrubbed} must be scrubbed from the child gh env"
    assert env.get("CE_KEEP_ME") == "ok"  # unrelated vars preserved


# ---------------------------------------------------------------------------
# Child-only scope — the parent os.environ is never mutated
# ---------------------------------------------------------------------------
def test_parent_environ_not_mutated(monkeypatch):
    monkeypatch.setenv("GH_TOKEN", "ambient-default")
    monkeypatch.setenv("GITHUB_TOKEN", "ambient-competing")
    spawn = _fake_spawn()
    runner = authenticated_gh_runner(_token(), spawn=spawn)
    runner(["gh", "api", "x"])
    assert os.environ["GH_TOKEN"] == "ambient-default"  # parent untouched
    assert os.environ["GITHUB_TOKEN"] == "ambient-competing"


# ---------------------------------------------------------------------------
# No-leak — the value is not exposed via the runner's repr or any attribute
# ---------------------------------------------------------------------------
def test_value_not_leaked_in_repr_or_attribute():
    token = _token()
    runner = authenticated_gh_runner(token, spawn=_fake_spawn())
    assert _SECRET not in repr(runner)
    assert _SECRET not in repr(token)  # ScopedToken's own redaction still holds
    assert not hasattr(runner, "value")
    assert not hasattr(runner, "token")


# ---------------------------------------------------------------------------
# Passthrough — returns the spawn's CompletedProcess; forwards input_text
# ---------------------------------------------------------------------------
def test_passthrough_returns_completedprocess_and_forwards_input():
    spawn = _fake_spawn(rc=0, stdout='{"ok":true}')
    runner = authenticated_gh_runner(_token(), spawn=spawn)
    proc = runner(["gh", "api", "-X", "PUT", "repos/o/n/pulls/1/merge"], '{"merge_method":"squash"}')
    assert isinstance(proc, subprocess.CompletedProcess)
    assert proc.returncode == 0 and proc.stdout == '{"ok":true}'
    assert spawn.calls[0]["input_text"] == '{"merge_method":"squash"}'


# ---------------------------------------------------------------------------
# Build-time refusal — an empty token value refuses BEFORE any spawn
# ---------------------------------------------------------------------------
def test_refuses_empty_token_value_at_build():
    spawn = _fake_spawn()
    with pytest.raises(ForgeConfigRefused):
        authenticated_gh_runner(_token(value=""), spawn=spawn)
    assert spawn.calls == []  # refuse-before-side-effect: no spawn occurred


# ---------------------------------------------------------------------------
# Zero live transport — the injected fake spawn is the sole transport
# ---------------------------------------------------------------------------
def test_zero_live_subprocess_or_socket(monkeypatch):
    def explode(*args, **kwargs):  # pragma: no cover - must never run
        raise AssertionError("the authenticated runner must not touch a live subprocess/socket")

    monkeypatch.setattr(subprocess, "run", explode)
    monkeypatch.setattr(subprocess, "Popen", explode)
    monkeypatch.setattr(socket, "socket", explode)
    spawn = _fake_spawn()
    runner = authenticated_gh_runner(_token(), spawn=spawn)
    proc = runner(["gh", "api", "x"])
    assert proc.returncode == 0
    assert len(spawn.calls) == 1  # the injected fake was the only transport


# ---------------------------------------------------------------------------
# Purity regression — no new check, no backend delta
# ---------------------------------------------------------------------------
def test_purity_unchanged():
    from creator_engine_validator.checks import registered_checks
    from creator_engine_validator.runner.backend import available_backends

    assert len(registered_checks()) == 66  # G-6 added ce_scope; v3.5-C A-C1..A-C4 added decision_record + storage_tier_finding + peer_authority + forge_claim_dedup; v3.5-E.3 E3-G1 added install_answers; ce-ops#26 added seat_event; ce-ops#142 added ce_computer_use_authority_envelope; ce-ops#145 added ce_playbook_format; ce-ops#167 added ce_brain_assertions; ce-ops#163 added seat_class_policy; ce-ops#168 added work_sizing; ce-ops#164/#170 added work_sizing_floor; ce-ops#23 S1 added brownfield_baseline_attestation; ce-ops#177 added ce_brain_drift; ce-ops#185 added devops_privileged_action_broker; ce-ops#162 added operator_runbook_refusal_sync; ce-ops#244 added worker_tier_contract; ce-ops#260 added release_artifact_parity_guard; ce-ops#262 added pr_closes_linkage
    assert available_backends() == ("gvisor-proxy", "local-noop", "openshell", "os-native")  # +openshell (v3.5-A.2a)
