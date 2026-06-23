"""ce-ops#197 PR-4 — doctor onboard phase-1 probes + brain_init library entry.

The low-TMPDIR + PATH-gap probes `ce onboard` phase 1 consumes, and the
library-callable `ce_cli.brain_init` the orchestrator drives (not via argv).
"""
from __future__ import annotations

from collections import namedtuple

import pytest

from creator_engine_validator import ce_cli, doctor_runtime

_Usage = namedtuple("_Usage", "total used free")


# --- low-TMPDIR probe (friction #3) ------------------------------------------
def test_low_tmpdir_true_below_floor():
    assert doctor_runtime.probe_low_tmpdir(
        "/tmp", floor_bytes=1024, disk_usage=lambda _p: _Usage(10, 10, 512)
    ) is True


def test_low_tmpdir_false_above_floor():
    assert doctor_runtime.probe_low_tmpdir(
        "/tmp", floor_bytes=1024, disk_usage=lambda _p: _Usage(10, 0, 4096)
    ) is False


def test_low_tmpdir_false_on_unreadable_path():
    def boom(_p):
        raise OSError("nope")

    assert doctor_runtime.probe_low_tmpdir("/nope", disk_usage=boom) is False


# --- PATH-gap probe (friction #2 / #212) -------------------------------------
def test_path_gap_true_when_local_bin_absent():
    assert doctor_runtime.probe_path_gap(
        path_value="/usr/bin:/bin", home="/home/u"
    ) is True


def test_path_gap_false_when_local_bin_present():
    assert doctor_runtime.probe_path_gap(
        path_value="/home/u/.local/bin:/usr/bin", home="/home/u"
    ) is False


def test_path_gap_false_without_home():
    assert doctor_runtime.probe_path_gap(path_value="/usr/bin", home="") is False


# --- probes surfaced in run_doctor payload -----------------------------------
def test_doctor_payload_carries_onboard_probes(tmp_path):
    report = doctor_runtime.run_doctor(tmp_path, check_packaging=False)
    assert "onboard_probes" in report.payload
    assert set(report.payload["onboard_probes"]) == {"low_tmpdir", "path_gap"}


# --- brain_init library entry (programmatic, not argv) -----------------------
def test_brain_init_creates_then_idempotent(tmp_path):
    state_root = str(tmp_path / "state")
    first = ce_cli.brain_init(state_root)
    assert first.created is True
    second = ce_cli.brain_init(state_root)
    assert second.created is False
    assert second.payload["already_initialized"] is True


def test_brain_init_refuses_corrupt_ledger(tmp_path):
    from creator_engine_validator import brain_runtime

    state_root = str(tmp_path / "state")
    path = brain_runtime.ledger_path(state_root)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("not: [valid: ledger\n", encoding="utf-8")
    with pytest.raises(ce_cli.BrainInitError):
        ce_cli.brain_init(state_root)
