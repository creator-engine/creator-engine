from __future__ import annotations

import json
from pathlib import Path

import pytest

from creator_engine_validator import brain_bootstrap as bootstrap
from creator_engine_validator import brain_runtime as rt


def _write_ledger(state_root: Path, records: list[dict]) -> None:
    path = rt.ledger_path(state_root)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(rt.serialize_ledger(records), encoding="utf-8")


def _records_with_assertions(state_root: Path) -> list[dict]:
    first = rt.assert_claim(
        assertion_id="brain-assertion-bootstrap-0001",
        claim={"subject": "repo", "predicate": "mode", "object": "governed"},
        scope="global",
        evidence_ref="validators/tests/unit/test_brain_bootstrap.py#first",
        state_root=state_root,
        records=[],
        write=lambda _path, _text: None,
    )
    second = rt.assert_claim(
        assertion_id="brain-assertion-bootstrap-0002",
        claim={"subject": "lane", "predicate": "seat", "object": "foreman"},
        scope={"project": "creator-engine", "role": "controller", "seat_class": "foreman"},
        evidence_ref="validators/tests/unit/test_brain_bootstrap.py#second",
        state_root=state_root,
        records=[first.record],
        write=lambda _path, _text: None,
    )
    other = rt.assert_claim(
        assertion_id="brain-assertion-bootstrap-0003",
        claim={"subject": "other", "predicate": "scope", "object": "hidden"},
        scope={"project": "other"},
        evidence_ref="validators/tests/unit/test_brain_bootstrap.py#other",
        state_root=state_root,
        records=[first.record, second.record],
        write=lambda _path, _text: None,
    )
    return [first.record, second.record, other.record]


def test_valid_ledger_loads_deterministically(tmp_path: Path):
    state_root = tmp_path / ".ce" / "state"
    records = _records_with_assertions(state_root)
    _write_ledger(state_root, records)

    payload_a = bootstrap.build_bootstrap_payload(
        state_root=state_root,
        scope={"project": "creator-engine", "role": "controller", "seat_class": "foreman"},
    )
    payload_b = bootstrap.build_bootstrap_payload(
        state_root=state_root,
        scope={"project": "creator-engine", "role": "controller", "seat_class": "foreman"},
    )

    assert payload_a == payload_b
    assert json.dumps(payload_a, sort_keys=True, separators=(",", ":")) == json.dumps(
        payload_b,
        sort_keys=True,
        separators=(",", ":"),
    )
    assert payload_a["knowledge_ssot"]["record_count"] == 3
    assert payload_a["knowledge_ssot"]["scope_relevant_count"] == 2
    assert payload_a["context"]["seat_class"] == "foreman"


def test_tampered_chain_raises_and_refuses_payload(tmp_path: Path):
    state_root = tmp_path / ".ce" / "state"
    records = _records_with_assertions(state_root)
    records[0]["claim"]["object"] = "tampered"
    _write_ledger(state_root, records)

    with pytest.raises(bootstrap.BrainBootstrapRefused):
        bootstrap.build_bootstrap_payload(
            state_root=state_root,
            scope={"project": "creator-engine", "role": "controller", "seat_class": "foreman"},
        )


def test_scope_filtering_returns_expected_assertions(tmp_path: Path):
    state_root = tmp_path / ".ce" / "state"
    _write_ledger(state_root, _records_with_assertions(state_root))

    payload = bootstrap.build_bootstrap_payload(
        state_root=state_root,
        scope={"project": "creator-engine", "role": "controller", "seat_class": "foreman"},
    )

    ids = [item["id"] for item in payload["knowledge_ssot"]["assertions"]]
    assert ids == ["brain-assertion-bootstrap-0001", "brain-assertion-bootstrap-0002"]


def test_default_scope_includes_controller_role_and_seat_class(tmp_path: Path):
    state_root = tmp_path / ".ce" / "state"
    records = _records_with_assertions(state_root)
    role_bound = rt.assert_claim(
        assertion_id="brain-assertion-bootstrap-0004",
        claim={"subject": "lane", "predicate": "role", "object": "controller"},
        scope={"role": "controller", "seat_class": "foreman"},
        evidence_ref="validators/tests/unit/test_brain_bootstrap.py#role-bound",
        state_root=state_root,
        records=records,
        write=lambda _path, _text: None,
    )
    _write_ledger(state_root, [*records, role_bound.record])

    payload = bootstrap.build_bootstrap_payload(state_root=state_root)

    assert payload["context"]["scope"] == {"role": "controller", "seat_class": "foreman"}
    ids = [item["id"] for item in payload["knowledge_ssot"]["assertions"]]
    assert ids == ["brain-assertion-bootstrap-0001", "brain-assertion-bootstrap-0004"]


