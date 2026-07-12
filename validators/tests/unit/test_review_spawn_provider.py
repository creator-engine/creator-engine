import json
from concurrent.futures import ThreadPoolExecutor

import pytest

from creator_engine_validator.forge import review_spawn_provider as provider


def _payload(**overrides):
    payload = {"version": 1, "request_id": "nonce-1", "repo": "owner/repo", "pr_number": 7,
               "head_sha": "a" * 40, "base_sha": "b" * 40,
               "carrier": {"path_count": 3, "sha256": "c" * 64},
               "author": "author", "reviewer": "reviewer"}
    payload.update(overrides)
    return payload


def _response(request, **overrides):
    value = {"version": 1, "request_id": request.request_id, "repo": request.repo,
             "pr_number": request.pr_number, "head_sha": request.head_sha,
             "author": request.author, "reviewer": request.reviewer, "verdict": "COMMENT",
             "summary": "bounded", "findings": [{"path": "x.py", "line": 1, "detail": "detail"}]}
    value.update(overrides)
    return (json.dumps(value) + "\n").encode()


def test_policy_is_default_off_and_parameterized():
    assert provider.ProviderPolicy.from_env({}).capacity == 0
    assert provider.ProviderPolicy.from_env({"CE_REVIEW_SPAWN_CAPACITY": "2", "CE_REVIEW_SPAWN_TIMEOUT_SECONDS": "30", "CE_REVIEW_SPAWN_RETENTION_SECONDS": "4"}).capacity == 2


def test_request_and_response_bind_every_immutable_identity():
    request = provider.parse_request(_payload())
    result = provider.parse_response(_response(request), request)
    assert result.verdict == "COMMENT"
    with pytest.raises(provider.ProviderRefused):
        provider.parse_response(_response(request, head_sha="d" * 40), request)


@pytest.mark.parametrize("payload", [{"version": 1}, _payload(author="reviewer"), _payload(head_sha="not-sha")])
def test_invalid_request_refuses(payload):
    with pytest.raises(provider.ProviderRefused):
        provider.parse_request(payload)


def test_response_refuses_approve_extra_json_and_bad_path():
    request = provider.parse_request(_payload())
    with pytest.raises(provider.ProviderRefused):
        provider.parse_response(_response(request, verdict="APPROVE"), request)
    with pytest.raises(provider.ProviderRefused):
        provider.parse_response(_response(request) + b"{}\n", request)
    with pytest.raises(provider.ProviderRefused):
        provider.parse_response(_response(request, findings=[{"path": "../secret", "line": 1, "detail": "x"}]), request)


def test_flock_claim_is_atomic_for_exact_head(tmp_path):
    request = provider.parse_request(_payload())
    def claim():
        return provider.acquire_dispatch_claim(tmp_path, request, owner="controller", nonce="n")
    with ThreadPoolExecutor(max_workers=2) as pool:
        outcomes = list(pool.map(lambda _: claim(), range(2)))
    assert outcomes.count(True) == 1
    assert outcomes.count(False) == 1


def test_argv_is_fixed_and_never_shell_template(tmp_path):
    request, response = tmp_path / "request.json", tmp_path / "response.json"
    assert provider.reviewer_argv("/usr/libexec/reviewer", request, response)[0] == "/usr/libexec/reviewer"
    with pytest.raises(provider.ProviderRefused):
        provider.reviewer_argv("reviewer --bad", request, response)
