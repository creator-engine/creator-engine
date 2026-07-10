"""Unit tests for the host-side contained-seat SELF-PUSH broker seam.

The handler accepts a JSON-like value request from the contained seat and invokes the
host-owned courier. Tests inject all live boundaries, so no real gh/git/network is required.
"""

import json
import os
import socket
import threading
import time

import pytest

from creator_engine_validator.forge.scoped_token import ScopedToken
from creator_engine_validator.forge.change_push import PushRefused
from creator_engine_validator.forge.github_repo_config import ForgeConfigError
from egress_broker import host_broker
from egress_broker.config import load_broker_config
from egress_broker.host_broker import (
    handle_self_push_json_line,
    handle_self_push_request,
    serve_self_push_unix_socket,
    systemd_activated_unix_socket,
)
from egress_broker.policy import CommitFacts
from egress_broker.orchestrator import contained_seat_self_push


def _connect_when_ready(socket_path, *, timeout=5.0):
    """Return a connected AF_UNIX client, retrying until the server is listening.

    The server binds the socket path (the file appears on disk) *before* it calls
    ``listen()``. A client that connects in that window gets ``ConnectionRefusedError``
    (Errno 111), and the path may not yet exist at all (``FileNotFoundError``). Both are
    transient readiness conditions, not failures, so retry the connect until the deadline.
    """
    deadline = time.monotonic() + timeout
    while True:
        client = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        try:
            client.connect(str(socket_path))
            return client
        except (ConnectionRefusedError, FileNotFoundError):
            client.close()
            if time.monotonic() >= deadline:
                raise
            time.sleep(0.01)


def _success_result(request, *, apply=True):
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


def _start_once_socket_server(socket_path, tmp_path, *, courier_fn, **kwargs):
    server_exceptions = []

    def run_server():
        try:
            serve_self_push_unix_socket(
                socket_path,
                config=_config(tmp_path),
                broker_seat_id="dev-4",
                host_repo_path="/host/workspaces/creator-engine",
                apply_default=True,
                once=True,
                courier_fn=courier_fn,
                allow_credential_requests=False,
                **kwargs,
            )
        except Exception as exc:  # pragma: no cover - asserted through server_exceptions
            server_exceptions.append(exc)

    server_thread = threading.Thread(target=run_server, daemon=True)
    server_thread.start()
    return server_thread, server_exceptions


def _start_looping_socket_server(socket_path, tmp_path, *, courier_fn, **kwargs):
    server_exceptions = []

    def run_server():
        try:
            serve_self_push_unix_socket(
                socket_path,
                config=_config(tmp_path),
                broker_seat_id="dev-4",
                host_repo_path="/host/workspaces/creator-engine",
                apply_default=True,
                once=False,
                courier_fn=courier_fn,
                allow_credential_requests=False,
                **kwargs,
            )
        except Exception as exc:  # pragma: no cover - asserted through server_exceptions
            server_exceptions.append(exc)

    server_thread = threading.Thread(target=run_server, daemon=True)
    server_thread.start()
    return server_thread, server_exceptions


def _send_socket_request(socket_path, *, send_request=True):
    with _connect_when_ready(socket_path) as client:
        client.settimeout(2)
        if send_request:
            client.sendall((json.dumps(_request()) + "\n").encode("utf-8"))
        data = b""
        while b"\n" not in data:
            chunk = client.recv(65536)
            assert chunk
            data += chunk
    return json.loads(data.decode("utf-8"))


def _audit_records(tmp_path):
    return [
        json.loads(line)
        for line in (tmp_path / "audit.jsonl").read_text(encoding="utf-8").splitlines()
    ]


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
        declared_work_class="story",
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
        declared_work_class="story",
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
        declared_work_class="story",
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
        declared_work_class="story",
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
        declared_work_class="story",
    )

    assert raw.endswith("\n")
    response = json.loads(raw)
    assert response["status"] == 200
    assert response["installation_id"] == 242
    assert _SENTINEL not in raw


