"""Unit tests for the ``version_boundary`` check (G-3.9 coexistence guard)."""

from __future__ import annotations

from creator_engine_validator import _versions as ver
from creator_engine_validator.runner import ring1_tool_guard as _ring1_tool_guard
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
    # (declared in-gate): 51 -> 52. ce-ops#26 added seat_event: 52 -> 53.
    # ce-ops#142 added ce_computer_use_authority_envelope: 53 -> 54.
    # ce-ops#145 added ce_playbook_format: 54 -> 55.
    # ce-ops#167 added ce_brain_assertions: 55 -> 56.
    # ce-ops#163 added seat_class_policy: 56 -> 57.
    # ce-ops#168 added work_sizing: 57 -> 58.
    # ce-ops#164/#170 G5 F2 added work_sizing_floor: 58 -> 59.
    # ce-ops#23 Slice 1 added brownfield_baseline_attestation: 59 -> 60.
    # ce-ops#177 added ce_brain_drift: 60 -> 61.
    # ce-ops#185 added devops_privileged_action_broker: 61 -> 62.
    # ce-ops#162 added operator_runbook_refusal_sync: 62 -> 63.
    assert len(reg) == 63


def test_green_on_real_package(version_boundary_real_run):
    result = version_boundary_real_run
    assert result.ok, [e.format() for e in result.errors]
    assert result.errors == ()
    assert result.warnings == ()


def test_hard_invariant_zero_v1_v3_crossings(version_boundary_modules):
    errors, _ = evaluate(version_boundary_modules)
    assert [e for e in errors if e.code == CODE_CROSS] == []


def test_runtime_policy_check_does_not_import_v3_runner(version_boundary_modules):
    errors, _ = evaluate(version_boundary_modules)
    assert [
        e for e in errors
        if e.code == CODE_UNALLOWED and "checks.ce_runtime_policy" in e.message
    ] == []


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
    # ce-ops#55 adds ``pickup`` (the ``ce pickup`` work-pickup poller) as the 24th.
    # ce-ops#207 W1 adds ``visibility_backend`` (the v1 launcher's visibility/
    # surface seam — a thin tmux_adapter wrapper consumed only by lane_runtime)
    # as the 25th. ce-ops#197 adds ``ce_profile_path`` as the v1 installer-adjacent
    # shell-profile PATH writer: 25 -> 26, and ``ce_provenance`` as the
    # post-install verifier backing ``ce verify-install``: 26 -> 27.
    # ce-ops#207 W2′ adds ``seat_pty_session`` (the CE-owned-PTY session
    # substrate the headless backend spawns through) as the 28th: 27 -> 28.
    # ce-ops#197 PR-5 adds ``ce_onboard`` (the ``ce onboard`` first-run
    # orchestrator — thin composition over the v1 kernel surfaces): 28 -> 29.
    # ce-ops#163 REQ-2 adds ``worker_spawn`` as the harness-agnostic worker
    # primitive over launch_runtime: 29 -> 30.
    # ce-ops#219 adds ``codex_pretooluse`` as the Codex managed PreToolUse
    # adapter over the retained v1 hook-check CLI: 30 -> 31.
    # ce-ops#128 SUB-C adds ``runtime_backend_bridge`` as the visible runner
    # composition bridge under launch_runtime/lane_runtime: 31 -> 32.
    # ce-ops#222 adds ``containment_status`` as the v1 fleet containment
    # attestation CLI runtime over shared probe helpers: 33 -> 34.
    assert len(ver.V1_RUNTIME) == 34
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
    # v3.5-E.4 added the greenfield first-project read model: 37 -> 38.
    # ce-ops#43 added the seat/venue retirement reaper — the substrate-neutral
    # policy fold (``seat_reaper``) + the per-substrate executors
    # (``reaper_executors``): 38 -> 40.
    # ce-ops#34 RS-1 added the AuthorityResolver seam: 40 -> 41.
    # ce-ops#71 Tranche 1 added the unprivileged OS-native backend scaffold
    # (``runner.os_native_backend``): 41 -> 42.
    # ce-ops#88 added the production live-forge ApplyDriver (``onboard_apply_live``): 42 -> 43.
    # G-A2 runner Ring-1 increment 1 added ``runner.ring1_tool_guard``: 43 -> 44.
    # ce-ops#99 P1 added three repo-scope devops forge ops
    # (``forge.ruleset``, ``forge.review_submit``, ``forge.auto_merge``): 44 -> 47.
    # ce-ops#157 added the shared-App user-side install discovery
    # (``forge.user_install_discovery``): 47 -> 48.
    # ce-ops#151 added the rebase-aware stale-review reconciler
    # (``forge.re_review``): 48 -> 49.
    # ce-ops#216 Unit 1 added integrator eviction detection
    # (``forge.eviction_detection``): 49 -> 50.
    # ce-ops#216 Unit 2 added deterministic resolver library
    # (``forge.deterministic_resolvers``): 50 -> 51.
    # ce-ops#216 Unit 4 added the unresolved integrator escalation seam
    # (``forge.integrator_escalation``): 51 -> 52.
    # ce-ops#216 Unit 3 added the deterministic executor race guard
    # (``forge.integrator_executor``): 52 -> 53.
    # ce-ops#216 Unit 5 added the one-shot integrator runner
    # (``forge.integrator_runner``): 53 -> 54.
    # ce-ops#218 added the belt-poller (``forge.integrator_belt``) — the bounded
    # merge-queue repair poll over the Unit 2-5 primitives; pure-forge v3, live
    # actions behind injectable adapters + the merge gate: 54 -> 55.
    assert len(ver.V3_RUNTIME) == 55
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
    assert ver.classify("worker_spawn") == ver.V1
    assert ver.classify("runtime_backend_bridge") == ver.V1
    assert ver.classify("orchestrator") == ver.V3
    assert ver.classify("onboard_apply") == ver.V3
    assert ver.classify("v3_greenfield") == ver.V3
    assert ver.classify("seat_reaper") == ver.V3
    assert ver.classify("reaper_executors") == ver.V3
    assert ver.classify("runner.os_native_backend") == ver.V3
    assert ver.classify("runner.ring1_tool_guard") == ver.V3
    assert ver.classify("forge.deterministic_resolvers") == ver.V3
    assert ver.classify("forge.integrator_escalation") == ver.V3
    assert ver.classify("forge.integrator_executor") == ver.V3
    assert ver.classify("forge.integrator_runner") == ver.V3
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


