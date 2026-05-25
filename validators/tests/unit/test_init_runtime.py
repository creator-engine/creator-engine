"""RV1-062 — ``ce init`` runtime (strict TDD).

``ce init`` performs idempotent local v1.0 kernel state initialization: it
creates only governed ``.hermes/`` state directories and refuses to overwrite
tracked governance artifacts / write ungoverned (non-ignored) state. Every
artifact is built under pytest ``tmp_path``; no production worktree is touched.
"""
from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from creator_engine_validator import init_runtime


def _git(args, cwd: Path):
    return subprocess.run(["git", *args], cwd=str(cwd), check=True, capture_output=True, text=True)


@pytest.fixture()
def governed_repo(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(["init", "--initial-branch=main"], repo)
    (repo / ".gitignore").write_text(".hermes/\n", encoding="utf-8")
    return repo


def test_init_creates_kernel_state_dirs(governed_repo: Path):
    result = init_runtime.init_repo(governed_repo)
    for rel in init_runtime.KERNEL_STATE_DIRS:
        assert (governed_repo / rel).is_dir(), f"expected state dir {rel}"
    assert result.created  # first run created at least the ledger dirs


def test_init_only_writes_under_hermes(governed_repo: Path):
    init_runtime.init_repo(governed_repo)
    # Everything created/written must live under the ignored .hermes/ root.
    for rel in init_runtime.KERNEL_STATE_DIRS:
        assert rel.split("/")[0] == ".hermes"
    assert init_runtime.marker_path(governed_repo).is_relative_to(governed_repo / ".hermes")


def test_init_is_idempotent(governed_repo: Path):
    first = init_runtime.init_repo(governed_repo)
    second = init_runtime.init_repo(governed_repo)
    assert first.created  # something created on the first pass
    assert second.created == []  # nothing new on a repeat
    assert set(second.existing) >= set(init_runtime.KERNEL_STATE_DIRS)


def test_init_does_not_clobber_existing_ledger_content(governed_repo: Path):
    init_runtime.init_repo(governed_repo)
    claim = governed_repo / ".hermes" / "active-work-ledger" / "claims" / "keep.yaml"
    claim.parent.mkdir(parents=True, exist_ok=True)
    claim.write_text("keepme\n", encoding="utf-8")
    init_runtime.init_repo(governed_repo)  # second init
    assert claim.read_text(encoding="utf-8") == "keepme\n"


def test_init_refuses_non_git_repo(tmp_path: Path):
    plain = tmp_path / "plain"
    plain.mkdir()
    with pytest.raises(init_runtime.InitRefused):
        init_runtime.init_repo(plain)


def test_init_refuses_ungoverned_hermes_posture(tmp_path: Path):
    repo = tmp_path / "ungoverned"
    repo.mkdir()
    _git(["init", "--initial-branch=main"], repo)
    # no .gitignore -> .hermes/ would be tracked/ungoverned state
    with pytest.raises(init_runtime.InitRefused):
        init_runtime.init_repo(repo)
    assert not (repo / ".hermes").exists()


def test_init_refuses_overwriting_tracked_artifact(governed_repo: Path):
    # A tracked file occupying a target state path must not be clobbered.
    target = governed_repo / ".hermes"
    # Force-track a file at the .hermes path (bypassing the ignore) to simulate
    # a tracked artifact collision.
    target.write_text("tracked sentinel\n", encoding="utf-8")
    _git(["add", "-f", ".hermes"], governed_repo)
    with pytest.raises(init_runtime.InitRefused):
        init_runtime.init_repo(governed_repo)
    assert target.read_text(encoding="utf-8") == "tracked sentinel\n"


def test_init_result_to_dict_is_json_safe(governed_repo: Path):
    result = init_runtime.init_repo(governed_repo)
    payload = result.to_dict()
    json.dumps(payload)  # must not raise
    assert payload["repo_root"] == str(governed_repo)
    assert "created" in payload and "existing" in payload
