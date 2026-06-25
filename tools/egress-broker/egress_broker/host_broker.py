"""Host-side contained-seat SELF-PUSH broker seam.

The contained seat sends only value facts: seat id, host-visible repo path, branch, and
optionally value-only launch observations. This module is the live-ready host boundary that
turns that request into the existing egress courier path. The host, not the contained seat,
owns all mint/sign/push/PR/revoke seams.

No credential is accepted from or returned to the contained seat. Token-shaped material in
the reported contained env/argv/files/logs is a fail-closed refusal before any courier call.
The successful path returns only a value-free result projection.
"""
from __future__ import annotations

import json
import re
import socket
from collections.abc import Callable, Mapping
from pathlib import Path
from typing import Any

from egress_broker.config import BrokerConfig
from egress_broker.orchestrator import (
    ContainedSeatSelfPushRequest,
    EgressRefused,
    contained_seat_self_push,
)

_TOKEN_VALUE_RE = re.compile(
    r"(?:gh[pousr]_[A-Za-z0-9_.\-]{8,}|github_pat_[A-Za-z0-9_.\-]{8,}|"
    r"Bearer\s+[A-Za-z0-9._~+/=-]{20,}|eyJ[A-Za-z0-9_-]+(?:\.[A-Za-z0-9_-]+){2})"
)
_SECRET_KEY_RE = re.compile(
    r"(?:authorization|cookie|credential|password|private[-_]?key|secret|token|api[-_]?key)",
    re.IGNORECASE,
)

CourierFn = Callable[..., Any]
_UNSUPPORTED_REQUEST_FIELDS = frozenset(
    {
        "command",
        "config",
        "config_path",
        "pem_path",
        "ref",
        "refspec",
        "remote",
        "token",
    }
)


def handle_self_push_request(
    request: Mapping[str, Any],
    *,
    config: BrokerConfig,
    broker_seat_id: str,
    host_repo_path: str,
    apply_default: bool = False,
    courier_fn: CourierFn = contained_seat_self_push,
    **host_courier_options: Any,
) -> dict[str, Any]:
    """Handle one contained-seat SELF-PUSH request as a host-side broker.

    ``host_courier_options`` are trusted host-owned seams (signer, transport, git/gh spawns,
    fake test hooks, etc.). They are deliberately not read from ``request``.
    """
    if not isinstance(request, Mapping):
        return {"status": 400, "reason": "bad_request"}

    unsupported = sorted(str(k) for k in request if str(k) in _UNSUPPORTED_REQUEST_FIELDS)
    if unsupported:
        return {"status": 400, "reason": "unsupported_request_field", "fields": unsupported}

    seat_id = str(request.get("seat_id") or "").strip()
    branch = str(request.get("branch") or "").strip()
    if not seat_id or not branch:
        return {"status": 400, "reason": "missing_required_field"}
    broker_seat_id = str(broker_seat_id or "").strip()
    if not broker_seat_id:
        return {"status": 500, "reason": "broker_seat_id_missing"}
    if seat_id != broker_seat_id:
        return {"status": 403, "reason": "wrong_seat", "expected_seat_id": broker_seat_id}
    host_repo_path = str(host_repo_path or "").strip()
    if not host_repo_path:
        return {"status": 500, "reason": "host_repo_path_missing"}

    findings = _contained_secret_findings(request)
    if findings:
        return {
            "status": 403,
            "reason": "contained_credential_material",
            "findings": list(findings),
        }

    try:
        result = courier_fn(
            ContainedSeatSelfPushRequest(
                seat_id=broker_seat_id,
                repo_path=host_repo_path,
                branch=branch,
            ),
            config=config,
            apply=bool(apply_default),
            **host_courier_options,
        )
    except EgressRefused as exc:
        response = {
            "status": 403,
            "reason": "egress_refused",
            "detail": str(exc),
            "audit_record": dict(exc.audit_record),
        }
        return _assert_response_secret_free(response)

    response = {
        "status": 200,
        "seat_id": result.seat_id,
        "branch": result.branch,
        "head_sha": result.head_sha,
        "allowed": result.allowed,
        "applied": result.applied,
        "pushed": result.pushed,
        "pr_number": result.pr_number,
        "installation_id": result.installation_id,
    }
    return _assert_response_secret_free(response)


