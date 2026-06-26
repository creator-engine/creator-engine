from __future__ import annotations

import json
from pathlib import Path

import pytest

from creator_engine_validator import brain_bootstrap as bootstrap
from creator_engine_validator import brain_probe
from creator_engine_validator import brain_runtime as rt


def _write_ledger(state_root: Path, records: list[dict]) -> None:
    path = rt.ledger_path(state_root)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(rt.serialize_ledger(records), encoding="utf-8")


def _write_authoritative_ledger(repo_root: Path, records: list[dict]) -> None:
    path = rt.authoritative_ledger_path(repo_root)
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


class FakeCompleted:
    def __init__(self, returncode: int, stdout: str = "") -> None:
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = ""


def _probe_runner(command):
    if command[:1] == ["tailscale"]:
        return FakeCompleted(1)
    if command[:1] == ["nvidia-smi"]:
        return FakeCompleted(1)
    return FakeCompleted(0)


def _self_identity_record(
    state_root: Path,
    *,
    assertion_id: str = "brain-assertion-bootstrap-self-identity",
    current_user: str = "controller",
    runtime_name: str,
    scope_seat: str | None = "controller",
    records: list[dict] | None = None,
) -> dict:
    result = rt.assert_claim(
        assertion_id=assertion_id,
        statement="self identity must match live runtime probe",
        assertion_type="capability",
        claim={
            "subject": "self-identity",
            "predicate": "probe-evidence",
            "object": "self_identity",
            "verdict": "present",
            "expected_live_evidence": {
                "current_user": current_user,
                "runtime_name": runtime_name,
            },
        },
        scope={"seat": scope_seat} if scope_seat is not None else "global",
        evidence_ref="probe:self_identity",
        verification_method={"type": "probe", "probe": "self_identity", "evidence_ref": "probe:self_identity"},
        state_root=state_root,
        records=records or [],
        write=lambda _path, _text: None,
    )
    return result.record


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


def test_bootstrap_payload_includes_mandatory_foreman_charter_and_worker_spawn(tmp_path: Path):
    state_root = tmp_path / ".ce" / "state"
    _write_ledger(state_root, _records_with_assertions(state_root))

    payload = bootstrap.build_bootstrap_payload(state_root=state_root)

    operating_mode = payload["operating_mode"]
    charter = operating_mode["foreman_charter"]
    dispatch_contract = operating_mode["foreman_dispatch_contract"]
    worker_spawn = operating_mode["capabilities"]["worker_spawn"]
    assert charter["id"] == bootstrap.FOREMAN_CHARTER_ID
    assert charter["mandatory"] is True
    assert charter["enforcement"] == "launcher-injected-non-optional"
    assert "delegate-substantive-implementation-review-and-build-work" in charter["directives"]
    assert dispatch_contract["id"] == bootstrap.FOREMAN_DISPATCH_CONTRACT_ID
    assert dispatch_contract["mandatory"] is True
    assert dispatch_contract["launch_pinned"] is True
    assert set(dispatch_contract["roles"]) == set(bootstrap.REQUIRED_FOREMAN_DISPATCH_ROLES)
    assert worker_spawn["id"] == bootstrap.WORKER_SPAWN_CAPABILITY_ID
    assert worker_spawn["mandatory"] is True
    assert worker_spawn["surface"]["cli"] == "ce worker spawn"
    assert worker_spawn["surface"]["module"] == "creator_engine_validator.worker_spawn"


def test_bootstrap_refuses_malformed_foreman_dispatch_contract(tmp_path: Path, monkeypatch):
    state_root = tmp_path / ".ce" / "state"
    _write_ledger(state_root, _records_with_assertions(state_root))
    malformed = dict(bootstrap.FOREMAN_DISPATCH_CONTRACT)
    malformed["launch_pinned"] = False
    monkeypatch.setattr(bootstrap, "FOREMAN_DISPATCH_CONTRACT", malformed)

    with pytest.raises(bootstrap.BrainBootstrapRefused) as ei:
        bootstrap.build_bootstrap_payload(state_root=state_root)

    assert "foreman_dispatch_contract.launch_pinned must be true" in "\n".join(ei.value.errors)


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


def test_authoritative_correction_is_synced_on_next_bootstrap(tmp_path: Path):
    repo_root = tmp_path / "repo"
    state_root = repo_root / ".ce" / "state"
    asserted = rt.assert_claim(
        assertion_id="brain-assertion-bootstrap-0001",
        claim={"subject": "lane", "predicate": "seat", "object": "worker"},
        scope="global",
        evidence_ref="validators/tests/unit/test_brain_bootstrap.py#original",
        state_root=state_root,
        records=[],
        write=lambda _path, _text: None,
    )
    _write_authoritative_ledger(repo_root, [asserted.record])

    before = bootstrap.build_bootstrap_payload(state_root=state_root)

    correction = rt.correct_claim(
        assertion_id="brain-assertion-bootstrap-0001",
        new_assertion_id="brain-assertion-bootstrap-0004",
        claim={"subject": "lane", "predicate": "seat", "object": "foreman"},
        scope="global",
        evidence_ref="validators/tests/unit/test_brain_bootstrap.py#correction",
        state_root=state_root,
        records=[asserted.record],
        write=lambda _path, _text: None,
    )
    _write_authoritative_ledger(repo_root, [asserted.record, correction.superseded_record, correction.record])

    after = bootstrap.build_bootstrap_payload(state_root=state_root)

    assert before["knowledge_ssot"]["authoritative_loaded"] is True
    assert before["knowledge_ssot"]["assertions"][0]["claim"]["object"] == "worker"
    assert rt.load_records(state_root) == [asserted.record, correction.superseded_record, correction.record]
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


