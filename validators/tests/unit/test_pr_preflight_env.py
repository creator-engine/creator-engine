from __future__ import annotations

from pathlib import Path

from creator_engine_validator import pr_preflight


def test_python_env_propagates_caller_pytest_environment(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("TMPDIR", "/custom/path")
    monkeypatch.setenv("PYTEST_ADDOPTS", "-p no:x")
    monkeypatch.setenv("PYTHONDONTWRITEBYTECODE", "0")
    monkeypatch.setenv("GH_TOKEN", "token-value")

    env = pr_preflight._python_env(tmp_path, pytest=True)

    assert env["TMPDIR"] == "/custom/path"
    assert env["PYTEST_ADDOPTS"] == "-p no:x"
    assert env["PYTHONDONTWRITEBYTECODE"] == "1"
    assert env["PYTHONPATH"].split(":")[0] == str(tmp_path / "validators")
    assert "GH_TOKEN" not in env


def test_python_env_omits_unset_caller_pytest_environment(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.delenv("TMPDIR", raising=False)
    monkeypatch.delenv("PYTEST_ADDOPTS", raising=False)

    env = pr_preflight._python_env(tmp_path, pytest=True)

    assert "TMPDIR" not in env
    assert "PYTEST_ADDOPTS" not in env


def test_python_env_explicit_tmpdir_overrides_caller_value(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("TMPDIR", "/caller/path")

    env = pr_preflight._python_env(tmp_path, pytest=True, tmpdir="/override/path")

    assert env["TMPDIR"] == "/override/path"
