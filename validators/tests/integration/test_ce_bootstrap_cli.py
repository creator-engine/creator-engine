"""ce-ops#148 — source-clone controller/seat provisioning."""
from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import pytest

from creator_engine_validator import bootstrap_runtime, ce_cli


def _python314() -> str:
    py = shutil.which("python3.14")
    if not py:
        pytest.skip("python3.14 is required for the cp314 offline wheelhouse")
    return py


def _venv(tmp_path: Path) -> Path:
    root = tmp_path
    venv = root / ".venv"
    subprocess.run([_python314(), "-m", "venv", str(venv)], check=True)
    return venv


def _load_stdout_json(capsys) -> dict:
    return json.loads(capsys.readouterr().out)


def _link_validators_source(source_root: Path, repo_root: Path) -> None:
    try:
        (source_root / "validators").symlink_to(repo_root / "validators", target_is_directory=True)
    except OSError:
        shutil.copytree(
            repo_root / "validators",
            source_root / "validators",
            ignore=shutil.ignore_patterns("__pycache__", ".pytest_cache"),
        )


def _script_shebang(script: Path) -> str:
    return script.read_text(encoding="utf-8").splitlines()[0]


def test_bootstrap_empty_venv_installs_app_scripts_and_is_idempotent(
    repo_root: Path, tmp_path: Path, capsys
):
    venv = _venv(tmp_path)

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


def test_bootstrap_relative_paths_write_absolute_shebangs_and_scripts_run(
    repo_root: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys,
):
    source_root = tmp_path / "checkout"
    source_root.mkdir()
    _link_validators_source(source_root, repo_root)
    venv = _venv(source_root)

    monkeypatch.chdir(source_root)
    rc = ce_cli.main(["bootstrap", "--repo-root", ".", "--venv", ".venv", "--json"])

    assert rc == 0
    result = _load_stdout_json(capsys)
    assert result["ok"] is True

    ce = venv / "bin" / "ce"
    cev3 = venv / "bin" / "cev3"
    for script in (ce, cev3):
        shebang = _script_shebang(script)
        assert shebang.startswith("#!")
        assert Path(shebang.removeprefix("#!")).is_absolute()

    unrelated_cwd = tmp_path / "unrelated"
    unrelated_cwd.mkdir()
    subprocess.run([str(ce), "--version"], cwd=unrelated_cwd, check=True, capture_output=True, text=True)


def test_doctor_names_absent_then_present_controller_seat_env(repo_root: Path, tmp_path: Path, capsys):
    venv = _venv(tmp_path)

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
