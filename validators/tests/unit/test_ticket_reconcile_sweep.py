from __future__ import annotations

import copy

import pytest

from creator_engine_validator import ticket_reconcile_sweep as sweep


def snapshot(*, tickets=None, pull_requests=None, complete=True) -> dict:
    return {
        "kind": "ticket-reconcile-snapshot",
        "schema_version": "1",
        "snapshot_digest": "a" * 64,
        "ticket_repository": "example/tickets",
        "pull_request_repository": "example/product",
        "observed_at": "2026-07-17T12:00:00Z",
        "pagination": {
            "complete": complete,
            "page_count": 1,
            "cursors": [None],
            "terminal_cursor": None,
        },
        "tickets": tickets
        if tickets is not None
        else [
            {
                "number": 518,
                "state": "open",
                "labels": ["triage:ready"],
                "kind": "standard",
                "updated_at": "2026-07-16T12:00:00Z",
            }
        ],
        "pull_requests": pull_requests
        if pull_requests is not None
        else [
            {
                "number": 900,
                "repository": "example/product",
                "merged_at": "2026-07-17T10:00:00Z",
                "merge_commit_sha": "b" * 40,
                "head_branch": "ce-518-reconcile-advisory-sweep",
                "title": "ordinary title",
                "body": "Closes example/tickets#518",
                "changed_changelog_fragments": [],
            }
        ],
    }


def packets(data: dict) -> list[dict]:
    return sweep.reduce_snapshot(data)


def test_explicit_closing_reference_emits_canonical_advisory_packet():
    packet = packets(snapshot())[0]

    assert packet == {
        "candidate_key": packet["candidate_key"],
        "completeness": {"complete": True, "page_count": 1},
        "disposition": "ADVISORY_PROPOSAL",
        "evidence_codes": ["branch", "explicit-closing-ref"],
        "kind": "ticket-reconcile-advisory",
        "merge_commit_sha": "b" * 40,
        "mode": "advisory",
        "observation_timestamp": "2026-07-17T12:00:00Z",
        "policy_version": "1",
        "proposed_action": "HUMAN_REVIEW_CLOSURE",
        "pull_request": {"number": 900, "repository": "example/product"},
        "repositories": {"ticket": "example/tickets", "pull_request": "example/product"},
        "schema_version": "1",
        "snapshot_digest": "a" * 64,
        "ticket": {"number": 518, "repository": "example/tickets"},
    }
    assert len(packet["candidate_key"]) == 64


def test_branch_and_strict_changelog_corroboration_is_probable_and_title_is_ignored():
    data = snapshot()
    pr = data["pull_requests"][0]
    pr["body"] = "No closing language."
    pr["title"] = "tickets#518 but title is not evidence"
    pr["changed_changelog_fragments"] = ["---\nissue: example/tickets#518\n---\ntext\n"]
    packet = packets(data)[0]
    assert packet["evidence_codes"] == ["branch", "changelog"]
    assert packet["disposition"] == "ADVISORY_PROPOSAL"


@pytest.mark.parametrize(
    ("body", "branch", "fragment"),
    [
        ("Closes example/tickets#5180", "topic/none", ""),
        ("Closes example/tickets#518 extra", "topic/none", ""),
        ("No closing language", "ce-5180-wrong", "---\nissue: example/tickets#518\n---\n"),
        ("No closing language", "ce-518-right", "---\nissue: example/tickets#5180\n---\n"),
    ],
)
def test_fuzzy_or_unbounded_signals_do_not_match(body: str, branch: str, fragment: str):
    data = snapshot()
    pr = data["pull_requests"][0]
    pr.update(body=body, head_branch=branch, changed_changelog_fragments=[fragment] if fragment else [])
    assert packets(data) == []


