"""Unit tests for the forge.board_sync adapter (Projects-v2 desired-state sync).

Mirrors the style of test_backlog.py: injectable GhRunner seam, zero live
network, focused per-behaviour tests.
"""
from __future__ import annotations

import json
import subprocess
import textwrap
from pathlib import Path

import pytest

from creator_engine_validator.forge.board_sync import (
    BoardItem,
    BoardSyncError,
    BoardSyncRef,
    DesiredItem,
    DriftReport,
    IssueCoord,
    SyncResult,
    compute_drift,
    load_desired_state,
    read_board_items,
    sync_board,
)

# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------

REF = BoardSyncRef(
    project_id="PVT_proj1",
    status_field_id="PVTSSF_field1",
    status_options={
        "In flight": "opt_inflight",
        "Done": "opt_done",
        "Planned": "opt_planned",
    },
)

_REPO = "creator-engine/ce-ops"


def _coord(number: int, repo: str = _REPO) -> IssueCoord:
    return IssueCoord(repo=repo, number=number)


def _desired(number: int, status: str = "In flight", repo: str = _REPO) -> DesiredItem:
    return DesiredItem(issue=_coord(number, repo), status=status)


def _board_item(
    number: int,
    status: str | None = "In flight",
    repo: str = _REPO,
    item_id: str | None = None,
) -> BoardItem:
    return BoardItem(
        item_id=item_id or f"PVTI_{number}",
        issue_repo=repo,
        issue_number=number,
        status=status,
        is_draft=False,
    )


def _items_page(items: list, has_next: bool = False, cursor: str | None = None) -> dict:
    """Build a GraphQL list-items response page."""
    return {
        "data": {
            "node": {
                "items": {
                    "pageInfo": {
                        "hasNextPage": has_next,
                        "endCursor": cursor,
                    },
                    "nodes": [
                        {
                            "id": it.item_id,
                            "status": (
                                {"name": it.status, "optionId": "opt_x"}
                                if it.status is not None else None
                            ),
                            "content": (
                                {
                                    "number": it.issue_number,
                                    "repository": {"nameWithOwner": it.issue_repo},
                                }
                                if not it.is_draft else {"title": "Draft"}
                            ),
                        }
                        for it in items
                    ],
                }
            }
        }
    }


def _empty_page() -> dict:
    return _items_page([])


# ---------------------------------------------------------------------------
# Mock GhRunner
# ---------------------------------------------------------------------------

class _Runner:
    """Injectable GhRunner that dispatches by call type, never hits the network."""

    def __init__(
        self,
        *,
        pages: list | None = None,
        issue_node_ids: dict | None = None,
        add_item_response: str = "PVTI_new_item",
    ):
        """
        pages: list of project-items GraphQL response dicts (consumed in order).
        issue_node_ids: mapping "owner/repo#N" -> "I_..." node id.
        add_item_response: item node id to return from addProjectV2ItemById.
        """
        self._pages = list(pages or [_empty_page()])
        self._issue_ids = issue_node_ids or {}
        self._add_item_response = add_item_response
        self.calls: list = []

    def __call__(self, argv, input_text=None):
        argv = list(argv)
        self.calls.append(argv)
        joined = " ".join(str(a) for a in argv)

        if "graphql" not in joined:
            # REST call — resolve issue node id
            node_id = self._resolve_node_id(argv)
            payload = {"node_id": node_id, "number": 0}
            return subprocess.CompletedProcess(argv, 0, stdout=json.dumps(payload), stderr="")

        if "addProjectV2ItemById" in joined:
            payload = {
                "data": {
                    "addProjectV2ItemById": {
                        "item": {"id": self._add_item_response}
                    }
                }
            }
            return subprocess.CompletedProcess(argv, 0, stdout=json.dumps(payload), stderr="")

        if "updateProjectV2ItemFieldValue" in joined:
            payload = {
                "data": {
                    "updateProjectV2ItemFieldValue": {
                        "projectV2Item": {"id": "PVTI_x"}
                    }
                }
            }
            return subprocess.CompletedProcess(argv, 0, stdout=json.dumps(payload), stderr="")

        # list-items query
        if self._pages:
            page = self._pages.pop(0)
        else:
            page = _empty_page()
        return subprocess.CompletedProcess(argv, 0, stdout=json.dumps(page), stderr="")

    def _resolve_node_id(self, argv: list) -> str:
        # Extract repo and number from "repos/{owner}/{repo}/issues/{number}"
        for part in argv:
            if "/issues/" in str(part) and not str(part).startswith("-"):
                segs = str(part).split("/")
                try:
                    owner = segs[1]
                    repo = segs[2]
                    number = int(segs[4])
                    key = f"{owner}/{repo}#{number}"
                    return self._issue_ids.get(key, f"I_mock_{number}")
                except (IndexError, ValueError):
                    pass
        return "I_mock_unknown"

    @property
    def write_calls(self) -> list:
        return [c for c in self.calls if "addProjectV2ItemById" in " ".join(c) or "updateProjectV2ItemFieldValue" in " ".join(c)]

    @property
    def add_calls(self) -> list:
        return [c for c in self.calls if "addProjectV2ItemById" in " ".join(c)]

    @property
    def update_calls(self) -> list:
        return [c for c in self.calls if "updateProjectV2ItemFieldValue" in " ".join(c)]

    @property
    def rest_calls(self) -> list:
        return [c for c in self.calls if "graphql" not in " ".join(c)]

    @property
    def read_calls(self) -> list:
        return [
            c for c in self.calls
            if "graphql" in " ".join(c)
            and "addProjectV2ItemById" not in " ".join(c)
            and "updateProjectV2ItemFieldValue" not in " ".join(c)
        ]


