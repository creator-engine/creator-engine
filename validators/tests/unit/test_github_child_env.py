"""Unit tests for the shared, pure GitHub child-environment policy."""
from __future__ import annotations

import subprocess

from creator_engine_validator.github_child_env import scoped_github_child_env
from creator_engine_validator import ticket_reconcile_feed
from creator_engine_validator.forge.credential_runner import authenticated_gh_runner
from creator_engine_validator.forge.scoped_token import ScopedToken


def test_policy_is_pure_and_scrubs_case_insensitively() -> None:
    parent = {
        "Gh_ToKeN": "ambient",
        "gItHuB_tOkEn": "competing",
        "Gh_HoSt": "untrusted.example",
        "Ce_App_PrIvAtE_KeY": "key-material",
        "CuStOm_SoUrCe": "source-secret",
        "CE_KEEP": "kept",
    }

    child = scoped_github_child_env(
        parent, "active-token", token_source_names=("custom_source",)
    )

    assert child == {"CE_KEEP": "kept", "GH_TOKEN": "active-token"}
    assert parent == {
        "Gh_ToKeN": "ambient",
        "gItHuB_tOkEn": "competing",
        "Gh_HoSt": "untrusted.example",
        "Ce_App_PrIvAtE_KeY": "key-material",
        "CuStOm_SoUrCe": "source-secret",
        "CE_KEEP": "kept",
    }


def test_reconciliation_and_credential_runner_have_identical_shared_outcome(
    monkeypatch,
) -> None:
    monkeypatch.setenv("gH_hOsT", "untrusted.example")
    monkeypatch.setenv("GiThUb_ToKeN", "ambient-token")
    monkeypatch.setenv("cE_aPp_PrIvAtE_kEy", "key-material")
    feed_calls: list[dict[str, str]] = []

    def feed_runner(argv, **kwargs):
        feed_calls.append(kwargs["env"])
        return subprocess.CompletedProcess(argv, 0, stdout="{}", stderr="")

    token = ScopedToken(
        run_id="run-1",
        repo="owner/repo",
        policy_sha="0" * 64,
        secret_name="forge-token",
        permissions=(("contents", "read"),),
        expires_at="2026-07-22T00:00:00Z",
        token_ref="owner/repo@2026-07-22T00:00:00Z",
        value="active-token",
    )
    credential_calls: list[dict[str, str]] = []

    def credential_spawn(argv, input_text, env):
        credential_calls.append(env)
        return subprocess.CompletedProcess(argv, 0, stdout="{}", stderr="")

    ticket_reconcile_feed._run_gh_json(
        ["gh", "api", "graphql"],
        runner=feed_runner,
        token="active-token",
        token_source_names=(),
    )
    authenticated_gh_runner(token, spawn=credential_spawn)(["gh", "api", "graphql"])

    assert feed_calls == credential_calls
