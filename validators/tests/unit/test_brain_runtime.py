from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest
import yaml

from creator_engine_validator import brain_runtime as rt


SCOPE = "creator-engine"
CLAIM = {"subject": "brain", "predicate": "mode", "object": "ssot"}
CORRECTED = {"subject": "brain", "predicate": "mode", "object": "deterministic-ssot"}
REPINNED = {"subject": "brain", "predicate": "mode", "object": "evidence-repinned-ssot"}
EVIDENCE = "docs/operations/PCL_PROTOCOL.md#hash-chain"


class CaptureWrite:
    def __init__(self) -> None:
        self.calls: list[tuple[Path, str]] = []

    def __call__(self, path: Path, text: str) -> None:
        self.calls.append((path, text))

    @property
    def text(self) -> str:
        assert self.calls
        return self.calls[-1][1]

    @property
    def records(self) -> list[dict]:
        return rt.load_ledger_text(self.text)


def _assert(records=None, write=None, **override) -> rt.AssertResult:
    kwargs = {
        "claim": CLAIM,
        "scope": SCOPE,
        "evidence_ref": EVIDENCE,
        "assertion_id": "brain-assertion-runtime-0001",
        "state_root": Path(".ce/state"),
        "records": [] if records is None else records,
        "write": write or CaptureWrite(),
    }
    kwargs.update(override)
    return rt.assert_claim(**kwargs)


def _chained_correction_records() -> list[dict]:
    first_sink = CaptureWrite()
    _assert(write=first_sink)

    second_sink = CaptureWrite()
    rt.correct_claim(
        assertion_id="brain-assertion-runtime-0001",
        new_assertion_id="brain-assertion-runtime-0002",
        claim=CORRECTED,
        evidence_ref="docs/operations/PCL_PROTOCOL.md#correction",
        records=first_sink.records,
        write=second_sink,
        state_root=Path(".ce/state"),
    )

    third_sink = CaptureWrite()
    rt.correct_claim(
        assertion_id="brain-assertion-runtime-0002",
        new_assertion_id="brain-assertion-runtime-0003",
        claim=REPINNED,
        evidence_ref="docs/operations/PCL_PROTOCOL.md#repin",
        records=second_sink.records,
        write=third_sink,
        state_root=Path(".ce/state"),
    )
    return third_sink.records


def _rehash_records(records: list[dict], start: int) -> list[dict]:
    updated = copy.deepcopy(records)
    for idx in range(start, len(updated)):
        updated[idx]["sequence"] = idx
        prev_hash = rt.GENESIS_PREV_HASH if idx == 0 else updated[idx - 1][rt.CONTENT_HASH_FIELD]
        updated[idx]["prev_hash"] = prev_hash
        updated[idx][rt.CONTENT_HASH_FIELD] = rt.canonical_content_hash(updated[idx])
    return updated


def test_assert_check_roundtrip_with_injected_write():
    sink = CaptureWrite()
    asserted = _assert(write=sink)

    assert sink.calls[0][0] == Path(".ce/state/brain/assertions.yaml")
    checked = rt.check_claim(claim=CLAIM, scope=SCOPE, records=sink.records)

    assert checked.status == "active"
    assert checked.record is not None
    assert checked.record["id"] == asserted.record["id"]
    assert checked.record["content_hash"] == asserted.content_hash
    assert checked.record["statement"] == "brain mode ssot"
    assert checked.record["type"] == "decision"
    assert checked.record["verification_method"] == {"evidence_ref": EVIDENCE, "type": "static"}


def test_correct_appends_supersede_marker_and_new_active_assertion():
    sink = CaptureWrite()
    _assert(write=sink)
    records = sink.records

    correction_sink = CaptureWrite()
    corrected = rt.correct_claim(
        assertion_id="brain-assertion-runtime-0001",
        new_assertion_id="brain-assertion-runtime-0002",
        claim=CORRECTED,
        evidence_ref="docs/operations/PCL_PROTOCOL.md#correction",
        records=records,
        write=correction_sink,
        state_root=Path(".ce/state"),
    )

    assert corrected.superseded_record["status"] == "superseded"
    assert corrected.superseded_record["superseded_by"] == "brain-assertion-runtime-0002"
    assert corrected.record["status"] == "active"

    current = correction_sink.records
    assert rt.check_claim(claim=CLAIM, scope=SCOPE, records=current).status == "unknown"
    checked = rt.check_claim(claim=CORRECTED, scope=SCOPE, records=current)
    assert checked.status == "active"
    assert checked.record is not None
    assert checked.record["id"] == "brain-assertion-runtime-0002"


