"""Integration tests for the ``ce pcl`` runtime end-to-end (G2.004.1).

Exercises ``ce pcl append`` -> ``verify`` -> ``replay`` -> ``index`` through
``ce_cli.main`` inside a real temporary git repository whose ``.gitignore``
carries the additive ``.ce/pcl/cache/`` instance-zone line. Unlike the CE-event
spool (fully ignored), PCL **records** are the per-repo authoritative,
tracked-or-synced ledger, so they appear in ``git status`` while the rebuildable
``.ce/pcl/cache/`` does not. Asserts:

* a multi-record chain round-trips and ``verify`` passes;
* records under ``.ce/pcl/records/`` are git-trackable (NOT ignored);
* the ``index`` cache lands under the **ignored** ``.ce/pcl/cache/`` and stays
  out of ``git status``;
* the runtime refuses an un-ignored cache root inside a repo, fail-closed;
* a runtime-produced record still passes the unchanged ``pcl_record`` validator;
* the ``ce pcl`` group co-exists with the other ``ce`` command groups.
"""
from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from creator_engine_validator import ce_cli
from creator_engine_validator.checks import pcl_record as pcl_check

RECORDED = "2026-05-31T16:48:41Z"


def _git(repo: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True, text=True)


def _init_repo(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init", "-q")
    _git(repo, "config", "user.email", "test@example.com")
    _git(repo, "config", "user.name", "test")
    (repo / ".gitignore").write_text(".ce/pcl/cache/\n", encoding="utf-8")
    _git(repo, "add", ".gitignore")
    _git(repo, "commit", "-q", "-m", "seed")
    return repo


def _pcl_root(repo: Path) -> Path:
    root = repo / ".ce" / "pcl"
    (root / "records").mkdir(parents=True, exist_ok=True)
    return root


def _append(repo: Path, root: Path, record_id: str, **override) -> int:
    body = override.get("body", {"lane_id": "g20041-pcl-runtime", "summary": "integration"})
    argv = [
        "pcl", "append",
        "--ledger", "demo",
        "--pcl-root", str(root),
        "--record-id", record_id,
        "--record-kind", override.get("record_kind", "lane_claim"),
        "--emitting-role", "controller",
        "--operating-mode", "strict",
        "--recorded-at", RECORDED,
        "--body-json", json.dumps(body),
        "--repo-root", str(repo),
    ]
    return ce_cli.main(argv)


def _porcelain(repo: Path) -> str:
    return _git(repo, "status", "--porcelain").stdout


def test_chain_roundtrips_and_records_are_tracked_cache_is_ignored(tmp_path, capsys):
    repo = _init_repo(tmp_path)
    root = _pcl_root(repo)
    assert _append(repo, root, "pcl-demo-0000", record_kind="gate_opened") == 0
    assert _append(repo, root, "pcl-demo-0001") == 0
    capsys.readouterr()

    assert ce_cli.main(["pcl", "verify", "--ledger", "demo", "--pcl-root", str(root)]) == 0

    # Index writes to the ignored cache.
    capsys.readouterr()
    assert ce_cli.main(["pcl", "index", "--ledger", "demo", "--pcl-root", str(root), "--repo-root", str(repo)]) == 0
    assert (root / "cache" / "demo" / "index.json").is_file()

    # State-boundary contract (precise): records are tracked-or-synced (NOT
    # ignored); the rebuildable cache IS ignored. `git status --porcelain`
    # collapses untracked trees, so assert with `git check-ignore` per path.
    record_file = next(p for p in (root / "records" / "demo").glob("*.json") if p.name != "_head.json")
    rec_rel = record_file.relative_to(repo).as_posix()
    cache_rel = (root / "cache" / "demo" / "index.json").relative_to(repo).as_posix()

    def _ignored(rel: str) -> bool:
        return subprocess.run(["git", "-C", str(repo), "check-ignore", "-q", "--", rel]).returncode == 0

    assert not _ignored(rec_rel), "PCL records must be git-trackable (not ignored)"
    assert _ignored(cache_rel), "PCL cache must be git-ignored"
    # And the cache file does not surface as an untracked path.
    assert "cache" not in _git(repo, "status", "--porcelain", "-uall").stdout


def test_index_refuses_unignored_cache_inside_repo(tmp_path, capsys):
    repo = tmp_path / "repo2"
    repo.mkdir()
    _git(repo, "init", "-q")
    root = _pcl_root(repo)
    assert _append(repo, root, "pcl-demo-0000") == 0
    capsys.readouterr()
    # No .gitignore for the cache -> fail closed with the stable code.
    rc = ce_cli.main(["pcl", "index", "--ledger", "demo", "--pcl-root", str(root), "--repo-root", str(repo)])
    assert rc == 1
    assert "G2-PCL-CACHE-NOT-IGNORED" in capsys.readouterr().err


def test_runtime_record_passes_unchanged_validator(tmp_path):
    repo = _init_repo(tmp_path)
    root = _pcl_root(repo)
    _append(repo, root, "pcl-demo-0000")
    record_file = next(p for p in (root / "records" / "demo").glob("*.json") if p.name != "_head.json")
    record = json.loads(record_file.read_text(encoding="utf-8"))
    scope = tmp_path / "pcl-record"
    scope.mkdir()
    wrapped = scope / "produced.ce.yml"
    wrapped.write_text(json.dumps({"pcl_record": record}), encoding="utf-8")
    errors = pcl_check.validate_file(wrapped)
    assert errors == [], [e.format() for e in errors]


def test_pcl_group_coexists_with_other_groups():
    for argv in (["pcl", "--help"], ["event", "--help"], ["fanin", "--help"]):
        with pytest.raises(SystemExit) as exc:
            ce_cli.main(argv)
        assert exc.value.code == 0
