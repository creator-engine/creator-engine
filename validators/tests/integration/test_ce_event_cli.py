"""Integration tests for the ``ce event`` runtime end-to-end (RV2-003-011..017).

Exercises the full ``ce event append`` -> ``verify`` -> ``replay`` -> ``index``
flow through ``ce_cli.main`` inside a real temporary git repository whose
``.gitignore`` carries the additive ``.ce/ce-events/spool/`` instance-zone line.
Asserts that:

* a multi-block chain round-trips and ``verify`` passes;
* every runtime write lands under the **ignored** spool, so ``git status
  --porcelain`` stays clean (no tracked runtime state);
* the runtime refuses an un-ignored spool root inside a repo, fail-closed;
* a runtime-produced chain still passes the unchanged ``ce_event_block``
  validator (G2.003.0 backward-compat canary);
* the ``ce event`` group co-exists with the other ``ce`` command groups.
"""
from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest
import yaml

from creator_engine_validator import ce_cli
from creator_engine_validator.checks import ce_event_block as block_check

RECORDED = "2026-05-30T16:00:00Z"


def _git(repo: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", "-C", str(repo), *args], check=True, capture_output=True, text=True
    )


def _init_repo(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init", "-q")
    _git(repo, "config", "user.email", "test@example.com")
    _git(repo, "config", "user.name", "test")
    # Additive instance-zone ignore line, mirroring the gate's .gitignore change.
    (repo / ".gitignore").write_text(".ce/ce-events/spool/\n", encoding="utf-8")
    _git(repo, "add", ".gitignore")
    _git(repo, "commit", "-q", "-m", "seed")
    return repo


def _event_json(summary: str = "integration", **override) -> str:
    base = {"kind": "gate_progress", "subject": "G2.003.1", "summary": summary}
    base.update(override)
    return json.dumps(base)


def _append(repo: Path, root: Path, block_id: str, **override) -> int:
    argv = [
        "event", "append",
        "--stream", "demo",
        "--event-root", str(root),
        "--block-id", block_id,
        "--emitting-role", "controller",
        "--operating-mode", "strict",
        "--recorded-at", RECORDED,
        "--event-json", override.get("event_json", _event_json()),
        "--repo-root", str(repo),
    ]
    return ce_cli.main(argv)


def _porcelain(repo: Path) -> str:
    return _git(repo, "status", "--porcelain").stdout


# ---------------------------------------------------------------------------
# end-to-end append -> verify -> replay -> index under an ignored spool
# ---------------------------------------------------------------------------


def test_append_chain_roundtrips_and_keeps_git_status_clean(tmp_path):
    repo = _init_repo(tmp_path)
    root = repo / ".ce" / "ce-events"

    assert _append(repo, root, "ceevt-demo-0000") == 0
    assert _append(repo, root, "ceevt-demo-0001") == 0
    assert ce_cli.main(["event", "verify", "--stream", "demo", "--event-root", str(root)]) == 0
    assert ce_cli.main(["event", "replay", "--stream", "demo", "--event-root", str(root)]) == 0
    assert ce_cli.main(["event", "index", "--stream", "demo", "--event-root", str(root)]) == 0

    # The spool exists on disk but git sees nothing to track: writes are ignored.
    assert (root / "spool" / "demo").is_dir()
    assert _porcelain(repo) == ""


def test_append_refuses_unignored_spool_root_in_repo(tmp_path):
    repo = tmp_path / "bare"
    repo.mkdir()
    _git(repo, "init", "-q")
    # No .ce ignore line: the spool root is NOT ignored, so append must refuse.
    root = repo / ".ce" / "ce-events"
    ret = _append(repo, root, "ceevt-demo-0000")
    assert ret != 0
    # Fail-closed: no CE-event block file was written anywhere under .ce/.
    assert list((repo / ".ce").rglob("*.json")) == []


def test_runtime_chain_passes_ce_event_block_validator(tmp_path, capsys):
    repo = _init_repo(tmp_path)
    root = repo / ".ce" / "ce-events"
    _append(repo, root, "ceevt-demo-0000")
    _append(repo, root, "ceevt-demo-0001")

    capsys.readouterr()  # drain the append human output before capturing replay JSON
    ce_cli.main(["event", "replay", "--stream", "demo", "--event-root", str(root), "--json"])
    blocks = json.loads(capsys.readouterr().out)["blocks"]

    canary = repo / "examples-scratch" / "ce-event-block" / "runtime.ce.yml"
    canary.parent.mkdir(parents=True, exist_ok=True)
    canary.write_text(yaml.safe_dump({"ce_event_chain": blocks}, sort_keys=True), encoding="utf-8")
    errors = block_check.validate_file(canary)
    assert errors == [], [e.format() for e in errors]


def test_ce_event_coexists_with_other_groups():
    for argv in (
        ["event", "append", "--help"],
        ["fanin", "build", "--help"],
        ["ledger", "verify", "--help"],
        ["lane", "verify", "--help"],
    ):
        with pytest.raises(SystemExit) as exc:
            ce_cli.main(argv)
        assert exc.value.code == 0