# ---------------------------------------------------------------------------
# ce-ops#43 §10.14 v3-boundary-holds — the reaper modules import no v1 module and
# cross to archive/release via subprocess+DATA only (AST-asserted contract).
# ---------------------------------------------------------------------------

import ast as _ast
from pathlib import Path as _Path

from creator_engine_validator import reaper_executors as _reaper_executors
from creator_engine_validator import seat_reaper as _seat_reaper


def _top_level_imports(module) -> set[str]:
    src = _Path(module.__file__).read_text(encoding="utf-8")
    tree = _ast.parse(src)
    referenced: set[str] = set()
    for node in _ast.walk(tree):
        if isinstance(node, _ast.Import):
            for alias in node.names:
                referenced.add(alias.name.split(".")[0])
        elif isinstance(node, _ast.ImportFrom):
            if node.module:
                referenced.add(node.module.split(".")[0])
            if node.level and node.module is None:  # `from . import x`
                for alias in node.names:
                    referenced.add(alias.name.split(".")[0])
    return referenced


def test_14_reaper_modules_are_v3_and_import_no_v1_module():
    assert "seat_reaper" in ver.V3_RUNTIME
    assert "reaper_executors" in ver.V3_RUNTIME
    for module in (_seat_reaper, _reaper_executors):
        crossed = _top_level_imports(module) & ver.V1_RUNTIME
        assert crossed == set(), f"{module.__name__} must import no v1 module, found {sorted(crossed)}"


def test_14_reaper_crosses_to_v1_legs_via_subprocess_data_only():
    # The two v1 surfaces the reaper depends on are reached by argv, never import:
    # `ce lane archive --json` and `creator-engine-validator pco-release`.
    src = _Path(_reaper_executors.__file__).read_text(encoding="utf-8")
    assert "lane" in src and "archive" in src and "pco-release" in src
    # and the v1 modules behind those legs are NOT imported by either reaper module
    forbidden = {"transcript_archive", "pco_allocator", "ce_cli", "lane_runtime", "launch_runtime"}
    for module in (_seat_reaper, _reaper_executors):
        assert _top_level_imports(module).isdisjoint(forbidden)


def test_ring1_tool_guard_is_v3_and_imports_no_v1_hook_check():
    assert "runner.ring1_tool_guard" in ver.V3_RUNTIME
    imports = _top_level_imports(_ring1_tool_guard)
    assert "hook_check" not in imports
