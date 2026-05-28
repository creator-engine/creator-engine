"""RV1-062 — integration test for ``ce init`` in a real temp git repo.

Confirms idempotent end-to-end initialization, that all writes stay under the
ignored ``.hermes/`` root (so ``git status`` stays clean of tracked changes),
and that existing ledger content survives a re-init.
"""
from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from creator_engine_validator import ce_cli, init_runtime


def _git(args, cwd: Path):
    return subprocess.run(["git", *args], cwd=str(cwd), check=True, capture_output=True, text=True)


@pytest.fixture()
def governed_repo(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(["init", "--initial-branch=main"], repo)
    (repo / ".gitignore").write_text(".hermes/\n", encoding="utf-8")
    _git(["add", ".gitignore"], repo)
    _git(["-c", "user.email=t@example.com", "-c", "user.name=t", "commit", "-m", "init"], repo)
    return repo


def test_ce_init_end_to_end_idempotent_and_ignored(governed_repo: Path, capsys):
    assert ce_cli.main(["init", "--repo-root", str(governed_repo), "--json"]) == 0
    capsys.readouterr()

    # Seed ledger content, then re-init; content must survive.
    claim = governed_repo / ".hermes" / "active-work-ledger" / "claims" / "live.yaml"
    claim.write_text("live claim\n", encoding="utf-8")

    assert ce_cli.main(["init", "--repo-root", str(governed_repo), "--json"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["created"] == []
    assert claim.read_text(encoding="utf-8") == "live claim\n"

    # All init writes are under ignored .hermes/, so the tracked tree is clean.
    status = _git(["status", "--porcelain"], governed_repo).stdout.strip()
    assert status == "", f"ce init left tracked changes: {status!r}"

    # Marker is real and JSON-parseable.
    marker = init_runtime.marker_path(governed_repo)
    assert json.loads(marker.read_text(encoding="utf-8"))["kind"] == "ce-init-marker"


def test_ce_init_creates_default_controller_mcp_config(governed_repo: Path, capsys):
    assert ce_cli.main(["init", "--repo-root", str(governed_repo), "--json"]) == 0
    capsys.readouterr()

    mcp_config = governed_repo / ".hermes" / "launch" / "ce-controller" / "mcp" / "ce-mcp.json"
    assert mcp_config.is_file()
    assert json.loads(mcp_config.read_text(encoding="utf-8")) == {"mcpServers": {}}

    status = _git(["status", "--porcelain"], governed_repo).stdout.strip()
    assert status == "", f"ce init left tracked changes: {status!r}"


def test_ce_init_preserves_existing_controller_mcp_config(governed_repo: Path, capsys):
    mcp_config = governed_repo / ".hermes" / "launch" / "ce-controller" / "mcp" / "ce-mcp.json"
    mcp_config.parent.mkdir(parents=True)
    existing = {"mcpServers": {"local-test": {"command": "true"}}}
    mcp_config.write_text(json.dumps(existing, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    assert ce_cli.main(["init", "--repo-root", str(governed_repo), "--json"]) == 0
    capsys.readouterr()

    assert json.loads(mcp_config.read_text(encoding="utf-8")) == existing
