"""Clean-room install S1 blocker regressions."""
from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import yaml

from creator_engine_validator import v3_cli, v3_installer

_REPO_ROOT = Path(__file__).resolve().parents[3]


def _signed_spec(tmp_path: Path) -> Path:
    canonical = """\
kind: ce-install-spec
signature:
  key_id: ce-root-v1
  algo: ssh-ed25519
  namespace: ce-spec-v1
  value: <published-with-this-spec>
  content_sha256: <published-with-this-spec>
"""
    digest = v3_installer.content_digest(v3_installer.canonical_spec_bytes(canonical))
    path = tmp_path / "signed-install.md"
    path.write_text(
        canonical.replace("  value: <published-with-this-spec>", "  value: c2ln").replace(
            "  content_sha256: <published-with-this-spec>",
            f"  content_sha256: {digest}",
        ),
        encoding="utf-8",
    )
    return path


def _greenfield_codex_answers(tmp_path: Path) -> Path:
    path = tmp_path / "answers.yaml"
    path.write_text(
        yaml.safe_dump(
            {
                "answers_version": 1,
                "profile": "solo-pilot",
                "host": {
                    "sudo_grant": ["git", "python", "runsc", "proxy"],
                    "userspace_install": True,
                    "workspace_root": str(tmp_path / "workspaces"),
                },
                "provider": {"harness": "codex", "openai_api_key": "env://OPENAI_API_KEY"},
                "github": {
                    "mode": "new",
                    "repo": "octo/greenfield",
                    "new_repo": {"visibility": "private", "default_branch": "main"},
                    "bootstrap_token": "env://CE_BOOTSTRAP",
                    "app": {"kind": "shared", "installation_id": 12345},
                    "protections": "reference",
                    "reviewer": "octo",
                },
                "project": {"name": "greenfield", "scaffold": {"kind": "minimal"}},
            },
            sort_keys=True,
        ),
        encoding="utf-8",
    )
    return path


def _brownfield_probe_without_origin() -> dict:
    return {
        "enabled": True,
        "project_root": ".",
        "history": {
            "mode": "git_history_absent",
            "head_sha": None,
            "default_branch": None,
            "commit_count": 0,
            "dirty": False,
        },
        "github": {"origin_remote": None},
        "ci": {"workflows": [], "current_required_checks": [], "workflow_present": False},
        "tests": {"commands": []},
        "conventions": {"branch_patterns": [], "commit_styles": []},
        "secrets": {"preflight": "required", "status": "not_run", "scanner_available": None, "findings": []},
    }


def test_install_sh_refuses_missing_git_before_file_not_found(tmp_path: Path):
    bash = shutil.which("bash")
    assert bash is not None
    env = {
        "HOME": str(tmp_path / "home"),
        "PATH": str(tmp_path / "empty-bin"),
        "CE_INSTALLER_TEST_MODE": "1",
    }
    Path(env["PATH"]).mkdir()

    proc = subprocess.run(
        [bash, str(_REPO_ROOT / "docs" / "install.sh"), "--inventory-only"],
        cwd=_REPO_ROOT,
        env=env,
        check=False,
        capture_output=True,
        text=True,
        timeout=10,
    )

    combined = proc.stdout + proc.stderr
    assert proc.returncode != 0
    assert "missing_bootstrap_dependency" in combined
    assert "git" in combined.lower()
    assert "install" in combined.lower()
    assert "FileNotFoundError" not in combined


def test_onboard_plan_warns_for_missing_spawn_prereqs(tmp_path, capsys, monkeypatch):
    monkeypatch.setattr(v3_cli, "_ssh_keygen_verify_runner", lambda **_kw: True)
    monkeypatch.setattr(v3_cli, "_detect_brownfield_project", lambda _root: _brownfield_probe_without_origin())
    monkeypatch.setattr(v3_cli, "_which", lambda tool: tool in {"git", "python", "uv"})

    code = v3_cli.main([
        "onboard",
        "--spec",
        str(_signed_spec(tmp_path)),
        "--answers",
        str(_greenfield_codex_answers(tmp_path)),
        "--plan",
        "--spawn-smoke",
        "--json",
    ])

    payload = json.loads(capsys.readouterr().out)
    assert code == 0, payload
    prereqs = {item["id"]: item for item in payload["prerequisites"]}
    assert prereqs["tmux"]["available"] is False
    assert prereqs["codex"]["available"] is False
    assert {warning["prerequisite"] for warning in payload["warnings"]} >= {"tmux", "codex"}
