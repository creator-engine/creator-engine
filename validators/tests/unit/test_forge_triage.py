from __future__ import annotations

import json
import re
import subprocess

import pytest

from creator_engine_validator import ce_cli
from creator_engine_validator import forge_triage as ft
from creator_engine_validator import work_claims as wc


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


def _claim_body(number: int) -> str:
    work_key = f"creator-engine/ce-ops:issue:{number}"
    return wc.render_marker(
        {
            "kind": "ce-work-claim",
            "schema_version": 1,
            "action": "acquire",
            "work_key": work_key,
            "claim_id": f"wclaim-{number}",
            "holder": "other-seat",
            "host": "other-host",
            "claimed_at": "2026-06-22T00:00:00Z",
            "stale_after_seconds": 999999999,
            "idempotency_key": f"id-{number}",
        }
    )


class FakeGh:
    def __init__(
        self,
        comments_by_number: dict[int, list[dict]] | None = None,
        timeline_by_number: dict[int, object] | None = None,
        timeline_pages_by_number: dict[int, dict[int, object]] | None = None,
        timeline_stdout_by_number: dict[int, str] | None = None,
        timeline_stdout_by_page: dict[tuple[int, int], str] | None = None,
        timeline_failures: set[int | tuple[int, int]] | None = None,
    ):
        self.comments_by_number = comments_by_number or {}
        self.timeline_by_number = timeline_by_number or {}
        self.timeline_pages_by_number = timeline_pages_by_number or {}
        self.timeline_stdout_by_number = timeline_stdout_by_number or {}
        self.timeline_stdout_by_page = timeline_stdout_by_page or {}
        self.timeline_failures = timeline_failures or set()
        self.calls: list[tuple[list[str], str | None]] = []

    def __call__(self, argv, input_text=None):
        self.calls.append((list(argv), input_text))
        path = argv[-1]
        match = re.search(r"/issues/(\d+)/timeline", path)
        if match:
            number = int(match.group(1))
            page_match = re.search(r"(?:\?|&)page=(\d+)", path)
            page = int(page_match.group(1)) if page_match else 1
            if (
                number in self.timeline_failures
                or (number, page) in self.timeline_failures
            ):
                return subprocess.CompletedProcess(
                    argv,
                    1,
                    stdout="",
                    stderr="timeline unavailable",
                )
            if (number, page) in self.timeline_stdout_by_page:
                return subprocess.CompletedProcess(
                    argv,
                    0,
                    stdout=self.timeline_stdout_by_page[(number, page)],
                    stderr="",
                )
            if number in self.timeline_stdout_by_number:
                return subprocess.CompletedProcess(
                    argv,
                    0,
                    stdout=self.timeline_stdout_by_number[number],
                    stderr="",
                )
            if number in self.timeline_pages_by_number:
                payload = self.timeline_pages_by_number[number].get(page, [])
            elif page == 1:
                payload = self.timeline_by_number.get(number, [])
            else:
                payload = []
            return subprocess.CompletedProcess(
                argv,
                0,
                stdout=json.dumps(payload),
                stderr="",
            )
        match = re.search(r"/issues/(\d+)/comments", path)
        if match:
            number = int(match.group(1))
            return subprocess.CompletedProcess(
                argv,
                0,
                stdout=json.dumps(self.comments_by_number.get(number, [])),
                stderr="",
            )
        return subprocess.CompletedProcess(argv, 0, stdout="{}", stderr="")


def test_plan_triage_is_deterministically_ordered_and_stable():
    payload = {"items": [_issue(5), _issue(2), _issue(5)]}

    first = ft.plan_triage(arc_ticket="creator-engine/ce-ops#187", issues=payload)
    second = ft.plan_triage(arc_ticket="creator-engine/ce-ops#187", issues=payload)

    assert first.to_dict() == second.to_dict()
    assert [item.issue.number for item in first.items] == [2, 5]
    assert all(item.pickup_query_hint == "--label ce-pickup/triage-ready" for item in first.items)
    assert first.to_dict()["count"] == 2


