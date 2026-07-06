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
import os
import re
import socket
import struct
import sys
from collections.abc import Callable, Mapping
from pathlib import Path
from typing import Any

from egress_broker.audit import append_audit
from egress_broker.config import BrokerConfig
from egress_broker.jit_credential import mint_seat_credential, revoke_seat_credential
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
_SD_LISTEN_FDS_START = 3
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


def systemd_activated_unix_socket(
    *,
    first_fd: int = _SD_LISTEN_FDS_START,
    unset_environment: bool = True,
) -> socket.socket | None:
    """Return the single systemd-activated Unix stream socket, if present.

    systemd passes listening descriptors through ``LISTEN_FDS`` starting at fd 3.
    ``socket.fromfd`` duplicates the inherited fd, so this helper closes the original
    after duplication and unsets the activation environment to avoid leaking it to
    child processes.
    """

    listen_fds_raw = os.environ.get("LISTEN_FDS")
    listen_pid_raw = os.environ.get("LISTEN_PID")

    def _unset() -> None:
        if unset_environment:
            os.environ.pop("LISTEN_FDS", None)
            os.environ.pop("LISTEN_PID", None)
            os.environ.pop("LISTEN_FDNAMES", None)

    if not listen_fds_raw:
        return None
    if listen_pid_raw is None:
        _unset()
        raise RuntimeError("systemd socket activation requires LISTEN_PID")

    try:
        listen_fds = int(listen_fds_raw)
    except ValueError as exc:
        _unset()
        raise RuntimeError("invalid systemd socket activation LISTEN_FDS") from exc

    try:
        listen_pid = int(listen_pid_raw)
    except ValueError as exc:
        _unset()
        raise RuntimeError("invalid systemd socket activation LISTEN_PID") from exc
    if listen_pid != os.getpid():
        _unset()
        return None

    if listen_fds == 0:
        _unset()
        return None
    if listen_fds != 1:
        _unset()
        raise RuntimeError(f"expected exactly one systemd socket fd, got {listen_fds}")

    try:
        inherited = socket.fromfd(first_fd, socket.AF_UNIX, socket.SOCK_STREAM)
    except OSError as exc:
        _unset()
        raise RuntimeError("could not inherit systemd socket activation fd") from exc

    try:
        os.close(first_fd)
    except OSError:
        pass
    _unset()
    inherited.setblocking(True)
    return inherited


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

    verb = str(request.get("verb") or "").strip()
    if verb in {"mint-seat-credential", "revoke-seat-credential"}:
        seat_id = str(request.get("seat_id") or "").strip()
        credential_class = str(request.get("credential_class") or "").strip()
        if not seat_id or not credential_class:
            return {"status": 400, "reason": "missing_required_field"}
        unsupported = sorted(str(k) for k in request if str(k) in _UNSUPPORTED_REQUEST_FIELDS)
        if unsupported:
            return _audit_credential_refusal(
                config,
                seat_id=seat_id,
                credential_class=credential_class,
                action="mint" if verb == "mint-seat-credential" else "revoke",
                status=400,
                reason="unsupported_request_field",
                extra={"fields": unsupported},
            )
        findings = _contained_secret_findings(request)
        if findings:
            return _audit_credential_refusal(
                config,
                seat_id=seat_id,
                credential_class=credential_class,
                action="mint" if verb == "mint-seat-credential" else "revoke",
                status=403,
                reason="contained_credential_material",
                extra={"findings": list(findings)},
            )
        broker_seat_id = str(broker_seat_id or "").strip()
        if not broker_seat_id:
            return {"status": 500, "reason": "broker_seat_id_missing"}
        if seat_id != broker_seat_id:
            return _audit_credential_refusal(
                config,
                seat_id=seat_id,
                credential_class=credential_class,
                action="mint" if verb == "mint-seat-credential" else "revoke",
                status=403,
                reason="wrong_seat",
                extra={"expected_seat_id": broker_seat_id},
            )
        if verb == "mint-seat-credential":
            return mint_seat_credential(
                seat_id,
                credential_class,
                config=config,
                store=host_courier_options.get("credential_store"),
                signer=host_courier_options.get("signer"),
                transport=host_courier_options.get("transport"),
                gh_spawn=host_courier_options.get("gh_spawn"),
                now=host_courier_options.get("now"),
                audit_now=host_courier_options.get("audit_now"),
                resolve_id_fn=host_courier_options.get("resolve_id_fn"),
                mint_fn=host_courier_options.get("mint_fn"),
                revoke_fn=host_courier_options.get("revoke_fn"),
                model_mint_fn=host_courier_options.get("model_mint_fn"),
            )
        return revoke_seat_credential(
            seat_id,
            credential_class,
            config=config,
            store=host_courier_options.get("credential_store"),
            now=host_courier_options.get("now"),
            audit_now=host_courier_options.get("audit_now"),
        )

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
    if _is_socket_credential_response(response):
        return json.dumps(response, sort_keys=True, separators=(",", ":")) + "\n"
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
    expected_peer_uids: frozenset[int] | None = None,
    expected_peer_gids: frozenset[int] | None = None,
    reject_unexpected_peer: bool = False,
    activated_socket: socket.socket | None = None,
    courier_fn: CourierFn = contained_seat_self_push,
    **host_courier_options: Any,
) -> None:
    """Serve the JSON-line SELF-PUSH protocol on a host-owned Unix socket.

    The caller is expected to create the parent directory with the desired UID/GID ownership.
    When ``activated_socket`` is unset, this function refuses to replace an existing path,
    binds a stream Unix socket, chmods it to ``mode`` (default ``0600``), and handles one
    request per connection. When systemd socket activation supplies ``activated_socket``, the
    broker uses that already-listening socket without touching the path, preserving the socket
    inode across daemon restarts. ``once=True`` is a CI/test seam; the live daemon leaves it
    false under a supervisor.
    """
    path = Path(socket_path)
    if activated_socket is None:
        if path.exists():
            raise RuntimeError(f"self-push socket path already exists: {path}")
        path.parent.mkdir(parents=True, exist_ok=True)
        server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        server.bind(str(path))
        path.chmod(mode)
        server.listen(16)
    else:
        server = activated_socket
    with server:
        while True:
            conn, _addr = server.accept()
            with conn:
                peer_record = _audit_self_push_peercred(
                    conn,
                    config=config,
                    broker_seat_id=broker_seat_id,
                    expected_peer_uids=expected_peer_uids,
                    expected_peer_gids=expected_peer_gids,
                    reject_unexpected_peer=reject_unexpected_peer,
                )
                if peer_record["decision"] == "reject":
                    response = json.dumps(
                        {"status": 403, "reason": "peer_credential_unexpected"},
                        sort_keys=True,
                        separators=(",", ":"),
                    ) + "\n"
                    try:
                        conn.sendall(response.encode("utf-8"))
                    except (BrokenPipeError, OSError):
                        print(
                            "[ce-egress-self-push] client disconnected before response; dropping connection",
                            file=sys.stderr,
                        )
                    if once:
                        break
                    continue
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
                try:
                    conn.sendall(response.encode("utf-8"))
                except (BrokenPipeError, OSError):
                    print(
                        "[ce-egress-self-push] client disconnected before response; dropping connection",
                        file=sys.stderr,
                    )
            if once:
                break