# ---------------------------------------------------------------------------
# IssueCoord.parse
# ---------------------------------------------------------------------------

def test_issue_coord_parse_valid():
    coord = IssueCoord.parse("creator-engine/creator-engine#617")
    assert coord.repo == "creator-engine/creator-engine"
    assert coord.number == 617


def test_issue_coord_parse_invalid_raises():
    with pytest.raises(ValueError, match="invalid issue ref"):
        IssueCoord.parse("no-hash-here")


# ---------------------------------------------------------------------------
# BoardSyncRef.option_id — fail-closed on unknown status
# ---------------------------------------------------------------------------

def test_option_id_known_returns_id():
    assert REF.option_id("In flight") == "opt_inflight"


def test_option_id_unknown_raises_board_sync_error():
    with pytest.raises(BoardSyncError, match="unknown status option"):
        REF.option_id("Nonexistent")


# ---------------------------------------------------------------------------
# read_board_items — parses GraphQL response
# ---------------------------------------------------------------------------

def test_read_board_items_parses_issue_items():
    item = _board_item(617, status="In flight")
    runner = _Runner(pages=[_items_page([item])])
    result = read_board_items(REF, gh_runner=runner)
    assert len(result) == 1
    assert result[0].issue_number == 617
    assert result[0].issue_repo == _REPO
    assert result[0].status == "In flight"
    assert not result[0].is_draft


def test_read_board_items_parses_draft_items():
    draft = BoardItem(item_id="PVTI_d1", issue_repo=None, issue_number=None, status="Planned", is_draft=True)
    runner = _Runner(pages=[
        {
            "data": {
                "node": {
                    "items": {
                        "pageInfo": {"hasNextPage": False, "endCursor": None},
                        "nodes": [
                            {
                                "id": "PVTI_d1",
                                "status": {"name": "Planned", "optionId": "opt_planned"},
                                "content": {"title": "A draft issue"},
                            }
                        ],
                    }
                }
            }
        }
    ])
    result = read_board_items(REF, gh_runner=runner)
    assert len(result) == 1
    assert result[0].is_draft
    assert result[0].issue_number is None


def test_read_board_items_handles_pagination():
    item1 = _board_item(616, "Done")
    item2 = _board_item(617, "In flight")
    page1 = _items_page([item1], has_next=True, cursor="cur_1")
    page2 = _items_page([item2], has_next=False)
    runner = _Runner(pages=[page1, page2])
    result = read_board_items(REF, gh_runner=runner)
    assert [b.issue_number for b in result] == [616, 617]
    assert len(runner.read_calls) == 2


def test_read_board_items_transport_failure_raises():
    def runner(argv, input_text=None):
        return subprocess.CompletedProcess(list(argv), 1, stdout="", stderr="network error")
    with pytest.raises(BoardSyncError):
        read_board_items(REF, gh_runner=runner)


# ---------------------------------------------------------------------------
# compute_drift — pure function
# ---------------------------------------------------------------------------

def test_compute_drift_no_drift_when_board_matches():
    item = _board_item(617, "In flight")
    d = _desired(617, "In flight")
    report = compute_drift(REF, [d], [item])
    assert not report.has_drift
    assert not report.fail_closed
    assert report.missing == ()
    assert report.stale_status == ()
    assert report.orphans == ()


def test_compute_drift_missing_when_item_not_on_board():
    d = _desired(617, "In flight")
    report = compute_drift(REF, [d], [])
    assert report.missing == (d,)
    assert report.stale_status == ()


def test_compute_drift_stale_status_when_status_differs():
    item = _board_item(617, status="Done")
    d = _desired(617, "In flight")
    report = compute_drift(REF, [d], [item])
    assert report.stale_status == ((d, item),)
    assert report.missing == ()


def test_compute_drift_orphan_when_item_not_in_desired():
    item = _board_item(999, "Done")
    report = compute_drift(REF, [], [item])
    assert report.orphans == (item,)
    assert report.missing == ()


