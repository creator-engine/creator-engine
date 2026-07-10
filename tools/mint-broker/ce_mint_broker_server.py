"""Stdlib HTTP entrypoint for the Creator Engine shared-App mint broker.

This module is intentionally a thin transport layer over the frozen pure service function
``mint_broker.service.handle_token_request``. It adds no independent authentication layer:
binding validation and the per-user rate cap in the pure service are the defense, while network
exposure, TLS, and reverse-proxy policy stay in the controller lane.

Runtime coupling: ``mint_broker.service`` imports ``egress_broker.audit`` for secret-free audit
records, so a source-checkout launch must place ``tools/egress-broker`` on ``sys.path``. The
systemd unit mirrors that with ``WorkingDirectory`` and ``PYTHONPATH``.

Secret hygiene is load-bearing. Request and response bodies are never logged. Access logging is
method, path, and status only. The configured PEM path is passed through to the signer unchanged;
this layer never reads PEM content and never includes PEM material in exceptions.
"""
from __future__ import annotations

import argparse
import json
import logging
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import stat
import subprocess
import sys
from collections.abc import Callable, Mapping
from typing import Any
from urllib.parse import urlsplit

_REPO_ROOT = Path(__file__).resolve().parents[2]
_EGRESS_BROKER_ROOT = _REPO_ROOT / "tools" / "egress-broker"
_VALIDATORS_ROOT = _REPO_ROOT / "validators"
for _path in (_EGRESS_BROKER_ROOT, _VALIDATORS_ROOT):
    _path_s = str(_path)
    if _path_s not in sys.path:
        sys.path.insert(0, _path_s)

from creator_engine_validator.forge.app_jwt_runner import Signer, Transport  # noqa: E402
from mint_broker.binding import assert_user_controls_installation  # noqa: E402
from mint_broker.config import MintBrokerConfig, load_mint_broker_config  # noqa: E402
from mint_broker.service import handle_token_request  # noqa: E402

DEFAULT_BIND_ADDRESS = "127.0.0.1"
DEFAULT_PORT = 8767
MAX_BODY_BYTES = 1024 * 1024
ACCESS_LOG = logging.getLogger("ce_mint_broker.access")

BindingCheck = Callable[..., None]


class MintBrokerServerError(Exception):
    """Value-free startup/runtime refusal for the mint-broker HTTP layer."""


def refuse_insecure_config_file(config_path: str | Path) -> Path:
    """Return an expanded config path, refusing group/world-writable files."""
    path = Path(config_path).expanduser()
    mode = path.stat().st_mode
    if mode & (stat.S_IWGRP | stat.S_IWOTH):
        raise MintBrokerServerError("mint-broker config file is group/world writable")
    return path


def load_server_config(config_path: str | Path) -> MintBrokerConfig:
    """Load config after the server-layer file-permission gate."""
    return load_mint_broker_config(refuse_insecure_config_file(config_path))


def openssl_signer(pem_path: str | Path, *, runner: Callable[..., Any] = subprocess.run) -> Signer:
    """Build the production RS256 signer without reading the PEM into this process."""
    pem = str(pem_path)

    def sign(signing_input: bytes) -> bytes:
        proc = runner(
            ["openssl", "dgst", "-sha256", "-sign", pem],
            input=signing_input,
            capture_output=True,
        )
        if getattr(proc, "returncode", 1) != 0:
            raise MintBrokerServerError(
                "openssl RS256 signing failed; refusing to mint"
            )
        signature = getattr(proc, "stdout", b"") or b""
        if not signature:
            raise MintBrokerServerError("openssl produced an empty RS256 signature")
        return signature

    return sign


def validate_bind_address(bind_address: str) -> str:
    """The process binds only 127.0.0.1; public exposure belongs to a reverse proxy."""
    candidate = str(bind_address or "").strip()
    if candidate != DEFAULT_BIND_ADDRESS:
        raise MintBrokerServerError("mint-broker refuses non-loopback bind addresses")
    return DEFAULT_BIND_ADDRESS


def coerce_port(raw_port: str | int) -> int:
    try:
        port = int(raw_port)
    except (TypeError, ValueError):
        raise MintBrokerServerError("mint-broker port must be an integer") from None
    if not (0 <= port <= 65535):
        raise MintBrokerServerError("mint-broker port must be between 0 and 65535")
    return port


def _json_body(payload: Mapping[str, Any]) -> bytes:
    return json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")


