from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from creator_engine_validator import brain_runtime
from creator_engine_validator.brain_intent_materializer import MEDIATION_ORDER, RecordBuilder


class Capture:
    text = ""

    def __call__(self, _path: Path, text: str) -> None:
        self.text = text


def _base_records() -> list[dict[str, Any]]:
    sink = Capture()
    brain_runtime.assert_claim(
        claim={"subject": "brain", "predicate": "intent", "object": "base"},
        scope="creator-engine",
        evidence_ref="docs/design/ce-491-optiona-merge-intent.md",
        assertion_id="brain-assertion-intent-base",
        records=[],
        state_root=Path(".ce/state"),
        write=sink,
    )
    return brain_runtime.load_ledger_text(sink.text)


def _active() -> dict:
    return {
        "kind": "brain-append-intent",
        "schema_version": "1",
        "intent_kind": "active_assertion_append",
        "active_assertion": {
            "assertion_id": "brain-assertion-intent-active",
            "claim": {"subject": "brain", "predicate": "intent", "object": "active"},
            "scope": "creator-engine",
            "evidence_ref": "docs/design/ce-491-optiona-merge-intent.md",
        },
    }


def _supersede() -> dict:
    return {
        "kind": "brain-append-intent",
        "schema_version": "1",
        "intent_kind": "ce411_supersede_pair",
        "supersede_pair": {
            "assertion_id": "brain-assertion-intent-base",
            "replacement": {
                "new_assertion_id": "brain-assertion-intent-next",
                "claim": {"subject": "brain", "predicate": "intent", "object": "next"},
                "scope": "creator-engine",
                "evidence_ref": "docs/design/ce-491-optiona-merge-intent.md",
            },
        },
    }


def _decision() -> dict:
    return {
        "kind": "brain-append-intent",
        "schema_version": "1",
        "intent_kind": "decision_append",
        "decision": {
            "decision_id": "brain-decision-intent-0001",
            "date": "2026-07-08",
            "scope": "creator-engine",
            "statement": "Materialize append intents after merge.",
            "authority": "docs/design/ce-491-optiona-merge-intent.md",
            "supersedes_ref": None,
        },
    }


def _lesson() -> dict:
    return {
        "kind": "brain-append-intent",
        "schema_version": "1",
        "intent_kind": "lesson_append",
        "lesson": {
            "lesson_id": "brain-lesson-intent-0001",
            "date": "2026-07-08",
            "scope": "creator-engine",
            "source": "ce-491",
            "feedback": "Direct ledger edits create stale-tail pressure.",
            "correction": "Carry data-only intents and materialize from the live tail.",
            "why": "The materializer owns prev_hash and content_hash.",
            "how_to_apply": "Keep intent YAML free of host and position fields.",
            "supersedes_ref": None,
        },
    }


def _build(intent: dict):
    records = _base_records()
    return RecordBuilder().build(
        intent_data=intent,
        live_records=records,
        live_tail_content_hash=records[-1]["content_hash"],
        repo_root=Path("."),
        merge_commit_sha="a" * 40,
        pr_number=491,
        branch_slug="ce-491-optiona-slice1",
        intent_path=".ce/brain/append-intents/ce-491-optiona-slice1.yaml",
        intent_sha256="b" * 64,
        materialization_key="c" * 64,
    )


@pytest.mark.parametrize("intent", [_active(), _supersede(), _decision(), _lesson()])
def test_record_builder_is_byte_deterministic_for_all_intent_kinds(intent: dict):
    first = _build(intent)
    second = _build(intent)

    assert first.ledger_text == second.ledger_text
    assert first.appended_records == second.appended_records
    assert first.generated_patch_sha256 == second.generated_patch_sha256


def test_mediation_block_has_required_fields_in_design_order():
    result = _build(_active())
    mediation = result.appended_records[0]["mediation"]

    assert list(mediation) == list(MEDIATION_ORDER)
    assert mediation["mode"] == "merge_time_intent"
    assert mediation["intent_kind"] == "active_assertion_append"
    assert mediation["materialization_record_index"] == 0
    assert mediation["materialization_record_count"] == 1


def test_supersede_pair_gets_two_record_indexes_and_chain():
    result = _build(_supersede())
    first, second = result.appended_records

    assert first["mediation"]["materialization_record_index"] == 0
    assert second["mediation"]["materialization_record_index"] == 1
    assert first["mediation"]["materialization_record_count"] == 2
    assert second["mediation"]["materialization_record_count"] == 2
    assert second["prev_hash"] == first["content_hash"]


def test_content_hashes_and_first_prev_hash_follow_live_tail():
    base = _base_records()
    result = _build(_active())
    appended = result.appended_records[0]

    assert appended["prev_hash"] == base[-1]["content_hash"]
    assert appended["content_hash"] == brain_runtime.canonical_content_hash(appended)
    assert result.ledger_tail_before == base[-1]["content_hash"]
    assert result.ledger_tail_after == appended["content_hash"]


def test_record_body_excludes_execution_environment_fields():
    result = _build(_active())
    rendered = result.ledger_text

    for forbidden in ("materialization_commit_sha", "pid", "hostname", "credential", "retry", "/var/tmp"):
        assert forbidden not in rendered
