"""Focused tests for v3 brownfield apply refusal messages."""

from __future__ import annotations

from pathlib import Path

import pytest

from creator_engine_validator import onboard_apply, v3_cli, v3_installer

_REPO_ROOT = Path(__file__).resolve().parents[3]

_GOOD_ANSWERS_YAML = """\
answers_version: 1
profile: solo-pilot
host:
  sudo_grant: [git, python, runsc, proxy]
cost:
  profile: default
provider:
  harness: claude-code
  anthropic_api_key: env://ANTHROPIC_API_KEY
github:
  mode: existing
  repo: acme/app
  bootstrap_token: prompt://github-bootstrap-token
  app:
    kind: shared
    installation_id: 12345678
  protections: reference
  reviewer: operator
"""


@pytest.fixture(autouse=True)
def _clear_forge_env(monkeypatch):
    for name in (
        "CE_FORGE_LIVE_FORGE",
        "CE_FORGE_ADOPTION_WRITE",
        "CE_FORGE_APP_CLIENT_ID",
        "CE_FORGE_INSTALLATION_ID",
        "CE_FORGE_APP_PEM",
        "CE_FORGE_MINT_BROKER_URL",
        "CE_FORGE_MINT_BROKER_USER_TOKEN",
    ):
        monkeypatch.delenv(name, raising=False)


@pytest.fixture(autouse=True)
def _ssh_keygen_present_for_stubbed_cli_verifier(monkeypatch):
    original_which = v3_cli.shutil.which

    def fake_which(command, *args, **kwargs):
        if command == "ssh-keygen":
            return "/usr/bin/ssh-keygen"
        return original_which(command, *args, **kwargs)

    monkeypatch.setattr(v3_cli.shutil, "which", fake_which)


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
    spec = tmp_path / "signed-install.md"
    spec.write_text(
        canonical.replace("  value: <published-with-this-spec>", "  value: c2ln").replace(
            "  content_sha256: <published-with-this-spec>",
            f"  content_sha256: {digest}",
        ),
        encoding="utf-8",
    )
    return spec


def _answers_file(tmp_path: Path) -> Path:
    path = tmp_path / "ce-install.answers.yaml"
    path.write_text(_GOOD_ANSWERS_YAML, encoding="utf-8")
    return path


def _brownfield_cli_probe() -> dict:
    return {
        "enabled": True,
        "project_root": ".",
        "history": {
            "mode": "git_history_present",
            "head_sha": "a" * 40,
            "default_branch": "main",
            "commit_count": 1,
            "dirty": False,
        },
        "github": {"origin_remote": "acme/app"},
        "ci": {"workflows": [], "current_required_checks": [], "workflow_present": False},
        "tests": {"commands": []},
        "conventions": {"branch_patterns": [], "commit_styles": []},
        "secrets": {
            "preflight": "required",
            "status": "not_run",
            "scanner_available": None,
            "findings": [],
        },
    }


def _run_brownfield_apply_refusal(tmp_path: Path, capsys, monkeypatch) -> tuple[int, str]:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(
        v3_cli,
        "_which",
        lambda tool: tool in ("git", "python", "uv", "runsc", "proxy", "claude"),
    )
    monkeypatch.setattr(v3_cli, "_ssh_keygen_verify_runner", lambda **_kw: True)
    monkeypatch.setattr(v3_cli, "_detect_brownfield_project", lambda _root: _brownfield_cli_probe())
    monkeypatch.setattr(v3_cli.onboard_apply, "repo_is_already_ce_governed", lambda *a, **k: False)

    def should_not_apply(*_args, **_kwargs):
        raise AssertionError("brownfield apply must refuse before the E2 executor runs")

    monkeypatch.setattr(onboard_apply, "apply_onboard", should_not_apply)
    code = v3_cli.main(
        [
            "install",
            "--spec",
            str(_signed_spec(tmp_path)),
            "--answers",
            str(_answers_file(tmp_path)),
            "--answers-schema",
            str(_REPO_ROOT / v3_installer.ANSWERS_SCHEMA_PATH),
            "--apply",
        ]
    )
    return code, capsys.readouterr().out


def test_brownfield_apply_vars_never_set_keeps_existing_refusal_message(
    tmp_path, capsys, monkeypatch
):
    code, out = _run_brownfield_apply_refusal(tmp_path, capsys, monkeypatch)

    assert code == 1
    assert (
        "E3 brownfield adoption is planned, but this onboard_apply run is not authorized "
        "for the adoption write escalation (set CE_FORGE_LIVE_FORGE + CE_FORGE_ADOPTION_WRITE)"
    ) in out


def test_brownfield_apply_vars_set_but_credentials_unresolved_names_credential_blocker(
    tmp_path, capsys, monkeypatch
):
    monkeypatch.setenv("CE_FORGE_LIVE_FORGE", "1")
    monkeypatch.setenv("CE_FORGE_ADOPTION_WRITE", "1")

    code, out = _run_brownfield_apply_refusal(tmp_path, capsys, monkeypatch)

    assert code == 1
    assert "cannot resolve the App credential for the adoption write escalation" in out
    assert "local PEM for kind: own or broker for kind: shared" in out
    assert "set CE_FORGE_LIVE_FORGE + CE_FORGE_ADOPTION_WRITE" not in out