def test_plan_triage_limits_candidates_to_arc_body_issue_refs():
    payload = {
        "items": [
            _issue(187, title="Arc", body="Stock the bounded slice with #10 and #20."),
            _issue(10),
            _issue(20),
            _issue(30),
        ]
    }

    result = ft.plan_triage(arc_ticket="creator-engine/ce-ops#187", issues=payload)

    assert [item.issue.number for item in result.items] == [10, 20]
    assert 30 not in {item.issue.number for item in result.items}


def test_plan_triage_invalid_arc_ticket_fails_closed_before_planning():
    payload = {"items": [_issue(1), _issue(2)]}

    with pytest.raises(ft.ForgeTriageError, match="arc ticket is invalid or ambiguous"):
        ft.plan_triage(arc_ticket="ce-ops#187", issues=payload)


def test_cli_apply_invalid_arc_ticket_refuses_before_mutation(tmp_path, monkeypatch, capsys):
    issues = tmp_path / "issues.json"
    issues.write_text(json.dumps({"items": [_issue(1), _issue(2)]}), encoding="utf-8")
    fake = FakeGh()
    monkeypatch.setattr(ce_cli, "_make_gh_runner", lambda: fake)

    rc = ce_cli.main(
        [
            "pickup",
            "triage",
            "--arc-ticket",
            "ce-ops#187",
            "--issues-json",
            str(issues),
            "--apply",
            "--json",
        ]
    )

    assert rc == 2
    payload = json.loads(capsys.readouterr().out)
    assert "arc ticket is invalid or ambiguous" in payload["error"]
    assert fake.calls == []


def test_plan_triage_explicit_arc_refs_exclude_unreferenced_cross_repo_candidates():
    payload = {
        "items": [
            _issue(187, title="Arc", body="Do #10 only."),
            _issue(10),
            _issue(99, repo="other/repo"),
        ]
    }

    result = ft.plan_triage(arc_ticket="creator-engine/ce-ops#187", issues=payload)

    assert [item.issue.work_key.work_key for item in result.items] == [
        "creator-engine/ce-ops:issue:10"
    ]


@pytest.mark.parametrize(
    "body",
    [
        "Blocked by: #12",
        "Depends on: #12",
        "blocked by creator-engine/ce-ops#12",
        "blocked by https://github.com/creator-engine/ce-ops/issues/12",
    ],
)
def test_readiness_blockers_detect_dependency_syntax_variants(body):
    candidate = ft.normalize_issue(_issue(1, body=body))

    assert candidate is not None
    assert ft.readiness_blockers(candidate) == ("blocked_dependency",)


def test_blocked_and_dependency_gates_do_not_surface_items():
    payload = {
        "items": [
            _issue(1, labels=[{"name": "blocked"}]),
            _issue(2, blocked_by=[1]),
            _issue(3),
        ]
    }

    result = ft.plan_triage(arc_ticket="creator-engine/ce-ops#187", issues=payload)

    assert [item.issue.number for item in result.items] == [3]
    skipped = {item["number"]: item["reason"] for item in result.skipped}
    assert skipped == {1: "blocked_label", 2: "blocked_dependency"}


def test_not_open_and_done_label_issues_are_skipped():
    payload = {
        "items": [
            _issue(1, state="closed"),
            _issue(2, labels=[{"name": "status:done"}]),
            _issue(3),
        ]
    }

    result = ft.plan_triage(arc_ticket="creator-engine/ce-ops#187", issues=payload)

    assert [item.issue.number for item in result.items] == [3]
    assert {item["number"]: item["reason"] for item in result.skipped} == {
        1: "not_open",
        2: "closed_or_done",
    }


def test_held_label_issue_is_skipped():
    result = ft.plan_triage(
        arc_ticket="creator-engine/ce-ops#187",
        issues={"items": [_issue(1, labels=[{"name": "held"}]), _issue(2)]},
    )

    assert [item.issue.number for item in result.items] == [2]
    assert result.skipped[0]["reason"] == "blocked_label"


def test_arc_held_checkpoint_list_issue_is_skipped():
    payload = {
        "items": [
            _issue(
                187,
                title="Arc",
                body="Stock #1 and #2.\n\nHeld checkpoints:\n- #1\n\n## Ready\n- #2",
            ),
            _issue(1),
            _issue(2),
        ]
    }

    result = ft.plan_triage(arc_ticket="creator-engine/ce-ops#187", issues=payload)

    assert [item.issue.number for item in result.items] == [2]
    assert result.skipped[0]["reason"] == "held_checkpoint"