def _audit_self_push_peercred(
    conn: socket.socket,
    *,
    config: BrokerConfig,
    broker_seat_id: str,
    expected_peer_uids: frozenset[int] | None,
    expected_peer_gids: frozenset[int] | None,
    reject_unexpected_peer: bool,
) -> dict[str, Any]:
    creds = conn.getsockopt(socket.SOL_SOCKET, socket.SO_PEERCRED, struct.calcsize("3i"))
    peer_pid, peer_uid, peer_gid = struct.unpack("3i", creds)
    profile_configured = expected_peer_uids is not None or expected_peer_gids is not None
    if not profile_configured:
        # Default remains best-effort host-origin record-and-flag for compatibility;
        # hard-reject-by-default is follow-on.
        origin = "host_origin"
        decision = "flag"
    else:
        uid_matches = expected_peer_uids is None or peer_uid in expected_peer_uids
        gid_matches = expected_peer_gids is None or peer_gid in expected_peer_gids
        if uid_matches and gid_matches:
            origin = "contained_seat"
            decision = "allow"
        elif reject_unexpected_peer:
            origin = "unexpected"
            decision = "reject"
        else:
            origin = "unexpected"
            decision = "flag"

    return append_audit(
        config.audit_log,
        {
            "event": "self_push_peercred",
            "broker_seat_id": broker_seat_id,
            "peer_uid": peer_uid,
            "peer_gid": peer_gid,
            "peer_pid": peer_pid,
            "origin": origin,
            "decision": decision,
        },
    )


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


def _audit_credential_refusal(
    config: BrokerConfig,
    *,
    seat_id: str,
    credential_class: str,
    action: str,
    status: int,
    reason: str,
    extra: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    audit_record = append_audit(
        config.audit_log,
        {
            "event": "seat_jit_credential",
            "seat_id": seat_id,
            "class": credential_class,
            "action": action,
            "decision": "deny",
            "reason": reason,
        },
    )
    return {
        "status": status,
        "reason": reason,
        "seat_id": seat_id,
        "credential_class": credential_class,
        "audit_record": audit_record,
        **dict(extra or {}),
    }


def _is_socket_credential_response(response: dict[str, Any]) -> bool:
    """The JIT mint path intentionally returns the secret on this socket only."""
    return (
        response.get("status") == 200
        and response.get("delivery") == "broker-socket-stream"
        and isinstance(response.get("credential"), str)
    )


__all__ = [
    "handle_self_push_json_line",
    "handle_self_push_request",
    "serve_self_push_unix_socket",
    "systemd_activated_unix_socket",
]
