from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

from creator_engine_validator.openbao_golive import (
    GO_LIVE_ARTIFACTS,
    read_go_live_artifact,
    validate_emergency_revoke_script,
    validate_provision_script,
    validate_snapshot_restore_scripts,
    validate_systemd_unit,
    validate_tailnet_tls_hcl,
)


def _write_executable(path: Path, text: str) -> Path:
    path.write_text(text, encoding="utf-8")
    path.chmod(0o755)
    return path


def test_openbao_golive_artifacts_exist(repo_root: Path):
    missing = [path for path in GO_LIVE_ARTIFACTS if not (repo_root / path).is_file()]
    assert missing == []


def test_openbao_hcl_is_raft_tailnet_tls_and_audit_fail_closed(repo_root: Path):
    hcl = read_go_live_artifact(repo_root, "docs/devops/openbao/openbao.hcl.tmpl")

    assert validate_tailnet_tls_hcl(hcl) == []
    assert "0.0.0.0" not in hcl
    assert "tls_disable = true" not in hcl


def test_openbao_systemd_unit_uses_dedicated_user_and_hardening(repo_root: Path):
    unit = read_go_live_artifact(repo_root, "docs/devops/openbao/openbao.service")

    assert validate_systemd_unit(unit) == []
    assert "User=root" not in unit


def test_openbao_provision_script_is_idempotent_and_not_trust_root(repo_root: Path):
    script = read_go_live_artifact(repo_root, "docs/devops/openbao/provision-openbao.sh")

    assert validate_provision_script(script) == []


def test_openbao_snapshot_restore_scripts_are_encrypted_and_proof_oriented(repo_root: Path):
    snapshot = read_go_live_artifact(repo_root, "docs/devops/openbao/snapshot-openbao.sh")
    restore = read_go_live_artifact(repo_root, "docs/devops/openbao/restore-drill-openbao.sh")

    assert validate_snapshot_restore_scripts(snapshot, restore) == []


def test_openbao_emergency_revoke_script_covers_per_dev_actions(repo_root: Path):
    script = read_go_live_artifact(repo_root, "docs/devops/openbao/emergency-revoke-openbao.sh")

    assert validate_emergency_revoke_script(script) == []


def test_provision_plan_refuses_public_listener(repo_root: Path):
    script = repo_root / "docs/devops/openbao/provision-openbao.sh"
    env = {
        **os.environ,
        "OPENBAO_TAILNET_HOSTNAME": "openbao.example.ts.net",
        "OPENBAO_TAILNET_BIND_ADDR": "0.0.0.0",
    }

    completed = subprocess.run(
        [str(script), "--plan"],
        env=env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )

    assert completed.returncode == 78
    assert "refusing public OpenBao listener address" in completed.stderr


def test_provision_plan_renders_tailnet_bound_config(repo_root: Path):
    script = repo_root / "docs/devops/openbao/provision-openbao.sh"
    env = {
        **os.environ,
        "OPENBAO_TAILNET_HOSTNAME": "openbao.example.ts.net",
        "OPENBAO_TAILNET_BIND_ADDR": "100.64.10.20",
    }

    completed = subprocess.run(
        [str(script), "--plan"],
        env=env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=True,
    )

    assert 'storage "raft"' in completed.stdout
    assert 'address         = "100.64.10.20:8200"' in completed.stdout
    assert "tls_disable      = false" in completed.stdout
    assert 'audit "file" "ce_audit"' in completed.stdout
    assert "operator init" not in completed.stdout
    assert "operator unseal" not in completed.stdout