def test_meta_issue_is_skipped_as_non_leaf_work():
    result = ft.plan_triage(
        arc_ticket="creator-engine/ce-ops#187",
        issues={"items": [_issue(1, labels=[{"name": "type/meta"}]), _issue(2)]},
    )

    assert [item.issue.number for item in result.items] == [2]
    assert result.skipped[0]["reason"] == "aggregate_issue"


def test_raw_kind_arc_is_skipped_as_non_leaf_work():
    result = ft.plan_triage(
        arc_ticket="creator-engine/ce-ops#187",
        issues={"items": [_issue(1, kind="arc"), _issue(2)]},
    )

    assert [item.issue.number for item in result.items] == [2]
    assert result.skipped[0]["reason"] == "aggregate_issue"


def test_already_assigned_issue_is_skipped():
    result = ft.plan_triage(
        arc_ticket="creator-engine/ce-ops#187",
        issues={"items": [_issue(1, assignees=[{"login": "ce-dev-2"}]), _issue(2)]},
    )

    assert [item.issue.number for item in result.items] == [2]
    assert result.skipped[0]["reason"] == "already_assigned"


def test_active_work_claim_is_skipped_when_gh_runner_is_supplied():
    comments = {
        1: [
            {
                "id": 1,
                "body": _claim_body(1),
                "created_at": "2026-06-22T00:00:00Z",
                "user": {"login": "bot"},
            }
        ]
    }
    result = ft.plan_triage(
        arc_ticket="creator-engine/ce-ops#187",
        issues={"items": [_issue(1), _issue(2)]},
        gh_runner=FakeGh(comments),
    )

    assert [item.issue.number for item in result.items] == [2]
    assert result.skipped[0]["reason"] == "active_claim"


def test_open_pr_reference_is_skipped_when_gh_runner_is_supplied():
    timeline = {
        1: [
            {
                "event": "cross-referenced",
                "source": {
                    "issue": {
                        "number": 99,
                        "state": "open",
                        "pull_request": {
                            "url": "https://api.github.com/repos/creator-engine/ce-ops/pulls/99"
                        },
                    }
                },
            }
        ]
    }

    result = ft.plan_triage(
        arc_ticket="creator-engine/ce-ops#187",
        issues={"items": [_issue(1), _issue(2)]},
        gh_runner=FakeGh(timeline_by_number=timeline),
    )

    assert [item.issue.number for item in result.items] == [2]
    assert result.skipped[0]["reason"] == "open_pr"


def test_open_pr_reference_paginates_until_later_open_pr():
    first_page = [
        {"event": "commented", "body": f"note {index}"} for index in range(100)
    ]
    second_page = [
        {
            "event": "cross-referenced",
            "source": {
                "issue": {
                    "number": 99,
                    "state": "open",
                    "pull_request": {
                        "url": "https://api.github.com/repos/creator-engine/ce-ops/pulls/99"
                    },
                }
            },
        }
    ]
    fake = FakeGh(timeline_pages_by_number={1: {1: first_page, 2: second_page}})

    result = ft.plan_triage(
        arc_ticket="creator-engine/ce-ops#187",
        issues={"items": [_issue(1), _issue(2)]},
        gh_runner=fake,
    )

    assert [item.issue.number for item in result.items] == [2]
    assert result.skipped[0]["reason"] == "open_pr"
    assert any(
        "/issues/1/timeline?per_page=100&page=2" in call[0][-1]
        for call in fake.calls
    )


def test_open_pr_lookup_failure_fails_closed():
    fake = FakeGh(timeline_failures={1})
    result = ft.plan_triage(
        arc_ticket="creator-engine/ce-ops#187",
        issues={"items": [_issue(1), _issue(2)]},
        gh_runner=fake,
    )

    assert [item.issue.number for item in result.items] == [2]
    assert result.skipped[0]["reason"] == "open_pr_status_unavailable"
    assert not any("/issues/1/comments" in call[0][-1] for call in fake.calls)


