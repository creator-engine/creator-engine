"""Unit tests for creator_engine_validator.disk_headroom (F-1.2).

Tests the public API of disk_headroom.py and the pr_preflight integration
that refuses to start the baseline-diff suite when free space is low.
"""

from __future__ import annotations

import io
import os
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

from creator_engine_validator import disk_headroom as dh
from creator_engine_validator import pr_preflight


# ---------------------------------------------------------------------------
# disk_headroom module — unit tests
# ---------------------------------------------------------------------------


class TestFreeGb:
    """Tests for disk_headroom.free_gb using a statvfs mock."""

    def _make_stat(self, *, f_bavail: int, f_frsize: int) -> object:
        """Build a minimal os.stat_result-like object."""

        class _StatVFS:
            pass

        s = _StatVFS()
        s.f_bavail = f_bavail
        s.f_frsize = f_frsize
        return s

    def test_returns_gib(self, tmp_path: Path) -> None:
        # 32 GiB free: 32 * 1024**3 bytes in blocks of 4096
        gib_32 = 32 * (1024 ** 3)
        block_size = 4096
        blocks = gib_32 // block_size
        with patch("os.statvfs", return_value=self._make_stat(f_bavail=blocks, f_frsize=block_size)):
            result = dh.free_gb(tmp_path)
        assert abs(result - 32.0) < 0.01

    def test_zero_free(self, tmp_path: Path) -> None:
        with patch("os.statvfs", return_value=self._make_stat(f_bavail=0, f_frsize=4096)):
            result = dh.free_gb(tmp_path)
        assert result == 0.0


class TestEffectiveMinFreeGb:
    def test_default(self, monkeypatch) -> None:
        monkeypatch.delenv(dh.MIN_FREE_GB_ENV, raising=False)
        assert dh.effective_min_free_gb() == dh.DEFAULT_MIN_FREE_GB

    def test_override_via_env(self, monkeypatch) -> None:
        monkeypatch.setenv(dh.MIN_FREE_GB_ENV, "15.5")
        assert dh.effective_min_free_gb() == pytest.approx(15.5)

    def test_invalid_env_raises(self, monkeypatch) -> None:
        monkeypatch.setenv(dh.MIN_FREE_GB_ENV, "not-a-number")
        with pytest.raises(RuntimeError, match=dh.MIN_FREE_GB_ENV):
            dh.effective_min_free_gb()

    def test_zero_env_raises(self, monkeypatch) -> None:
        monkeypatch.setenv(dh.MIN_FREE_GB_ENV, "0")
        with pytest.raises(RuntimeError, match=dh.MIN_FREE_GB_ENV):
            dh.effective_min_free_gb()

    def test_negative_env_raises(self, monkeypatch) -> None:
        monkeypatch.setenv(dh.MIN_FREE_GB_ENV, "-5")
        with pytest.raises(RuntimeError, match=dh.MIN_FREE_GB_ENV):
            dh.effective_min_free_gb()

    def test_empty_env_uses_default(self, monkeypatch) -> None:
        monkeypatch.setenv(dh.MIN_FREE_GB_ENV, "")
        assert dh.effective_min_free_gb() == dh.DEFAULT_MIN_FREE_GB


class TestCheckHeadroom:
    """Tests for disk_headroom.check_headroom using a statvfs seam."""

    def _patch_free_gb(self, measured_gb: float):
        return patch.object(dh, "free_gb", return_value=measured_gb)

    def test_passes_when_above_threshold(self, tmp_path: Path) -> None:
        with self._patch_free_gb(50.0):
            result = dh.check_headroom(tmp_path, min_free_gb=30.0)
        assert result == pytest.approx(50.0)

    def test_passes_at_exact_threshold(self, tmp_path: Path) -> None:
        with self._patch_free_gb(30.0):
            result = dh.check_headroom(tmp_path, min_free_gb=30.0)
        assert result == pytest.approx(30.0)

    def test_raises_when_below_threshold(self, tmp_path: Path) -> None:
        with self._patch_free_gb(10.0):
            with pytest.raises(dh.DiskHeadroomError) as exc_info:
                dh.check_headroom(tmp_path, min_free_gb=30.0)
        err = exc_info.value
        assert err.free_gb == pytest.approx(10.0)
        assert err.min_free_gb == pytest.approx(30.0)
        assert "disk_headroom" in str(err)
        assert "10.0 GiB free" in str(err)
        assert "30.0 GiB required" in str(err)
        assert dh.MIN_FREE_GB_ENV in str(err)

    def test_names_module_in_error_message(self, tmp_path: Path) -> None:
        """Error message must name 'disk_headroom' for operator visibility."""
        with self._patch_free_gb(0.5):
            with pytest.raises(dh.DiskHeadroomError, match="disk_headroom"):
                dh.check_headroom(tmp_path, min_free_gb=30.0)

    def test_uses_env_threshold_when_min_free_gb_is_none(self, tmp_path: Path, monkeypatch) -> None:
        monkeypatch.setenv(dh.MIN_FREE_GB_ENV, "20")
        with self._patch_free_gb(25.0):
            result = dh.check_headroom(tmp_path)
        assert result == pytest.approx(25.0)

    def test_uses_default_threshold_when_no_arg_no_env(self, tmp_path: Path, monkeypatch) -> None:
        monkeypatch.delenv(dh.MIN_FREE_GB_ENV, raising=False)
        with self._patch_free_gb(dh.DEFAULT_MIN_FREE_GB - 1.0):
            with pytest.raises(dh.DiskHeadroomError):
                dh.check_headroom(tmp_path)

    def test_zero_free_raises(self, tmp_path: Path) -> None:
        with self._patch_free_gb(0.0):
            with pytest.raises(dh.DiskHeadroomError):
                dh.check_headroom(tmp_path, min_free_gb=1.0)


