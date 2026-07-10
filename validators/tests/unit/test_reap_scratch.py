"""Tests for deploy/storage-reaper/reap-scratch.sh (F-1.3 slice 1).

These tests exercise the script via subprocess with ``--dry-run`` so they
do not touch real disk state.  A fixture directory aged beyond the policy
threshold is created under /var/tmp/wt-* to prove the scanner picks it up.
"""

from __future__ import annotations

import os
import subprocess
import time
from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# Locate the script relative to the repo root
# ---------------------------------------------------------------------------

_REPO_ROOT = Path(__file__).resolve().parents[3]
_SCRIPT = _REPO_ROOT / "deploy" / "storage-reaper" / "reap-scratch.sh"


@pytest.fixture(scope="module")
def script_path() -> Path:
    if not _SCRIPT.is_file():
        pytest.skip(f"reap-scratch.sh not found at {_SCRIPT}")
    return _SCRIPT


# ---------------------------------------------------------------------------
# Helper: create an aged directory with a specific mtime
# ---------------------------------------------------------------------------

def _make_aged_dir(base: Path, name: str, age_hours: float) -> Path:
    """Create *base/name* and set its mtime to *age_hours* in the past."""
    target = base / name
    target.mkdir(parents=True, exist_ok=True)
    # touch a file inside so du -sb reports non-zero
    (target / "data.bin").write_bytes(b"\x00" * 1024)
    past = time.time() - (age_hours * 3600)
    os.utime(target, (past, past))
    return target


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_dry_run_exits_zero(script_path: Path, tmp_path: Path) -> None:
    """--dry-run must always exit 0 regardless of disk state."""
    result = subprocess.run(
        ["bash", str(script_path), "--dry-run"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, f"stderr: {result.stderr}"


def test_dry_run_reports_start_complete(script_path: Path) -> None:
    """--dry-run output must contain sweep start and completion markers."""
    result = subprocess.run(
        ["bash", str(script_path), "--dry-run"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert "starting sweep" in result.stdout
    assert "sweep complete" in result.stdout


def test_dry_run_lists_aged_wt_fixture(script_path: Path) -> None:
    """A wt-* dir older than 48h must appear in --dry-run output."""
    # Create a fixture under /var/tmp that is 50h old
    fixture = _make_aged_dir(Path("/var/tmp"), "wt-test-reap-scratch-fixture-50h", age_hours=50)
    try:
        result = subprocess.run(
            ["bash", str(script_path), "--dry-run"],
            capture_output=True,
            text=True,
            check=False,
        )
        assert result.returncode == 0, f"stderr: {result.stderr}"
        # The fixture path must appear in the dry-run listing
        assert str(fixture) in result.stdout, (
            f"Expected {fixture} in dry-run output.\nstdout:\n{result.stdout}"
        )
        assert "[dry-run] would remove" in result.stdout
    finally:
        import shutil
        shutil.rmtree(fixture, ignore_errors=True)


def test_dry_run_does_not_list_fresh_wt_dir(script_path: Path) -> None:
    """A wt-* dir only 1h old must NOT appear in --dry-run output (below 48h threshold)."""
    fixture = _make_aged_dir(Path("/var/tmp"), "wt-test-reap-scratch-fresh-1h", age_hours=1)
    try:
        result = subprocess.run(
            ["bash", str(script_path), "--dry-run"],
            capture_output=True,
            text=True,
            check=False,
        )
        assert result.returncode == 0, f"stderr: {result.stderr}"
        assert str(fixture) not in result.stdout
    finally:
        import shutil
        shutil.rmtree(fixture, ignore_errors=True)


def test_dry_run_lists_aged_pt_fixture(script_path: Path) -> None:
    """A pt-* dir older than 24h must appear in --dry-run output."""
    fixture = _make_aged_dir(Path("/var/tmp"), "pt-test-reap-scratch-fixture-30h", age_hours=30)
    try:
        result = subprocess.run(
            ["bash", str(script_path), "--dry-run"],
            capture_output=True,
            text=True,
            check=False,
        )
        assert result.returncode == 0, f"stderr: {result.stderr}"
        assert str(fixture) in result.stdout, (
            f"Expected {fixture} in dry-run output.\nstdout:\n{result.stdout}"
        )
    finally:
        import shutil
        shutil.rmtree(fixture, ignore_errors=True)


def test_dry_run_does_not_list_fresh_pt_dir(script_path: Path) -> None:
    """A pt-* dir only 2h old must NOT appear in --dry-run output (below 24h threshold)."""
    fixture = _make_aged_dir(Path("/var/tmp"), "pt-test-reap-scratch-fresh-2h", age_hours=2)
    try:
        result = subprocess.run(
            ["bash", str(script_path), "--dry-run"],
            capture_output=True,
            text=True,
            check=False,
        )
        assert result.returncode == 0, f"stderr: {result.stderr}"
        assert str(fixture) not in result.stdout
    finally:
        import shutil
        shutil.rmtree(fixture, ignore_errors=True)


def test_dry_run_does_not_delete_aged_fixture(script_path: Path) -> None:
    """--dry-run must not actually remove the fixture directory."""
    fixture = _make_aged_dir(Path("/var/tmp"), "wt-test-reap-no-delete-dry-run", age_hours=72)
    try:
        subprocess.run(
            ["bash", str(script_path), "--dry-run"],
            capture_output=True,
            text=True,
            check=False,
        )
        # The directory must still exist after --dry-run
        assert fixture.exists(), "--dry-run must not delete the fixture directory"
    finally:
        import shutil
        shutil.rmtree(fixture, ignore_errors=True)


def test_unknown_flag_exits_nonzero(script_path: Path) -> None:
    """An unrecognised flag must cause the script to exit non-zero."""
    result = subprocess.run(
        ["bash", str(script_path), "--unknown-flag"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode != 0
    assert "unknown argument" in result.stderr or "unknown argument" in result.stdout
