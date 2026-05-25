"""RV1-062 — unit tests for the ``ce init`` CLI surface.

Drives ``creator_engine_validator.ce_cli.main`` directly against governed /
ungoverned temp git repos built under pytest ``tmp_path``.
"""
from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from creator_engine_validator import ce_cli


def _git(args, cwd: Path):
    return subprocess.run(["git", *args], cwd=str(cwd), check=True, capture_output=True, text=True)


@pytest.fixture()
def governed_repo(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(["init", "--initial-branch=main"], repo)
    (repo / ".gitignore").write_text(".hermes/\n", encoding="utf-8")
    return repo


def test_init_help_is_reachable():
    with pytest.raises(SystemExit) as exc:
        ce_cli.main(["init", "--help"])
    assert exc.value.code == 0


def test_ce_init_json_initializes_state(governed_repo: Path, capsys):
    ret = ce_cli.main(["init", "--repo-root", str(governed_repo), "--json"])
    assert ret == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["created"]
    assert (governed_repo / ".hermes" / "active-work-ledger" / "claims").is_dir()


def test_ce_init_is_idempotent_via_cli(governed_repo: Path, capsys):
    assert ce_cli.main(["init", "--repo-root", str(governed_repo), "--json"]) == 0
    capsys.readouterr()
    assert ce_cli.main(["init", "--repo-root", str(governed_repo), "--json"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["created"] == []


def test_ce_init_refuses_ungoverned_repo(tmp_path: Path):
    repo = tmp_path / "ungoverned"
    repo.mkdir()
    _git(["init", "--initial-branch=main"], repo)
    ret = ce_cli.main(["init", "--repo-root", str(repo), "--json"])
    assert ret != 0
    assert not (repo / ".hermes").exists()


def test_ce_init_refuses_non_git_repo(tmp_path: Path):
    plain = tmp_path / "plain"
    plain.mkdir()
    ret = ce_cli.main(["init", "--repo-root", str(plain)])
    assert ret != 0