def test_snapshot_script_encrypts_and_copies_offhost_for_local_drill(
    repo_root: Path,
    tmp_path: Path,
):
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    log = tmp_path / "calls.log"
    _write_executable(
        bin_dir / "bao",
        f"""#!/usr/bin/env bash
set -euo pipefail
echo "$@" >> {log}
if [[ "$*" == "operator raft snapshot save "* ]]; then
  printf 'raft-snapshot' > "${{@: -1}}"
fi
""",
    )
    _write_executable(
        bin_dir / "age",
        """#!/usr/bin/env bash
set -euo pipefail
out=''
input=''
while [[ $# -gt 0 ]]; do
  case "$1" in
    -o) out="$2"; shift 2 ;;
    -r) shift 2 ;;
    *) input="$1"; shift ;;
  esac
done
printf 'encrypted:' > "$out"
cat "$input" >> "$out"
""",
    )
    offhost = tmp_path / "offhost"
    offhost.mkdir()
    workdir = tmp_path / "work"
    env = {
        **os.environ,
        "PATH": f"{bin_dir}:{os.environ['PATH']}",
        "OPENBAO_SNAPSHOT_WORKDIR": str(workdir),
        "OPENBAO_AGE_RECIPIENT": "age1testrecipient",
        "OPENBAO_SNAPSHOT_REMOTE_URI": f"file:{offhost}",
        "OPENBAO_SNAPSHOT_ALLOW_LOCAL": "1",
    }

    subprocess.run(
        [str(repo_root / "docs/devops/openbao/snapshot-openbao.sh")],
        env=env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=True,
    )

    encrypted = sorted(offhost.glob("*.snap.age"))
    checksums = sorted(offhost.glob("*.snap.age.sha256"))
    assert len(encrypted) == 1
    assert len(checksums) == 1
    assert encrypted[0].read_text(encoding="utf-8") == "encrypted:raft-snapshot"
    assert "operator raft snapshot save" in log.read_text(encoding="utf-8")


def test_restore_drill_script_restores_throwaway_and_writes_proof(
    repo_root: Path,
    tmp_path: Path,
):
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    log = tmp_path / "calls.log"
    _write_executable(
        bin_dir / "bao",
        f"""#!/usr/bin/env bash
set -euo pipefail
echo "$@" >> {log}
if [[ "$*" == "read -format=json "* ]]; then
  printf '{{"data":{{"data":{{"ok":"restored"}}}}}}'
fi
""",
    )
    _write_executable(
        bin_dir / "age",
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
    )
    encrypted = tmp_path / "snapshot.snap.age"
    encrypted.write_text("encrypted-snapshot", encoding="utf-8")
    identity = tmp_path / "identity.txt"
    identity.write_text("AGE-SECRET-KEY-test", encoding="utf-8")
    proof = tmp_path / "proof.json"
    env = {
        **os.environ,
        "PATH": f"{bin_dir}:{os.environ['PATH']}",
        "OPENBAO_RESTORE_DRILL_CONFIRM": "throwaway",
        "OPENBAO_RESTORE_DRILL_ADDR": "http://127.0.0.1:18200",
        "OPENBAO_ENCRYPTED_SNAPSHOT": str(encrypted),
        "OPENBAO_AGE_IDENTITY": str(identity),
        "OPENBAO_RESTORE_TOKEN": "target-drill-token",
        "OPENBAO_VERIFY_TOKEN": "restored-snapshot-token",
        "RESTORE_DRILL_PROOF": str(proof),
        "PYTHON_BIN": sys.executable,
    }

    subprocess.run(
        [str(repo_root / "docs/devops/openbao/restore-drill-openbao.sh")],
        env=env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=True,
    )

    calls = log.read_text(encoding="utf-8")
    assert "operator raft snapshot restore -force" in calls
    assert "read -format=json secret/data/ce-openbao-restore-canary" in calls
    payload = json.loads(proof.read_text(encoding="utf-8"))
    assert payload["ok"] is True
    assert payload["canary_field"] == "ok"


def test_emergency_revoke_execute_approle_uses_per_dev_identity(
    repo_root: Path,
    tmp_path: Path,
):
    fake_bao = _write_executable(
        tmp_path / "bao",
        f"""#!/usr/bin/env bash
set -euo pipefail
echo "$@" >> {tmp_path / "bao.log"}
""",
    )
    env = {
        **os.environ,
        "BAO_BIN": str(fake_bao),
        "CE_DEV_ID": "dev-1",
        "OPENBAO_SECRET_ID_ACCESSOR": "secret-accessor",
        "OPENBAO_TOKEN_ACCESSOR": "token-accessor",
    }

    subprocess.run(
        [str(repo_root / "docs/devops/openbao/emergency-revoke-openbao.sh"), "--execute", "approle"],
        env=env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=True,
    )

    calls = (tmp_path / "bao.log").read_text(encoding="utf-8")
    assert "write auth/approle/role/ce-dev-1/secret-id-accessor/destroy secret_id_accessor=secret-accessor" in calls
    assert "token revoke -accessor token-accessor" in calls