def test_chained_supersede_validates_and_current_view_resolves_to_latest_active():
    records = _chained_correction_records()

    assert rt.validate_records(records) == []
    assert rt.check_claim(claim=CLAIM, scope=SCOPE, records=records).status == "unknown"
    assert rt.check_claim(claim=CORRECTED, scope=SCOPE, records=records).status == "unknown"
    checked = rt.check_claim(claim=REPINNED, scope=SCOPE, records=records)

    assert checked.status == "active"
    assert checked.record is not None
    assert checked.record["id"] == "brain-assertion-runtime-0003"


def test_supersede_cycle_is_rejected():
    records = _chained_correction_records()
    v2_tombstone_idx = max(
        idx
        for idx, record in enumerate(records)
        if record["id"] == "brain-assertion-runtime-0002" and record["status"] == "superseded"
    )
    records[v2_tombstone_idx]["superseded_by"] = "brain-assertion-runtime-0001"
    records = _rehash_records(records, v2_tombstone_idx)

    errors = rt.validate_records(records)

    assert not any(error.code == rt.CODE_CONTENT_ADDRESS for error in errors), [error.format() for error in errors]
    assert any(
        error.code == rt.CODE_SUPERSEDE_TARGET and "superseded assertion chain contains a cycle" in error.message
        for error in errors
    ), [error.format() for error in errors]


def test_supersede_chain_dead_ending_in_missing_id_is_rejected():
    records = _chained_correction_records()
    v2_tombstone_idx = max(
        idx
        for idx, record in enumerate(records)
        if record["id"] == "brain-assertion-runtime-0002" and record["status"] == "superseded"
    )
    records[v2_tombstone_idx]["superseded_by"] = "brain-assertion-runtime-9999"
    records = _rehash_records(records, v2_tombstone_idx)

    errors = rt.validate_records(records)

    assert not any(error.code == rt.CODE_CONTENT_ADDRESS for error in errors), [error.format() for error in errors]
    assert any(
        error.code == rt.CODE_SUPERSEDE_TARGET
        and error.message == "superseded assertion must point at an existing assertion id"
        for error in errors
    ), [error.format() for error in errors]
    assert any(
        error.code == rt.CODE_SUPERSEDE_TARGET
        and error.message == "superseded assertion must point at a currently active assertion"
        for error in errors
    ), [error.format() for error in errors]


def test_tamper_is_caught_by_content_hash_check():
    sink = CaptureWrite()
    _assert(write=sink)
    records = sink.records
    records[0]["claim"]["object"] = "mutated"

    errors = rt.validate_records(records)

    assert any(error.code == rt.CODE_CONTENT_ADDRESS for error in errors), [e.format() for e in errors]


def test_unknown_claim_returns_unknown_without_guessing():
    result = rt.check_claim(
        claim={"subject": "brain", "predicate": "missing", "object": "fact"},
        scope=SCOPE,
        records=[],
    )

    assert result.status == "unknown"
    assert result.record is None


def test_on_disk_empty_records_ledger_fails_closed_and_is_not_rewritten(tmp_path: Path):
    state_root = tmp_path / ".ce" / "state"
    path = state_root / "brain" / "assertions.yaml"
    path.parent.mkdir(parents=True)
    original = yaml.safe_dump(
        {
            "kind": rt.LEDGER_KIND,
            "record_type": rt.LEDGER_RECORD_TYPE,
            "schema_version": rt.SCHEMA_VERSION,
            "records": [],
        },
        sort_keys=True,
    )
    path.write_text(original, encoding="utf-8")

    with pytest.raises(rt.BrainLedgerInvalid):
        rt.load_records(state_root)

    with pytest.raises(rt.BrainLedgerInvalid):
        rt.check_claim(claim=CLAIM, scope=SCOPE, state_root=state_root)

    write = CaptureWrite()
    with pytest.raises(rt.BrainLedgerInvalid):
        rt.assert_claim(
            claim={"subject": "brain", "predicate": "new", "object": "fact"},
            scope=SCOPE,
            evidence_ref=EVIDENCE,
            state_root=state_root,
            assertion_id="brain-assertion-runtime-0003",
            write=write,
        )
    assert write.calls == []
    assert path.read_text(encoding="utf-8") == original


