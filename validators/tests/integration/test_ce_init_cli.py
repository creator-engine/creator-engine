"""Integration tests for the public CE-native ``ce init`` scaffold."""
from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from creator_engine_validator import ce_cli

pytestmark = pytest.mark.slow


def _git(args, cwd: Path):
    return subprocess.run(["git", *args], cwd=str(cwd), check=True, capture_output=True, text=True)


@pytest.fixture()
def existing_project(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(["init", "--initial-branch=main"], repo)
    (repo / "README.md").write_text("# Existing project\n", encoding="utf-8")
    _git(["add", "README.md"], repo)
    _git(["-c", "user.email=t@example.com", "-c", "user.name=t", "commit", "-m", "init"], repo)
    return repo


def test_ce_init_end_to_end_idempotent_and_no_specify(existing_project: Path, capsys):
    assert ce_cli.main(["init", str(existing_project), "--json"]) == 0
    first = json.loads(capsys.readouterr().out)
    assert ".ce/README.md" in first["created"]
    assert "README.md" in first["skipped"]

    assert ce_cli.main(["init", str(existing_project), "--json"]) == 0
    second = json.loads(capsys.readouterr().out)
    assert second["created"] == []
    assert second["overwritten"] == []

    assert not (existing_project / ".specify").exists()
    assert (existing_project / ".ce" / "skills" / "ce-review-evidence" / "SKILL.md").is_file()
    assert "Frame -> Shape -> Build -> Review -> Ship" in (
        existing_project / ".ce" / "README.md"
    ).read_text(encoding="utf-8")


def test_ce_init_force_refreshes_existing_ce_template(existing_project: Path, capsys):
    template = existing_project / ".ce" / "changelog" / "_template.md"
    template.parent.mkdir(parents=True)
    template.write_text("custom\n", encoding="utf-8")

    assert ce_cli.main(["init", str(existing_project), "--force", "--json"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert ".ce/changelog/_template.md" in payload["overwritten"]
    assert "slug: <branch-slug>" in template.read_text(encoding="utf-8")
