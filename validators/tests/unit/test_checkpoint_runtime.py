from __future__ import annotations

import json
import stat
import subprocess
from pathlib import Path

import pytest

from creator_engine_validator import checkpoint_runtime as runtime


def _git_root(path: Path) -> Path:
    subprocess.run(["git", "init", "-q", str(path)], check=True)
    return path


def _document(*, label: str = "probed") -> dict[str, object]:
    fact = {"label": label, "fact": "safe bounded fact", "source": "safe/source.md"}
    return {
        "facts": {name: dict(fact) for name in runtime.FACT_SECTIONS},
        "delta": [dict(fact)],
        "next_safe_act": "Read the named durable source.",
        "reload_sources": ["safe/source.md"],
    }


def _facts_file(root: Path, document: dict[str, object]) -> Path:
    path = root / "facts.json"
    path.write_text(json.dumps(document), encoding="utf-8")
    return path


def test_checkpoint_is_deterministic_atomic_owner_only_and_idempotent(tmp_path: Path) -> None:
    root = _git_root(tmp_path)
    source = _facts_file(root, _document())
    first = runtime.create_checkpoint(
        repo_root=root,
        facts_path=source,
        clean_boundary="focused work is complete",
        as_of="2026-07-12T10:11:12Z",
    )
    assert first.path == root / ".ce/state/research/RESUME_STATE_20260712T101112Z.md"
    assert first.sha256 == __import__("hashlib").sha256(first.path.read_bytes()).hexdigest()
    assert stat.S_IMODE(first.path.stat().st_mode) == 0o600
    assert "# Resume state — 2026-07-12T10:11:12Z" in first.path.read_text(encoding="utf-8")
    assert "Next safe act: Read the named durable source." in first.path.read_text(encoding="utf-8")
    assert runtime.create_checkpoint(
        repo_root=root, facts_path=source, clean_boundary="focused work is complete", as_of="2026-07-12T10:11:12Z"
    ).idempotent is True


def test_checkpoint_refuses_collision_secret_and_incomplete_facts(tmp_path: Path) -> None:
    root = _git_root(tmp_path)
    source = _facts_file(root, _document())
    runtime.create_checkpoint(repo_root=root, facts_path=source, clean_boundary="clean", as_of="2026-07-12T10:11:12Z")
    changed = _document()
    changed["next_safe_act"] = "Different content"
    source = _facts_file(root, changed)
    with pytest.raises(runtime.CheckpointError, match="collision"):
        runtime.create_checkpoint(repo_root=root, facts_path=source, clean_boundary="clean", as_of="2026-07-12T10:11:12Z")
    unsafe = _document()
    unsafe["facts"]["heads_and_bases"]["token"] = "nope"  # type: ignore[index]
    with pytest.raises(runtime.CheckpointError, match="unsafe"):
        runtime.create_checkpoint(repo_root=root, facts_path=_facts_file(root, unsafe), clean_boundary="clean", as_of="2026-07-12T10:11:13Z")
    incomplete = _document()
    del incomplete["facts"]["arc_rung_stamp"]  # type: ignore[index]
    with pytest.raises(runtime.CheckpointError, match="invalid checkpoint facts"):
        runtime.create_checkpoint(repo_root=root, facts_path=_facts_file(root, incomplete), clean_boundary="clean", as_of="2026-07-12T10:11:14Z")


def test_checkpoint_refuses_tracked_target_and_unsafe_root(tmp_path: Path) -> None:
    root = _git_root(tmp_path)
    target = root / ".ce/state/research/RESUME_STATE_20260712T101112Z.md"
    target.parent.mkdir(parents=True)
    target.write_text("tracked\n", encoding="utf-8")
    subprocess.run(["git", "add", target.relative_to(root).as_posix()], cwd=root, check=True)
    with pytest.raises(runtime.CheckpointError, match="tracked"):
        runtime.create_checkpoint(repo_root=root, facts_path=_facts_file(root, _document()), clean_boundary="clean", as_of="2026-07-12T10:11:12Z")
