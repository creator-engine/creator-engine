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
    _resolve_from,
    build_edges,
    discover_modules,
    evaluate,
)


# --- registration + green on the real package -------------------------------

def test_registered_in_check_surface():
    reg = registered_checks()
    assert CHECK_NAME in reg
    # 47 with the G-6 ce_scope check registered alongside version_boundary.
    # v3.5-C A-C1 added the decision_record check: 47 -> 48. v3.5-C A-C2 added
    # the storage_tier_finding check: 48 -> 49. v3.5-C A-C3 added the
    # peer_authority check: 49 -> 50. v3.5-C A-C4 added the forge_claim_dedup
    # check: 50 -> 51. v3.5-E.3 E3-G1 added the install_answers check
    # (declared in-gate): 51 -> 52.
    assert len(reg) == 53


def test_green_on_real_package(version_boundary_real_run):
    result = version_boundary_real_run
    assert result.ok, [e.format() for e in result.errors]
    assert result.errors == ()
    assert result.warnings == ()


def test_hard_invariant_zero_v1_v3_crossings(version_boundary_modules):
    errors, _ = evaluate(version_boundary_modules)
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


def test_allowlist_has_no_stale_entries_on_main(version_boundary_modules):
    # Every allowlisted edge must still exist -> no CODE_STALE warnings on main.
    _, warnings = evaluate(version_boundary_modules)
    assert warnings == []


def test_taxonomy_counts_and_disjoint():
    # v3.5-F Q1 added the per-seat resource-bounding launch mechanics
    # (``resource_bound_spec``, sibling of ``claude_launch_spec``): 21 -> 22.
    # G1-codex adds ``codex_launch_spec`` as the 23rd v1 runtime module.
    assert len(ver.V1_RUNTIME) == 23
    # v3 gained the G-7 product surface — the two-mode installer logic
    # (``v3_installer``) atop the Completion Report (``v3_report``), the shaping
    # dialogue (``v3_shaping``), the session render (``v3_session``), the CLI
    # (``v3_cli``), and the G-6 spine: 24 -> 26. v3.5-A.1 added the OpenShell
    # runner backend (``runner.openshell_backend``): 26 -> 27. v3.5-D.0.1 added
    # the live usage tap (``runner.usage_tap``): 27 -> 28. v3.5-B.1 added the
    # Cockpit family — the L2 read-model (= harness-paper F1,
    # ``runner.cockpit_readmodel``), the CE_DEMO seed
    # (``runner.cockpit_demo_seed``, Fork F-b), and the L3 Textual view
    # (``v3_cockpit``): 28 -> 31. The v3.5-C α-precursor added the Projects-v2
    # backlog adapter + forge-projected claim (``forge.backlog``): 31 -> 32.
    # v3.1-G1 added the live-spawn bridge (``v3_seat_bridge``): 32 -> 33.
    # v3.1-G2a added the branch-push primitive (``forge.change_push``): 33 -> 34,
    # and the forge-leg composition root (``v3_forge_join``): 34 -> 35. v3.1-B.8
    # added the Operator-notify feed (``runner.notify_feed``): 35 -> 36.
    # v3.5-E.2 added the signed-spec onboard apply executor: 36 -> 37.
    assert len(ver.V3_RUNTIME) == 37
    assert ver.V1_RUNTIME.isdisjoint(ver.V3_RUNTIME)


# --- teeth: each guard fires on a synthetic violation -----------------------

def test_cross_fires_when_v1_module_moved_to_v3(monkeypatch, version_boundary_modules):
    # tmux_adapter (v1) is imported by lane_runtime/ce_cli (v1); moving it to v3
    # makes those edges v1->v3 crossings.
    monkeypatch.setattr(ver, "V1_RUNTIME", ver.V1_RUNTIME - {"tmux_adapter"})
    monkeypatch.setattr(ver, "V3_RUNTIME", ver.V3_RUNTIME | {"tmux_adapter"})
    errors, _ = evaluate(version_boundary_modules)
    assert [e for e in errors if e.code == CODE_CROSS]