def test_schema_invalid_ledger_fails_closed():
    sink = CaptureWrite()
    _assert(write=sink)
    records = sink.records
    del records[0]["evidence_ref"]

    with pytest.raises(rt.BrainLedgerInvalid):
        rt.check_claim(claim=CLAIM, scope=SCOPE, records=records)


@pytest.mark.parametrize("field", ["statement", "type", "verification_method"])
def test_canonical_assertion_fields_are_required(field: str):
    sink = CaptureWrite()
    _assert(write=sink)
    records = sink.records
    del records[0][field]

    with pytest.raises(rt.BrainLedgerInvalid):
        rt.check_claim(claim=CLAIM, scope=SCOPE, records=records)


def test_probe_assertion_derives_verification_method():
    sink = CaptureWrite()
    _assert(
        write=sink,
        claim={
            "subject": "capability",
            "predicate": "probe-verdict",
            "object": "harness_fan_out",
            "verdict": "present",
        },
        assertion_type="capability",
        evidence_ref="probe:harness_fan_out",
        assertion_id="brain-assertion-runtime-probe",
    )

    record = sink.records[0]

    assert record["type"] == "capability"
    assert record["statement"] == "capability probe-verdict harness_fan_out"
    assert record["verification_method"] == {
        "evidence_ref": "probe:harness_fan_out",
        "probe": "harness_fan_out",
        "type": "probe",
    }


def test_on_disk_non_mapping_record_fails_closed_and_is_not_rewritten(tmp_path: Path):
    sink = CaptureWrite()
    _assert(write=sink)
    data = yaml.safe_load(sink.text)
    data["records"].insert(0, "bad")
    state_root = tmp_path / ".ce" / "state"
    path = state_root / "brain" / "assertions.yaml"
    path.parent.mkdir(parents=True)
    original = yaml.safe_dump(data, sort_keys=True)
    path.write_text(original, encoding="utf-8")

    with pytest.raises(rt.BrainLedgerInvalid):
        rt.check_claim(claim=CLAIM, scope=SCOPE, state_root=state_root)

    write = CaptureWrite()
    with pytest.raises(rt.BrainLedgerInvalid):
        rt.assert_claim(
            claim={"subject": "brain", "predicate": "new", "object": "fact"},
            scope=SCOPE,
            evidence_ref=EVIDENCE,
            state_root=state_root,
            assertion_id="brain-assertion-runtime-0003",
            write=write,
        )
    assert write.calls == []
    assert path.read_text(encoding="utf-8") == original


def test_structured_claim_is_required():
    with pytest.raises(rt.BrainAssertionRefused):
        rt.assert_claim(
            claim="free prose",  # type: ignore[arg-type]
            scope=SCOPE,
            evidence_ref=EVIDENCE,
            records=[],
            write=CaptureWrite(),
        )


def test_deterministic_bytes_for_same_input():
    a = CaptureWrite()
    b = CaptureWrite()
    _assert(write=a)
    _assert(write=b)

    assert a.text == b.text
    assert yaml.safe_load(a.text) == yaml.safe_load(b.text)


def test_forbidden_identifier_keys_fail_closed():
    with pytest.raises(rt.BrainAssertionRefused):
        rt.assert_claim(
            claim={"subject": "brain", "predicate": "host", "host": "example"},
            scope=SCOPE,
            evidence_ref=EVIDENCE,
            records=[],
            write=CaptureWrite(),
        )


def test_decision_and_lesson_records_hydrate_in_deterministic_active_order(tmp_path: Path):
    sink = CaptureWrite()
    rt._append_decision(
        date="2026-07-08",
        scope="forge",
        statement="second by date",
        authority="controller",
        decision_id="brain-decision-runtime-0002",
        records=[],
        state_root=tmp_path / ".ce" / "state",
        write=sink,
    )
    rt._append_decision(
        date="2026-07-07",
        scope="forge",
        statement="first by date",
        authority="operator",
        decision_id="brain-decision-runtime-0001",
        records=sink.records,
        state_root=tmp_path / ".ce" / "state",
        write=sink,
    )
    rt._append_decision(
        date="2026-07-09",
        scope="forge",
        statement="replacement decision",
        authority="controller",
        supersedes_ref="brain-decision-runtime-0002",
        decision_id="brain-decision-runtime-0003",
        records=sink.records,
        state_root=tmp_path / ".ce" / "state",
        write=sink,
    )
    rt._append_lesson(
        date="2026-07-07",
        scope="takeover",
        source="review:PR-888",
        feedback="standby controller lacked operating context",
        correction="hydrate memory from artifacts",
        why="session-only memory is not recoverable",
        how_to_apply="run ce brain hydrate --json during takeover",
        lesson_id="brain-lesson-runtime-0001",
        records=sink.records,
        state_root=tmp_path / ".ce" / "state",
        write=sink,
    )
    ledger = tmp_path / ".ce" / "state" / "brain" / "assertions.yaml"
    ledger.parent.mkdir(parents=True)
    ledger.write_text(sink.text, encoding="utf-8")

    payload = rt.hydrate_contract(tmp_path / ".ce" / "state")

    assert [record["id"] for record in payload["active_decisions"]] == [
        "brain-decision-runtime-0001",
        "brain-decision-runtime-0003",
    ]
    assert [record["id"] for record in payload["active_lessons"]] == [
        "brain-lesson-runtime-0001"
    ]
    assert payload["active_decisions"][0]["authority"] == "operator"
    assert payload["active_lessons"][0]["source"] == "review:PR-888"
    assert payload["summary"] == {
        "active_decision_count": 2,
        "active_lesson_count": 1,
        "newest_resume_state_present": False,
    }


