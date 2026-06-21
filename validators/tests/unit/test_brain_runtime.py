from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from creator_engine_validator import brain_runtime as rt


SCOPE = "creator-engine"
CLAIM = {"subject": "brain", "predicate": "mode", "object": "ssot"}
CORRECTED = {"subject": "brain", "predicate": "mode", "object": "deterministic-ssot"}
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
        "records": records,
        "write": write or CaptureWrite(),
    }
    kwargs.update(override)
    return rt.assert_claim(**kwargs)


def test_assert_check_roundtrip_with_injected_write():
    sink = CaptureWrite()
    asserted = _assert(write=sink)

    assert sink.calls[0][0] == Path(".ce/state/brain/assertions.yaml")
    checked = rt.check_claim(claim=CLAIM, scope=SCOPE, records=sink.records)

    assert checked.status == "active"
    assert checked.record is not None
    assert checked.record["id"] == asserted.record["id"]
    assert checked.record["content_hash"] == asserted.content_hash


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


def test_schema_invalid_ledger_fails_closed():
    sink = CaptureWrite()
    _assert(write=sink)
    records = sink.records
    del records[0]["evidence_ref"]

    with pytest.raises(rt.BrainLedgerInvalid):
        rt.check_claim(claim=CLAIM, scope=SCOPE, records=records)


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