def test_compute_drift_draft_items_are_not_orphans():
    draft = BoardItem(item_id="PVTI_d", issue_repo=None, issue_number=None, status=None, is_draft=True)
    report = compute_drift(REF, [], [draft])
    assert report.orphans == ()


def test_compute_drift_repo_name_comparison_is_case_insensitive():
    # Board item has uppercase repo; desired has lowercase
    item = BoardItem(item_id="PVTI_1", issue_repo="Creator-Engine/CE-Ops", issue_number=617, status="In flight")
    d = _desired(617, "In flight")  # repo = "creator-engine/ce-ops"
    report = compute_drift(REF, [d], [item])
    assert not report.has_drift


def test_compute_drift_unknown_status_option_collected():
    d = DesiredItem(issue=_coord(617), status="Nonexistent")
    report = compute_drift(REF, [d], [])
    assert "Nonexistent" in report.unknown_status_options
    assert report.fail_closed


def test_compute_drift_multiple_unknown_options_deduplicated():
    items = [
        DesiredItem(issue=_coord(i), status="Ghost")
        for i in range(3)
    ]
    report = compute_drift(REF, items, [])
    assert list(report.unknown_status_options) == ["Ghost"]


# ---------------------------------------------------------------------------
# sync_board — dry-run (plan mode)
# ---------------------------------------------------------------------------

def test_sync_dry_run_writes_nothing():
    runner = _Runner(pages=[_empty_page()])
    d = _desired(617)
    result = sync_board(REF, [d], apply=False, gh_runner=runner)
    assert not result.applied
    assert runner.write_calls == []
    assert d in result.drift.missing


def test_sync_dry_run_is_default():
    # Calling sync_board without apply= should default to plan mode
    runner = _Runner(pages=[_empty_page()])
    result = sync_board(REF, [_desired(617)], gh_runner=runner)
    assert not result.applied
    assert runner.write_calls == []


# ---------------------------------------------------------------------------
# sync_board — fail-closed on unknown status option
# ---------------------------------------------------------------------------

def test_sync_fail_closed_on_unknown_status_option():
    runner = _Runner(pages=[_empty_page()])
    d = DesiredItem(issue=_coord(617), status="UnknownStatus")
    result = sync_board(REF, [d], apply=True, gh_runner=runner)
    assert not result.applied
    assert runner.write_calls == []
    assert result.errors
    assert "unknown status option" in result.errors[0].lower() or "UnknownStatus" in result.errors[0]


# ---------------------------------------------------------------------------
# sync_board — execute mode
# ---------------------------------------------------------------------------

def test_sync_execute_adds_missing_item_and_sets_status():
    runner = _Runner(
        pages=[_empty_page()],
        issue_node_ids={f"{_REPO}#617": "I_617"},
        add_item_response="PVTI_new617",
    )
    d = _desired(617, "In flight")
    result = sync_board(REF, [d], apply=True, gh_runner=runner)
    assert result.applied
    assert d in result.added
    assert d in result.status_updated
    assert not result.errors
    # One REST call to resolve issue node id
    assert len(runner.rest_calls) == 1
    # One addProjectV2ItemById mutation
    assert len(runner.add_calls) == 1
    # One updateProjectV2ItemFieldValue mutation
    assert len(runner.update_calls) == 1


def test_sync_execute_updates_stale_status():
    # Item already on board but with wrong status
    item = _board_item(617, status="Done", item_id="PVTI_617")
    runner = _Runner(pages=[_items_page([item])])
    d = _desired(617, "In flight")
    result = sync_board(REF, [d], apply=True, gh_runner=runner)
    assert result.applied
    assert result.added == ()           # not added (already on board)
    assert d in result.status_updated
    assert not result.errors
    # Only one update call — no add, no REST
    assert runner.add_calls == []
    assert runner.rest_calls == []
    assert len(runner.update_calls) == 1
    # Verify option_id used in update call
    update_argv = " ".join(runner.update_calls[0])
    assert "opt_inflight" in update_argv


def test_sync_execute_multiple_items():
    # Two missing, one stale, one already correct
    stale = _board_item(616, status="Done", item_id="PVTI_616")
    correct = _board_item(100, status="In flight", item_id="PVTI_100")
    runner = _Runner(
        pages=[_items_page([stale, correct])],
        issue_node_ids={f"{_REPO}#617": "I_617", f"{_REPO}#618": "I_618"},
        add_item_response="PVTI_new",
    )
    desired = [
        _desired(616, "In flight"),   # stale
        _desired(617, "In flight"),   # missing
        _desired(618, "Done"),        # missing
        _desired(100, "In flight"),   # already correct
    ]
    result = sync_board(REF, desired, apply=True, gh_runner=runner)
    assert result.applied
    assert len(result.added) == 2        # 617 and 618
    assert len(runner.update_calls) == 3  # stale 616 + status for 617 + status for 618
    assert not result.errors


