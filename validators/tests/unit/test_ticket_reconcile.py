from __future__ import annotations

import json

from creator_engine_validator import ticket_reconcile as tr

_EXAMPLE_REPO = "example/example-ops"


def test_branch_slug_match_reports_stale_open_ticket():
    matches = tr.reconcile_stale_tickets(
        [{"number": 518, "title": "stale ticket reconcile"}],
        [{"number": 73, "title": "landed elsewhere", "head_branch": "dev/ce-518-reconcile-s1"}],
        ticket_repo=_EXAMPLE_REPO,
    )

    assert tr.render_report(matches) == "STALE-OPEN example-ops#518 <- PR#73 (branch)"


def test_ticket_branch_slug_hint_matches_head_branch():
    matches = tr.reconcile_stale_tickets(
        [{"number": 700, "title": "custom slug", "branch_slug_hints": ["stale-ticket-sweep"]}],
        [{"number": 74, "title": "custom", "head_branch": "users/dev/stale-ticket-sweep"}],
        ticket_repo=_EXAMPLE_REPO,
    )

    assert tr.render_report(matches) == "STALE-OPEN example-ops#700 <- PR#74 (branch)"


def test_body_ref_match_reports_ticket_ref_evidence():
    matches = tr.reconcile_stale_tickets(
        [{"number": 519, "title": "body ref"}],
        [
            {
                "number": 75,
                "title": "merged fix",
                "head_branch": "fix/no-ticket-slug",
                "body": "Implements example/example-ops#519 without a close keyword.",
            }
        ],
        ticket_repo=_EXAMPLE_REPO,
    )

    assert tr.render_report(matches) == "STALE-OPEN example-ops#519 <- PR#75 (ticket-ref)"


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
        ticket_repo=_EXAMPLE_REPO,
    )

    assert matches == []
    assert tr.render_report(matches) == ""


def test_dedups_when_branch_and_ticket_ref_both_match():
    matches = tr.reconcile_stale_tickets(
        [{"number": 521, "title": "dedup"}],
        [
            {
                "number": 77,
                "title": "example-ops#521 report",
                "head_branch": "ce-521-dedup",
                "body": "Also references example/example-ops#521.",
            }
        ],
        ticket_repo=_EXAMPLE_REPO,
    )

    assert len(matches) == 1
    assert tr.render_report(matches) == "STALE-OPEN example-ops#521 <- PR#77 (branch+ticket-ref)"


def test_json_mode_is_machine_readable_and_deterministic():
    matches = tr.reconcile_stale_tickets(
        [{"number": 522, "title": "json"}],
        [{"number": 78, "title": "json", "head_branch": "ce-522-json", "body": ""}],
        ticket_repo=_EXAMPLE_REPO,
    )

    payload = json.loads(tr.render_json(matches))

    assert payload == {
        "matches": [
            {
                "evidence": ["branch"],
                "evidence_tag": "branch",
                "pr_number": 78,
                "report_line": "STALE-OPEN example-ops#522 <- PR#78 (branch)",
                "ticket_number": 522,
            }
        ]
    }


def test_branch_slug_boundary_ticket_51_does_not_match_ce_518_branch():
    """Trailing-hyphen anchor (ticket_reconcile.py:260): ticket 51 must not produce a
    STALE-OPEN match against a PR whose head branch is ce-518-foo."""
    matches = tr.reconcile_stale_tickets(
        [{"number": 51, "title": "boundary safety"}],
        [{"number": 80, "title": "unrelated", "head_branch": "ce-518-foo"}],
        ticket_repo=_EXAMPLE_REPO,
    )

    assert matches == []


def test_ref_lookahead_ticket_518_does_not_match_reference_to_5180():
    """(?!\\d) lookahead (ticket_reconcile.py:272-273): reconciling ticket 518 must not
    match a PR whose body contains the qualified reference example-ops#5180."""
    matches = tr.reconcile_stale_tickets(
        [{"number": 518, "title": "lookahead check"}],
        [
            {
                "number": 81,
                "title": "unrelated",
                "head_branch": "fix/no-slug",
                "body": "Implements example/example-ops#5180 as a separate concern.",
            }
        ],
        ticket_repo=_EXAMPLE_REPO,
    )

    assert matches == []


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

    assert tr.main(["--json", "--ticket-repo", _EXAMPLE_REPO, str(tickets_path), str(prs_path)]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["matches"][0]["report_line"] == "STALE-OPEN example-ops#523 <- PR#79 (branch)"


def _canonical_refs(title: str, body: str) -> list[int]:
    refs: list[int] = []
    if "ce-518" in title.lower():
        refs.append(518)
    if "closes example-ops#519" in body.lower():
        refs.append(519)
    return refs


def test_fixed_projection_suppresses_branch_when_title_parser_sees_ce_number():
    matches = tr.reconcile_stale_tickets(
        [{"number": 518}],
        [{"number": 90, "title": "feat: ce-518 landed", "head_branch": "ce-518-fix"}],
        ticket_repo=_EXAMPLE_REPO,
        reference_numbers=_canonical_refs,
    )

    assert matches == []


def test_fixed_projection_suppresses_branch_when_closing_body_parser_sees_ticket():
    matches = tr.reconcile_stale_tickets(
        [{"number": 519}],
        [
            {
                "number": 91,
                "title": "land fix",
                "head_branch": "users/dev/ce-519-fix",
                "body": "Closes example-ops#519",
            }
        ],
        ticket_repo=_EXAMPLE_REPO,
        reference_numbers=_canonical_refs,
    )

    assert matches == []


def test_fixed_projection_retains_branch_for_bare_body_mention():
    matches = tr.reconcile_stale_tickets(
        [{"number": 519}],
        [
            {
                "number": 92,
                "title": "land fix",
                "head_branch": "refs/heads/ce-519-fix",
                "body": "Context only: example-ops#519",
            }
        ],
        ticket_repo=_EXAMPLE_REPO,
        reference_numbers=_canonical_refs,
    )

    assert tr.render_report(matches) == "STALE-OPEN example-ops#519 <- PR#92 (branch)"


def test_fixed_projection_requires_literal_branch_marker_and_sorts_pairs():
    matches = tr.reconcile_stale_tickets(
        [
            {"number": 52, "branch_slug_hints": ["custom-hint"]},
            {"number": 51},
        ],
        [
            {"number": 102, "head_branch": "ce-52-fix"},
            {"number": 101, "head_branch": "origin/ce-51-fix"},
            {"number": 100, "head_branch": "ce-518-wrong-boundary"},
            {"number": 99, "head_branch": "users/custom-hint"},
        ],
        ticket_repo=_EXAMPLE_REPO,
        reference_numbers=lambda _title, _body: [],
    )

    assert [(match.ticket_number, match.pr_number) for match in matches] == [(51, 101), (52, 102)]


def test_reference_callback_is_evaluated_once_per_pr():
    calls: list[tuple[str, str]] = []

    def parser(title: str, body: str) -> list[int]:
        calls.append((title, body))
        return []

    tr.reconcile_stale_tickets(
        [{"number": 51}, {"number": 52}],
        [{"number": 100, "title": "one", "body": "body", "head_branch": "ce-51-fix"}],
        reference_numbers=parser,
    )

    assert calls == [("one", "body")]
