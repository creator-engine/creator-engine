"""Unit tests for the PR-diff dual-format sync gate."""

from __future__ import annotations

import subprocess
from pathlib import Path

from creator_engine_validator.checks import dual_format_sync as chk
from creator_engine_validator.checks import registered_checks


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


def _write_repo_file(repo: Path, rel: str, text: str) -> None:
    target = repo / rel
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(text, encoding="utf-8")


def _commit_all(repo: Path, message: str = "change") -> None:
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", message)


def _init_repo(tmp_path: Path) -> tuple[Path, str]:
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init", "-q")
    _git(repo, "config", "user.email", "test@example.com")
    _git(repo, "config", "user.name", "Test")
    _write_repo_file(repo, "docs/guide/example.md", "# Example\n\nBase.\n")
    _write_repo_file(repo, "docs/guide/example.html", "<!DOCTYPE html>\n<title>Example</title>\n")
    _write_repo_file(repo, "docs/guide/unpaired.md", "# Unpaired\n")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "base")
    return repo, _head(repo)


def test_registered_in_check_surface() -> None:
    registry = registered_checks()

    assert chk.CHECK_NAME in registry and registry[chk.CHECK_NAME].frs


def test_pair_modified_together_passes(tmp_path: Path) -> None:
    repo, base = _init_repo(tmp_path)
    _write_repo_file(repo, "docs/guide/example.md", "# Example\n\nUpdated.\n")
    _write_repo_file(repo, "docs/guide/example.html", "<!DOCTYPE html>\n<title>Updated</title>\n")
    _commit_all(repo)

    result = chk.run_with_base([repo], base)

    assert result.ok, [error.format() for error in result.errors]


def test_markdown_only_change_fails_naming_html_sibling(tmp_path: Path) -> None:
    repo, base = _init_repo(tmp_path)
    _write_repo_file(repo, "docs/guide/example.md", "# Example\n\nMarkdown only.\n")
    _commit_all(repo)

    result = chk.run_with_base([repo], base)

    assert not result.ok
    assert {error.code for error in result.errors} == {chk.CODE_STALE_SIBLING}
    rendered = "\n".join(error.format() for error in result.errors)
    assert "docs/guide/example.html" in rendered


def test_html_only_change_fails_naming_markdown_sibling(tmp_path: Path) -> None:
    repo, base = _init_repo(tmp_path)
    _write_repo_file(repo, "docs/guide/example.html", "<!DOCTYPE html>\n<title>HTML only</title>\n")
    _commit_all(repo)

    result = chk.run_with_base([repo], base)

    assert not result.ok
    assert {error.code for error in result.errors} == {chk.CODE_STALE_SIBLING}
    rendered = "\n".join(error.format() for error in result.errors)
    assert "docs/guide/example.md" in rendered


def test_unpaired_markdown_file_is_untouched_by_gate(tmp_path: Path) -> None:
    repo, base = _init_repo(tmp_path)
    _write_repo_file(repo, "docs/guide/unpaired.md", "# Unpaired\n\nChanged.\n")
    _commit_all(repo)

    result = chk.run_with_base([repo], base)

    assert result.ok, [error.format() for error in result.errors]


def test_tracked_file_discovery_failure_fails_closed(tmp_path: Path, monkeypatch) -> None:
    repo, base = _init_repo(tmp_path)
    _write_repo_file(repo, "docs/guide/unpaired.md", "# Unpaired\n\nChanged.\n")
    _commit_all(repo)
    real_run_git = chk.run_git

    def failing_ls_files(args: list[str], repo_root: Path):
        if args == ["ls-files", "-z"]:
            return 1, "", "simulated repository failure"
        return real_run_git(args, repo_root)

    monkeypatch.setattr(chk, "run_git", failing_ls_files)

    result = chk.run_with_base([repo], base)

    assert not result.ok
    assert {error.code for error in result.errors} == {chk.CODE_INVALID}
    assert "git ls-files -z failed" in "\n".join(error.format() for error in result.errors)
