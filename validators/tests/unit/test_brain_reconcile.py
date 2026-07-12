from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

import pytest

from creator_engine_validator import brain_reconcile, brain_runtime as rt


def _ledger(repo: Path, values: list[str] = ["old"]) -> tuple[Path, list[Path]]:
    files: list[Path] = []
    records: list[dict] = []
    for index, value in enumerate(values):
        evidence = repo / f"evidence-{index}.txt"
        evidence.write_text(value, encoding="utf-8")
        files.append(evidence)
        captured: list[tuple[Path, str]] = []
        rt.assert_claim(
            assertion_id=f"brain-assertion-reconcile-{index:04d}",
            claim={"subject": "artifact", "predicate": "hash", "object": evidence.name,
                   "evidence_sha256": hashlib.sha256(value.encode()).hexdigest()},
            scope="test", evidence_ref=evidence.name,
            verification_method={"type": "static", "evidence_ref": evidence.name},
            state_root=repo / ".ce", records=records,
            write=lambda path, text: captured.append((path, text)),
        )
        path, text = captured[-1]
        records = rt.load_ledger_text(text)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(rt.serialize_ledger(records), encoding="utf-8")
    return path, files


def _ids(amount: int) -> list[str]:
    return [f"brain-assertion-reconcile-{index:04d}" for index in range(amount)]


def test_plan_is_stable_read_only_and_json_shaped(tmp_path: Path):
    path, files = _ledger(tmp_path)
    files[0].write_text("changed", encoding="utf-8")
    before = path.read_bytes()
    first = brain_reconcile.plan(repo_root=tmp_path, assertion_ids=_ids(1))
    second = brain_reconcile.plan(repo_root=tmp_path, assertion_ids=_ids(1))
    assert first == second
    assert first["write_required"] is True
    assert first["plan_sha256"] == hashlib.sha256(
        json.dumps({key: value for key, value in first.items() if key != "plan_sha256"}, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    assert path.read_bytes() == before


def test_apply_requires_exact_digest_and_is_idempotent(tmp_path: Path):
    path, files = _ledger(tmp_path)
    files[0].write_text("changed", encoding="utf-8")
    plan = brain_reconcile.plan(repo_root=tmp_path, assertion_ids=_ids(1))
    with pytest.raises(brain_reconcile.BrainReconcileRefused):
        brain_reconcile.apply(repo_root=tmp_path, assertion_ids=_ids(1), accept_plan_sha="0" * 64)
    result = brain_reconcile.apply(repo_root=tmp_path, assertion_ids=_ids(1), accept_plan_sha=plan["plan_sha256"])
    assert result.written and result.persisted_sha256 == hashlib.sha256(path.read_bytes()).hexdigest()
    assert os.stat(path).st_mode & 0o777 == 0o600
    no_change = brain_reconcile.plan(repo_root=tmp_path, assertion_ids=_ids(1))
    assert not no_change["write_required"]


def test_multiple_readdresses_downstream_and_preserves_semantics(tmp_path: Path):
    path, files = _ledger(tmp_path, ["one", "two", "three"])
    files[0].write_text("changed-one", encoding="utf-8")
    files[2].write_text("changed-three", encoding="utf-8")
    before = rt.load_records_from_path(path)
    plan = brain_reconcile.plan(repo_root=tmp_path, assertion_ids=[_ids(3)[0], _ids(3)[2]])
    brain_reconcile.apply(repo_root=tmp_path, assertion_ids=[_ids(3)[0], _ids(3)[2]], accept_plan_sha=plan["plan_sha256"])
    after = rt.load_records_from_path(path)
    assert plan["affected_record_count"] == 3
    for index, record in enumerate(after):
        assert {key: value for key, value in record.items() if key not in {"claim", "prev_hash", "content_hash"}} == {key: value for key, value in before[index].items() if key not in {"claim", "prev_hash", "content_hash"}}
    assert after[1]["prev_hash"] == after[0]["content_hash"]


@pytest.mark.parametrize("bad", ["../outside", "/tmp/outside", "https://example.invalid/e", "missing.txt"])
def test_refuses_unsafe_or_missing_evidence(tmp_path: Path, bad: str):
    path, _ = _ledger(tmp_path)
    records = rt.load_records_from_path(path)
    records[0]["evidence_ref"] = bad
    records[0]["verification_method"]["evidence_ref"] = bad
    records[0]["content_hash"] = rt.canonical_content_hash(records[0])
    path.write_text(rt.serialize_ledger(records), encoding="utf-8")
    with pytest.raises(brain_reconcile.BrainReconcileRefused):
        brain_reconcile.plan(repo_root=tmp_path, assertion_ids=_ids(1))


def test_refuses_duplicate_unknown_inactive_and_ambiguous(tmp_path: Path):
    path, _ = _ledger(tmp_path)
    with pytest.raises(brain_reconcile.BrainReconcileRefused): brain_reconcile.plan(repo_root=tmp_path, assertion_ids=[_ids(1)[0], _ids(1)[0]])
    with pytest.raises(brain_reconcile.BrainReconcileRefused): brain_reconcile.plan(repo_root=tmp_path, assertion_ids=["brain-assertion-unknown-0000"])
    records = rt.load_records_from_path(path)
    records[0]["claim"]["sha256"] = "1" * 64
    records[0]["content_hash"] = rt.canonical_content_hash(records[0])
    path.write_text(rt.serialize_ledger(records), encoding="utf-8")
    with pytest.raises(brain_reconcile.BrainReconcileRefused): brain_reconcile.plan(repo_root=tmp_path, assertion_ids=_ids(1))
