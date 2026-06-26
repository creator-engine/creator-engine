from __future__ import annotations

import http.server
import json
import os
import socket
import socketserver
import subprocess
import threading
import time
from pathlib import Path

import pytest

from creator_engine_validator.openbao_p3 import (
    AuditFailClosedProbe,
    OpenBaoHttpConfig,
    WrappedAppRoleBootstrapConfig,
    make_openbao_http_runner,
    unwrap_wrapped_approle_secret_id,
    verify_audit_fail_closed,
)
from creator_engine_validator.secret_identity import (
    OpenBaoSecretIdentityBackend,
    SecretRef,
    SecretRequest,
)
pytestmark = pytest.mark.slow



def _free_port() -> int:
    sock = socket.socket()
    sock.bind(("127.0.0.1", 0))
    port = sock.getsockname()[1]
    sock.close()
    return port


class _AuditHandler(http.server.BaseHTTPRequestHandler):
    def do_POST(self) -> None:
        length = int(self.headers.get("content-length", "0"))
        if length:
            self.rfile.read(length)
        self.send_response(204)
        self.end_headers()

    def log_message(self, *_args) -> None:
        return None


def _run_bao(bin_path: Path, env: dict[str, str], *args: str) -> str:
    completed = subprocess.run(
        [str(bin_path), *args],
        env=env,
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    return completed.stdout


@pytest.mark.skipif(not os.environ.get("CE_OPENBAO_BIN"), reason="CE_OPENBAO_BIN not set")
def test_openbao_p3_live_wrapped_approle_and_audit_fail_closed(tmp_path: Path):
    bao_bin = Path(os.environ["CE_OPENBAO_BIN"])
    audit_port = _free_port()
    bao_port = _free_port()
    tls_dir = tmp_path / "tls"
    tls_dir.mkdir()

    audit_server = socketserver.TCPServer(("127.0.0.1", audit_port), _AuditHandler)
    audit_thread = threading.Thread(target=audit_server.serve_forever, daemon=True)
    audit_thread.start()

    config = tmp_path / "openbao.hcl"
    config.write_text(
        f'''audit "http" "http" {{
  description = "local p3 http audit"
  options {{
    uri = "http://127.0.0.1:{audit_port}/audit"
    write_timeout = "1s"
  }}
}}
''',
        encoding="utf-8",
    )
    server_log = (tmp_path / "server.log").open("w", encoding="utf-8")
    proc = subprocess.Popen(
        [
            str(bao_bin),
            "server",
            "-dev",
            "-dev-tls",
            f"-dev-tls-cert-dir={tls_dir}",
            "-dev-root-token-id=root",
            f"-dev-listen-address=127.0.0.1:{bao_port}",
            "-dev-no-store-token",
            f"-config={config}",
        ],
        stdout=server_log,
        stderr=subprocess.STDOUT,
        text=True,
    )
    try:
        ca_path = tls_dir / "vault-ca.pem"
        address = f"https://127.0.0.1:{bao_port}"
        for _ in range(100):
            if ca_path.exists():
                try:
                    with subprocess.Popen(
                        [str(bao_bin), "status", "-format=json"],
                        env={
                            **os.environ,
                            "BAO_ADDR": address,
                            "BAO_TOKEN": "root",
                            "BAO_CACERT": str(ca_path),
                        },
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                    ) as status_proc:
                        if status_proc.wait(timeout=1) == 0:
                            break
                except Exception:
                    pass
            time.sleep(0.1)
        else:
            pytest.fail("local OpenBao dev server did not become ready")

        root_env = {
            **os.environ,
            "BAO_ADDR": address,
            "BAO_TOKEN": "root",
            "BAO_CACERT": str(ca_path),
        }
        policy = tmp_path / "ce-broker.hcl"
        policy.write_text(
            '''
path "sys/audit" {
  capabilities = ["read", "sudo"]
}
path "secret/data/canary" {
  capabilities = ["read"]
}
''',
            encoding="utf-8",
        )
        _run_bao(bao_bin, root_env, "policy", "write", "ce-broker", str(policy))
        _run_bao(bao_bin, root_env, "auth", "enable", "approle")
        _run_bao(
            bao_bin,
            root_env,
            "write",
            "auth/approle/role/ce-broker",
            "token_policies=ce-broker",
            "token_ttl=5m",
            "token_max_ttl=5m",
            "secret_id_num_uses=1",
            "secret_id_ttl=3m",
        )
        role_id = _run_bao(
            bao_bin,
            root_env,
            "read",
            "-field=role_id",
            "auth/approle/role/ce-broker/role-id",
        ).strip()
        wrapped = json.loads(
            _run_bao(
                bao_bin,
                root_env,
                "write",
                "-format=json",
                "-wrap-ttl=2m",
                "-f",
                "auth/approle/role/ce-broker/secret-id",
            )
        )
        wrapping_token = wrapped["wrap_info"]["token"]
        _run_bao(bao_bin, root_env, "kv", "put", "secret/canary", "ok=local-canary")

        runner = make_openbao_http_runner(
            OpenBaoHttpConfig(address=address, ca_bundle=str(ca_path), timeout_seconds=5)
        )
        session = unwrap_wrapped_approle_secret_id(
            WrappedAppRoleBootstrapConfig(
                role_name="ce-broker",
                role_id_supplier=lambda: role_id,
                wrapping_token_supplier=lambda: wrapping_token,
            ),
            runner=runner,
        )
        ref = SecretRef(
            backend="openbao",
            mount="secret",
            path="canary",
            field="ok",
            version=1,
            purpose="runtime-canary",
            owner_ref="local-p3",
            policy_sha="a" * 64,
        )
        materialized: list[tuple[str, str]] = []
        backend = OpenBaoSecretIdentityBackend(
            session.as_openbao_config(address=address, kv_mount="secret", verify_tls=True),
            runner=runner,
            materializer=lambda target_ref, value: materialized.append((target_ref, value)),
            allowed_refs={ref},
        )
        grant = backend.issue(
            SecretRequest(
                run_id="local-p3",
                seat_id="dev-1",
                repo="creator-engine/creator-engine",
                secret_ref=ref,
                ttl_seconds=300,
                delivery="file",
                requested_capabilities=("read",),
            )
        )
        backend.materialize(grant, "tmpfs:/run/ce/local-canary")
        assert materialized == [("tmpfs:/run/ce/local-canary", "local-canary")]

        result = verify_audit_fail_closed(
            AuditFailClosedProbe(
                token_supplier=session.token_supplier,
                canary_path="/v1/secret/data/canary",
            ),
            runner=runner,
            break_audit=lambda: (
                audit_server.shutdown(),
                audit_server.server_close(),
                audit_thread.join(timeout=2),
            ),
        )
        assert result.before_status == 200
        assert result.after_status >= 400
        assert result.fail_closed is True
    finally:
        if proc.poll() is None:
            proc.terminate()
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()
        server_log.close()
        try:
            audit_server.server_close()
        except Exception:
            pass