# ---------------------------------------------------------------------------
# Idempotency: second run produces no mutations
# ---------------------------------------------------------------------------

def test_sync_idempotent_second_run_produces_no_writes():
    # First run: board empty, execute mode
    item617 = _board_item(617, "In flight", item_id="PVTI_617")
    runner1 = _Runner(
        pages=[_empty_page()],
        issue_node_ids={f"{_REPO}#617": "I_617"},
        add_item_response="PVTI_617",
    )
    r1 = sync_board(REF, [_desired(617)], apply=True, gh_runner=runner1)
    assert r1.applied and r1.added

    # Second run: board now has the item in the correct state
    runner2 = _Runner(pages=[_items_page([item617])])
    r2 = sync_board(REF, [_desired(617)], apply=True, gh_runner=runner2)
    assert r2.applied
    assert r2.added == ()
    assert r2.status_updated == ()
    assert runner2.write_calls == []


# ---------------------------------------------------------------------------
# load_desired_state — YAML parser
# ---------------------------------------------------------------------------

def test_load_desired_state_valid_yaml(tmp_path):
    yaml_text = textwrap.dedent("""\
        project_id: "PVT_test"
        status_field_id: "PVTSSF_test"
        status_options:
          "In flight": "opt_inf"
          "Done": "opt_done"
        items:
          - issue: creator-engine/creator-engine#617
            status: "In flight"
            label: "optional label"
          - issue: creator-engine/creator-engine#618
            status: "Done"
    """)
    f = tmp_path / "board-state.yaml"
    f.write_text(yaml_text, encoding="utf-8")
    ref, items = load_desired_state(f)
    assert ref.project_id == "PVT_test"
    assert ref.status_field_id == "PVTSSF_test"
    assert ref.status_options == {"In flight": "opt_inf", "Done": "opt_done"}
    assert len(items) == 2
    assert items[0].issue.number == 617
    assert items[0].status == "In flight"
    assert items[1].issue.number == 618
    assert items[1].status == "Done"


def test_load_desired_state_missing_file_raises(tmp_path):
    with pytest.raises(BoardSyncError, match="could not read"):
        load_desired_state(tmp_path / "nonexistent.yaml")


def test_load_desired_state_missing_project_id_raises(tmp_path):
    f = tmp_path / "bad.yaml"
    f.write_text("status_field_id: x\nstatus_options:\n  Done: opt\nitems: []\n", encoding="utf-8")
    with pytest.raises(BoardSyncError, match="project_id"):
        load_desired_state(f)


def test_load_desired_state_missing_status_field_id_raises(tmp_path):
    f = tmp_path / "bad.yaml"
    f.write_text("project_id: x\nstatus_options:\n  Done: opt\nitems: []\n", encoding="utf-8")
    with pytest.raises(BoardSyncError, match="status_field_id"):
        load_desired_state(f)


def test_load_desired_state_empty_status_options_raises(tmp_path):
    f = tmp_path / "bad.yaml"
    f.write_text("project_id: x\nstatus_field_id: y\nstatus_options: {}\nitems: []\n", encoding="utf-8")
    with pytest.raises(BoardSyncError, match="status_options"):
        load_desired_state(f)


def test_load_desired_state_bad_issue_ref_raises(tmp_path):
    f = tmp_path / "bad.yaml"
    f.write_text(
        "project_id: x\nstatus_field_id: y\n"
        "status_options:\n  Done: opt\n"
        "items:\n  - issue: not-a-valid-ref\n    status: Done\n",
        encoding="utf-8",
    )
    with pytest.raises(BoardSyncError, match="issue"):
        load_desired_state(f)


def test_load_desired_state_missing_status_on_item_raises(tmp_path):
    f = tmp_path / "bad.yaml"
    f.write_text(
        "project_id: x\nstatus_field_id: y\n"
        "status_options:\n  Done: opt\n"
        "items:\n  - issue: creator-engine/creator-engine#617\n",
        encoding="utf-8",
    )
    with pytest.raises(BoardSyncError, match="status"):
        load_desired_state(f)


# ---------------------------------------------------------------------------
# Zero live network — subprocess.run must never be called
# ---------------------------------------------------------------------------

def test_zero_live_network(monkeypatch):
    def explode(*args, **kwargs):  # pragma: no cover — must never run
        raise AssertionError("board_sync must not touch a live forge in tests")

    monkeypatch.setattr(subprocess, "run", explode)
    monkeypatch.setattr(subprocess, "Popen", explode)

    runner = _Runner(pages=[_items_page([_board_item(617, "In flight")])])
    result = sync_board(REF, [_desired(617, "In flight")], apply=True, gh_runner=runner)
    assert result.applied
    assert result.added == ()
    assert result.status_updated == ()
