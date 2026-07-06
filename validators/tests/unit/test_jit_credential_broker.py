"""JIT seat credential broker tests.

These tests cover the failure direction for the JIT credential mechanism: no Docker/env delivery,
unknown classes fail closed with audit, TTL expiry is enforced, and concurrent
mint requests serialize through the broker flock.
"""

import json
import threading
import time
from datetime import datetime, timedelta, timezone

from creator_engine_validator.forge.scoped_token import ScopedToken
from egress_broker.config import load_broker_config
from egress_broker.host_broker import handle_self_push_json_line, handle_self_push_request
from egress_broker.jit_credential import ModelCredential, SeatCredentialStore

_MODEL_SECRET = "sk-ce-model-api-sentinel-1234567890"
_FORGE_SECRET = "ghs_jit_forge_sentinel_1234567890"


def _config(tmp_path):
    return load_broker_config(
        {
            "repo": "creator-engine/creator-engine",
            "installation_owner": "creator-engine",
            "audit_log": str(tmp_path / "audit.jsonl"),
            "policy": {
                "base_branch": "main",
                "allowed_branch_namespaces": ["ce-"],
                "forbidden_branches": [],
                "authorized_emails": [],
                "authorized_logins": ["seat-dev-test"],
                "max_pushes_per_window": 10,
                "window_seconds": 3600,
            },
            "seats": {
                "dev-3": {
                    "app_id": "12345",
                    "app_owner": "seat-dev-test",
                    "pem_path": "/dev/shm/ce-dev3/ce-forge-dev3.pem",
                    "installation_id": 242,
                    "allowed_credential_classes": ["model-api", "forge-scoped"],
                },
                "dev-4": {
                    "app_id": "4085526",
                    "app_owner": "cedev4vps-coder",
                    "pem_path": "/dev/shm/ce-dev4/ce-forge-dev4.pem",
                    "installation_id": 242,
                    "allowed_credential_classes": [],
                },
            },
        }
    )


def _records(tmp_path):
    return [
        json.loads(line)
        for line in (tmp_path / "audit.jsonl").read_text(encoding="utf-8").splitlines()
    ]


def _model_supplier(now, calls):
    def mint(seat_id, ttl_seconds):
        calls.append((seat_id, ttl_seconds))
        return ModelCredential(
            value=_MODEL_SECRET,
            expires_at=(now() + timedelta(seconds=ttl_seconds)).isoformat().replace("+00:00", "Z"),
            credential_ref=f"{seat_id}/model-api/1",
        )

    return mint


def test_mint_model_api_delivers_only_on_socket_not_env_argv_or_docker(tmp_path):
    now_value = datetime(2026, 7, 6, 17, 0, tzinfo=timezone.utc)
    calls = []
    request = {
        "verb": "mint-seat-credential",
        "seat_id": "dev-3",
        "credential_class": "model-api",
        "contained": {
            "env": {"CE_SEAT_ID": "dev-3"},
            "argv": ["ce", "credential", "mint"],
            "docker": ["docker", "run", "creator-engine-seat"],
        },
    }

    raw = handle_self_push_json_line(
        json.dumps(request),
        config=_config(tmp_path),
        broker_seat_id="dev-3",
        host_repo_path="/host/workspace",
        credential_store=SeatCredentialStore(tmp_path / "jit.lock"),
        model_mint_fn=_model_supplier(lambda: now_value, calls),
        now=lambda: now_value,
    )

    response = json.loads(raw)
    assert response["status"] == 200
    assert response["credential"] == _MODEL_SECRET
    assert response["delivery"] == "broker-socket-stream"
    assert calls == [("dev-3", 300)]

    contained_surface = json.dumps(request["contained"], sort_keys=True)
    assert _MODEL_SECRET not in contained_surface
    assert "docker -e" not in contained_surface
    assert "docker run -e" not in contained_surface
    assert "docker exec --env" not in contained_surface
    assert _MODEL_SECRET not in (tmp_path / "audit.jsonl").read_text(encoding="utf-8")