def test_open_pr_lookup_full_page_then_next_page_failure_fails_closed():
    first_page = [
        {"event": "commented", "body": f"note {index}"} for index in range(100)
    ]
    fake = FakeGh(
        timeline_pages_by_number={1: {1: first_page}},
        timeline_failures={(1, 2)},
    )

    result = ft.plan_triage(
        arc_ticket="creator-engine/ce-ops#187",
        issues={"items": [_issue(1), _issue(2)]},
        gh_runner=fake,
    )

    assert [item.issue.number for item in result.items] == [2]
    assert result.skipped[0]["reason"] == "open_pr_status_unavailable"
    assert any(
        "/issues/1/timeline?per_page=100&page=2" in call[0][-1]
        for call in fake.calls
    )
    assert not any("/issues/1/comments" in call[0][-1] for call in fake.calls)


def test_open_pr_lookup_malformed_response_fails_closed():
    fake = FakeGh(timeline_stdout_by_number={1: "{not-json"})
    result = ft.plan_triage(
        arc_ticket="creator-engine/ce-ops#187",
        issues={"items": [_issue(1), _issue(2)]},
        gh_runner=fake,
    )

    assert [item.issue.number for item in result.items] == [2]
    assert result.skipped[0]["reason"] == "open_pr_status_unavailable"
    assert not any("/issues/1/comments" in call[0][-1] for call in fake.calls)


def test_items_carry_declared_work_and_mutation_sizing():
    result = ft.plan_triage(
        arc_ticket="creator-engine/ce-ops#187",
        issues={
            "items": [
                _issue(
                    9,
                    labels=[{"name": "size/tiny"}, {"name": "mutation:docs"}],
                )
            ]
        },
    )

    item = result.items[0].to_dict()
    assert item["work_class"] == "tiny"
    assert item["mutation_class"] == "docs"
    assert item["sizing"]["kind"] == "sizing-record"
    assert item["sizing"]["intent_ref"] == "creator-engine/ce-ops:issue:9"
    assert item["sizing"]["artifact_set"] == ["scope_card"]
    assert item["sizing"]["ratification_gates"] == ["auto_back_gate"]


def test_cli_dry_run_outputs_json_without_gh_runner(tmp_path, monkeypatch, capsys):
    issues = tmp_path / "issues.json"
    issues.write_text(json.dumps({"items": [_issue(10)]}), encoding="utf-8")

    def _boom():
        raise AssertionError("dry-run triage must not create a gh runner")

    monkeypatch.setattr(ce_cli, "_make_gh_runner", _boom)
    rc = ce_cli.main(
        [
            "pickup",
            "triage",
            "--arc-ticket",
            "creator-engine/ce-ops#187",
            "--issues-json",
            str(issues),
            "--json",
        ]
    )

    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["count"] == 1
    assert payload["pickup_label"] == "ce-pickup/triage-ready"
    assert payload["pickup_query_hint"] == "--label ce-pickup/triage-ready"
    assert payload["items"][0]["planned_mutations"] == [
        {"kind": "add_label", "status": "planned", "value": "ce-pickup/triage-ready"}
    ]


def test_cli_check_claims_dry_run_uses_runner_and_skips_active_claim(
    tmp_path, monkeypatch, capsys
):
    issues = tmp_path / "issues.json"
    issues.write_text(json.dumps({"items": [_issue(1), _issue(2)]}), encoding="utf-8")
    fake = FakeGh(
        {
            1: [
                {
                    "id": 1,
                    "body": _claim_body(1),
                    "created_at": "2026-06-22T00:00:00Z",
                    "user": {"login": "bot"},
                }
            ]
        }
    )

    monkeypatch.setattr(ce_cli, "_make_gh_runner", lambda: fake)
    rc = ce_cli.main(
        [
            "pickup",
            "triage",
            "--arc-ticket",
            "creator-engine/ce-ops#187",
            "--issues-json",
            str(issues),
            "--check-claims",
            "--json",
        ]
    )

    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["applied"] is False
    assert payload["count"] == 1
    assert payload["items"][0]["issue"]["number"] == 2
    assert payload["skipped"] == [
        {
            "repo": "creator-engine/ce-ops",
            "number": 1,
            "work_key": "creator-engine/ce-ops:issue:1",
            "reason": "active_claim",
        }
    ]
    assert any("/issues/1/comments" in call[0][-1] for call in fake.calls)
