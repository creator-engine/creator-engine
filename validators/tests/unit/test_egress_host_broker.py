"""Unit tests for the host-side contained-seat SELF-PUSH broker seam.

The handler accepts a JSON-like value request from the contained seat and invokes the
host-owned courier. Tests inject all live boundaries, so no real gh/git/network is required.
"""

import json

from creator_engine_validator.forge.scoped_token import ScopedToken
from egress_broker.config import load_broker_config
from egress_broker.host_broker import handle_self_push_json_line, handle_self_push_request
from egress_broker.policy import CommitFacts

_GOOD_FACTS = CommitFacts(
    head_sha="a" * 40,
    signature_status="G",
    signer="cedev4vps-coder",
    author_name="ce-dev-4",
    author_email="150906340+cedev4vps-coder@users.noreply.github.com",
)
_SENTINEL = "ghs_LIVE_READY_SENTINEL_1234567890"


def _config(tmp_path):
    return load_broker_config(
        {
            "repo": "creator-engine/creator-engine",
            "installation_owner": "creator-engine",
            "audit_log": str(tmp_path / "audit.jsonl"),
            "policy": {
                "base_branch": "main",
                "allowed_branch_namespaces": ["ce242-", "ce-"],
                "forbidden_branches": [],
                "authorized_emails": [],
                "authorized_logins": ["cedev4vps-coder"],
                "max_pushes_per_window": 10,
                "window_seconds": 3600,
            },
            "seats": {
                "dev-4": {
                    "app_id": "4085526",
                    "app_owner": "cedev4vps-coder",
                    "pem_path": "/dev/shm/ce-dev4/ce-forge-dev4.pem",
                    "installation_id": 242,
                }
            },
        }
    )


class _HostSpy:
    def __init__(self):
        self.calls = []
        self.child_env_values = []
        self.token = ScopedToken(
            run_id="ce242-r",
            repo="creator-engine/creator-engine",
            policy_sha="2" * 64,
            secret_name="forge_egress_push_pr",
            permissions=(("contents", "write"), ("pull_requests", "write")),
            expires_at="2026-06-25T13:00:00Z",
            token_ref="ce242-token-ref",
            value=_SENTINEL,
        )

    def resolve_id(self, seat):
        self.calls.append(("resolve_id", seat.seat_id))
        return 242

    def mint(self, seat, installation_id):
        self.calls.append(("mint", seat.seat_id, installation_id))
        return self.token

    def push(self, token):
        self.calls.append(("push", "host-child-transport"))
        self.child_env_values.append(token.value)
        return {"pushed": True, "remote_head": _GOOD_FACTS.head_sha, "local_head": _GOOD_FACTS.head_sha}

    def open_pr(self, token):
        self.calls.append(("open_pr", "host-child-transport"))
        self.child_env_values.append(token.value)
        return {"pr_number": 242, "created": True}

    def revoke(self, token):
        self.calls.append(("revoke", "host-child-transport"))
        self.child_env_values.append(token.value)
        return True


def _request():
    return {
        "seat_id": "dev-4",
        "repo_path": "/seat/workspace/creator-engine",
        "branch": "ce242-live-self-push",
        "contained": {
            "env": {"CE_SEAT_ID": "dev-4", "CE_BRANCH": "ce242-live-self-push"},
            "argv": ["ce", "self-push", "--branch", "ce242-live-self-push"],
            "fs": {"/tmp/request.json": '{"branch":"ce242-live-self-push"}'},
            "logs": ["self-push requested", "waiting for host broker"],
        },
    }


def _assert_sentinel_absent(*objects):
    for obj in objects:
        rendered = obj if isinstance(obj, str) else json.dumps(obj, sort_keys=True, default=repr)
        assert _SENTINEL not in rendered


def test_host_broker_handles_apply_request_without_returning_or_recording_token(tmp_path):
    spy = _HostSpy()

    response = handle_self_push_request(
        _request(),
        config=_config(tmp_path),
        broker_seat_id="dev-4",
        host_repo_path="/host/workspaces/creator-engine",
        apply_default=True,
        read_facts_fn=lambda: _GOOD_FACTS,
        resolve_id_fn=spy.resolve_id,
        mint_fn=spy.mint,
        push_fn=spy.push,
        open_pr_fn=spy.open_pr,
        revoke_fn=spy.revoke,
    )

    assert response["status"] == 200
    assert response["pushed"] is True
    assert response["pr_number"] == 242
    assert [c[0] for c in spy.calls] == ["resolve_id", "mint", "push", "open_pr", "revoke"]
    assert spy.child_env_values == [_SENTINEL, _SENTINEL, _SENTINEL]
    _assert_sentinel_absent(response, _request(), (tmp_path / "audit.jsonl").read_text())


def test_host_broker_refuses_contained_token_material_before_courier(tmp_path):
    spy = _HostSpy()
    req = _request()
    req["contained"]["env"]["GH_TOKEN"] = _SENTINEL
    req["contained"]["logs"].append(f"debug token {_SENTINEL}")

    response = handle_self_push_request(
        req,
        config=_config(tmp_path),
        broker_seat_id="dev-4",
        host_repo_path="/host/workspaces/creator-engine",
        read_facts_fn=lambda: _GOOD_FACTS,
        resolve_id_fn=spy.resolve_id,
        mint_fn=spy.mint,
        push_fn=spy.push,
        open_pr_fn=spy.open_pr,
        revoke_fn=spy.revoke,
    )

    assert response["status"] == 403
    assert response["reason"] == "contained_credential_material"
    assert spy.calls == []
    assert not (tmp_path / "audit.jsonl").exists()