def test_serve_unix_socket_audits_real_peercred(tmp_path):
    socket_path = tmp_path / "peercred-real.sock"
    courier_calls = []

    def fake_courier(request, *, config, apply, **kw):
        courier_calls.append(request.branch)
        return _success_result(request, apply=apply)

    server_thread, server_exceptions = _start_once_socket_server(
        socket_path,
        tmp_path,
        courier_fn=fake_courier,
    )

    response = _send_socket_request(socket_path)
    server_thread.join(timeout=2)

    assert response["status"] == 200
    assert courier_calls == ["ce242-live-self-push"]
    assert server_exceptions == []
    assert not server_thread.is_alive()
    peercred = _audit_records(tmp_path)[0]
    assert peercred["event"] == "self_push_peercred"
    assert peercred["broker_seat_id"] == "dev-4"
    assert peercred["peer_uid"] == os.getuid()
    assert peercred["peer_gid"] == os.getgid()
    assert isinstance(peercred["peer_pid"], int)
    assert peercred["peer_pid"] > 0
    assert peercred["origin"] == "host_origin"
    assert peercred["decision"] == "flag"


def test_serve_unix_socket_allows_matching_expected_peercred(tmp_path):
    socket_path = tmp_path / "peercred-allow.sock"
    courier_calls = []

    def fake_courier(request, *, config, apply, **kw):
        courier_calls.append(request.branch)
        return _success_result(request, apply=apply)

    server_thread, server_exceptions = _start_once_socket_server(
        socket_path,
        tmp_path,
        courier_fn=fake_courier,
        expected_peer_uids=frozenset({os.getuid()}),
        expected_peer_gids=frozenset({os.getgid()}),
    )

    response = _send_socket_request(socket_path)
    server_thread.join(timeout=2)

    assert response["status"] == 200
    assert courier_calls == ["ce242-live-self-push"]
    assert server_exceptions == []
    assert not server_thread.is_alive()
    peercred = _audit_records(tmp_path)[0]
    assert peercred["origin"] == "contained_seat"
    assert peercred["decision"] == "allow"


def test_serve_unix_socket_rejects_unexpected_peercred_when_enabled(tmp_path):
    socket_path = tmp_path / "peercred-reject.sock"
    courier_calls = []

    def fake_courier(request, *, config, apply, **kw):
        courier_calls.append(request.branch)
        return _success_result(request, apply=apply)

    server_thread, server_exceptions = _start_once_socket_server(
        socket_path,
        tmp_path,
        courier_fn=fake_courier,
        expected_peer_uids=frozenset({os.getuid() + 1}),
        reject_unexpected_peer=True,
    )

    response = _send_socket_request(socket_path, send_request=False)
    server_thread.join(timeout=2)

    assert response == {"status": 403, "reason": "peer_credential_unexpected"}
    assert courier_calls == []
    assert server_exceptions == []
    assert not server_thread.is_alive()
    peercred = _audit_records(tmp_path)[0]
    assert peercred["origin"] == "unexpected"
    assert peercred["decision"] == "reject"


def test_serve_unix_socket_rejects_unexpected_peercred_by_default_when_expected_configured(
    tmp_path,
):
    socket_path = tmp_path / "pd-rej.sock"
    courier_calls = []

    def fake_courier(request, *, config, apply, **kw):
        courier_calls.append(request.branch)
        return _success_result(request, apply=apply)

    server_thread, server_exceptions = _start_once_socket_server(
        socket_path,
        tmp_path,
        courier_fn=fake_courier,
        expected_peer_uids=frozenset({os.getuid() + 1}),
    )

    response = _send_socket_request(socket_path, send_request=False)
    server_thread.join(timeout=2)

    assert response == {"status": 403, "reason": "peer_credential_unexpected"}
    assert courier_calls == []
    assert server_exceptions == []
    assert not server_thread.is_alive()
    peercred = _audit_records(tmp_path)[0]
    assert peercred["origin"] == "unexpected"
    assert peercred["decision"] == "reject"


def test_serve_unix_socket_requires_peercred_expectations_for_credential_requests(tmp_path):
    socket_path = tmp_path / "credential.sock"

    with pytest.raises(RuntimeError, match="requires expected peer UID/GID configuration"):
        serve_self_push_unix_socket(
            socket_path,
            config=_config(tmp_path),
            broker_seat_id="dev-4",
            host_repo_path="/host/workspaces/creator-engine",
            once=True,
        )

    assert not socket_path.exists()


def test_systemd_activation_helper_uses_fromfd_and_unsets_environment(tmp_path, monkeypatch):
    socket_path = tmp_path / "activated-helper.sock"
    listener = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    listener.bind(str(socket_path))
    listener.listen(1)
    activation_fd = os.dup(listener.fileno())
    listener.close()

    monkeypatch.setenv("LISTEN_FDS", "1")
    monkeypatch.setenv("LISTEN_PID", str(os.getpid()))
    monkeypatch.setenv("LISTEN_FDNAMES", "egress-broker")

    activated = systemd_activated_unix_socket(first_fd=activation_fd)

    assert activated is not None
    assert "LISTEN_FDS" not in os.environ
    assert "LISTEN_PID" not in os.environ
    assert "LISTEN_FDNAMES" not in os.environ

    with activated:
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as client:
            client.connect(str(socket_path))
            conn, _addr = activated.accept()
            conn.close()