def test_unallowed_fires_when_allowlist_emptied(monkeypatch, version_boundary_modules):
    monkeypatch.setattr(ver, "BASELINE_SHARED_TO_VERSION_ALLOWLIST", frozenset())
    errors, _ = evaluate(version_boundary_modules)
    unallowed = [e for e in errors if e.code == CODE_UNALLOWED]
    assert len(unallowed) == 3


def test_missing_fires_for_ghost_runtime_module(monkeypatch, version_boundary_modules):
    monkeypatch.setattr(ver, "V1_RUNTIME", ver.V1_RUNTIME | {"ghost_module"})
    errors, _ = evaluate(version_boundary_modules)
    assert [e for e in errors if e.code == CODE_MISSING]


def test_overlap_fires_for_module_in_both_surfaces(monkeypatch, version_boundary_modules):
    monkeypatch.setattr(ver, "V3_RUNTIME", ver.V3_RUNTIME | {"tmux_adapter"})
    errors, _ = evaluate(version_boundary_modules)
    assert [e for e in errors if e.code == CODE_OVERLAP]


def test_classify_lines():
    assert ver.classify("lane_runtime") == ver.V1
    assert ver.classify("orchestrator") == ver.V3
    assert ver.classify("onboard_apply") == ver.V3
    assert ver.classify("loader") == ver.SHARED
    assert ver.classify("runtime_evidence_spine") == ver.SHARED  # deliberate call
    assert ver.classify("evidence_sink") == ver.V3              # deliberate call
    assert ver.classify("environment_guard") == ver.SHARED      # deliberate call


# --- regression: relative imports inside __init__.py (reviewer finding) ------

PKG = "creator_engine_validator"


def test_resolve_from_anchors_package_init_at_itself():
    # A package's own __init__ (discovered dotted name == the package) anchors
    # relative imports at the package itself, NOT its parent.
    assert _resolve_from(f"{PKG}.forge", True, 1, "change") == f"{PKG}.forge.change"
    assert _resolve_from(f"{PKG}.forge", True, 2, "lane_runtime") == f"{PKG}.lane_runtime"
    assert _resolve_from(PKG, True, 1, "orchestrator") == f"{PKG}.orchestrator"
    # A regular module anchors relatives at its parent package.
    assert (
        _resolve_from(f"{PKG}.checks.ce_runtime_evidence", False, 2, "runtime_evidence_spine")
        == f"{PKG}.runtime_evidence_spine"
    )


def _write_pkg(root, rel_path, body):
    p = root / rel_path
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(body, encoding="utf-8")


def test_relative_cross_version_import_in_init_is_detected(tmp_path):
    # Synthetic creator_engine_validator package: a v3 subpackage __init__ uses a
    # RELATIVE import of a v1 module. The guard must capture the edge (the bug was
    # that __init__ relative imports were silently dropped -> boundary bypassable).
    root = tmp_path / PKG
    _write_pkg(root, "__init__.py", "from .orchestrator import Orchestrator\n")  # shared->v3 relative
    _write_pkg(root, "orchestrator.py", "class Orchestrator: ...\n")
    _write_pkg(root, "lane_runtime.py", "class LaneError(Exception): ...\n")
    _write_pkg(root, "forge/__init__.py", "from ..lane_runtime import LaneError\n")  # v3->v1 relative
    _write_pkg(root, "forge/change.py", "VALUE = 1\n")

    edges = build_edges(discover_modules(root))
    # both relative-__init__ edges are now resolved (previously: missing)
    assert ("forge", "lane_runtime") in edges        # v3 -> v1 (a HARD cross)
    assert ("", "orchestrator") in edges             # root __init__ (shared) -> v3
    # and they classify as boundary-relevant under the real taxonomy
    assert {ver.classify("forge"), ver.classify("lane_runtime")} == {ver.V3, ver.V1}
    assert ver.classify("orchestrator") == ver.V3
