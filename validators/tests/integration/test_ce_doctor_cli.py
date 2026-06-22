"""RV1-061 — integration tests for ``ce doctor`` against real temp git repos.

These exercise the real host-detection seam (git check-ignore, interpreter,
packaging contract) end-to-end. They never touch a production worktree or
ledger; governed/ungoverned postures are built under pytest ``tmp_path``.
"""
from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import pytest

from creator_engine_validator import ce_cli
from creator_engine_validator import environment_guard as guard


def _git(args, cwd: Path):
    return subprocess.run(["git", *args], cwd=str(cwd), check=True, capture_output=True, text=True)


@pytest.fixture()
def governed_repo(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(["init", "--initial-branch=main"], repo)
    (repo / ".gitignore").write_text(".hermes/\n", encoding="utf-8")
    return repo


@pytest.fixture()
def ungoverned_repo(tmp_path: Path) -> Path:
    repo = tmp_path / "ungoverned"
    repo.mkdir()
    _git(["init", "--initial-branch=main"], repo)
    # no .gitignore -> .hermes/ is NOT ignored -> ungoverned state-path posture
    return repo


def test_doctor_passes_on_governed_temp_repo(governed_repo: Path, capsys):
    ret = ce_cli.main(["doctor", "--json", "--repo-root", str(governed_repo), "--no-check-packaging"])
    assert ret == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["ok"] is True
    assert payload["prerequisites"]["hermes_state_ignored"] is True


def test_doctor_refuses_ungoverned_temp_repo(ungoverned_repo: Path, capsys):
    ret = ce_cli.main(["doctor", "--json", "--repo-root", str(ungoverned_repo), "--no-check-packaging"])
    assert ret != 0
    payload = json.loads(capsys.readouterr().out)
    assert guard.CLAUSE_STATE_PATH in payload["refused_clauses"]


def test_doctor_passes_on_real_kernel_repo_with_packaging_clause(repo_root: Path, capsys):
    # End-to-end proof that the cp314 Option B packaging contract is GREEN under
    # the guard (RED-G-6) on the real kernel repo, on an in-contract interpreter.
    ret = ce_cli.main(["doctor", "--json", "--repo-root", str(repo_root)])
    assert ret == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["ok"] is True
    packaging = [c for c in payload["checks"] if c["clause"] == guard.CLAUSE_PACKAGING][0]
    assert packaging["ok"] is True
    assert payload["prerequisites"]["python_in_contract"] is True
    assert payload["prerequisites"]["dependency_wheelhouse_offline"] is True
    assert payload["prerequisites"]["first_party_app_wheel_committed"] is False


def test_doctor_reports_first_party_app_wheel_separately_from_dependency_wheelhouse(
    tmp_path: Path, repo_root: Path, capsys
):
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(["init", "--initial-branch=main"], repo)
    (repo / ".gitignore").write_text(".hermes/\n", encoding="utf-8")
    validators = repo / "validators"
    validators.mkdir()
    source_validators = repo_root / "validators"
    for filename in ("pyproject.toml", "requirements.txt", "uv.lock"):
        shutil.copy2(source_validators / filename, validators / filename)
    shutil.copytree(source_validators / "wheelhouse", validators / "wheelhouse")
    (validators / "wheelhouse" / "creator_engine_validator-0.2.0-py3-none-any.whl").write_bytes(
        b"reintroduced first-party app wheel"
    )

    ret = ce_cli.main(["doctor", "--json", "--repo-root", str(repo)])

    assert ret != 0
    payload = json.loads(capsys.readouterr().out)
    packaging = [c for c in payload["checks"] if c["clause"] == guard.CLAUSE_PACKAGING][0]
    assert packaging["ok"] is False
    assert "first-party app wheels" in packaging["detail"]
    assert payload["prerequisites"]["wheelhouse_offline"] is True
    assert payload["prerequisites"]["dependency_wheelhouse_offline"] is True
    assert payload["prerequisites"]["dependency_wheelhouse_violations"] == []
    assert payload["prerequisites"]["first_party_app_wheel_committed"] is True


# ---------------------------------------------------------------------------
# RV1-064 — agent-native bootstrap seam (preflight via `ce doctor --json`)
#
# The bootstrap preflight contract IS the doctor surface, so its template +
# doc are validated alongside the doctor integration tests.
# ---------------------------------------------------------------------------

import yaml  # noqa: E402  (kept local to this RV1-064 section)


def _bootstrap_template(repo_root: Path) -> dict:
    path = repo_root / "templates" / "hermes" / "agent-native-bootstrap.yaml"
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def test_bootstrap_template_is_safe_loadable_yaml(repo_root: Path):
    data = _bootstrap_template(repo_root)
    assert isinstance(data, dict)
    assert data["kind"] == "agent-native-bootstrap"


def test_bootstrap_preflight_uses_ce_doctor_json_with_blocked_report(repo_root: Path):
    data = _bootstrap_template(repo_root)
    preflight = data["preflight"]
    assert preflight["command"] == [
        "${CE_VALIDATOR_PYTHON:-.venv/bin/python}",
        "-m",
        "creator_engine_validator.ce_cli",
        "doctor",
        "--json",
    ]
    assert preflight["env"] == {
        "CE_VALIDATOR_PYTHON": "${CE_VALIDATOR_PYTHON:-.venv/bin/python}",
        "PYTHONPATH": "validators",
    }
    assert preflight["requires"] == ["install"]
    assert preflight["on_failure"] == "blocked-report"
    assert preflight["blocked_report"]["stop"] is True


def test_bootstrap_authority_is_one_directional_no_hosted(repo_root: Path):
    data = _bootstrap_template(repo_root)
    assert data["authority_model"]["direction"] == "one-directional"
    assert data["authority_model"]["hosted_team_github_authority"] is False
    boundaries = data["boundaries"]
    assert boundaries["hosted_service"] is False
    assert boundaries["team_mode"] is False
    assert boundaries["github_connector"] is False


def test_bootstrap_install_is_uv_first_with_pip_fallback(repo_root: Path):
    data = _bootstrap_template(repo_root)
    install = data["install"]
    assert install["contract"] == "source-pythonpath-with-offline-runtime-deps"
    assert install["python_floor"] == ">=3.14"
    assert install["validator_python_env"] == "CE_VALIDATOR_PYTHON"
    assert install["validator_python_default"] == ".venv/bin/python"
    assert install["network"] == "forbidden"
    assert install["source_path"] == "validators"
    # uv-first command and a pip fallback are both present and offline.
    assert any("uv" in step for step in install["uv_first"])
    assert any("pip" in step for step in install["pip_fallback"])
    assert any("--python" in step and "${CE_VALIDATOR_PYTHON:-.venv/bin/python}" in step for step in install["uv_first"])
    install_steps = [step for step in install["uv_first"] + install["pip_fallback"] if "install" in step]
    for step in install_steps:
        assert "--no-index" in step
        assert "-r" in step
        assert "validators/requirements.txt" in step


def test_bootstrap_installs_runtime_deps_before_source_doctor(repo_root: Path):
    data = _bootstrap_template(repo_root)
    keys = list(data)
    assert keys.index("install") < keys.index("preflight")
    assert data["preflight"]["requires"] == ["install"]


def test_bootstrap_doc_references_doctor_and_template(repo_root: Path):
    doc = (repo_root / "docs" / "operations" / "AGENT_NATIVE_BOOTSTRAP.md").read_text(encoding="utf-8")
    assert "ce doctor --json" in doc
    assert "templates/hermes/agent-native-bootstrap.yaml" in doc
    assert doc.index("## 3. Install") < doc.index("## 4. Preflight")
    assert doc.index("uv pip install --python \"$CE_VALIDATOR_PYTHON\" --no-index") < doc.index(
        "PYTHONPATH=validators \"$CE_VALIDATOR_PYTHON\" -m creator_engine_validator.ce_cli doctor --json"
    )
    assert "blocked" in doc.lower()


def test_failed_doctor_preflight_drives_blocked_report(tmp_path: Path, capsys):
    # The bootstrap relies on `ce doctor --json` exiting non-zero on an
    # ungoverned host to trigger its blocked-report path.
    repo = tmp_path / "ungoverned"
    repo.mkdir()
    subprocess.run(["git", "init", "--initial-branch=main"], cwd=str(repo), check=True, capture_output=True)
    ret = ce_cli.main(["doctor", "--json", "--repo-root", str(repo), "--no-check-packaging"])
    assert ret != 0  # non-zero preflight => bootstrap must emit a blocked report