def test_systemd_activation_helper_requires_listen_pid(monkeypatch):
    monkeypatch.setenv("LISTEN_FDS", "1")
    monkeypatch.delenv("LISTEN_PID", raising=False)
    monkeypatch.setenv("LISTEN_FDNAMES", "egress-broker")

    try:
        with pytest.raises(RuntimeError, match="LISTEN_PID"):
            systemd_activated_unix_socket(first_fd=9999)
    finally:
        assert "LISTEN_FDS" not in os.environ
        assert "LISTEN_PID" not in os.environ
        assert "LISTEN_FDNAMES" not in os.environ


def test_serve_unix_socket_activation_keeps_existing_inode(tmp_path):
    socket_path = tmp_path / "activated-self-push.sock"
    listener = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    listener.bind(str(socket_path))
    listener.listen(16)
    before = socket_path.stat()
    courier_calls = []

    def fake_courier(request, *, config, apply, **kw):
        courier_calls.append(request.branch)
        return _success_result(request, apply=apply)

    server_exceptions = []

    def run_server():
        try:
            serve_self_push_unix_socket(
                socket_path,
                config=_config(tmp_path),
                broker_seat_id="dev-4",
                host_repo_path="/host/workspaces/creator-engine",
                apply_default=True,
                once=True,
                allow_credential_requests=False,
                activated_socket=listener,
                courier_fn=fake_courier,
            )
        except Exception as exc:  # pragma: no cover - asserted through server_exceptions
            server_exceptions.append(exc)

    server_thread = threading.Thread(target=run_server, daemon=True)
    server_thread.start()

    response = _send_socket_request(socket_path)
    server_thread.join(timeout=2)
    after = socket_path.stat()

    assert response["status"] == 200
    assert courier_calls == ["ce242-live-self-push"]
    assert server_exceptions == []
    assert not server_thread.is_alive()
    assert (after.st_dev, after.st_ino) == (before.st_dev, before.st_ino)


def test_serve_unix_socket_empty_connection_continues(tmp_path):
    socket_path = tmp_path / "empty-connection.sock"
    courier_calls = []

    def fake_courier(request, *, config, apply, **kw):
        courier_calls.append(request.branch)
        return _success_result(request, apply=apply)

    server_thread, server_exceptions = _start_looping_socket_server(
        socket_path,
        tmp_path,
        courier_fn=fake_courier,
    )

    with _connect_when_ready(socket_path):
        pass
    response = _send_socket_request(socket_path)

    assert response["status"] == 200
    assert courier_calls == ["ce242-live-self-push"]
    assert server_exceptions == []
    assert server_thread.is_alive()


def test_serve_unix_socket_mid_recv_disconnect_continues(tmp_path):
    socket_path = tmp_path / "mid-recv-disconnect.sock"
    courier_calls = []

    def fake_courier(request, *, config, apply, **kw):
        courier_calls.append(request.branch)
        return _success_result(request, apply=apply)

    server_thread, server_exceptions = _start_looping_socket_server(
        socket_path,
        tmp_path,
        courier_fn=fake_courier,
    )

    with _connect_when_ready(socket_path) as client:
        client.sendall(b'{"seat_id":"dev-4"')
    response = _send_socket_request(socket_path)

    assert response["status"] == 200
    assert courier_calls == ["ce242-live-self-push"]
    assert server_exceptions == []
    assert server_thread.is_alive()