def test_unknown_class_refused_and_audited(tmp_path):
    response = handle_self_push_request(
        {
            "verb": "mint-seat-credential",
            "seat_id": "dev-3",
            "credential_class": "root-admin",
        },
        config=_config(tmp_path),
        broker_seat_id="dev-3",
        host_repo_path="/host/workspace",
        credential_store=SeatCredentialStore(tmp_path / "jit.lock"),
        model_mint_fn=lambda seat_id, ttl: ModelCredential("unused", "", "unused"),
    )

    assert response["status"] == 403
    assert response["reason"] == "unknown_credential_class"
    records = _records(tmp_path)
    assert records[-1]["event"] == "seat_jit_credential"
    assert records[-1]["action"] == "mint"
    assert records[-1]["decision"] == "deny"
    assert records[-1]["reason"] == "unknown_credential_class"


def test_credential_verb_refuses_wrong_bound_seat_and_request_token_field(tmp_path):
    store = SeatCredentialStore(tmp_path / "jit.lock")
    response = handle_self_push_request(
        {
            "verb": "mint-seat-credential",
            "seat_id": "dev-3",
            "credential_class": "model-api",
        },
        config=_config(tmp_path),
        broker_seat_id="dev-4",
        host_repo_path="/host/workspace",
        credential_store=store,
        model_mint_fn=lambda seat_id, ttl: ModelCredential(_MODEL_SECRET, "", "unused"),
    )

    assert response["status"] == 403
    assert response["reason"] == "wrong_seat"

    response = handle_self_push_request(
        {
            "verb": "mint-seat-credential",
            "seat_id": "dev-3",
            "credential_class": "model-api",
            "token": _MODEL_SECRET,
        },
        config=_config(tmp_path),
        broker_seat_id="dev-3",
        host_repo_path="/host/workspace",
        credential_store=store,
        model_mint_fn=lambda seat_id, ttl: ModelCredential(_MODEL_SECRET, "", "unused"),
    )

    assert response["status"] == 400
    assert response["reason"] == "unsupported_request_field"
    assert response["fields"] == ["token"]
    records = _records(tmp_path)
    assert [record["reason"] for record in records[-2:]] == [
        "wrong_seat",
        "unsupported_request_field",
    ]


def test_ttl_expiry_revokes_and_prevents_late_explicit_revoke(tmp_path):
    clock = {"now": datetime(2026, 7, 6, 17, 0, tzinfo=timezone.utc)}
    revoked = []

    def mint_model(seat_id, ttl_seconds):
        return ModelCredential(
            value=_MODEL_SECRET,
            expires_at=(clock["now"] + timedelta(seconds=1)).isoformat().replace("+00:00", "Z"),
            credential_ref=f"{seat_id}/model-api/short",
        )

    store = SeatCredentialStore(tmp_path / "jit.lock")
    response = handle_self_push_request(
        {"verb": "mint-seat-credential", "seat_id": "dev-3", "credential_class": "model-api"},
        config=_config(tmp_path),
        broker_seat_id="dev-3",
        host_repo_path="/host/workspace",
        credential_store=store,
        model_mint_fn=mint_model,
        revoke_fn=lambda material: revoked.append(material.credential_ref) or True,
        now=lambda: clock["now"],
    )
    assert response["status"] == 200

    clock["now"] = clock["now"] + timedelta(seconds=2)
    response = handle_self_push_request(
        {"verb": "revoke-seat-credential", "seat_id": "dev-3", "credential_class": "model-api"},
        config=_config(tmp_path),
        broker_seat_id="dev-3",
        host_repo_path="/host/workspace",
        credential_store=store,
        now=lambda: clock["now"],
    )

    assert response["status"] == 404
    assert response["reason"] == "no_active_credential"
    assert revoked == ["dev-3/model-api/short"]
    records = _records(tmp_path)
    assert any(rec["action"] == "expire" and rec["reason"] == "ttl_expired" for rec in records)


