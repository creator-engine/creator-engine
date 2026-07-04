from __future__ import annotations

import io
import json

from creator_engine_validator import ce_cli
from creator_engine_validator import dispatch_plan as dp


def _issue(
    number: int,
    *,
    repo: str = "creator-engine/ce-ops",
    labels: list[str | dict] | None = None,
    assignees: list[str | dict] | None = None,
    title: str | None = None,
    **extra,
) -> dict:
    raw = {
        "number": number,
        "title": title or f"issue {number}",
        "state": "open",
        "html_url": f"https://github.com/{repo}/issues/{number}",
        "repository_url": f"https://api.github.com/repos/{repo}",
        "labels": labels or [],
        "assignees": assignees or [],
    }
    raw.update(extra)
    return raw


def test_plan_dispatch_round_robins_seat_assignment():
    payload = {"items": [_issue(1), _issue(2), _issue(3)]}

    result = dp.plan_dispatch(
        arc_ticket="creator-engine/ce-ops#187",
        issues=payload,
        assign_to=("dev-1", "dev-2"),
    )

    assert [item.issue.number for item in result.items] == [1, 2, 3]
    assert [item.seat for item in result.items] == ["dev-1", "dev-2", "dev-1"]


def test_skip_reasons_propagate_from_plan_triage():
    payload = {
        "items": [
            _issue(1, labels=[{"name": "blocked"}]),
            _issue(2, assignees=[{"login": "dev-9"}]),
            _issue(3, labels=[{"name": "aggregate"}]),
            _issue(4, body="Awaiting operator confirmation."),
            _issue(5),
        ]
    }

    result = dp.plan_dispatch(arc_ticket="creator-engine/ce-ops#187", issues=payload)

    assert [item.issue.number for item in result.items] == [5]
    skipped = {item["number"]: item["reason"] for item in result.skipped}
    assert skipped == {
        1: "blocked_label",
        2: "already_assigned",
        3: "aggregate_issue",
        4: "held_marker",
    }


def test_suggested_branch_is_path_safe():
    payload = {
        "items": [
            _issue(42, title="Fix: dry-run dispatch / seat planner!? now"),
        ]
    }

    result = dp.plan_dispatch(arc_ticket="creator-engine/ce-ops#187", issues=payload)

    assert result.items[0].suggested_branch == "creator-engine-42-fix-dry-run-dispatch-seat-planner"
    assert " " not in result.items[0].suggested_branch
    assert "/" not in result.items[0].suggested_branch
    assert ":" not in result.items[0].suggested_branch


def test_plan_dispatch_is_deterministic():
    payload = {"items": [_issue(3), _issue(1), _issue(2)]}

    first = dp.plan_dispatch(
        arc_ticket="creator-engine/ce-ops#187",
        issues=payload,
        assign_to=("dev-1", "dev-2"),
    )
    second = dp.plan_dispatch(
        arc_ticket="creator-engine/ce-ops#187",
        issues=payload,
        assign_to=("dev-1", "dev-2"),
    )

    assert first.to_dict() == second.to_dict()


def test_cli_json_output_shape(tmp_path, capsys):
    issues = tmp_path / "issues.json"
    issues.write_text(json.dumps({"items": [_issue(1), _issue(2)]}), encoding="utf-8")

    rc = ce_cli.main(
        [
            "pickup",
            "dispatch-plan",
            "--arc-ticket",
            "creator-engine/ce-ops#187",
            "--issues-json",
            str(issues),
            "--json",
        ]
    )

    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["kind"] == "dispatch-plan"
    assert payload["count"] == len(payload["items"]) == 2
    assert payload["skipped_count"] == len(payload["skipped"]) == 0


def test_cli_human_output_prints_one_line_per_item_with_seat_and_work_class(tmp_path, capsys):
    issues = tmp_path / "issues.json"
    issues.write_text(json.dumps({"items": [_issue(1), _issue(2)]}), encoding="utf-8")

    rc = ce_cli.main(
        [
            "pickup",
            "dispatch-plan",
            "--arc-ticket",
            "creator-engine/ce-ops#187",
            "--issues-json",
            str(issues),
            "--seat",
            "dev-1",
        ]
    )

    assert rc == 0
    lines = capsys.readouterr().out.splitlines()
    item_lines = [line for line in lines if line.strip().startswith("- ")]
    assert len(item_lines) == 2
    assert all("-> dev-1" in line for line in item_lines)
    assert all("(S/code)" in line for line in item_lines)


def test_cli_json_flag_accepts_stdin_and_outputs_valid_json(monkeypatch, capsys):
    monkeypatch.setattr("sys.stdin", io.StringIO(json.dumps({"items": [_issue(1)]})))

    rc = ce_cli.main(
        [
            "pickup",
            "dispatch-plan",
            "--arc-ticket",
            "creator-engine/ce-ops#187",
            "--json",
        ]
    )

    assert rc == 0
    assert json.loads(capsys.readouterr().out)["kind"] == "dispatch-plan"


def test_empty_issue_list_returns_empty_plan():
    result = dp.plan_dispatch(arc_ticket="creator-engine/ce-ops#187", issues=[])

    assert result.items == ()
    assert result.skipped == ()
    assert result.to_dict()["count"] == 0
    assert result.to_dict()["skipped_count"] == 0
