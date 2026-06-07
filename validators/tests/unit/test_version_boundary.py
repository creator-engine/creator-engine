"""Unit tests for the ``version_boundary`` check (G-3.9 coexistence guard)."""

from __future__ import annotations

from creator_engine_validator import _versions as ver
from creator_engine_validator.checks import registered_checks
from creator_engine_validator.checks.version_boundary import (
    CHECK_NAME,
    CODE_CROSS,
    CODE_MISSING,
    CODE_OVERLAP,
    CODE_UNALLOWED,
    _package_dir,
    discover_modules,
    evaluate,
    run,
)


def _mods():
    return discover_modules(_package_dir())


# --- registration + green on the real package -------------------------------

def test_registered_as_check_44():
    reg = registered_checks()
    assert CHECK_NAME in reg
    assert len(reg) == 44


def test_green_on_real_package():
    result = run([])
    assert result.ok, [e.format() for e in result.errors]
    assert result.errors == ()
    assert result.warnings == ()


def test_hard_invariant_zero_v1_v3_crossings():
    errors, _ = evaluate(_mods())
    assert [e for e in errors if e.code == CODE_CROSS] == []


# --- the baselined allowlist is exactly the 3 derived edges, and minimal ----

def test_allowlist_is_the_three_baselined_edges():
    assert ver.BASELINE_SHARED_TO_VERSION_ALLOWLIST == frozenset(
        {
            ("cli", "hook_check"),
            ("cli", "pco_allocator"),
            ("environment_guard", "packaging_runtime"),
        }
    )


def test_allowlist_has_no_stale_entries_on_main():
    # Every allowlisted edge must still exist -> no CODE_STALE warnings on main.
    _, warnings = evaluate(_mods())
    assert warnings == []


def test_taxonomy_counts_and_disjoint():
    assert len(ver.V1_RUNTIME) == 21
    assert len(ver.V3_RUNTIME) == 18
    assert ver.V1_RUNTIME.isdisjoint(ver.V3_RUNTIME)


# --- teeth: each guard fires on a synthetic violation -----------------------

def test_cross_fires_when_v1_module_moved_to_v3(monkeypatch):
    # tmux_adapter (v1) is imported by lane_runtime/ce_cli (v1); moving it to v3
    # makes those edges v1->v3 crossings.
    monkeypatch.setattr(ver, "V1_RUNTIME", ver.V1_RUNTIME - {"tmux_adapter"})
    monkeypatch.setattr(ver, "V3_RUNTIME", ver.V3_RUNTIME | {"tmux_adapter"})
    errors, _ = evaluate(_mods())
    assert [e for e in errors if e.code == CODE_CROSS]


def test_unallowed_fires_when_allowlist_emptied(monkeypatch):
    monkeypatch.setattr(ver, "BASELINE_SHARED_TO_VERSION_ALLOWLIST", frozenset())
    errors, _ = evaluate(_mods())
    unallowed = [e for e in errors if e.code == CODE_UNALLOWED]
    assert len(unallowed) == 3


def test_missing_fires_for_ghost_runtime_module(monkeypatch):
    monkeypatch.setattr(ver, "V1_RUNTIME", ver.V1_RUNTIME | {"ghost_module"})
    errors, _ = evaluate(_mods())
    assert [e for e in errors if e.code == CODE_MISSING]


def test_overlap_fires_for_module_in_both_surfaces(monkeypatch):
    monkeypatch.setattr(ver, "V3_RUNTIME", ver.V3_RUNTIME | {"tmux_adapter"})
    errors, _ = evaluate(_mods())
    assert [e for e in errors if e.code == CODE_OVERLAP]


def test_classify_lines():
    assert ver.classify("lane_runtime") == ver.V1
    assert ver.classify("orchestrator") == ver.V3
    assert ver.classify("loader") == ver.SHARED
    assert ver.classify("runtime_evidence_spine") == ver.SHARED  # deliberate call
    assert ver.classify("evidence_sink") == ver.V3              # deliberate call
    assert ver.classify("environment_guard") == ver.SHARED      # deliberate call
