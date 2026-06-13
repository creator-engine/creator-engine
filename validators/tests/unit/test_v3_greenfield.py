"""Unit tests for the E4 greenfield first-project read model."""

from __future__ import annotations

import inspect

from creator_engine_validator import _versions as ver
from creator_engine_validator import v3_greenfield as gf


def _values(**overrides):
    values = {
        "host.workspace_root": "~/ce-workspaces",
        "github.mode": "new",
        "github.repo": "octo/greenfield",
        "project.name": "greenfield",
        "project.scaffold.kind": "minimal",
    }
    values.update(overrides)
    return values


def test_greenfield_module_is_v3_and_pure():
    assert ver.classify("v3_greenfield") == ver.V3
    src = inspect.getsource(gf)
    for marker in ("open(", "read_text", "write_text", "subprocess", "socket", "datetime", "random"):
        assert marker not in src


def test_first_project_plan_is_greenfield_only_and_references_e2():
    assert gf.build_first_project_plan({**_values(), "github.mode": "existing"}) is None
    plan = gf.build_first_project_plan(_values(), missing_keys=["project.name"])
    assert plan["mode"] == "greenfield"
    assert plan["project_root"] == "~/ce-workspaces/greenfield"
    assert plan["scaffold_input"]["kind"] == "minimal"
    assert plan["scaffold_input"]["supplied_to_e2_leg"] == "workspace_checkout"
    assert plan["e2_plan_ref"] == "github_leg"
    assert plan["e2_apply_result_ref"] is None
    assert plan["e2_apply_required"] is True
    assert plan["frame_to_ship"] == {key: False for key in gf.FRAME_TO_SHIP_KEYS}
    assert plan["first_ship_not_yet_counted"] is True
    assert plan["missing_answers"] == ["project.name"]


def test_e2_apply_result_is_read_through_not_recounted():
    result = {
        "legs_total": 12,
        "verified_count": 11,
        "applied": 4,
        "already_satisfied": 7,
        "failed": 1,
        "refused": 0,
        "greenfield_repos_created": 1,
        "repos_already_satisfied": 0,
        "legs": [
            {"id": "workspace_checkout", "status": "applied", "verification": {"ok": True, "path": "/w/app"}},
            {"id": "github_repo_create", "status": "applied", "verification": {"ok": True}},
            {"id": "github_app_install", "status": "already_satisfied", "verification": {"ok": True}},
            {"id": "github_workflow_install", "status": "failed", "verification": {"ok": False}},
            {"id": "github_branch_protection", "status": "skipped", "verification": {}},
        ],
    }
    plan = gf.build_first_project_plan(_values(), e2_apply_result=result, e2_apply_result_ref="state/onboard/ledger.ndjson")
    assert plan["e2_apply_required"] is False
    assert plan["e2_apply_result_ref"] == "state/onboard/ledger.ndjson"
    convergence = plan["e2_convergence"]
    assert convergence["counts"]["verified_count"] == 11
    assert convergence["counts"]["applied"] == 4
    assert convergence["legs"]["workspace_checkout"]["verified"] is True
    assert convergence["legs"]["github_workflow_install"]["verified"] is False


def test_e2_smoke_scope_never_counts_as_e4_first_scope():
    state = gf.frame_to_ship_state({
        "scope_id": gf.E2_SMOKE_SCOPE_ID,
        "scope_filed": True,
        "scope_ratified": True,
        "build_spawned": True,
        "pr_opened": True,
        "review_recorded": True,
        "pr_merged": True,
    })
    assert state == {key: False for key in gf.FRAME_TO_SHIP_KEYS}


def test_first_ship_requires_review_before_merge():
    without_review = gf.frame_to_ship_state({
        "scope_id": "first-real-change",
        "scope_filed": True,
        "scope_ratified": True,
        "build_spawned": True,
        "pr_opened": True,
        "review_recorded": False,
        "pr_merged": True,
    })
    assert without_review["first_pr_merged"] is False

    with_review = gf.frame_to_ship_state({
        "scope_id": "first-real-change",
        "scope_filed": True,
        "scope_ratified": True,
        "build_spawned": True,
        "pr_opened": True,
        "review_recorded": True,
        "pr_merged": True,
    })
    assert with_review["first_pr_merged"] is True


def test_review_ship_agreement_checks_pr_number_consistency():
    ok = gf.review_ship_agreement({
        "scope_id": "first-real-change",
        "run_id": "run-1",
        "pr_number": 7,
        "review_evidence": {"pr_number": 7},
        "merge_evidence": {"pr_number": 7},
        "runtime_evidence": {"path": "runs/run-1.yaml"},
        "manifest_evidence": {"path": ".ce/pr-manifests/x.md"},
        "report_evidence": {"path": "report.md"},
    })
    assert ok["ok"] is True

    bad = gf.review_ship_agreement({
        "scope_id": "first-real-change",
        "run_id": "run-1",
        "pr_number": 7,
        "review_evidence": {"pr_number": 9},
        "merge_evidence": {"pr_number": 7},
        "runtime_evidence": {"path": "runs/run-1.yaml"},
        "manifest_evidence": {"path": ".ce/pr-manifests/x.md"},
        "report_evidence": {"path": "report.md"},
    })
    assert bad["ok"] is False
    assert bad["mismatches"] == ["review_pr_number"]
