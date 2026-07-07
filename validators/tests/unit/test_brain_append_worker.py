from __future__ import annotations
import json
from pathlib import Path
import pytest
import yaml
from creator_engine_validator import brain_runtime as rt
from creator_engine_validator.brain_append_worker import (
    BrainAppendRefusal,
    load_intent,
    run_once,
    validate_intent_doc,
)
CLAIM = {"subject": "brain", "predicate": "append", "object": "mediated"}
class Capture:
    text = ""
    def __call__(self, _path: Path, text: str) -> None:
        self.text = text
def _base_ledger() -> str:
    sink = Capture()
    rt.assert_claim(
        claim=CLAIM,
        scope="creator-engine",
        evidence_ref="docs/adr/ADR-0005-mediated-brain-ledger-append.md",
        assertion_id="brain-assertion-append-base",
        records=[],
        state_root=Path(".ce/state"),
        write=sink,
    )
    return sink.text
def _active(assertion_id: str = "brain-assertion-append-new", claim: dict | None = None) -> dict:
    return {
        "kind": "brain-append-intent",
        "schema_version": "1",
        "intent_kind": "active_assertion_append",
        "active_assertion": {
            "assertion_id": assertion_id,
            "claim": claim or {"subject": "brain", "predicate": "worker", "object": assertion_id[-3:]},
            "scope": "creator-engine",
            "evidence_ref": "docs/adr/ADR-0005-mediated-brain-ledger-append.md#7",
        },
    }
def _supersede() -> dict:
    return {
        "kind": "brain-append-intent",
        "schema_version": "1",
        "intent_kind": "ce411_supersede_pair",
        "supersede_pair": {
            "assertion_id": "brain-assertion-append-base",
            "replacement": {
                "new_assertion_id": "brain-assertion-append-next",
                "claim": {"subject": "brain", "predicate": "append", "object": "mediated-v2"},
                "scope": "creator-engine",
                "evidence_ref": "docs/adr/ADR-0005-mediated-brain-ledger-append.md#7",
            },
        },
    }
def _decision() -> dict:
    return {
        "kind": "brain-append-intent",
        "schema_version": "1",
        "intent_kind": "decision_append",
        "decision": {
            "decision_id": "brain-decision-append-0001",
            "date": "2026-07-07",
            "scope": "controller-memory",
            "statement": "Takeover must hydrate controller memory from artifacts.",
            "supersedes_ref": None,
        },
    }
def _lesson() -> dict:
    return {
        "kind": "brain-append-intent",
        "schema_version": "1",
        "intent_kind": "lesson_append",
        "lesson": {
            "lesson_id": "brain-lesson-append-0001",
            "date": "2026-07-07",
            "scope": "controller-memory",
            "feedback": "A standby controller could not reconstruct forge housekeeping.",
            "correction": "Persist operating context in a deterministic hydration contract.",
            "why": "Session memory is not available after takeover.",
            "how_to_apply": "Read ce brain hydrate --json during takeover Hydrate.",
            "supersedes_ref": None,
        },
    }
def _queued(tmp_path: Path, data: dict) -> Path:
    queue = tmp_path / "queue"
    queue.mkdir()
    (queue / "001.yaml").write_text(yaml.safe_dump(data, sort_keys=True), encoding="utf-8")
    return queue
def _git_show(text: str):
    return lambda args, _cwd: (0, text, "") if args == ["show", "origin/main:.ce/brain/assertions.yaml"] else (1, "", "bad args")
def _run(tmp_path: Path, data: dict, git_show=None):
    return run_once(
        queue_dir=_queued(tmp_path, data),
        repo_root=tmp_path,
        out_dir=tmp_path / "out",
        git_runner=git_show or _git_show(_base_ledger()),
    )
def test_envelope_validation_rejects_position_bearing_and_malformed_intents(tmp_path: Path):
    data = _active()
    data["active_assertion"]["sequence"] = 99
    errors = validate_intent_doc(data)
    assert any(error.code == "brain_append_intent_schema" for error in errors)
    assert any(error.code == "brain_append_contained_boundary" for error in errors)
    path = tmp_path / "bad.yaml"
    path.write_text("kind: brain-append-intent\nschema_version: '1'\n", encoding="utf-8")
    with pytest.raises(BrainAppendRefusal) as exc:
        load_intent(path)
    assert exc.value.invariant == "brain_append_intent_schema"
@pytest.mark.parametrize("intent, sequences", [(_active(), [1]), (_supersede(), [1, 2])])
def test_success_assigns_sequence_prev_hash_and_evidence(tmp_path: Path, intent: dict, sequences: list[int]):
    outcome = _run(tmp_path, intent)
    evidence = json.loads(outcome.evidence_path.read_text(encoding="utf-8"))
    assert outcome.outcome == "committed"
    assert outcome.patch_path is not None and outcome.patch_path.is_file()
    assert evidence["appended_sequences"] == sequences
    assert evidence["appended_prev_hashes"][0] == evidence["head_before"]
    assert evidence["record_count_after"] == 1 + len(sequences)
@pytest.mark.parametrize(
    "intent, kind, record_id",
    [
        (_decision(), "brain-decision", "brain-decision-append-0001"),
        (_lesson(), "brain-lesson", "brain-lesson-append-0001"),
    ],
)
def test_memory_record_kinds_round_trip_through_mediated_append(
    tmp_path: Path, intent: dict, kind: str, record_id: str
):
    outcome = _run(tmp_path, intent)

    evidence = json.loads(outcome.evidence_path.read_text(encoding="utf-8"))

    assert outcome.outcome == "committed"
    assert evidence["appended_kinds"] == [kind]
    assert evidence["appended_ids"] == [record_id]
    assert evidence["appended_sequences"] == [1]
    assert evidence["record_count_after"] == 2
def test_refusal_names_duplicate_active_invariant(tmp_path: Path):
    outcome = _run(tmp_path, _active("brain-assertion-append-other", CLAIM))
    evidence = json.loads(outcome.evidence_path.read_text(encoding="utf-8"))
    assert outcome.outcome == "refused"
    assert outcome.invariant == "active_assertion_unique"
    assert evidence["invariant"] == "active_assertion_unique"
    assert not list((tmp_path / "out").glob("*.ledger.patch"))
def test_refusal_when_origin_main_ledger_cannot_materialize(tmp_path: Path):
    outcome = _run(tmp_path, _active(), lambda _args, _cwd: (1, "", "missing origin/main"))
    assert outcome.outcome == "refused"
    assert outcome.invariant == "origin_main_ledger_materialized"

def test_malformed_yaml_intent_is_refused_not_raised(tmp_path: Path):
    queue = tmp_path / "queue"
    queue.mkdir()
    (queue / "001.yaml").write_text("key: [unclosed", encoding="utf-8")
    outcome = run_once(
        queue_dir=queue,
        repo_root=tmp_path,
        out_dir=tmp_path / "out",
        git_runner=_git_show(_base_ledger()),
    )
    assert outcome.outcome == "refused"
    assert outcome.invariant == "brain_append_intent_schema"
