from __future__ import annotations

import json

from creator_engine_validator import ticket_reconcile as tr


def test_branch_slug_match_reports_stale_open_ticket():
    matches = tr.reconcile_stale_tickets(
        [{"number": 518, "title": "stale ticket reconcile"}],
        [{"number": 73, "title": "landed elsewhere", "head_branch": "dev/ce-518-reconcile-s1"}],
    )

    assert tr.render_report(matches) == "STALE-OPEN ce-ops#518 <- PR#73 (branch)"


def test_ticket_branch_slug_hint_matches_head_branch():
    matches = tr.reconcile_stale_tickets(
        [{"number": 700, "title": "custom slug", "branch_slug_hints": ["stale-ticket-sweep"]}],
        [{"number": 74, "title": "custom", "head_branch": "users/dev/stale-ticket-sweep"}],
    )

    assert tr.render_report(matches) == "STALE-OPEN ce-ops#700 <- PR#74 (branch)"


def test_body_ref_match_reports_ticket_ref_evidence():
    matches = tr.reconcile_stale_tickets(
        [{"number": 519, "title": "body ref"}],
        [
            {
                "number": 75,
                "title": "merged fix",
                "head_branch": "fix/no-ticket-slug",
                "body": "Implements creator-engine/ce-ops#519 without a close keyword.",
            }
        ],
    )

    assert tr.render_report(matches) == "STALE-OPEN ce-ops#519 <- PR#75 (ticket-ref)"


def test_no_match_stays_silent_and_ignores_fuzzy_title_overlap():
    matches = tr.reconcile_stale_tickets(
        [{"number": 520, "title": "stale ticket reconciliation module"}],
        [
            {
                "number": 76,
                "title": "stale ticket reconciliation module landed",
                "head_branch": "topic/reconciliation-module",
                "body": "No qualified ticket reference.",
            }
        ],
    )

    assert matches == []
    assert tr.render_report(matches) == ""


def test_dedups_when_branch_and_ticket_ref_both_match():
    matches = tr.reconcile_stale_tickets(
        [{"number": 521, "title": "dedup"}],
        [
            {
                "number": 77,
                "title": "ce-ops#521 report",
                "head_branch": "ce-521-dedup",
                "body": "Also references creator-engine/ce-ops#521.",
            }
        ],
    )

    assert len(matches) == 1
    assert tr.render_report(matches) == "STALE-OPEN ce-ops#521 <- PR#77 (branch+ticket-ref)"


def test_json_mode_is_machine_readable_and_deterministic():
    matches = tr.reconcile_stale_tickets(
        [{"number": 522, "title": "json"}],
        [{"number": 78, "title": "json", "head_branch": "ce-522-json", "body": ""}],
    )

    payload = json.loads(tr.render_json(matches))

    assert payload == {
        "matches": [
            {
                "evidence": ["branch"],
                "evidence_tag": "branch",
                "pr_number": 78,
                "report_line": "STALE-OPEN ce-ops#522 <- PR#78 (branch)",
                "ticket_number": 522,
            }
        ]
    }


def test_cli_reads_json_files_and_emits_json(tmp_path, capsys):
    tickets_path = tmp_path / "tickets.json"
    prs_path = tmp_path / "prs.json"
    tickets_path.write_text(json.dumps({"tickets": [{"number": 523, "title": "cli"}]}))
    prs_path.write_text(
        json.dumps(
            {
                "pull_requests": [
                    {"number": 79, "title": "cli", "headBranch": "ce-523-cli", "body": ""}
                ]
            }
        )
    )

    assert tr.main(["--json", str(tickets_path), str(prs_path)]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["matches"][0]["report_line"] == "STALE-OPEN ce-ops#523 <- PR#79 (branch)"
