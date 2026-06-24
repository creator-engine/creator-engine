from __future__ import annotations

import csv
import os
import subprocess
from pathlib import Path


def _run_script(repo_root: Path, *args: str, env: dict[str, str]):
    return subprocess.run(
        [str(repo_root / "docs/devops/openbao/bringup-container-openbao.sh"), *args],
        env=env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )


def test_container_bringup_plan_is_dry_run_value_free(repo_root: Path, tmp_path: Path):
    completed = _run_script(
        repo_root,
        "--plan",
        env={
            **os.environ,
            "OPENBAO_CONTAINER_ENGINE": "container-tool",
            "OPENBAO_CONTAINER_WORKDIR": str(tmp_path / "openbao"),
            "OPENBAO_DEV_IDS": "dev-1,dev-2",
        },
    )

    assert completed.returncode == 0
    assert "Dry-run status: no container commands executed" in completed.stdout
    assert "bao operator init -key-shares=1 -key-threshold=1 -format=json" in completed.stdout
    assert "ce-kv/data/devs/<dev>/runtime/claude-code-oauth-token" in completed.stdout
    assert "ce-kv/data/forge/github-apps/creator-engine-shared/private-key" in completed.stdout
    assert "ce-transit/governance/signing/ce-root-v1" in completed.stdout
    assert not (tmp_path / "openbao").exists()
    assert "hvs." not in completed.stdout
    assert "root_token" not in completed.stdout


def test_container_bringup_refuses_repo_workdir(repo_root: Path):
    completed = _run_script(
        repo_root,
        "--plan",
        env={
            **os.environ,
            "OPENBAO_CONTAINER_ENGINE": "container-tool",
            "OPENBAO_CONTAINER_WORKDIR": str(repo_root / "tmp" / "openbao"),
        },
    )

    assert completed.returncode == 78
    assert "refusing workdir inside repository" in completed.stderr


def test_openbao_secret_path_map_covers_track_b_names_value_free(repo_root: Path):
    path_map = repo_root / "docs/devops/openbao/openbao-secret-path-map.tsv"
    rows = list(csv.DictReader(path_map.open(encoding="utf-8"), delimiter="\t"))

    names = {row["secret_name"]: row for row in rows}
    assert "per-dev-github-pat" in names
    assert "claude-code-oauth-token" in names
    assert "github-app-creator-engine-shared-pem" in names
    assert "github-app-creator-engine-shared-config" in names
    assert "github-app-creator-engine-dev-config-family" in names
    assert "github-app-reviewer-config" in names
    assert "github-app-reviewer-pem" in names
    assert "ce-root-v1-private-signing-key" in names
    assert names["per-dev-github-pat"]["openbao_ref"] == (
        "openbao-ref:ce-kv/devs/dev-N/runtime/github-pat"
    )
    assert names["claude-code-oauth-token"]["openbao_ref"] == (
        "openbao-ref:ce-kv/devs/dev-N/runtime/claude-code-oauth-token"
    )
    assert names["github-app-creator-engine-shared-pem"]["field"] == "pem"
    assert names["github-app-creator-engine-shared-config"]["field"] == "json"
    assert names["github-app-reviewer-pem"]["openbao_ref"] == (
        "openbao-ref:ce-kv/forge/github-apps/reviewer/private-key"
    )
    assert names["ce-root-v1-private-signing-key"]["mount"] == "ce-transit"

    target_refs = [row["openbao_ref"] for row in rows]
    assert len(target_refs) == len(set(target_refs))
    joined = "\n".join("\t".join(row.values()) for row in rows)
    for marker in ("hvs.", "hvb.", "bao.", "-----BEGIN", "password=", "client_secret="):
        assert marker not in joined


def test_openbao_runbooks_document_live_tests_and_launcher_cutover(repo_root: Path):
    production = (repo_root / "docs/devops/openbao-production-golive.md").read_text(
        encoding="utf-8"
    )
    operator = (repo_root / "docs/devops/openbao-operator-bringup.md").read_text(
        encoding="utf-8"
    )

    assert "bringup-container-openbao.sh --apply" in production
    assert "tests/integration/test_openbao_p3_live.py" in production
    assert "tests/integration/test_openbao_golive_restore_drill_live.py" in production
    assert "CE_OPENBAO_GOLIVE_DOWNLOAD_SMOKE=1" in production
    assert "deploy/dgx-controller-runsc/run-controller-runsc.sh" in production
    assert "deploy/vps-runsc/run-vps-runsc.sh" in production
    assert "CLAUDE_CODE_OAUTH_TOKEN" in production
    assert "SecretIdentityBackend" in operator
    assert "secret-ref:ce-kv/devs/<dev>/runtime/claude-code-oauth-token" in operator
