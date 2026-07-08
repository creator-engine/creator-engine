"""Harness-support promotion matrix tests."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from creator_engine_validator import ce_cli
from creator_engine_validator import harness_matrix as hm

REPO_ROOT = Path(__file__).resolve().parents[3]
EXPECTED_PROVIDERS = (
    "claude_code",
    "codex",
    "lane_worker",
    "contained_controller_scaffold",
    "ephemeral_controller_providers",
)


def _matrix() -> hm.HarnessMatrix:
    return hm.build_matrix(repo_root=REPO_ROOT)


def _row(matrix: hm.HarnessMatrix, provider: str, ring: str) -> hm.HarnessRow:
    return next(row for row in matrix.rows if row.provider == provider and row.ring == ring)


def _provider_set(matrix: hm.HarnessMatrix) -> tuple[str, ...]:
    return tuple(dict.fromkeys(row.provider for row in matrix.rows))


def test_matrix_covers_required_providers_and_promotion_columns():
    matrix = _matrix()
    assert hm.HARNESSES == EXPECTED_PROVIDERS
    assert _provider_set(matrix) == EXPECTED_PROVIDERS
    assert hm.CAPABILITIES == ("code-support", "launch-wired", "live-proven", "promotion-approved")
    for row in matrix.rows:
        assert tuple(row.cells) == hm.CAPABILITIES


def test_matrix_payload_is_json_safe():
    payload = json.loads(hm.render_json(_matrix()))
    assert payload["kind"] == "harness-support-promotion-matrix"
    assert payload["issue"] == "ticket-479"
    assert payload["capabilities"] == list(hm.CAPABILITIES)
    assert [row["provider"] for row in payload["rows"][:3]] == ["claude_code", "claude_code", "claude_code"]


@pytest.mark.parametrize("ring", ["Ring 0", "Ring 1", "Ring 2"])
def test_claude_rings_are_full_and_gate_capable(ring: str):
    row = _row(_matrix(), "claude_code", ring)
    assert hm.row_all_green(row)
    assert row.gate_capable.value == hm.GATE_YES
    assert row.exception is None


def test_codex_ring0_is_full_but_ring1_waits_for_promotion_packet():
    matrix = _matrix()
    ring0 = _row(matrix, "codex", "Ring 0")
    assert hm.row_all_green(ring0)
    assert ring0.gate_capable.value == hm.GATE_YES

    ring1 = _row(matrix, "codex", "Ring 1")
    assert ring1.cells["code-support"].value == hm.GREEN
    assert ring1.cells["launch-wired"].value == hm.GREEN
    assert ring1.cells["live-proven"].value == hm.RED
    assert ring1.cells["promotion-approved"].value == hm.RED
    assert ring1.gate_capable.value == hm.GATE_NO
    assert "ticket 480" in ring1.cells["live-proven"].provenance


def test_codex_ring2_and_containment_are_not_promoted():
    matrix = _matrix()
    ring2 = _row(matrix, "codex", "Ring 2")
    containment = _row(matrix, "codex", "containment")
    assert ring2.gate_capable.value == hm.GATE_NO
    assert containment.cells["launch-wired"].value == hm.YELLOW
    assert containment.gate_capable.value == hm.GATE_NO


@pytest.mark.parametrize("ring", ["Ring 0", "Ring 1", "Ring 2"])
def test_lane_worker_rows_are_gate_capable_only_as_worker_fanout(ring: str):
    row = _row(_matrix(), "lane_worker", ring)
    assert hm.row_all_green(row)
    assert row.gate_capable.value == hm.GATE_YES
    assert "worker" in row.cells["promotion-approved"].provenance
    assert "controller authority" in row.cells["promotion-approved"].provenance


def test_contained_controller_scaffold_stays_static_dry_run_only():
    matrix = _matrix()
    static = _row(matrix, "contained_controller_scaffold", "C1 static/dry-run")
    assert static.cells["code-support"].value == hm.GREEN
    assert static.cells["launch-wired"].value == hm.YELLOW
    assert static.gate_capable.value == hm.GATE_NO
    for ring in ("C2", "C3", "C4"):
        row = _row(matrix, "contained_controller_scaffold", ring)
        assert row.cells["live-proven"].value == hm.RED
        assert row.gate_capable.value == hm.GATE_NO


def test_ephemeral_controller_providers_are_design_stage_only():
    row = _row(_matrix(), "ephemeral_controller_providers", "design-stage")
    assert row.cells["code-support"].value == hm.YELLOW
    assert row.cells["launch-wired"].value == hm.RED
    assert row.cells["live-proven"].value == hm.RED
    assert row.cells["promotion-approved"].value == hm.RED
    assert row.gate_capable.value == hm.GATE_NO


def test_doc_is_rendered_from_the_matrix():
    expected = hm.render_markdown(_matrix())
    actual = (REPO_ROOT / hm.DOC_PATH).read_text(encoding="utf-8")
    assert actual == expected


def test_cli_renders_markdown(capsys):
    ret = ce_cli.main(["harness-matrix", "--repo-root", str(REPO_ROOT)])
    assert ret == 0
    out = capsys.readouterr().out
    assert "CE harness-support capability matrix" in out
    assert "| claude_code | Ring 0 | green | green | green | green | yes | none |" in out
    assert "| codex | Ring 1 | green | green | red | red | no | none |" in out
    assert "| ephemeral_controller_providers | design-stage | yellow * | red | red | red | no | none |" in out


def test_cli_renders_json(capsys):
    ret = ce_cli.main(["harness-matrix", "--repo-root", str(REPO_ROOT), "--json"])
    assert ret == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["kind"] == "harness-support-promotion-matrix"
    assert tuple(dict.fromkeys(row["provider"] for row in payload["rows"])) == hm.HARNESSES
