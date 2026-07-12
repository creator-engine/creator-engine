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
    with pytest.raises(brain_reconcile.BrainReconcileRefused, match="not active"):
        brain_reconcile.plan(repo_root=tmp_path, assertion_ids=_ids(1))
    no_change = brain_reconcile.plan(
        repo_root=tmp_path,
        assertion_ids=[plan["changes"][0]["replacement_id"]],
    )
    assert not no_change["write_required"]


def test_multiple_appends_preserve_exact_ledger_prefix_and_supersede_pairs(tmp_path: Path):
    path, files = _ledger(tmp_path, ["one", "two", "three"])
    files[0].write_text("changed-one", encoding="utf-8")
    files[2].write_text("changed-three", encoding="utf-8")
    before = path.read_bytes()
    original_records = rt.load_records_from_path(path)
    plan = brain_reconcile.plan(repo_root=tmp_path, assertion_ids=[_ids(3)[0], _ids(3)[2]])
    brain_reconcile.apply(repo_root=tmp_path, assertion_ids=[_ids(3)[0], _ids(3)[2]], accept_plan_sha=plan["plan_sha256"])
    after = rt.load_records_from_path(path)
    assert plan["affected_record_count"] == 4
    assert plan["flat_active_count_delta"] == 2
    assert len(after) == len(original_records) + 4
    assert after[:len(original_records)] == original_records
    for change, tombstone, replacement in zip(plan["changes"], after[-4::2], after[-3::2]):
        assert tombstone["id"] == change["id"]
        assert tombstone["status"] == "superseded"
        assert tombstone["superseded_by"] == replacement["id"] == change["replacement_id"]
        assert replacement["status"] == "active"
        assert replacement["claim"]["evidence_sha256"] == change["new_sha256"]


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


def test_refuses_duplicate_unknown_and_ambiguous(tmp_path: Path):
    path, _ = _ledger(tmp_path)
    with pytest.raises(brain_reconcile.BrainReconcileRefused): brain_reconcile.plan(repo_root=tmp_path, assertion_ids=[_ids(1)[0], _ids(1)[0]])
    with pytest.raises(brain_reconcile.BrainReconcileRefused): brain_reconcile.plan(repo_root=tmp_path, assertion_ids=["brain-assertion-unknown-0000"])
    records = rt.load_records_from_path(path)
    records[0]["claim"]["sha256"] = "1" * 64
    records[0]["content_hash"] = rt.canonical_content_hash(records[0])
    path.write_text(rt.serialize_ledger(records), encoding="utf-8")
    with pytest.raises(brain_reconcile.BrainReconcileRefused): brain_reconcile.plan(repo_root=tmp_path, assertion_ids=_ids(1))


def test_refuses_inactive_assertion(tmp_path: Path):
    _path, files = _ledger(tmp_path)
    files[0].write_text("changed", encoding="utf-8")
    initial = brain_reconcile.plan(repo_root=tmp_path, assertion_ids=_ids(1))
    brain_reconcile.apply(repo_root=tmp_path, assertion_ids=_ids(1), accept_plan_sha=initial["plan_sha256"])
    with pytest.raises(brain_reconcile.BrainReconcileRefused, match="not active"):
        brain_reconcile.plan(repo_root=tmp_path, assertion_ids=_ids(1))


def test_refuses_non_static_assertion(tmp_path: Path):
    path, _files = _ledger(tmp_path)
    records = rt.load_records_from_path(path)
    records[0]["verification_method"] = {"type": "probe", "probe": "self_identity"}
    records[0]["evidence_ref"] = "probe:self_identity"
    records[0]["content_hash"] = rt.canonical_content_hash(records[0])
    path.write_text(rt.serialize_ledger(records), encoding="utf-8")
    with pytest.raises(brain_reconcile.BrainReconcileRefused, match="not static evidence"):
        brain_reconcile.plan(repo_root=tmp_path, assertion_ids=_ids(1))


def test_apply_verifies_only_selected_static_replacements(tmp_path: Path, monkeypatch):
    _path, files = _ledger(tmp_path)
    files[0].write_text("changed", encoding="utf-8")
    current = brain_reconcile.plan(repo_root=tmp_path, assertion_ids=_ids(1))
    monkeypatch.setattr(
        brain_reconcile.ce_brain_drift,
        "verify_state_root",
        lambda *_args, **_kwargs: pytest.fail("reconcile must not live-probe unrelated active assertions"),
    )
    result = brain_reconcile.apply(
        repo_root=tmp_path,
        assertion_ids=_ids(1),
        accept_plan_sha=current["plan_sha256"],
    )
    assert result.written


def test_apply_preserves_primary_error_when_rollback_fails(tmp_path: Path, monkeypatch):
    path, files = _ledger(tmp_path)
    files[0].write_text("changed", encoding="utf-8")
    current = brain_reconcile.plan(repo_root=tmp_path, assertion_ids=_ids(1))
    original_write = brain_reconcile._atomic_write
    calls = 0

    def fail_rollback(target: Path, text: str) -> None:
        nonlocal calls
        calls += 1
        if calls == 1:
            original_write(target, text)
            return
        raise OSError("rollback unavailable")

    monkeypatch.setattr(brain_reconcile, "_atomic_write", fail_rollback)
    monkeypatch.setattr(brain_reconcile, "_verify_replacements", lambda **_kwargs: (_ for _ in ()).throw(RuntimeError("primary failure")))
    with pytest.raises(RuntimeError, match="primary failure"):
        brain_reconcile.apply(
            repo_root=tmp_path,
            assertion_ids=_ids(1),
            accept_plan_sha=current["plan_sha256"],
        )
    assert calls == 2