def test_scope_seat_class_cannot_bypass_resolved_bootstrap_context(tmp_path: Path):
    state_root = tmp_path / ".ce" / "state"
    records = _records_with_assertions(state_root)
    worker = rt.assert_claim(
        assertion_id="brain-assertion-bootstrap-0004",
        claim={"subject": "lane", "predicate": "seat", "object": "worker"},
        scope={"project": "creator-engine", "role": "controller", "seat_class": "worker"},
        evidence_ref="validators/tests/unit/test_brain_bootstrap.py#worker",
        state_root=state_root,
        records=records,
        write=lambda _path, _text: None,
    )
    _write_ledger(state_root, [*records, worker.record])

    payload = bootstrap.build_bootstrap_payload(
        state_root=state_root,
        scope={"project": "creator-engine", "role": "controller", "seat_class": "worker"},
        seat_class="bogus",
    )

    assert payload["context"]["seat_class"] == "foreman"
    assert payload["context"]["scope"] == {
        "project": "creator-engine",
        "role": "controller",
        "seat_class": "foreman",
    }
    ids = [item["id"] for item in payload["knowledge_ssot"]["assertions"]]
    assert ids == ["brain-assertion-bootstrap-0001", "brain-assertion-bootstrap-0002"]


def test_corrected_assertion_is_reflected_on_next_bootstrap(tmp_path: Path):
    state_root = tmp_path / ".ce" / "state"
    asserted = rt.assert_claim(
        assertion_id="brain-assertion-bootstrap-0001",
        claim={"subject": "lane", "predicate": "seat", "object": "worker"},
        scope={"project": "creator-engine", "role": "controller", "seat_class": "foreman"},
        evidence_ref="validators/tests/unit/test_brain_bootstrap.py#original",
        state_root=state_root,
        records=[],
        write=lambda _path, _text: None,
    )
    _write_ledger(state_root, [asserted.record])

    before = bootstrap.build_bootstrap_payload(
        state_root=state_root,
        scope={"project": "creator-engine", "role": "controller", "seat_class": "foreman"},
    )
    correction = rt.correct_claim(
        assertion_id="brain-assertion-bootstrap-0001",
        new_assertion_id="brain-assertion-bootstrap-0004",
        claim={"subject": "lane", "predicate": "seat", "object": "foreman"},
        scope={"project": "creator-engine", "role": "controller", "seat_class": "foreman"},
        evidence_ref="validators/tests/unit/test_brain_bootstrap.py#correction",
        state_root=state_root,
        records=[asserted.record],
        write=lambda _path, _text: None,
    )
    _write_ledger(state_root, [asserted.record, correction.superseded_record, correction.record])

    after = bootstrap.build_bootstrap_payload(
        state_root=state_root,
        scope={"project": "creator-engine", "role": "controller", "seat_class": "foreman"},
    )

    assert before["knowledge_ssot"]["assertions"][0]["claim"]["object"] == "worker"
    assert [item["id"] for item in after["knowledge_ssot"]["assertions"]] == ["brain-assertion-bootstrap-0004"]
    assert after["knowledge_ssot"]["assertions"][0]["claim"]["object"] == "foreman"


def test_missing_ledger_refuses_bootstrap(tmp_path: Path):
    state_root = tmp_path / ".ce" / "state"

    with pytest.raises(bootstrap.BrainBootstrapRefused) as ei:
        bootstrap.build_bootstrap_payload(
            state_root=state_root,
            scope={"project": "creator-engine", "role": "controller"},
        )

    assert "no brain assertion ledger" in "\n".join(ei.value.errors)


def test_absent_or_unknown_seat_class_fails_closed_to_foreman(tmp_path: Path):
    state_root = tmp_path / ".ce" / "state"
    _write_ledger(state_root, _records_with_assertions(state_root))

    payload = bootstrap.build_bootstrap_payload(
        state_root=state_root,
        scope={"project": "creator-engine", "role": "controller"},
        seat_class="bogus",
    )

    assert payload["context"]["scope"]["seat_class"] == "foreman"
    assert payload["context"]["seat_class"] == "foreman"
