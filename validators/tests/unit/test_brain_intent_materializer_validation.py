from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from creator_engine_validator.brain_append_worker import BrainAppendRefusal
from creator_engine_validator.brain_intent_materializer import IntentDiscovery


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


def _write(tmp_path: Path, slug: str, data: dict) -> Path:
    path = tmp_path / f"{slug}.yaml"
    path.write_text(yaml.safe_dump(data, sort_keys=True), encoding="utf-8")
    return path


def test_valid_intent_is_accepted_and_hashed(tmp_path: Path):
    path = _write(tmp_path, "ce-branch", _active())

    discovered = IntentDiscovery().discover(merge_commit_sha="a" * 40, intent_path=path, branch_slug="ce-branch")

    assert discovered.data["intent_kind"] == "active_assertion_append"
    assert len(discovered.intent_sha256) == 64
    assert discovered.materialization_key.intent_sha256 == discovered.intent_sha256


def test_branch_slug_mismatch_is_refused(tmp_path: Path):
    path = _write(tmp_path, "actual", _active())

    with pytest.raises(BrainAppendRefusal) as exc:
        IntentDiscovery().discover(merge_commit_sha="a" * 40, intent_path=path, branch_slug="expected")

    assert exc.value.invariant == "brain_append_intent_path_binding"


@pytest.mark.parametrize("field", ["prev_hash", "content_hash"])
def test_position_hash_fields_are_refused(tmp_path: Path, field: str):
    data = _active()
    data["active_assertion"][field] = "x"
    path = _write(tmp_path, "ce-branch", data)

    with pytest.raises(BrainAppendRefusal):
        IntentDiscovery().discover(merge_commit_sha="a" * 40, intent_path=path, branch_slug="ce-branch")


def test_position_or_host_fields_are_refused_even_inside_payload_mappings(tmp_path: Path):
    data = _active()
    data["active_assertion"]["claim"]["host_path"] = "/tmp/local"
    path = _write(tmp_path, "ce-branch", data)

    with pytest.raises(BrainAppendRefusal) as exc:
        IntentDiscovery().discover(merge_commit_sha="a" * 40, intent_path=path, branch_slug="ce-branch")

    assert exc.value.invariant == "brain_append_contained_boundary"


def test_unknown_intent_kind_is_refused(tmp_path: Path):
    data = _active()
    data["intent_kind"] = "unknown_append"
    path = _write(tmp_path, "ce-branch", data)

    with pytest.raises(BrainAppendRefusal) as exc:
        IntentDiscovery().discover(merge_commit_sha="a" * 40, intent_path=path, branch_slug="ce-branch")

    assert exc.value.invariant == "brain_append_intent_schema"


def test_malformed_yaml_is_refused(tmp_path: Path):
    path = tmp_path / "ce-branch.yaml"
    path.write_text("kind: [unclosed", encoding="utf-8")

    with pytest.raises(BrainAppendRefusal) as exc:
        IntentDiscovery().discover(merge_commit_sha="a" * 40, intent_path=path, branch_slug="ce-branch")

    assert exc.value.invariant == "brain_append_intent_schema"


@pytest.mark.parametrize("intent", [_active(), _supersede(), _decision(), _lesson()])
def test_all_four_valid_intent_kinds_are_accepted(tmp_path: Path, intent: dict):
    path = _write(tmp_path, "ce-branch", intent)

    discovered = IntentDiscovery().discover(merge_commit_sha="a" * 40, intent_path=path, branch_slug="ce-branch")

    assert discovered.data["intent_kind"] == intent["intent_kind"]