def handle_self_push_json_line(
    line: str,
    *,
    config: BrokerConfig,
    broker_seat_id: str,
    host_repo_path: str,
    apply_default: bool = False,
    courier_fn: CourierFn = contained_seat_self_push,
    **host_courier_options: Any,
) -> str:
    """JSON-lines daemon seam: one request line in, one secret-free response line out."""
    try:
        request = json.loads(line)
    except (TypeError, json.JSONDecodeError, ValueError):
        response = {"status": 400, "reason": "bad_json"}
    else:
        response = handle_self_push_request(
            request,
            config=config,
            broker_seat_id=broker_seat_id,
            host_repo_path=host_repo_path,
            apply_default=apply_default,
            courier_fn=courier_fn,
            **host_courier_options,
        )
    return json.dumps(_assert_response_secret_free(response), sort_keys=True, separators=(",", ":")) + "\n"


def serve_self_push_unix_socket(
    socket_path: str | Path,
    *,
    config: BrokerConfig,
    broker_seat_id: str,
    host_repo_path: str,
    apply_default: bool = True,
    once: bool = False,
    mode: int = 0o600,
    courier_fn: CourierFn = contained_seat_self_push,
    **host_courier_options: Any,
) -> None:
    """Serve the JSON-line SELF-PUSH protocol on a host-owned Unix socket.

    The caller is expected to create the parent directory with the desired UID/GID ownership.
    This function refuses to replace an existing path, binds a stream Unix socket, chmods it
    to ``mode`` (default ``0600``), and handles one request per connection. ``once=True`` is
    a CI/test seam; the live daemon leaves it false under a supervisor.
    """
    path = Path(socket_path)
    if path.exists():
        raise RuntimeError(f"self-push socket path already exists: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as server:
        server.bind(str(path))
        path.chmod(mode)
        server.listen(16)
        while True:
            conn, _addr = server.accept()
            with conn:
                data = b""
                while True:
                    chunk = conn.recv(65536)
                    if not chunk:
                        break
                    data += chunk
                    if b"\n" in data:
                        break
                line = data.decode("utf-8", errors="replace").splitlines()[0] if data else ""
                response = handle_self_push_json_line(
                    line,
                    config=config,
                    broker_seat_id=broker_seat_id,
                    host_repo_path=host_repo_path,
                    apply_default=apply_default,
                    courier_fn=courier_fn,
                    **host_courier_options,
                )
                conn.sendall(response.encode("utf-8"))
            if once:
                break


def _contained_secret_findings(request: Mapping[str, Any]) -> tuple[str, ...]:
    contained = request.get("contained") or {}
    findings: list[str] = []
    if isinstance(contained, Mapping):
        _scan(contained.get("env") or {}, "contained.env", findings, keys_are_secret=True)
        _scan(contained.get("argv") or (), "contained.argv", findings)
        _scan(contained.get("fs") or {}, "contained.fs", findings, keys_are_secret=True)
        _scan(contained.get("logs") or (), "contained.logs", findings)
    return tuple(sorted(findings))


def _scan(obj: object, path: str, findings: list[str], *, keys_are_secret: bool = False) -> None:
    if isinstance(obj, Mapping):
        for key, value in obj.items():
            key_s = str(key)
            child = f"{path}.{key_s}"
            if keys_are_secret and _SECRET_KEY_RE.search(key_s):
                findings.append(child)
            _scan(value, child, findings)
    elif isinstance(obj, (list, tuple)):
        for idx, value in enumerate(obj):
            _scan(value, f"{path}[{idx}]", findings)
    elif isinstance(obj, str) and _TOKEN_VALUE_RE.search(obj):
        findings.append(path)


def _assert_response_secret_free(response: dict[str, Any]) -> dict[str, Any]:
    rendered = json.dumps(response, sort_keys=True, default=repr)
    if _TOKEN_VALUE_RE.search(rendered):
        return {"status": 500, "reason": "response_secret_material_refused"}
    return response


__all__ = [
    "handle_self_push_json_line",
    "handle_self_push_request",
    "serve_self_push_unix_socket",
]
