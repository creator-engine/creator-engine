"""Unit tests for the public CE-native ``ce init`` project scaffold."""
from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from creator_engine_validator import ce_cli


def _git(args, cwd: Path):
    return subprocess.run(["git", *args], cwd=str(cwd), check=True, capture_output=True, text=True)


def test_init_help_is_reachable():
    with pytest.raises(SystemExit) as exc:
        ce_cli.main(["init", "--help"])
    assert exc.value.code == 0


def test_ce_init_json_scaffolds_project(tmp_path: Path, capsys):
    target = tmp_path / "project"
    ret = ce_cli.main(["init", str(target), "--json"])
    assert ret == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["created"]
    assert payload["overwritten"] == []
    assert (target / ".ce" / "scopes" / "templates" / "XS-scope-card.md").is_file()
    assert (target / ".ce" / "pr-manifests" / "_template.md").is_file()
    assert not (target / ".specify").exists()


def test_ce_init_is_idempotent_via_cli(tmp_path: Path, capsys):
    target = tmp_path / "project"
    assert ce_cli.main(["init", str(target), "--json"]) == 0
    capsys.readouterr()

    assert ce_cli.main(["init", str(target), "--json"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["created"] == []
    assert payload["overwritten"] == []
    assert ".ce/README.md" in payload["skipped"]


def test_ce_init_preserves_user_edits_without_force(tmp_path: Path, capsys):
    target = tmp_path / "project"
    target.mkdir()
    readme = target / "README.md"
    readme.write_text("# My existing project\n", encoding="utf-8")

    assert ce_cli.main(["init", str(target), "--json"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert "README.md" in payload["skipped"]
    assert readme.read_text(encoding="utf-8") == "# My existing project\n"


def test_ce_init_force_overwrites_differing_scaffold_files(tmp_path: Path, capsys):
    target = tmp_path / "project"
    target.mkdir()
    readme = target / "README.md"
    readme.write_text("# My existing project\n", encoding="utf-8")

    assert ce_cli.main(["init", str(target), "--force", "--json"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert "README.md" in payload["overwritten"]
    assert "Frame -> Shape -> Build -> Review -> Ship" in readme.read_text(encoding="utf-8")


def test_ce_init_hidden_repo_root_preserves_kernel_state_compatibility(tmp_path: Path, capsys):
    target = tmp_path / "project"
    target.mkdir()
    _git(["init", "--initial-branch=main"], target)
    (target / ".gitignore").write_text(".hermes/\n", encoding="utf-8")

    ret = ce_cli.main(["init", "--repo-root", str(target), "--json"])
    assert ret == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["repo_root"] == str(target)
    assert (target / ".hermes" / "active-work-ledger" / "claims").is_dir()
    assert not (target / ".ce" / "changelog" / "_template.md").exists()


def test_ce_init_refuses_file_target(tmp_path: Path):
    target = tmp_path / "not-a-directory"
    target.write_text("x\n", encoding="utf-8")
    assert ce_cli.main(["init", str(target)]) != 0