def test_host_broker_ignores_request_apply_choice_and_rejects_wrong_seat(tmp_path):
    spy = _HostSpy()
    req = _request()
    req["apply"] = False

    response = handle_self_push_request(
        req,
        config=_config(tmp_path),
        broker_seat_id="dev-4",
        host_repo_path="/host/workspaces/creator-engine",
        apply_default=True,
        read_facts_fn=lambda: _GOOD_FACTS,
        resolve_id_fn=spy.resolve_id,
        mint_fn=spy.mint,
        push_fn=spy.push,
        open_pr_fn=spy.open_pr,
        revoke_fn=spy.revoke,
    )

    assert response["status"] == 200
    assert [c[0] for c in spy.calls] == ["resolve_id", "mint", "push", "open_pr", "revoke"]

    req = _request()
    req["seat_id"] = "ce-dgx-codex"
    response = handle_self_push_request(
        req,
        config=_config(tmp_path),
        broker_seat_id="dev-4",
        host_repo_path="/host/workspaces/creator-engine",
        apply_default=True,
        read_facts_fn=lambda: _GOOD_FACTS,
        resolve_id_fn=spy.resolve_id,
        mint_fn=spy.mint,
        push_fn=spy.push,
        open_pr_fn=spy.open_pr,
        revoke_fn=spy.revoke,
    )

    assert response["status"] == 403
    assert response["reason"] == "wrong_seat"
    assert [c[0] for c in spy.calls] == ["resolve_id", "mint", "push", "open_pr", "revoke"]


def test_host_broker_overrides_container_repo_path_with_host_repo_path(tmp_path):
    seen = {}

    def fake_courier(request, *, config, apply, **kw):
        seen["repo_path"] = request.repo_path
        seen["apply"] = apply
        return type(
            "Result",
            (),
            {
                "seat_id": request.seat_id,
                "branch": request.branch,
                "head_sha": _GOOD_FACTS.head_sha,
                "allowed": True,
                "applied": True,
                "pushed": True,
                "pr_number": 242,
                "installation_id": 242,
            },
        )()

    response = handle_self_push_request(
        _request(),
        config=_config(tmp_path),
        broker_seat_id="dev-4",
        host_repo_path="/host/trusted/creator-engine",
        apply_default=True,
        courier_fn=fake_courier,
    )

    assert response["status"] == 200
    assert seen == {"repo_path": "/host/trusted/creator-engine", "apply": True}


def test_host_broker_host_apply_default_controls_apply_even_when_request_asks_apply(tmp_path):
    seen = {}
    req = _request()
    req["apply"] = True

    def fake_courier(request, *, config, apply, **kw):
        seen["apply"] = apply
        return type(
            "Result",
            (),
            {
                "seat_id": request.seat_id,
                "branch": request.branch,
                "head_sha": _GOOD_FACTS.head_sha,
                "allowed": True,
                "applied": apply,
                "pushed": False,
                "pr_number": None,
                "installation_id": None,
            },
        )()

    response = handle_self_push_request(
        req,
        config=_config(tmp_path),
        broker_seat_id="dev-4",
        host_repo_path="/host/trusted/creator-engine",
        apply_default=False,
        courier_fn=fake_courier,
    )

    assert response["status"] == 200
    assert seen == {"apply": False}
    assert response["applied"] is False


def test_host_broker_malformed_request_and_json_are_refused(tmp_path):
    response = handle_self_push_request(
        ["not", "a", "mapping"],
        config=_config(tmp_path),
        broker_seat_id="dev-4",
        host_repo_path="/host/trusted/creator-engine",
    )
    assert response == {"status": 400, "reason": "bad_request"}

    raw = handle_self_push_json_line(
        "{not-json",
        config=_config(tmp_path),
        broker_seat_id="dev-4",
        host_repo_path="/host/trusted/creator-engine",
    )
    assert json.loads(raw) == {"status": 400, "reason": "bad_json"}


def test_host_broker_refuses_token_shaped_success_response(tmp_path):
    def leaking_courier(request, *, config, apply, **kw):
        return type(
            "Result",
            (),
            {
                "seat_id": request.seat_id,
                "branch": f"ce242-{_SENTINEL}",
                "head_sha": _GOOD_FACTS.head_sha,
                "allowed": True,
                "applied": True,
                "pushed": True,
                "pr_number": 242,
                "installation_id": 242,
            },
        )()

    response = handle_self_push_request(
        _request(),
        config=_config(tmp_path),
        broker_seat_id="dev-4",
        host_repo_path="/host/trusted/creator-engine",
        apply_default=True,
        courier_fn=leaking_courier,
    )

    assert response == {"status": 500, "reason": "response_secret_material_refused"}


def test_json_line_seam_returns_one_secret_free_response_line(tmp_path):
    spy = _HostSpy()
    line = json.dumps(_request())

    raw = handle_self_push_json_line(
        line,
        config=_config(tmp_path),
        broker_seat_id="dev-4",
        host_repo_path="/host/workspaces/creator-engine",
        apply_default=True,
        read_facts_fn=lambda: _GOOD_FACTS,
        resolve_id_fn=spy.resolve_id,
        mint_fn=spy.mint,
        push_fn=spy.push,
        open_pr_fn=spy.open_pr,
        revoke_fn=spy.revoke,
    )

    assert raw.endswith("\n")
    response = json.loads(raw)
    assert response["status"] == 200
    assert response["installation_id"] == 242
    assert _SENTINEL not in raw
