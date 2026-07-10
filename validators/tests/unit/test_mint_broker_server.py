"""Unit coverage for the mint-broker stdlib HTTP server entrypoint."""

from __future__ import annotations

import json
import threading
import urllib.error
import urllib.request

import pytest

import ce_mint_broker_server as server
from mint_broker.config import load_mint_broker_config

_MINTED = "ghs_server_minted_value"


def _config(tmp_path, **over):
    base = {
        "app_client_id": "Iv1.shared0000",
        "pem_path": str(tmp_path / "shared.pem"),
        "audit_log": str(tmp_path / "audit.jsonl"),
        "permission_ceiling": {
            "metadata": "read",
            "contents": "write",
            "pull_requests": "write",
        },
        "declared_minimum_grant": {
            "metadata": "read",
            "contents": "write",
            "pull_requests": "write",
        },
        "per_user_rate_cap": 30,
        "rate_window_seconds": 3600,
    }
    base.update(over)
    return load_mint_broker_config(base)


def _request(**over):
    base = {
        "installation_id": 222,
        "repo": "owner/repo",
        "permissions": {"contents": "write", "pull_requests": "write"},
        "caller_user_token": "ghu_caller_secret_value",
    }
    base.update(over)
    return base


def _signer(_signing_input: bytes) -> bytes:
    return b"fake-rs256-signature"


def _allow_binding(*_a, **_k):
    return None


def _mint_transport(_method, _url, headers, _body):
    assert headers.get("Authorization", "").startswith("Bearer ")
    return 201, json.dumps(
        {
            "token": _MINTED,
            "expires_at": "2026-06-21T15:00:00Z",
            "permissions": {"contents": "write", "pull_requests": "write"},
        }
    )


class _AccessLogger:
    def __init__(self):
        self.calls = []

    def info(self, *args):
        self.calls.append(args)


@pytest.fixture
def mint_http(tmp_path):
    httpd = server.build_http_server(
        bind_address="127.0.0.1",
        port=0,
        config=_config(tmp_path),
        binding_check=_allow_binding,
        signer=_signer,
        transport=_mint_transport,
    )
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{httpd.server_address[1]}"
    finally:
        httpd.shutdown()
        httpd.server_close()
        thread.join(timeout=5)


def _open(method: str, url: str, payload=None):
    data = None
    headers = {}
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, method=method, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=5) as resp:
            return resp.status, dict(resp.headers), resp.read()
    except urllib.error.HTTPError as exc:
        return exc.code, dict(exc.headers), exc.read()


def test_post_token_wires_the_pure_mint_handler(mint_http):
    status, _headers, body = _open("POST", f"{mint_http}/v1/token", _request())

    assert status == 200
    response = json.loads(body.decode("utf-8"))
    assert response["token"] == _MINTED
    assert response["repo"] == "owner/repo"
    assert response["status"] == 200


def test_healthz_returns_200_with_no_body(mint_http):
    status, headers, body = _open("GET", f"{mint_http}/healthz")

    assert status == 200
    assert body == b""
    assert headers["Content-Length"] == "0"


def test_unknown_route_is_404(mint_http):
    status, _headers, body = _open("GET", f"{mint_http}/nope")

    assert status == 404
    assert json.loads(body.decode("utf-8"))["reason"] == "not_found"


def test_token_wrong_method_is_405(mint_http):
    status, headers, body = _open("GET", f"{mint_http}/v1/token")

    assert status == 405
    assert headers["Allow"] == "POST"
    assert json.loads(body.decode("utf-8"))["reason"] == "method_not_allowed"


def test_non_loopback_bind_address_is_refused(tmp_path):
    with pytest.raises(server.MintBrokerServerError, match="non-loopback"):
        server.build_http_server(
            bind_address="0.0.0.0",
            port=0,
            config=_config(tmp_path),
            binding_check=_allow_binding,
            signer=_signer,
            transport=_mint_transport,
        )


def test_access_logging_never_receives_request_or_response_body_content(tmp_path):
    access_logger = _AccessLogger()
    httpd = server.build_http_server(
        bind_address="127.0.0.1",
        port=0,
        config=_config(tmp_path),
        binding_check=_allow_binding,
        signer=_signer,
        transport=_mint_transport,
        access_logger=access_logger,
    )
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    try:
        status, _headers, _body = _open(
            "POST",
            f"http://127.0.0.1:{httpd.server_address[1]}/v1/token",
            _request(),
        )
    finally:
        httpd.shutdown()
        httpd.server_close()
        thread.join(timeout=5)

    assert status == 200
    logged = repr(access_logger.calls)
    assert "POST" in logged
    assert "/v1/token" in logged
    assert "ghu_caller_secret_value" not in logged
    assert _MINTED not in logged
    assert "owner/repo" not in logged


def _write_config_json(path):
    path.write_text(
        json.dumps(
            {
                "app_client_id": "Iv1.shared0000",
                "pem_path": str(path.parent / "shared.pem"),
                "audit_log": str(path.parent / "audit.jsonl"),
                "permission_ceiling": {"contents": "write"},
                "declared_minimum_grant": {"contents": "write"},
                "per_user_rate_cap": 30,
                "rate_window_seconds": 3600,
            }
        ),
        encoding="utf-8",
    )


def test_group_writable_config_file_is_refused(tmp_path):
    config_path = tmp_path / "mint-broker.json"
    _write_config_json(config_path)
    config_path.chmod(0o660)

    with pytest.raises(server.MintBrokerServerError, match="group/world writable"):
        server.load_server_config(config_path)


def test_world_writable_config_file_is_refused(tmp_path):
    config_path = tmp_path / "mint-broker-world.json"
    _write_config_json(config_path)
    config_path.chmod(0o646)

    with pytest.raises(server.MintBrokerServerError, match="group/world writable"):
        server.load_server_config(config_path)


def test_post_healthz_is_405(mint_http):
    status, headers, body = _open("POST", f"{mint_http}/healthz")

    assert status == 405
    assert headers["Allow"] == "GET"
    assert json.loads(body.decode("utf-8"))["reason"] == "method_not_allowed"
