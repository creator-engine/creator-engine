"""Harness-support capability matrix tests."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from creator_engine_validator import ce_cli
from creator_engine_validator import harness_matrix as hm

REPO_ROOT = Path(__file__).resolve().parents[3]
EXPECTED_HARNESSES = (
    "claude_code",
    "codex",
    "lane",
    "hermes",
    "opencode",
    "copilot_cli",
    "nanoclaw",
    "discord",
    "slack",
)


def _matrix() -> hm.HarnessMatrix:
    return hm.build_matrix(repo_root=REPO_ROOT)


def _row(matrix: hm.HarnessMatrix, harness: str) -> hm.HarnessRow:
    return next(row for row in matrix.rows if row.harness == harness)


def test_matrix_covers_required_harnesses_and_columns():
    matrix = _matrix()
    assert hm.HARNESSES == EXPECTED_HARNESSES
    assert tuple(row.harness for row in matrix.rows) == EXPECTED_HARNESSES
    assert hm.CAPABILITIES == ("ring0", "ring1", "ring2", "containment", "native_fanout", "status")
    for row in matrix.rows:
        assert tuple(row.cells) == hm.CAPABILITIES


def test_matrix_payload_is_json_safe():
    payload = json.loads(hm.render_json(_matrix()))
    assert payload["kind"] == "harness-support-matrix"
    assert payload["issue"] == "harness-support-matrix"
    assert payload["capabilities"] == list(hm.CAPABILITIES)
    assert [row["harness"] for row in payload["rows"]] == list(hm.HARNESSES)


def test_claude_code_is_ring_0_1_2_full_and_file_backed():
    row = _row(_matrix(), "claude_code")
    assert row.cells["ring0"].value == hm.STATUS_FULL
    assert row.cells["ring1"].value == hm.STATUS_FULL
    assert row.cells["ring2"].value == hm.STATUS_FULL
    assert row.cells["status"].value == hm.STATUS_FULL
    assert "claude_launch_spec.py" in row.cells["ring0"].provenance
    assert ".claude/settings.json" in row.cells["ring1"].provenance
    assert "hook_check.py" in row.cells["ring2"].provenance


def test_codex_is_ring_0_only_with_ring_1_deferred_pending_containment():
    row = _row(_matrix(), "codex")
    assert row.cells["ring0"].value == hm.STATUS_FULL
    assert row.cells["ring0"].verified is True
    assert row.cells["ring1"].value == hm.STATUS_DEFERRED
    assert row.cells["ring1"].verified is False
    assert "deferred pending containment acceptance" in row.cells["ring1"].provenance
    assert row.cells["ring2"].value == hm.STATUS_NONE
    assert row.cells["status"].value == hm.STATUS_PARTIAL


def test_lane_row_is_restored_and_ring1_is_probed_from_lane_invariants():
    row = _row(_matrix(), "lane")
    assert row.cells["ring0"].value == hm.STATUS_FULL
    assert row.cells["ring1"].value == hm.STATUS_FULL
    assert row.cells["ring1"].verified is True
    assert ".claude/settings.json" in row.cells["ring1"].provenance
    assert "CE_LEDGER_ROOT" in row.cells["ring1"].provenance
    assert "lane_runtime.py" in row.cells["ring1"].provenance
    assert row.cells["ring2"].value == hm.STATUS_FULL
    assert row.cells["native_fanout"].value == hm.STATUS_FULL
    assert row.cells["status"].value == hm.STATUS_FULL


def test_lane_ring1_drift_does_not_promote_from_ring0(monkeypatch):
    monkeypatch.setattr(hm, "_lane_ledger_root_env_wired", lambda: False)

    row = _row(_matrix(), "lane")

    assert row.cells["ring0"].value == hm.STATUS_FULL
    assert row.cells["ring0"].verified is True
    assert row.cells["ring1"].verified is False
    assert row.cells["ring1"].value != hm.STATUS_FULL
    assert "CE_LEDGER_ROOT" in row.cells["ring1"].provenance


@pytest.mark.parametrize("harness", ["hermes", "opencode", "copilot_cli"])
def test_unverified_actor_harnesses_stay_deferred(harness: str):
    row = _row(_matrix(), harness)
    assert row.cells["status"].value == hm.STATUS_DEFERRED
    assert row.cells["status"].verified is False
    assert row.cells["ring1"].value == hm.STATUS_DEFERRED
    assert row.cells["ring2"].value == hm.STATUS_DEFERRED


@pytest.mark.parametrize("surface", ["nanoclaw", "discord", "slack"])
def test_emission_only_surfaces_are_non_actors_with_no_ring1_gate(surface: str):
    row = _row(_matrix(), surface)
    assert row.cells["ring0"].value == hm.STATUS_NONE
    assert row.cells["ring1"].value == hm.STATUS_NONE
    assert row.cells["ring2"].value == hm.STATUS_NONE
    assert row.cells["containment"].value == hm.STATUS_NONE
    assert row.cells["native_fanout"].value == hm.STATUS_FULL
    assert row.cells["status"].value == hm.STATUS_NONE
    assert "non-actor" in row.cells["status"].provenance


def test_doc_is_rendered_from_the_matrix():
    expected = hm.render_markdown(_matrix())
    actual = (REPO_ROOT / hm.DOC_PATH).read_text(encoding="utf-8")
    assert actual == expected


def test_cli_renders_markdown(capsys):
    ret = ce_cli.main(["harness-matrix", "--repo-root", str(REPO_ROOT)])
    assert ret == 0
    out = capsys.readouterr().out
    assert "CE harness-support capability matrix" in out
    assert "| claude_code | full | full | full |" in out
    assert "| codex | full | deferred * | none |" in out
    assert "| lane | full | full | full |" in out


def test_cli_renders_json(capsys):
    ret = ce_cli.main(["harness-matrix", "--repo-root", str(REPO_ROOT), "--json"])
    assert ret == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["kind"] == "harness-support-matrix"
    assert [row["harness"] for row in payload["rows"]] == list(hm.HARNESSES)
