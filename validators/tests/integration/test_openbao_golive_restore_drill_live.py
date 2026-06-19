from __future__ import annotations

import os
import socket
import subprocess
import sys
import time
from pathlib import Path

import pytest


def _free_port() -> int:
    sock = socket.socket()
    sock.bind(("127.0.0.1", 0))
    port = sock.getsockname()[1]
    sock.close()
    return port


def _wait_tcp(port: int, proc: subprocess.Popen, log_path: Path) -> None:
    for _ in range(200):
        sock = socket.socket()
        sock.settimeout(0.2)
        try:
            sock.connect(("127.0.0.1", port))
            return
        except OSError:
            if proc.poll() is not None:
                pytest.fail(f"OpenBao server exited early:\n{log_path.read_text(encoding='utf-8')}")
            time.sleep(0.1)
        finally:
            sock.close()
    pytest.fail(f"OpenBao server did not listen on {port}:\n{log_path.read_text(encoding='utf-8')}")


def _run_bao(bao_bin: Path, env: dict[str, str], *args: str) -> str:
    completed = subprocess.run(
        [str(bao_bin), *args],
        env=env,
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    return completed.stdout


def _json_field(payload: str, expression: str) -> str:
    import json

    value = json.loads(payload)
    for part in expression.split("."):
        if part.endswith("]"):
            key, index = part[:-1].split("[", 1)
            value = value[key][int(index)]
        else:
            value = value[part]
    return str(value)


def _start_raft_server(bao_bin: Path, root: Path, node_id: str) -> tuple[subprocess.Popen, str]:
    api_port = _free_port()
    cluster_port = _free_port()
    raft_path = root / "raft"
    raft_path.mkdir(parents=True)
    config = root / "openbao.hcl"
    config.write_text(
        f'''ui = false
api_addr = "http://127.0.0.1:{api_port}"
cluster_addr = "http://127.0.0.1:{cluster_port}"
storage "raft" {{ path = "{raft_path}" node_id = "{node_id}" }}
listener "tcp" {{ address = "127.0.0.1:{api_port}" cluster_address = "127.0.0.1:{cluster_port}" tls_disable = true }}
''',
        encoding="utf-8",
    )
    log_path = root / "server.log"
    log = log_path.open("w", encoding="utf-8")
    proc = subprocess.Popen(
        [str(bao_bin), "server", f"-config={config}"],
        stdout=log,
        stderr=subprocess.STDOUT,
        text=True,
    )
    _wait_tcp(api_port, proc, log_path)
    log.close()
    return proc, f"http://127.0.0.1:{api_port}"


@pytest.mark.skipif(not os.environ.get("CE_OPENBAO_BIN"), reason="CE_OPENBAO_BIN not set")
def test_openbao_golive_restore_drill_script_against_throwaway_raft(
    repo_root: Path,
    tmp_path: Path,
):
    bao_bin = Path(os.environ["CE_OPENBAO_BIN"])
    source_proc: subprocess.Popen | None = None
    target_proc: subprocess.Popen | None = None
    try:
        source_proc, source_addr = _start_raft_server(bao_bin, tmp_path / "source", "source")
        source_base_env = {**os.environ, "BAO_ADDR": source_addr}
        init1 = _run_bao(
            bao_bin,
            source_base_env,
            "operator",
            "init",
            "-key-shares=1",
            "-key-threshold=1",
            "-format=json",
        )
        source_key = _json_field(init1, "unseal_keys_b64[0]")
        source_root = _json_field(init1, "root_token")
        _run_bao(bao_bin, source_base_env, "operator", "unseal", source_key)
        source_env = {**source_base_env, "BAO_TOKEN": source_root}
        _run_bao(bao_bin, source_env, "secrets", "enable", "-path=ce-kv", "kv-v2")
        _run_bao(
            bao_bin,
            source_env,
            "kv",
            "put",
            "ce-kv/devs/dev-1/runtime/restore-canary",
            "ok=restored",
        )
        snapshot = tmp_path / "source.snap"
        _run_bao(bao_bin, source_env, "operator", "raft", "snapshot", "save", str(snapshot))
        source_proc.terminate()
        source_proc.wait(timeout=10)
        source_proc = None

        target_proc, target_addr = _start_raft_server(bao_bin, tmp_path / "target", "target")
        target_base_env = {**os.environ, "BAO_ADDR": target_addr}
        init2 = _run_bao(
            bao_bin,
            target_base_env,
            "operator",
            "init",
            "-key-shares=1",
            "-key-threshold=1",
            "-format=json",
        )
        target_key = _json_field(init2, "unseal_keys_b64[0]")
        target_root = _json_field(init2, "root_token")
        _run_bao(bao_bin, target_base_env, "operator", "unseal", target_key)

        bin_dir = tmp_path / "bin"
        bin_dir.mkdir()
        fake_age = bin_dir / "age"
        fake_age.write_text(
            """#!/usr/bin/env bash
set -euo pipefail
out=''
input=''
while [[ $# -gt 0 ]]; do
  case "$1" in
    -d) shift ;;
    -i) shift 2 ;;
    -o) out="$2"; shift 2 ;;
    *) input="$1"; shift ;;
  esac
done
cp "$input" "$out"
""",
            encoding="utf-8",
        )
        fake_age.chmod(0o755)
        encrypted_snapshot = tmp_path / "source.snap.age"
        encrypted_snapshot.write_bytes(snapshot.read_bytes())
        identity = tmp_path / "age-identity.txt"
        identity.write_text("AGE-SECRET-KEY-local-drill\n", encoding="utf-8")
        source_key_file = tmp_path / "source-unseal-key.txt"
        source_key_file.write_text(source_key, encoding="utf-8")
        proof = tmp_path / "restore-proof.json"
        env = {
            **os.environ,
            "PATH": f"{bin_dir}:{os.environ['PATH']}",
            "BAO_BIN": str(bao_bin),
            "PYTHON_BIN": sys.executable,
            "OPENBAO_RESTORE_DRILL_CONFIRM": "throwaway",
            "OPENBAO_RESTORE_DRILL_ADDR": target_addr,
            "OPENBAO_ENCRYPTED_SNAPSHOT": str(encrypted_snapshot),
            "OPENBAO_AGE_IDENTITY": str(identity),
            "OPENBAO_RESTORE_TOKEN": target_root,
            "OPENBAO_VERIFY_TOKEN": source_root,
            "OPENBAO_RESTORE_DRILL_UNSEAL_KEY_FILE": str(source_key_file),
            "OPENBAO_RESTORE_CANARY_PATH": "ce-kv/data/devs/dev-1/runtime/restore-canary",
            "OPENBAO_RESTORE_CANARY_FIELD": "ok",
            "RESTORE_DRILL_PROOF": str(proof),
        }

        subprocess.run(
            [str(repo_root / "docs/devops/openbao/restore-drill-openbao.sh")],
            env=env,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=60,
        )

        assert '"ok": true' in proof.read_text(encoding="utf-8")
    finally:
        for proc in (source_proc, target_proc):
            if proc is not None and proc.poll() is None:
                proc.terminate()
                try:
                    proc.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    proc.kill()
