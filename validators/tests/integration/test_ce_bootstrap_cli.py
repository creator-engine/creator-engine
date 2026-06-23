"""ce-ops#148 — source-clone controller/seat provisioning."""
from __future__ import annotations

import json
import shutil
import subprocess
import uuid
from pathlib import Path

import pytest

from creator_engine_validator import bootstrap_runtime, ce_cli


TMP_ROOT = Path("/home/ce-dev-3/tmp-ce148")


def _python314() -> str:
    py = shutil.which("python3.14")
    if not py:
        pytest.skip("python3.14 is required for the cp314 offline wheelhouse")
    return py


def _case_root(name: str) -> Path:
    root = TMP_ROOT / f"{name}-{uuid.uuid4().hex}"
    root.mkdir(parents=True, exist_ok=False)
    return root


def _venv(name: str) -> Path:
    root = _case_root(name)
    venv = root / ".venv"
    subprocess.run([_python314(), "-m", "venv", str(venv)], check=True)
    return venv


def _load_stdout_json(capsys) -> dict:
    return json.loads(capsys.readouterr().out)


def test_bootstrap_empty_venv_installs_app_scripts_and_is_idempotent(repo_root: Path, capsys):
    venv = _venv("bootstrap-idempotent")

    rc = ce_cli.main(["bootstrap", "--repo-root", str(repo_root), "--venv", str(venv), "--json"])
    assert rc == 0
    first = _load_stdout_json(capsys)
    assert first["ok"] is True
    assert first["installer"] in {"pip", "uv"}
    assert first["changed"] is True

    python = venv / "bin" / "python"
    ce = venv / "bin" / "ce"
    cev3 = venv / "bin" / "cev3"
    subprocess.run([str(python), "-c", "import creator_engine_validator"], check=True)
    subprocess.run([str(ce), "--version"], check=True, capture_output=True, text=True)
    subprocess.run([str(cev3), "--version"], check=True, capture_output=True, text=True)

    rc = ce_cli.main(["bootstrap", "--repo-root", str(repo_root), "--venv", str(venv), "--json"])
    assert rc == 0
    second = _load_stdout_json(capsys)
    assert second["ok"] is True
    assert second["changed"] is False


def test_doctor_names_absent_then_present_controller_seat_env(repo_root: Path, capsys):
    venv = _venv("doctor-seat-env")

    rc = ce_cli.main([
        "doctor",
        "--repo-root",
        str(repo_root),
        "--venv",
        str(venv),
        "--no-check-packaging",
        "--json",
    ])
    assert rc != 0
    missing = _load_stdout_json(capsys)
    assert bootstrap_runtime.DOCTOR_CLAUSE in missing["refused_clauses"]
    check = [c for c in missing["checks"] if c["clause"] == bootstrap_runtime.DOCTOR_CLAUSE][0]
    assert check["ok"] is False
    assert check["package_importable"] is False
    assert "ce" in check["missing_scripts"]
    assert "cev3" in check["missing_scripts"]
    assert "ce bootstrap" in check["remediation"]

    assert ce_cli.main(["bootstrap", "--repo-root", str(repo_root), "--venv", str(venv), "--json"]) == 0
    _load_stdout_json(capsys)

    rc = ce_cli.main([
        "doctor",
        "--repo-root",
        str(repo_root),
        "--venv",
        str(venv),
        "--no-check-packaging",
        "--json",
    ])
    assert rc == 0
    present = _load_stdout_json(capsys)
    check = [c for c in present["checks"] if c["clause"] == bootstrap_runtime.DOCTOR_CLAUSE][0]
    assert check["ok"] is True
    assert check["missing_scripts"] == []