# ---------------------------------------------------------------------------
# pr_preflight integration — disk_headroom gate
# ---------------------------------------------------------------------------


class _MinimalFakeRunner:
    """Minimal fake runner for headroom-specific preflight path tests.

    Wires every check to pass trivially.  The headroom gate itself is
    exercised via ``patch.object(dh, 'free_gb', ...)``, keeping the runner
    orthogonal to the headroom logic.
    """

    def __init__(self, repo_root: Path) -> None:
        self.repo_root = repo_root
        self.pytest_called: bool = False

    def __call__(self, argv, cwd, env=None, *, timeout=None):
        argv = list(argv)
        if argv == ["git", "rev-parse", "--show-toplevel"]:
            return pr_preflight.CommandResult(0, str(self.repo_root) + "\n", "")
        if argv == ["git", "status", "--porcelain"]:
            return pr_preflight.CommandResult(0, "", "")
        if argv == ["git", "branch", "--show-current"]:
            return pr_preflight.CommandResult(0, "ce-f1-storage-admission\n", "")
        if argv[:2] == ["git", "fetch"]:
            return pr_preflight.CommandResult(0, "", "")
        if argv[:2] == ["git", "merge-base"]:
            return pr_preflight.CommandResult(0, "deadbeef\n", "")
        if argv[:3] == ["git", "diff", "--name-only"]:
            return pr_preflight.CommandResult(0, "", "")
        if argv[:2] == ["git", "show"]:
            return pr_preflight.CommandResult(1, "", "not found in test fixture")
        if argv[:4] == ["git", "worktree", "add", "--detach"]:
            return pr_preflight.CommandResult(0, "", "")
        if argv[:4] == ["git", "worktree", "remove", "--force"]:
            return pr_preflight.CommandResult(0, "", "")
        if "pytest" in " ".join(str(a) for a in argv):
            self.pytest_called = True
            return pr_preflight.CommandResult(0, "1 passed in 0.01s\n", "")
        return pr_preflight.CommandResult(0, "ok\n", "")


def _stub_all_heavy_gates(monkeypatch) -> None:
    """Monkeypatch away every expensive / filesystem-touching preflight gate.

    Leaves the disk_headroom gate and the runner-dispatched checks in place
    so the headroom integration can be verified in isolation.
    """
    monkeypatch.setattr(pr_preflight, "_assert_brain_ledger_delta_uses_current_tail",
                        lambda *_a, **_k: "not applicable (test stub)")
    monkeypatch.setattr(pr_preflight, "_assert_brain_append_intent_xor",
                        lambda *_a, **_k: "not applicable (test stub)")
    monkeypatch.setattr(pr_preflight, "_reconcile_local_brain_state_if_safe",
                        lambda *_a, **_k: "not applicable (test stub)")
    monkeypatch.setattr(pr_preflight, "_yaml_parse", lambda *_a, **_k: None)
    monkeypatch.setattr(pr_preflight, "_workflow_yaml_paths", lambda r: [])
    monkeypatch.setattr(pr_preflight, "_artifact_yaml_paths", lambda r: [])
    monkeypatch.setattr(pr_preflight, "_workflow_permissions_audit", lambda r: None)


def _config_for_headroom(repo_root: Path) -> pr_preflight.PreflightConfig:
    return pr_preflight.PreflightConfig(
        repo_root=repo_root,
        base="origin/main",
        head_ref="ce-f1-storage-admission",
        declared_work_class="S",
    )


def test_preflight_refuses_when_disk_below_threshold(tmp_path: Path, monkeypatch) -> None:
    """run_preflight must stop before baseline-diff when disk is low."""
    _stub_all_heavy_gates(monkeypatch)
    runner = _MinimalFakeRunner(tmp_path)
    config = _config_for_headroom(tmp_path)
    out = io.StringIO()
    err = io.StringIO()

    with patch.object(dh, "free_gb", return_value=5.0):
        rc = pr_preflight.run_preflight(config, runner=runner, out=out, err=err)

    assert rc == 1
    # Must name disk_headroom in output
    output = out.getvalue() + err.getvalue()
    assert "disk_headroom" in output
    assert "5.0 GiB" in output
    # Baseline-diff (pytest) must NOT have been launched
    assert not runner.pytest_called


def test_preflight_passes_headroom_check_when_disk_sufficient(tmp_path: Path, monkeypatch) -> None:
    """When disk is ample, the disk_headroom check passes and suite proceeds."""
    _stub_all_heavy_gates(monkeypatch)
    runner = _MinimalFakeRunner(tmp_path)
    config = _config_for_headroom(tmp_path)
    out = io.StringIO()
    err = io.StringIO()

    with patch.object(dh, "free_gb", return_value=50.0):
        pr_preflight.run_preflight(config, runner=runner, out=out, err=err)

    output = out.getvalue()
    assert f"[PASS] {pr_preflight.DISK_HEADROOM_CHECK_NAME}" in output
    assert "50.0 GiB free" in output
    # Suite was allowed to proceed (runner saw pytest)
    assert runner.pytest_called


def test_disk_headroom_error_is_distinct_runtime_error(tmp_path: Path) -> None:
    """DiskHeadroomError must be a RuntimeError so _run_check handles it."""
    with patch.object(dh, "free_gb", return_value=1.0):
        with pytest.raises(dh.DiskHeadroomError) as exc_info:
            dh.check_headroom(tmp_path, min_free_gb=30.0)
    assert isinstance(exc_info.value, RuntimeError)