def make_handler(
    *,
    config: MintBrokerConfig,
    binding_check: BindingCheck = assert_user_controls_installation,
    signer: Signer,
    transport: Transport | None = None,
    access_logger: logging.Logger = ACCESS_LOG,
) -> type[BaseHTTPRequestHandler]:
    """Create an injectable request handler for tests and the live server."""

    class MintBrokerRequestHandler(BaseHTTPRequestHandler):
        server_version = "ce-mint-broker"
        protocol_version = "HTTP/1.1"

        def log_message(self, _format: str, *_args: Any) -> None:
            return

        def log_request(self, _code: int | str = "-", _size: int | str = "-") -> None:
            return

        @property
        def _route_path(self) -> str:
            return urlsplit(self.path).path

        def _access(self, status: int) -> None:
            access_logger.info("%s %s %s", self.command, self._route_path, status)

        def _send(
            self,
            status: int,
            body: bytes = b"",
            *,
            content_type: str | None = None,
            allow: str | None = None,
        ) -> None:
            self.send_response(status)
            if content_type:
                self.send_header("Content-Type", content_type)
            if allow:
                self.send_header("Allow", allow)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            if body:
                self.wfile.write(body)
            self._access(status)

        def _send_json(self, status: int, payload: Mapping[str, Any]) -> None:
            self._send(status, _json_body(payload), content_type="application/json")

        def _not_found(self) -> None:
            self._send_json(404, {"status": 404, "reason": "not_found"})

        def _method_not_allowed(self, allow: str) -> None:
            self._send(
                405,
                _json_body({"status": 405, "reason": "method_not_allowed"}),
                content_type="application/json",
                allow=allow,
            )

        def do_GET(self) -> None:
            if self._route_path == "/healthz":
                self._send(200)
            elif self._route_path == "/v1/token":
                self._method_not_allowed("POST")
            else:
                self._not_found()

        def do_POST(self) -> None:
            if self._route_path == "/healthz":
                self._method_not_allowed("GET")
                return
            if self._route_path != "/v1/token":
                self._not_found()
                return

            try:
                raw_length = int(self.headers.get("Content-Length") or "0")
            except ValueError:
                self._send_json(400, {"status": 400, "reason": "bad_content_length"})
                return
            if raw_length < 0 or raw_length > MAX_BODY_BYTES:
                self._send_json(413, {"status": 413, "reason": "body_too_large"})
                return
            raw_body = self.rfile.read(raw_length)
            try:
                payload = json.loads(raw_body.decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError, ValueError):
                self._send_json(400, {"status": 400, "reason": "bad_json"})
                return
            if not isinstance(payload, Mapping):
                self._send_json(400, {"status": 400, "reason": "bad_json"})
                return

            try:
                response = handle_token_request(
                    payload,
                    config=config,
                    binding_check=binding_check,
                    signer=signer,
                    transport=transport,
                )
            except Exception:  # noqa: BLE001 - fail closed without echoing secret-bearing detail
                response = {"status": 502, "reason": "mint_transport_error"}
            status = int(response.get("status", 500))
            self._send_json(status, response)

        def do_PUT(self) -> None:
            self._handle_other_method()

        def do_PATCH(self) -> None:
            self._handle_other_method()

        def do_DELETE(self) -> None:
            self._handle_other_method()

        def _handle_other_method(self) -> None:
            if self._route_path == "/healthz":
                self._method_not_allowed("GET")
            elif self._route_path == "/v1/token":
                self._method_not_allowed("POST")
            else:
                self._not_found()

    return MintBrokerRequestHandler


def build_http_server(
    *,
    bind_address: str,
    port: str | int,
    config: MintBrokerConfig,
    binding_check: BindingCheck = assert_user_controls_installation,
    signer: Signer,
    transport: Transport | None = None,
    access_logger: logging.Logger = ACCESS_LOG,
) -> ThreadingHTTPServer:
    """Build the loopback-only HTTP server with injectable pure-service seams."""
    host = validate_bind_address(bind_address)
    handler = make_handler(
        config=config,
        binding_check=binding_check,
        signer=signer,
        transport=transport,
        access_logger=access_logger,
    )
    return ThreadingHTTPServer((host, coerce_port(port)), handler)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the Creator Engine mint broker")
    parser.add_argument(
        "--config",
        default=os.environ.get("CE_MINT_BROKER_CONFIG"),
        help="Path to the mint-broker JSON config",
    )
    parser.add_argument(
        "--port",
        default=os.environ.get("CE_MINT_BROKER_PORT", str(DEFAULT_PORT)),
        help="Loopback TCP port to listen on",
    )
    parser.add_argument(
        "--bind-address",
        default=os.environ.get("CE_MINT_BROKER_BIND_ADDRESS", DEFAULT_BIND_ADDRESS),
        help="Bind address; only 127.0.0.1 is accepted",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(level=os.environ.get("CE_MINT_BROKER_LOG_LEVEL", "INFO"))
    args = parse_args(argv)
    if not args.config:
        raise SystemExit("CE_MINT_BROKER_CONFIG or --config is required")

    try:
        config = load_server_config(args.config)
        httpd = build_http_server(
            bind_address=args.bind_address,
            port=args.port,
            config=config,
            signer=openssl_signer(config.pem_path),
        )
    except MintBrokerServerError as exc:
        raise SystemExit(str(exc)) from None

    httpd.serve_forever()
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