def test_concurrent_mint_uses_flock_and_keeps_single_active(tmp_path):
    clock = datetime(2026, 7, 6, 17, 0, tzinfo=timezone.utc)
    store = SeatCredentialStore(tmp_path / "jit.lock")
    active = {"count": 0, "max": 0, "seq": 0}
    calls = []
    revoked = []
    guard = threading.Lock()

    def mint_model(seat_id, ttl_seconds):
        with guard:
            active["count"] += 1
            active["max"] = max(active["max"], active["count"])
            active["seq"] += 1
            seq = active["seq"]
        time.sleep(0.03)
        with guard:
            calls.append(seq)
            active["count"] -= 1
        return ModelCredential(
            value=f"{_MODEL_SECRET}-{seq}",
            expires_at=(clock + timedelta(seconds=ttl_seconds)).isoformat().replace("+00:00", "Z"),
            credential_ref=f"dev-3/model-api/{seq}",
        )

    def run_one():
        return handle_self_push_request(
            {"verb": "mint-seat-credential", "seat_id": "dev-3", "credential_class": "model-api"},
            config=_config(tmp_path),
            broker_seat_id="dev-3",
            host_repo_path="/host/workspace",
            credential_store=store,
            model_mint_fn=mint_model,
            revoke_fn=lambda material: revoked.append(material.credential_ref) or True,
            now=lambda: clock,
        )

    results = []
    threads = [threading.Thread(target=lambda: results.append(run_one())) for _ in range(2)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=2)

    assert sorted(result["status"] for result in results) == [200, 200]
    assert calls == [1, 2]
    assert active["max"] == 1
    assert revoked == ["dev-3/model-api/1"]
    assert len([rec for rec in _records(tmp_path) if rec["action"] == "mint"]) == 2


def test_forge_scoped_reuses_scoped_token_request_and_explicit_revoke(tmp_path):
    clock = datetime(2026, 7, 6, 17, 0, tzinfo=timezone.utc)
    seen_requests = []
    revoked = []

    def mint_forge(request):
        seen_requests.append(request)
        return ScopedToken(
            run_id=request.run_id,
            repo=request.repo,
            policy_sha=request.policy_sha,
            secret_name=request.secret_name,
            permissions=tuple(sorted(request.permissions.items())),
            expires_at=(clock + timedelta(seconds=300)).isoformat().replace("+00:00", "Z"),
            token_ref="creator-engine/creator-engine@forge-scoped",
            value=_FORGE_SECRET,
        )

    store = SeatCredentialStore(tmp_path / "jit.lock")
    response = handle_self_push_request(
        {"verb": "mint-seat-credential", "seat_id": "dev-3", "credential_class": "forge-scoped"},
        config=_config(tmp_path),
        broker_seat_id="dev-3",
        host_repo_path="/host/workspace",
        credential_store=store,
        resolve_id_fn=lambda seat: 242,
        mint_fn=mint_forge,
        revoke_fn=lambda token: revoked.append(token.token_ref) or True,
        now=lambda: clock,
    )

    assert response["status"] == 200
    assert response["credential"] == _FORGE_SECRET
    assert seen_requests[0].permissions == {
        "metadata": "read",
        "issues": "read",
        "pull_requests": "read",
    }
    assert seen_requests[0].requested_ttl_seconds == 300

    response = handle_self_push_request(
        {"verb": "revoke-seat-credential", "seat_id": "dev-3", "credential_class": "forge-scoped"},
        config=_config(tmp_path),
        broker_seat_id="dev-3",
        host_repo_path="/host/workspace",
        credential_store=store,
        now=lambda: clock,
    )

    assert response["status"] == 200
    assert response["revoked"] is True
    assert revoked == ["creator-engine/creator-engine@forge-scoped"]
    assert _FORGE_SECRET not in (tmp_path / "audit.jsonl").read_text(encoding="utf-8")