def test_directive_without_acceptance_evidence_needs_evidence_and_never_proposes():
    data = snapshot()
    data["tickets"][0]["kind"] = "directive"
    packet = packets(data)[0]
    assert packet["disposition"] == "NEEDS_ACCEPTANCE_EVIDENCE"
    assert packet["proposed_action"] == "NONE"
    data["pull_requests"][0]["body"] += "\nAcceptance-Evidence: tests pass"
    assert packets(data)[0]["disposition"] == "ADVISORY_PROPOSAL"


@pytest.mark.parametrize("reason", ["partial_slice", "multiple_prs", "ticket_updated", "missing_merge_sha"])
def test_human_recheck_cases_suppress_proposals(reason: str):
    data = snapshot()
    if reason == "partial_slice":
        data["tickets"][0]["partial_slice"] = True
    elif reason == "multiple_prs":
        other = copy.deepcopy(data["pull_requests"][0])
        other["number"] = 901
        other["merge_commit_sha"] = "c" * 40
        data["pull_requests"].append(other)
    elif reason == "ticket_updated":
        data["tickets"][0]["updated_at"] = "2026-07-17T11:00:00Z"
    else:
        data["pull_requests"][0]["merge_commit_sha"] = None
    packet = packets(data)[0]
    assert packet["disposition"] == "REQUIRES_HUMAN_RECHECK"
    assert packet["proposed_action"] == "NONE"


def test_incomplete_pagination_emits_only_incomplete_evidence():
    data = snapshot(complete=False)
    packet = packets(data)[0]
    assert packet["disposition"] == "REQUIRES_HUMAN_RECHECK"
    assert packet["evidence_codes"] == ["incomplete-pagination"]
    assert packet["proposed_action"] == "NONE"


def test_ordering_deduplication_and_keys_are_deterministic():
    data = snapshot()
    second = copy.deepcopy(data["tickets"][0])
    second["number"] = 473
    data["tickets"].append(second)
    data["pull_requests"][0]["body"] = "Closes example/tickets#518"
    other = copy.deepcopy(data["pull_requests"][0])
    other.update(number=901, merge_commit_sha="c" * 40, head_branch="ce-473-local", body="Closes example/tickets#473")
    data["pull_requests"].append(other)
    first = packets(data)
    second_run = packets(copy.deepcopy(data))
    assert first == second_run
    assert [packet["ticket"]["number"] for packet in first] == [473, 518]
    assert len({packet["candidate_key"] for packet in first}) == 2


@pytest.mark.parametrize(
    "mutate",
    [
        lambda data: data.update(extra=True),
        lambda data: data["tickets"].append(copy.deepcopy(data["tickets"][0])),
        lambda data: data["pull_requests"][0].update(title="bad\x00title"),
        lambda data: data["pull_requests"][0].update(repository="other/repo"),
        lambda data: data["pagination"].update(cursors=[None, "next"]),
        lambda data: data["tickets"][0].update(updated_at="2026-19-55T12:00:00Z"),
    ],
)
def test_schema_and_hostile_input_are_rejected(mutate):
    data = snapshot()
    mutate(data)
    with pytest.raises(sweep.SnapshotValidationError):
        packets(data)


@pytest.mark.parametrize("number", [473, 459, 500])
def test_historical_changelog_linked_classes_are_inert_local_data(number: int):
    data = snapshot()
    data["tickets"][0]["number"] = number
    data["pull_requests"][0]["body"] = "No closing language"
    data["pull_requests"][0]["head_branch"] = f"ce-{number}-local-fixture"
    data["pull_requests"][0]["changed_changelog_fragments"] = [
        f"---\nticket: example/tickets#{number}\n---\nfixture\n"
    ]
    assert packets(data)[0]["evidence_codes"] == ["branch", "changelog"]


def test_historical_453_part_b_is_partial_slice_suppression():
    data = snapshot()
    data["tickets"][0].update(number=453, partial_slice=True)
    data["pull_requests"][0]["body"] = "Closes example/tickets#453"
    assert packets(data)[0]["disposition"] == "REQUIRES_HUMAN_RECHECK"
