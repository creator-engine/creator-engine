import json
import logging
import subprocess

import pytest

import ce_egress_self_review_broker as broker
from creator_engine_validator.forge.scoped_token import ScopedToken, TokenRequest
from egress_broker.config import load_broker_config

_REPO = "creator-engine/creator-engine"
_HEAD = "a" * 40
_SECRET = "ghs_abcdefghijklmnopqrstuvwxyz1234567890"

# The seat in ``_config`` posts AS ``cedev4vps-coder`` (its App owner). A
# distinct PR author keeps the author≠reviewer guard satisfied for the
# happy-path tests; the guard-specific tests below override this.
_OTHER_AUTHOR = "some-other-author"


def _author(login=_OTHER_AUTHOR):
    """Injectable author resolver: no live ``gh api`` call in unit tests."""
    return lambda repo, pr_number: login


def _config():
    return load_broker_config(
        {
            "repo": _REPO,
            "installation_owner": "creator-engine",
            "audit_log": "",
            "policy": {
                "base_branch": "main",
                "allowed_branch_namespaces": ["ce-"],
                "forbidden_branches": [],
                "authorized_emails": [],
                "authorized_logins": ["cedev4vps-coder"],
                "max_pushes_per_window": 10,
                "window_seconds": 3600,
            },
            "seats": {
                "seat-reviewer-1": {
                    "app_id": "4085526",
                    "app_owner": "cedev4vps-coder",
                    "pem_path": "/dev/shm/ce-dev4/ce-forge-dev4.pem",
                    "installation_id": 123,
                }
            },
        }
    )


def _request(event="COMMENT", body="Looks reasonable."):
    return broker.SelfReviewRequest(
        seat_id="seat-reviewer-1",
        pr_number=7,
        head_sha=_HEAD,
        event=event,
        body=body,
    )


def _token(value=_SECRET):
    return ScopedToken(
        run_id="self-review-run",
        repo=_REPO,
        policy_sha="0" * 64,
        secret_name="forge_self_review",
        permissions=(("metadata", "read"), ("pull_requests", "write")),
        expires_at="2026-06-25T12:00:00Z",
        token_ref="creator-engine/creator-engine@self-review",
        value=value,
    )


def test_comment_review_mints_and_injects_token_only_into_gh_env(caplog):
    minted: list[TokenRequest] = []
    spawned: list[tuple[list[str], str | None, dict[str, str]]] = []

    def mint(req: TokenRequest):
        minted.append(req)
        return _token()

    def spawn(argv, input_text, env):
        spawned.append((list(argv), input_text, dict(env)))
        return subprocess.CompletedProcess(argv, 0, stdout=json.dumps({"id": 987}), stderr="")

    caplog.set_level(logging.INFO, logger="ce-egress-self-review")
    result = broker.submit_self_review(
        _request(),
        config=_config(),
        resolve_id_fn=lambda seat: 123,
        mint_fn=mint,
        gh_spawn=spawn,
        resolve_author_fn=_author(),
    )

    assert result.to_dict() == {
        "ok": True,
        "repo": _REPO,
        "pr_number": 7,
        "head_sha": _HEAD,
        "event": "COMMENT",
        "review_id": 987,
        "applied": True,
    }
    assert minted[0].repo == _REPO
    assert minted[0].permissions == broker.REVIEW_PERMISSIONS
    assert minted[0].requested_ttl_seconds == broker.REVIEW_TTL_SECONDS

    argv, input_text, child_env = spawned[0]
    assert argv == ["gh", "api", "-X", "POST", f"repos/{_REPO}/pulls/7/reviews", "--input", "-"]
    assert json.loads(input_text or "") == {
        "body": "Looks reasonable.",
        "commit_id": _HEAD,
        "event": "COMMENT",
    }
    assert child_env["GH_TOKEN"] == _SECRET

    evidence = (
        json.dumps(result.to_dict(), sort_keys=True)
        + repr(argv)
        + (input_text or "")
        + caplog.text
    )
    assert _SECRET not in evidence
    assert "GH_TOKEN" not in evidence


def test_request_changes_review_uses_same_review_api_shape():
    spawned: list[tuple[list[str], str | None, dict[str, str]]] = []

    def spawn(argv, input_text, env):
        spawned.append((list(argv), input_text, dict(env)))
        return subprocess.CompletedProcess(argv, 0, stdout=json.dumps({"id": 988}), stderr="")

    result = broker.submit_self_review(
        _request(event="REQUEST_CHANGES", body="Please fix the failing path."),
        config=_config(),
        resolve_id_fn=lambda seat: 123,
        mint_fn=lambda req: _token(),
        gh_spawn=spawn,
        resolve_author_fn=_author(),
    )

    assert result.event == "REQUEST_CHANGES"
    argv, input_text, _env = spawned[0]
    assert argv == ["gh", "api", "-X", "POST", f"repos/{_REPO}/pulls/7/reviews", "--input", "-"]
    assert json.loads(input_text or "")["event"] == "REQUEST_CHANGES"