@pytest.mark.parametrize("disconnect_error", [ConnectionResetError, OSError])
def test_serve_unix_socket_recv_disconnect_exception_continues(tmp_path, monkeypatch, disconnect_error):
    class StopServing(Exception):
        pass

    class FakeConnection:
        def __init__(self, chunks):
            self.chunks = list(chunks)
            self.responses = []

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def recv(self, _size):
            next_chunk = self.chunks.pop(0)
            if isinstance(next_chunk, BaseException):
                raise next_chunk
            return next_chunk

        def sendall(self, response):
            self.responses.append(response)

    class FakeServer:
        def __init__(self, connections):
            self.connections = list(connections)

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def accept(self):
            if not self.connections:
                raise StopServing
            return self.connections.pop(0), None

    failed_connection = FakeConnection([disconnect_error("client vanished")])
    valid_connection = FakeConnection([(json.dumps(_request()) + "\n").encode("utf-8")])
    listener = FakeServer([failed_connection, valid_connection])
    courier_calls = []

    def fake_courier(request, *, config, apply, **kw):
        courier_calls.append(request.branch)
        return _success_result(request, apply=apply)

    monkeypatch.setattr(
        host_broker,
        "_audit_self_push_peercred",
        lambda *args, **kwargs: {"decision": "allow"},
    )

    with pytest.raises(StopServing):
        serve_self_push_unix_socket(
            tmp_path / "fake-recv.sock",
            config=_config(tmp_path),
            broker_seat_id="dev-4",
            host_repo_path="/host/workspaces/creator-engine",
            once=False,
            allow_credential_requests=False,
            activated_socket=listener,
            courier_fn=fake_courier,
        )

    assert failed_connection.responses == []
    assert json.loads(valid_connection.responses[0])["status"] == 200
    assert courier_calls == ["ce242-live-self-push"]


def test_serve_unix_socket_push_refused_returns_403(tmp_path):
    socket_path = tmp_path / "push-refused.sock"
    spy = _HostSpy()

    def refuse_push(token):
        raise PushRefused("non-fast-forward")

    server_thread, server_exceptions = _start_looping_socket_server(
        socket_path,
        tmp_path,
        courier_fn=contained_seat_self_push,
        read_facts_fn=lambda: _GOOD_FACTS,
        resolve_id_fn=spy.resolve_id,
        mint_fn=spy.mint,
        push_fn=refuse_push,
        open_pr_fn=spy.open_pr,
        revoke_fn=spy.revoke,
        declared_work_class="story",
    )

    response = _send_socket_request(socket_path)
    second_response = _send_socket_request(socket_path)

    assert response["status"] == 403
    assert response["reason"] == "egress_refused"
    assert second_response["status"] == 403
    assert [call[0] for call in spy.calls] == [
        "resolve_id", "mint", "revoke", "resolve_id", "mint", "revoke",
    ]
    assert server_exceptions == []
    assert server_thread.is_alive()


def test_serve_unix_socket_forge_config_error_returns_500(tmp_path):
    socket_path = tmp_path / "forge-config-error.sock"

    def mint_failure(*args, **kwargs):
        raise ForgeConfigError("mint failed")

    server_thread, server_exceptions = _start_looping_socket_server(
        socket_path,
        tmp_path,
        courier_fn=mint_failure,
    )

    response = _send_socket_request(socket_path)
    second_response = _send_socket_request(socket_path)

    assert response == {
        "status": 500,
        "reason": "broker_internal_error",
        "error_class": "ForgeConfigError",
    }
    assert second_response["status"] == 500
    assert server_exceptions == []
    assert server_thread.is_alive()


def test_serve_unix_socket_half_closed_client(tmp_path):
    socket_path = tmp_path / "self-push.sock"
    courier_started = threading.Event()
    release_response = threading.Event()
    server_exceptions = []
    courier_calls = []

    def fake_courier(request, *, config, apply, **kw):
        courier_calls.append(request.branch)
        if len(courier_calls) == 1:
            courier_started.set()
            assert release_response.wait(timeout=2)
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

    def run_server():
        try:
            serve_self_push_unix_socket(
                socket_path,
                config=_config(tmp_path),
                broker_seat_id="dev-4",
                host_repo_path="/host/workspaces/creator-engine",
                apply_default=True,
                once=False,
                allow_credential_requests=False,
                courier_fn=fake_courier,
            )
        except Exception as exc:  # pragma: no cover - asserted through server_exceptions
            server_exceptions.append(exc)

    server_thread = threading.Thread(target=run_server, daemon=True)
    server_thread.start()

    with _connect_when_ready(socket_path) as client:
        client.sendall((json.dumps(_request()) + "\n").encode("utf-8"))
        assert courier_started.wait(timeout=2)

    release_response.set()

    with _connect_when_ready(socket_path) as client:
        client.settimeout(2)
        client.sendall((json.dumps(_request()) + "\n").encode("utf-8"))
        data = b""
        while b"\n" not in data:
            chunk = client.recv(65536)
            assert chunk
            data += chunk

    response = json.loads(data.decode("utf-8"))
    assert response["status"] == 200
    assert response["pr_number"] == 242
    assert courier_calls == ["ce242-live-self-push", "ce242-live-self-push"]
    assert server_exceptions == []
    assert server_thread.is_alive()