def test_hydrate_empty_or_absent_ledger_returns_well_formed_contract(tmp_path: Path):
    state_root = tmp_path / ".ce" / "state"

    absent = rt.hydrate_contract(state_root)

    assert absent["kind"] == rt.HYDRATION_KIND
    assert absent["ledger_present"] is False
    assert absent["active_decisions"] == []
    assert absent["active_lessons"] == []
    assert absent["newest_resume_state"] is None

    path = state_root / "brain" / "assertions.yaml"
    path.parent.mkdir(parents=True)
    path.write_text("records: []\n", encoding="utf-8")

    empty = rt.hydrate_contract(state_root)

    assert empty["ledger_present"] is True
    assert empty["record_count"] == 0
    assert empty["active_decisions"] == []
    assert empty["active_lessons"] == []


def test_hydrate_contract_is_byte_identical_for_seeded_resume_state(tmp_path: Path):
    state_root = tmp_path / ".ce" / "state"
    sink = CaptureWrite()
    rt._append_decision(
        date="2026-07-07",
        scope="takeover",
        statement="Hydration must be deterministic for takeover.",
        authority="controller",
        decision_id="brain-decision-runtime-determinism",
        records=[],
        state_root=state_root,
        write=sink,
    )
    rt._append_lesson(
        date="2026-07-07",
        scope="takeover",
        source="review:PR-888",
        feedback="Resume metadata changed after touching files.",
        correction="Expose resume content hash instead of mtime.",
        why="Takeover evidence must serialize byte-identically for the same state.",
        how_to_apply="Compare content_sha256 when inspecting newest_resume_state.",
        lesson_id="brain-lesson-runtime-determinism",
        records=sink.records,
        state_root=state_root,
        write=sink,
    )
    ledger = state_root / "brain" / "assertions.yaml"
    ledger.parent.mkdir(parents=True)
    ledger.write_text(sink.text, encoding="utf-8")
    resume = state_root / "sessions" / "controller-resume.json"
    resume.parent.mkdir(parents=True)
    resume.write_text('{"resume":true}\n', encoding="utf-8")

    first = json.dumps(rt.hydrate_contract(state_root), sort_keys=True, separators=(",", ":"))
    second = json.dumps(rt.hydrate_contract(state_root), sort_keys=True, separators=(",", ":"))

    assert first == second
    payload = json.loads(first)
    assert payload["schema_version"] == rt.SCHEMA_VERSION
    assert payload["newest_resume_state"]["content_sha256"] == (
        "1b9c7213273033f30c70340a757e6037e02de0e59962ca8356b4c2fedf2a44ad"
    )
    assert "mtime" not in payload["newest_resume_state"]


def test_resume_state_pointer_selects_newest_resume_path_before_hash(tmp_path: Path):
    state_root = tmp_path / ".ce" / "state"
    sessions = state_root / "sessions"
    sessions.mkdir(parents=True)
    older = sessions / "20260707T000000-controller-resume.json"
    newer = sessions / "20260708T000000-controller-resume.json"
    older.write_text("older", encoding="utf-8")
    newer.write_text("newer", encoding="utf-8")

    pointer = rt._resume_state_pointer(state_root)

    assert pointer == {
        "path": str(newer),
        "content_sha256": "804f51f71254c4081e37e7c887073560f4a6fa6cdad202e9ac67e032c43ed1e1",
        "size_bytes": 5,
    }