def test_approve_is_refused_before_resolve_mint_or_transport():
    called = {"resolve": 0, "mint": 0, "spawn": 0}

    with pytest.raises(broker.SelfReviewRefused) as exc:
        broker.submit_self_review(
            _request(event="APPROVE"),
            config=_config(),
            resolve_id_fn=lambda seat: called.__setitem__("resolve", called["resolve"] + 1),
            mint_fn=lambda req: called.__setitem__("mint", called["mint"] + 1),
            gh_spawn=lambda *args: called.__setitem__("spawn", called["spawn"] + 1),
        )

    assert "COMMENT or REQUEST_CHANGES" in str(exc.value)
    assert called == {"resolve": 0, "mint": 0, "spawn": 0}


def test_author_is_refused_before_resolve_mint_or_transport():
    # The seat posts AS ``cedev4vps-coder`` (its App owner). If the PR author
    # resolves to that same login, the seat is reviewing its own PR — refused
    # for COMMENT/REQUEST_CHANGES, before any installation/credential mint or
    # source-host write (parity with the APPROVE refusal).
    called = {"resolve": 0, "mint": 0, "spawn": 0}

    with pytest.raises(broker.SelfReviewRefused) as exc:
        broker.submit_self_review(
            _request(),
            config=_config(),
            resolve_id_fn=lambda seat: called.__setitem__("resolve", called["resolve"] + 1),
            mint_fn=lambda req: called.__setitem__("mint", called["mint"] + 1),
            gh_spawn=lambda *args: called.__setitem__("spawn", called["spawn"] + 1),
            resolve_author_fn=_author("cedev4vps-coder"),
        )

    assert "author≠reviewer" in str(exc.value)
    assert called == {"resolve": 0, "mint": 0, "spawn": 0}


def test_unresolvable_author_fails_closed_before_resolve_mint_or_transport():
    # Author resolution failure (network/API error) must REFUSE, never post.
    called = {"resolve": 0, "mint": 0, "spawn": 0}

    def boom(repo, pr_number):
        raise broker.SelfReviewRefused(
            f"could not resolve PR author for {repo}#{pr_number}; refusing fail-closed"
        )

    with pytest.raises(broker.SelfReviewRefused) as exc:
        broker.submit_self_review(
            _request(),
            config=_config(),
            resolve_id_fn=lambda seat: called.__setitem__("resolve", called["resolve"] + 1),
            mint_fn=lambda req: called.__setitem__("mint", called["mint"] + 1),
            gh_spawn=lambda *args: called.__setitem__("spawn", called["spawn"] + 1),
            resolve_author_fn=boom,
        )

    assert "refusing fail-closed" in str(exc.value)
    assert called == {"resolve": 0, "mint": 0, "spawn": 0}


def test_parse_request_refuses_approve_before_core_call():
    with pytest.raises(broker.SelfReviewRefused) as exc:
        broker.parse_request(
            {
                "seat_id": "seat-reviewer-1",
                "pr_number": 7,
                "head_sha": _HEAD,
                "event": "APPROVE",
                "body": "not gate-valid",
            }
        )
    assert "APPROVE is controller approval-wall only" in str(exc.value)


def test_missing_injected_credential_fails_closed_before_gh_spawn():
    spawned: list[object] = []

    with pytest.raises(broker.SelfReviewRefused) as exc:
        broker.submit_self_review(
            _request(),
            config=_config(),
            resolve_id_fn=lambda seat: 123,
            mint_fn=lambda req: _token(value=""),
            gh_spawn=lambda *args: spawned.append(args),
            resolve_author_fn=_author(),
        )

    assert spawned == []
    assert "refused before forge side effect" in str(exc.value)


def test_secret_redacted_from_failed_gh_stderr_and_response():
    def spawn(argv, input_text, env):
        return subprocess.CompletedProcess(
            argv,
            1,
            stdout="",
            stderr=f"gh failed with bearer {_SECRET}",
        )

    with pytest.raises(broker.SelfReviewRefused) as exc:
        broker.submit_self_review(
            _request(),
            config=_config(),
            resolve_id_fn=lambda seat: 123,
            mint_fn=lambda req: _token(),
            gh_spawn=spawn,
            resolve_author_fn=_author(),
        )

    assert _SECRET not in str(exc.value)
    response = {"ok": False, "error": str(exc.value)}
    assert _SECRET not in json.dumps(response)


def test_bounded_json_request_refuses_oversize_and_non_object():
    with pytest.raises(broker.SelfReviewRefused):
        broker.bounded_json_load(b'{"x":"' + b"a" * 20 + b'"}', max_bytes=8)
    with pytest.raises(broker.SelfReviewRefused):
        broker.bounded_json_load(b'["not", "object"]', max_bytes=100)
