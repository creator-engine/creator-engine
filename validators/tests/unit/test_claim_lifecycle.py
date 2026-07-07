from __future__ import annotations

import json
from pathlib import Path
import subprocess

import pytest

from creator_engine_validator import claim_lifecycle as lifecycle


NOW = "2026-07-06T14:00:00Z"


def _write_claim(root: Path, slug: str, state: str = "claimed") -> Path:
    path = root / ".ce" / "claims" / f"{slug}.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        f"""---
slug: {slug}
issue: 476
repo: creator-engine/creator-engine
state: {state}
seat: seat-alpha
controller: CE-DEV-2
claimed_at: 2026-07-06T13:00:00Z
transitioned_at: 2026-07-06T13:00:00Z
pr: null
merge_sha: null
refs:
  - tracker#476
---
human notes
""",
        encoding="utf-8",
    )
    return path


def _git(root: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=root,
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    return result.stdout.strip()


def _init_git_repo(root: Path, branch: str = "main") -> str:
    _git(root, "init", "-b", branch)
    _git(root, "config", "user.name", "CE Test")
    _git(root, "config", "user.email", "ce-test@example.invalid")
    (root / "README.md").write_text("initial\n", encoding="utf-8")
    _git(root, "add", "README.md")
    _git(root, "commit", "-m", "initial")
    return _git(root, "rev-parse", "HEAD")


def _create_non_ancestor_sha(root: Path) -> str:
    _git(root, "checkout", "--orphan", "side")
    _git(root, "rm", "-rf", ".")
    (root / "side.txt").write_text("side\n", encoding="utf-8")
    _git(root, "add", "side.txt")
    _git(root, "commit", "-m", "side")
    sha = _git(root, "rev-parse", "HEAD")
    _git(root, "checkout", "main")
    return sha


def test_transition_moves_forward_and_emits_structured_log(tmp_path: Path) -> None:
    _write_claim(tmp_path, "ce-476-claim-lifecycle")

    result = lifecycle.transition_claim(
        tmp_path,
        "ce-476-claim-lifecycle",
        "in-build",
        pr="https://github.com/creator-engine/creator-engine/pull/123",
        now=NOW,
    )

    assert result.old_state == "claimed"
    assert result.new_state == "in-build"
    payload = json.loads(lifecycle.structured_log_line(result))
    assert payload["event"] == "ce_claim_transition"
    assert payload["pr"].endswith("/123")
    written = (tmp_path / ".ce" / "claims" / "ce-476-claim-lifecycle.md").read_text(encoding="utf-8")
    assert "state: in-build" in written
    assert "transitioned_at: 2026-07-06T14:00:00Z" in written
    assert "human notes" in written


def test_claim_lifecycle_imports_from_packaged_path() -> None:
    assert lifecycle.__name__ == "creator_engine_validator.claim_lifecycle"


def test_backward_transition_requires_force(tmp_path: Path) -> None:
    _write_claim(tmp_path, "ce-476-claim-lifecycle", state="ready")

    with pytest.raises(lifecycle.ClaimLifecycleError, match="backward"):
        lifecycle.transition_claim(tmp_path, "ce-476-claim-lifecycle", "in-build", now=NOW)

    result = lifecycle.transition_claim(
        tmp_path,
        "ce-476-claim-lifecycle",
        "in-build",
        force=True,
        now=NOW,
    )
    assert result.new_state == "in-build"


def test_illegal_forward_skip_is_refused(tmp_path: Path) -> None:
    _write_claim(tmp_path, "ce-476-claim-lifecycle")

    with pytest.raises(lifecycle.ClaimLifecycleError, match="illegal"):
        lifecycle.transition_claim(tmp_path, "ce-476-claim-lifecycle", "landed", sha="abc123", now=NOW)


def test_terminal_transition_without_evidence_is_refused(tmp_path: Path) -> None:
    _write_claim(tmp_path, "ce-476-claim-lifecycle", state="harvested")

    with pytest.raises(lifecycle.ClaimLifecycleError, match="requires merge/release SHA evidence"):
        lifecycle.transition_claim(tmp_path, "ce-476-claim-lifecycle", "landed", now=NOW)


def test_terminal_transition_without_git_metadata_is_refused(tmp_path: Path) -> None:
    _write_claim(tmp_path, "ce-476-claim-lifecycle", state="harvested")

    with pytest.raises(lifecycle.ClaimLifecycleError, match="no \\.git metadata"):
        lifecycle.transition_claim(tmp_path, "ce-476-claim-lifecycle", "landed", sha="abc123", now=NOW)


def test_force_does_not_bypass_landed_evidence_check(tmp_path: Path) -> None:
    _write_claim(tmp_path, "ce-476-claim-lifecycle", state="harvested")

    with pytest.raises(lifecycle.ClaimLifecycleError, match="no \\.git metadata"):
        lifecycle.transition_claim(
            tmp_path,
            "ce-476-claim-lifecycle",
            "landed",
            sha="abc123",
            force=True,
            now=NOW,
        )


def test_force_does_not_bypass_unreachable_landed_sha(tmp_path: Path) -> None:
    _init_git_repo(tmp_path)
    non_ancestor_sha = _create_non_ancestor_sha(tmp_path)
    _write_claim(tmp_path, "ce-476-claim-lifecycle", state="harvested")

    with pytest.raises(lifecycle.ClaimLifecycleError, match="not reachable from main ref"):
        lifecycle.transition_claim(
            tmp_path,
            "ce-476-claim-lifecycle",
            "landed",
            sha=non_ancestor_sha,
            force=True,
            now=NOW,
        )


def test_force_does_not_bypass_released_evidence_check(tmp_path: Path) -> None:
    _write_claim(tmp_path, "ce-476-claim-lifecycle", state="landed")

    with pytest.raises(lifecycle.ClaimLifecycleError, match="no \\.git metadata"):
        lifecycle.transition_claim(
            tmp_path,
            "ce-476-claim-lifecycle",
            "released",
            sha="abc123",
            force=True,
            now=NOW,
        )


def test_terminal_transition_with_ancestor_sha_passes(tmp_path: Path) -> None:
    sha = _init_git_repo(tmp_path)
    _write_claim(tmp_path, "ce-476-claim-lifecycle", state="harvested")

    result = lifecycle.transition_claim(
        tmp_path,
        "ce-476-claim-lifecycle",
        "landed",
        sha=sha,
        now=NOW,
    )

    assert result.new_state == "landed"
    assert result.merge_sha == sha


def test_force_bypasses_order_but_still_requires_verified_terminal_sha(tmp_path: Path) -> None:
    sha = _init_git_repo(tmp_path)
    _write_claim(tmp_path, "ce-476-claim-lifecycle", state="claimed")

    result = lifecycle.transition_claim(
        tmp_path,
        "ce-476-claim-lifecycle",
        "landed",
        sha=sha,
        force=True,
        now=NOW,
    )

    assert result.old_state == "claimed"
    assert result.new_state == "landed"
    assert result.merge_sha == sha


def test_terminal_transition_with_non_ancestor_sha_is_refused(tmp_path: Path) -> None:
    _init_git_repo(tmp_path)
    non_ancestor_sha = _create_non_ancestor_sha(tmp_path)
    _write_claim(tmp_path, "ce-476-claim-lifecycle", state="harvested")

    with pytest.raises(lifecycle.ClaimLifecycleError, match="not reachable from main ref"):
        lifecycle.transition_claim(
            tmp_path,
            "ce-476-claim-lifecycle",
            "landed",
            sha=non_ancestor_sha,
            now=NOW,
        )


def test_terminal_transition_without_main_refs_is_refused(tmp_path: Path) -> None:
    sha = _init_git_repo(tmp_path, branch="topic")
    _write_claim(tmp_path, "ce-476-claim-lifecycle", state="harvested")

    with pytest.raises(lifecycle.ClaimLifecycleError, match="no accessible main refs"):
        lifecycle.transition_claim(tmp_path, "ce-476-claim-lifecycle", "landed", sha=sha, now=NOW)


def test_claimed_to_abandoned_is_refused_without_force(tmp_path: Path) -> None:
    _write_claim(tmp_path, "ce-476-claim-lifecycle")

    with pytest.raises(lifecycle.ClaimLifecycleError, match="illegal"):
        lifecycle.transition_claim(tmp_path, "ce-476-claim-lifecycle", "abandoned", now=NOW)


def test_same_state_same_sha_transition_is_byte_identical_noop(tmp_path: Path) -> None:
    sha = _init_git_repo(tmp_path)
    path = _write_claim(tmp_path, "ce-476-claim-lifecycle", state="landed")
    original = path.read_text(encoding="utf-8").replace("merge_sha: null", f"merge_sha: {sha}")
    path.write_text(original, encoding="utf-8")

    result = lifecycle.transition_claim(
        tmp_path,
        "ce-476-claim-lifecycle",
        "landed",
        sha=sha,
        now="2026-07-06T15:00:00Z",
    )

    assert result.old_state == "landed"
    assert result.new_state == "landed"
    assert path.read_text(encoding="utf-8") == original


def test_same_state_different_sha_transition_updates_claim(tmp_path: Path) -> None:
    old_sha = _init_git_repo(tmp_path)
    (tmp_path / "README.md").write_text("updated\n", encoding="utf-8")
    _git(tmp_path, "add", "README.md")
    _git(tmp_path, "commit", "-m", "update")
    new_sha = _git(tmp_path, "rev-parse", "HEAD")
    path = _write_claim(tmp_path, "ce-476-claim-lifecycle", state="landed")
    original = path.read_text(encoding="utf-8").replace("merge_sha: null", f"merge_sha: {old_sha}")
    path.write_text(original, encoding="utf-8")

    result = lifecycle.transition_claim(
        tmp_path,
        "ce-476-claim-lifecycle",
        "landed",
        sha=new_sha,
        now="2026-07-06T15:00:00Z",
    )

    written = path.read_text(encoding="utf-8")
    assert result.old_state == "landed"
    assert result.new_state == "landed"
    assert result.merge_sha == new_sha
    assert written != original
    assert f"merge_sha: {new_sha}" in written
    assert "transitioned_at: 2026-07-06T15:00:00Z" in written


def test_legacy_claim_is_upgraded_from_prose(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CE_SEAT", "seat-alpha")
    monkeypatch.setenv("CE_CONTROLLER", "CE-DEV-2")
    path = tmp_path / ".ce" / "claims" / "ce-476-claim-lifecycle.md"
    path.parent.mkdir(parents=True)
    path.write_text("CE-DEV-2 dispatched ce-476 to seat-alpha\n", encoding="utf-8")

    lifecycle.transition_claim(tmp_path, "ce-476-claim-lifecycle", "in-build", now=NOW)

    written = path.read_text(encoding="utf-8")
    assert written.startswith("---\nslug: ce-476-claim-lifecycle\n")
    assert "state: in-build" in written
    assert "seat: seat-alpha" in written
    assert "CE-DEV-2 dispatched ce-476" in written


def test_list_claims_filters_state_and_seat(tmp_path: Path) -> None:
    _write_claim(tmp_path, "ce-476-claim-lifecycle", state="ready")
    other = _write_claim(tmp_path, "ce-477-other", state="claimed")
    other.write_text(other.read_text(encoding="utf-8").replace("seat: seat-alpha", "seat: seat-beta"), encoding="utf-8")

    rows = lifecycle.list_claims(tmp_path, state="ready", seat="seat-alpha")

    assert [row["slug"] for row in rows] == ["ce-476-claim-lifecycle"]
    table = lifecycle.format_table(rows)
    assert "SLUG" in table
    assert "ce-476-claim-lifecycle" in table
