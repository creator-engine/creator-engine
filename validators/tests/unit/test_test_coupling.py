"""Unit tests for the PR-diff ``test_coupling`` gate."""

from __future__ import annotations

import subprocess
from pathlib import Path

from creator_engine_validator.checks import registered_checks
from creator_engine_validator.checks.git_helpers import repo_root_for, run_git
from creator_engine_validator.checks import test_coupling as chk


def _git(repo: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=repo, check=True, capture_output=True, text=True)


def _head(repo: Path) -> str:
    return subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def _init_repo(tmp_path: Path) -> tuple[Path, str]:
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init", "-q")
    _git(repo, "config", "user.email", "test@example.com")
    _git(repo, "config", "user.name", "Test")
    _write_repo_file(repo, "src/app.py", "def existing():\n    return 1\n")
    _git(repo, "add", "src/app.py")
    _git(repo, "commit", "-q", "-m", "base")
    return repo, _head(repo)


def _write_repo_file(repo: Path, rel: str, text: str) -> None:
    target = repo / rel
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(text)


def _commit_all(repo: Path, message: str = "change") -> None:
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", message)


def test_registered_in_check_surface() -> None:
    reg = registered_checks()
    assert chk.CHECK_NAME in reg and reg[chk.CHECK_NAME].frs


def test_uses_shared_public_git_helpers(tmp_path: Path) -> None:
    repo, _base = _init_repo(tmp_path)

    returncode, stdout, stderr = run_git(["rev-parse", "--show-toplevel"], repo)

    assert returncode == 0, stderr
    assert Path(stdout.strip()) == repo_root_for(repo / "src" / "app.py")


def test_code_change_without_test_emits_finding(tmp_path: Path) -> None:
    repo, base = _init_repo(tmp_path)
    _write_repo_file(repo, "src/app.py", "def existing():\n    return 2\n")
    _commit_all(repo)

    result = chk.run_with_base([repo], base)

    assert not result.ok
    assert {e.code for e in result.errors} == {chk.CODE_MISSING_TEST}


def test_code_change_with_test_passes(tmp_path: Path) -> None:
    repo, base = _init_repo(tmp_path)
    _write_repo_file(repo, "src/app.py", "def existing():\n    return 2\n")
    _write_repo_file(repo, "tests/test_app.py", "def test_existing():\n    assert True\n")
    _commit_all(repo)

    result = chk.run_with_base([repo], base)

    assert result.ok, [e.format() for e in result.errors]


def test_docs_only_passes(tmp_path: Path) -> None:
    repo, base = _init_repo(tmp_path)
    _write_repo_file(repo, "docs/usage.md", "# Usage\n\nText.\n")
    _commit_all(repo)

    result = chk.run_with_base([repo], base)

    assert result.ok, [e.format() for e in result.errors]


def test_deletion_only_passes(tmp_path: Path) -> None:
    repo, base = _init_repo(tmp_path)
    _write_repo_file(repo, "src/app.py", "def existing():\n")
    _commit_all(repo)

    result = chk.run_with_base([repo], base)

    assert result.ok, [e.format() for e in result.errors]


def test_opt_out_marker_passes(tmp_path: Path) -> None:
    repo, base = _init_repo(tmp_path)
    _write_repo_file(repo, "src/app.py", "def existing():\n    return 2\n")
    _commit_all(repo)

    result = chk.run_with_base([repo], base, pr_body=f"Documented exemption: {chk.OPT_OUT_MARKER}")

    assert result.ok, [e.format() for e in result.errors]