def test_bootstrap_accepts_matching_self_identity_probe_assertion(tmp_path: Path):
    state_root = tmp_path / ".ce" / "state"
    records = [*_records_with_assertions(state_root)]
    self_identity = _self_identity_record(state_root, runtime_name="seat-a", records=records)
    _write_ledger(state_root, [*records, self_identity])

    payload = bootstrap.build_bootstrap_payload(
        state_root=state_root,
        scope={"seat": "controller"},
        probe_context=brain_probe.ProbeContext(
            env={"HOSTNAME": "seat-a", "USER": "controller"},
            run=_probe_runner,
        ),
    )

    ids = [item["id"] for item in payload["knowledge_ssot"]["assertions"]]
    assert "brain-assertion-bootstrap-self-identity" in ids


def test_bootstrap_skips_other_seat_self_identity_drift(tmp_path: Path):
    state_root = tmp_path / ".ce" / "state"
    records = [*_records_with_assertions(state_root)]
    other_seat_identity = _self_identity_record(
        state_root,
        current_user="seat-a",
        runtime_name="seat-a-host",
        scope_seat="seat-a",
        records=records,
    )
    _write_ledger(state_root, [*records, other_seat_identity])

    payload = bootstrap.build_bootstrap_payload(
        state_root=state_root,
        scope={"seat": "seat-b"},
        probe_context=brain_probe.ProbeContext(
            env={"HOSTNAME": "seat-b-host", "USER": "seat-b"},
            run=_probe_runner,
        ),
    )

    ids = [item["id"] for item in payload["knowledge_ssot"]["assertions"]]
    assert "brain-assertion-bootstrap-self-identity" not in ids


def test_global_bootstrap_skips_foreign_self_identity_but_refuses_own_drift(tmp_path: Path):
    state_root = tmp_path / ".ce" / "state"
    records = [*_records_with_assertions(state_root)]
    foreign_identity = _self_identity_record(
        state_root,
        current_user="seat-a",
        runtime_name="seat-a-host",
        scope_seat="seat-a",
        records=records,
    )
    _write_ledger(state_root, [*records, foreign_identity])

    payload = bootstrap.build_bootstrap_payload(
        state_root=state_root,
        scope="global",
        probe_context=brain_probe.ProbeContext(
            env={"HOSTNAME": "seat-b-host", "USER": "seat-b"},
            run=_probe_runner,
        ),
    )

    ids = [item["id"] for item in payload["knowledge_ssot"]["assertions"]]
    assert "brain-assertion-bootstrap-self-identity" not in ids

    own_identity = _self_identity_record(
        state_root,
        assertion_id="brain-assertion-bootstrap-self-identity-seat-b",
        current_user="seat-b",
        runtime_name="seat-b-old-host",
        scope_seat="seat-b",
        records=[*records, foreign_identity],
    )
    _write_ledger(state_root, [*records, foreign_identity, own_identity])

    with pytest.raises(bootstrap.BrainBootstrapRefused) as ei:
        bootstrap.build_bootstrap_payload(
            state_root=state_root,
            scope="global",
            probe_context=brain_probe.ProbeContext(
                env={"HOSTNAME": "seat-b-host", "USER": "seat-b"},
                run=_probe_runner,
            ),
        )

    rendered = "\n".join(ei.value.errors)
    assert "self-identity drift at runtime_name" in rendered
    assert "remembered 'seat-b-old-host', live 'seat-b-host'" in rendered


def test_bootstrap_refuses_mutated_hostname_self_identity_drift(tmp_path: Path, caplog):
    state_root = tmp_path / ".ce" / "state"
    records = [*_records_with_assertions(state_root)]
    self_identity = _self_identity_record(state_root, runtime_name="seat-a", records=records)
    _write_ledger(state_root, [*records, self_identity])

    with pytest.raises(bootstrap.BrainBootstrapRefused) as ei:
        bootstrap.build_bootstrap_payload(
            state_root=state_root,
            scope={"seat": "controller"},
            probe_context=brain_probe.ProbeContext(
                env={"HOSTNAME": "seat-b", "USER": "controller"},
                run=_probe_runner,
            ),
        )

    rendered = "\n".join(ei.value.errors)
    assert "self-identity drift at runtime_name" in rendered
    assert "remembered 'seat-a', live 'seat-b'" in rendered
    assert "brain bootstrap self-identity drift" in caplog.text


def test_bootstrap_refuses_self_identity_verdict_drift(tmp_path: Path):
    state_root = tmp_path / ".ce" / "state"
    records = [*_records_with_assertions(state_root)]
    self_identity = _self_identity_record(state_root, runtime_name="seat-a", records=records)
    _write_ledger(state_root, [*records, self_identity])

    with pytest.raises(bootstrap.BrainBootstrapRefused) as ei:
        bootstrap.build_bootstrap_payload(
            state_root=state_root,
            scope={"seat": "controller"},
            probe_context=brain_probe.ProbeContext(
                probes={
                    "self_identity": lambda _context: brain_probe.ProbeResult(
                        "self_identity",
                        "unknown",
                        {"runtime_name": "seat-a", "os_users": {"current_user": "controller"}},
                    )
                }
            ),
        )

    assert "self-identity verdict drift" in "\n".join(ei.value.errors)
