"""Unit tests for the v3 G-1.3a runtime-evidence spine substrate + dogfood check.

The spine (``runtime_evidence_spine.append`` / ``verify_chain``) is PURE — these
tests perform ZERO live subprocess and write nothing to disk (the G-1.2 no-live
discipline). The ``ce_runtime_evidence`` check validates static chain files
against the schema + tamper-evidence predicates, reusing the spine semantics.
"""

import socket
import subprocess
from pathlib import Path

import yaml

from creator_engine_validator.checks import registered_checks
from creator_engine_validator.checks.ce_runtime_evidence import (
    CHECK_NAME,
    CODE_CHAIN_LINK,
    CODE_CONTENT_ADDRESS,
    CODE_POLICY_UNBOUND,
    CODE_SCHEMA,
    CODE_SEQUENCE,
    run,
    validate_runtime_evidence_chain,
)
from creator_engine_validator.runtime_evidence_spine import (
    CHAIN_KIND,
    GENESIS_PREV_HASH,
    RATIFICATION_RECORD_KIND,
    RATIFICATION_RECORD_TYPE,
    RUN_OUTCOME_RECORD_KIND,
    RUN_OUTCOME_RECORD_TYPE,
    RUN_OUTCOMES,
    append,
    canonical_content_hash,
    is_policy_sha,
    verify_chain,
)

_POLICY = "1" * 64
_PHASES = ("provision", "run", "collect", "teardown")


def _body(phase: str = "provision", classification: str = "allowed", policy: str = _POLICY) -> dict:
    # ``recorded_at`` is deliberately not ISO-timestamp-shaped so a yaml
    # round-trip (safe_dump/safe_load) does not coerce it to a datetime.
    return {
        "kind": "runtime-evidence-record",
        "record_type": "runtime_evidence",
        "schema_version": "1",
        "policy_sha": policy,
        "run_id": "run-implementer-0001",
        "lifecycle_phase": phase,
        "classification": classification,
        "recorded_at": "t0",
        "backend_key": "gvisor-proxy",
    }


def _good_chain(n: int = 3) -> list[dict]:
    chain: list[dict] = []
    for i in range(n):
        chain.append(append(chain, _body(phase=_PHASES[i % len(_PHASES)])))
    return chain


def _kinds(findings) -> list[str]:
    return [f.kind for f in findings]


def _codes(errors) -> set[str]:
    return {e.code for e in errors}


def _chain_file(records: list[dict]) -> dict:
    return {
        "kind": CHAIN_KIND,
        "record_type": "runtime_evidence_chain",
        "schema_version": "1",
        "records": records,
    }


def _outcome_body(outcome: str = "pr_opened", policy: str = _POLICY) -> dict:
    # A G-3.6a typed terminal run-OUTCOME record: no lifecycle_phase; carries the
    # plural ``outcome`` + a value-free ``change_set`` pointer.
    return {
        "kind": RUN_OUTCOME_RECORD_KIND,
        "record_type": RUN_OUTCOME_RECORD_TYPE,
        "schema_version": "1",
        "policy_sha": policy,
        "run_id": "run-implementer-0001",
        "recorded_at": "t9",
        "outcome": outcome,
        "change_set": {
            "branch": "ce/run-implementer-0001",
            "base": "main",
            "manifest_paths": ["a.py"],
            "head_sha": "d" * 40,
        },
    }


def _chain_with_outcome(outcome: str = "pr_opened") -> dict:
    chain: list[dict] = []
    for phase in ("provision", "run", "collect"):
        chain.append(append(chain, _body(phase=phase)))
    chain.append(append(chain, _outcome_body(outcome=outcome)))
    return _chain_file(chain)


# ---------------------------------------------------------------------------
# G-3.6a — typed run-outcome record (orthogonal to lifecycle_phase)
# ---------------------------------------------------------------------------
def test_chain_with_typed_run_outcome_record_validates_clean():
    """A terminal ``runtime_run_outcome`` record is schema-valid + chain-clean."""
    doc = _chain_with_outcome("pr_opened")
    errors = validate_runtime_evidence_chain(doc, Path("outcome-chain.yml"))
    assert errors == []
    assert verify_chain(doc["records"]) == []
    tail = doc["records"][-1]
    assert tail["record_type"] == RUN_OUTCOME_RECORD_TYPE
    assert "lifecycle_phase" not in tail


def test_run_outcome_with_bad_outcome_value_is_schema_violation():
    """A run-outcome record whose ``outcome`` is not in the enum fails the schema."""
    doc = _chain_with_outcome("not-a-real-outcome")
    errors = validate_runtime_evidence_chain(doc, Path("bad-outcome.yml"))
    assert CODE_SCHEMA in _codes(errors)


# ---------------------------------------------------------------------------
# G-3.7b.0 — the pr_merged run-outcome MODEL (additive vocabulary; producer-less
# until G-3.7b.1; the live merge is G-3.8).
# ---------------------------------------------------------------------------
def test_pr_merged_is_in_run_outcomes_vocabulary():
    """``pr_merged`` is a first-class run-outcome member (the gated-merge disposition)."""
    assert "pr_merged" in RUN_OUTCOMES


def test_chain_with_pr_merged_outcome_validates_clean():
    """A terminal ``runtime_run_outcome`` record with ``outcome: pr_merged`` is schema-valid + chain-clean."""
    doc = _chain_with_outcome("pr_merged")
    errors = validate_runtime_evidence_chain(doc, Path("pr-merged-chain.yml"))
    assert errors == []
    assert verify_chain(doc["records"]) == []
    tail = doc["records"][-1]
    assert tail["record_type"] == RUN_OUTCOME_RECORD_TYPE
    assert tail["outcome"] == "pr_merged"
    assert "lifecycle_phase" not in tail  # an outcome is NEVER a container phase


# ---------------------------------------------------------------------------
# F6 Phase-0 — typed change-restamp + merge-audit records (additive; orthogonal)
# ---------------------------------------------------------------------------
def _restamp_body(policy: str = _POLICY, **over) -> dict:
    body = {
        "kind": "runtime-change-restamp",
        "record_type": "runtime_change_restamp",
        "schema_version": "1",
        "policy_sha": policy,
        "run_id": "run-implementer-0001",
        "recorded_at": "t7",
        "restamp_type": "base_only",
        "authority": "machine_rebase_equivalence",
        "pr_number": 123,
        "branch": "ce/run-implementer-0001",
        "base": "main",
        "old_base_sha": "a" * 40,
        "old_head_sha": "d" * 40,
        "new_base_sha": "b" * 40,
        "new_head_sha": "c" * 40,
        "manifest_paths_sha256": "1" * 64,
        "old_content_diff_id": "2" * 64,
        "new_content_diff_id": "2" * 64,
        "old_patch_id": "e" * 40,
        "new_patch_id": "e" * 40,
        "proof_inputs_sha256": "3" * 64,
    }
    body.update(over)
    return body


def _audit_body(policy: str = _POLICY, **over) -> dict:
    body = {
        "kind": "runtime-merge-audit",
        "record_type": "runtime_merge_audit",
        "schema_version": "1",
        "policy_sha": policy,
        "run_id": "run-implementer-0001",
        "recorded_at": "t8",
        "pr_number": 123,
        "tested_head_sha": "c" * 40,
        "tested_tree_sha": "a" * 40,
        "merge_method": "squash",
        "merge_commit_sha": "f" * 40,
        "merged_tree_sha": "a" * 40,
        "tree_equivalence": True,
    }
    body.update(over)
    return body


def _chain_with_restamp_and_audit() -> dict:
    chain: list[dict] = []
    for phase in ("provision", "run", "collect"):
        chain.append(append(chain, _body(phase=phase)))
    chain.append(append(chain, _outcome_body(outcome="pr_opened")))
    chain.append(append(chain, _restamp_body()))
    chain.append(append(chain, _outcome_body(outcome="pr_merged")))
    chain.append(append(chain, _audit_body()))
    return _chain_file(chain)


def test_chain_with_restamp_and_audit_validates_clean():
    """The full F6 base-only re-stamp chain (pr_opened → restamp → pr_merged → audit) is clean."""
    doc = _chain_with_restamp_and_audit()
    errors = validate_runtime_evidence_chain(doc, Path("restamp-chain.yml"))
    assert errors == []
    assert verify_chain(doc["records"]) == []
    restamp = next(r for r in doc["records"] if r["record_type"] == "runtime_change_restamp")
    audit = next(r for r in doc["records"] if r["record_type"] == "runtime_merge_audit")
    assert "lifecycle_phase" not in restamp and "lifecycle_phase" not in audit
    assert restamp["authority"] == "machine_rebase_equivalence"
    assert audit["tree_equivalence"] is True


def test_restamp_bad_restamp_type_is_schema_violation():
    chain = [append([], _restamp_body(restamp_type="content_amendment"))]
    assert CODE_SCHEMA in _codes(validate_runtime_evidence_chain(_chain_file(chain), Path("b.yml")))


def test_restamp_bad_authority_is_schema_violation():
    chain = [append([], _restamp_body(authority="operator_override"))]
    assert CODE_SCHEMA in _codes(validate_runtime_evidence_chain(_chain_file(chain), Path("b.yml")))


def test_restamp_missing_proof_field_is_schema_violation():
    body = _restamp_body()
    del body["proof_inputs_sha256"]
    assert CODE_SCHEMA in _codes(validate_runtime_evidence_chain(_chain_file([append([], body)]), Path("b.yml")))


def test_merge_audit_non_squash_method_is_schema_violation():
    chain = [append([], _audit_body(merge_method="merge"))]
    assert CODE_SCHEMA in _codes(validate_runtime_evidence_chain(_chain_file(chain), Path("b.yml")))


def test_merge_audit_tree_mismatch_validates_but_records_false():
    # A false tree_equivalence is a valid (alarm) record — the schema admits it; semantics flag it.
    doc = _chain_file([append([], _audit_body(tree_equivalence=False, merged_tree_sha="b" * 40))])
    assert validate_runtime_evidence_chain(doc, Path("mismatch.yml")) == []
    assert doc["records"][0]["tree_equivalence"] is False


def test_restamp_tamper_breaks_content_address():
    chain = _chain_with_restamp_and_audit()["records"]
    chain[4]["new_head_sha"] = "9" * 40  # mutate the persisted restamp record after hashing
    assert any(f.kind == "content_address" for f in verify_chain(chain))


# ---------------------------------------------------------------------------
# G-3.7.2a — typed ratification record (value-free; NEVER a lifecycle_phase)
# ---------------------------------------------------------------------------
def _ratification_body(
    policy: str = _POLICY,
    approver_ref: str = "2" * 64,
    prompt_sha: str = "3" * 64,
    binding_ref: str = "4" * 64,
    head_sha: str = "d" * 40,
) -> dict:
    # A value-free ratification attestation: only opaque hashes + a git head SHA +
    # run/policy ids. NO raw account / host / credential / installation identifier.
    return {
        "kind": RATIFICATION_RECORD_KIND,
        "record_type": RATIFICATION_RECORD_TYPE,
        "schema_version": "1",
        "policy_sha": policy,
        "run_id": "run-implementer-0001",
        "recorded_at": "t1",
        "ratified_prompt_sha": prompt_sha,
        "approver_ref": approver_ref,
        "ratified_head_sha": head_sha,
        "binding_ref": binding_ref,
    }


def _chain_with_ratification(**over) -> dict:
    # Ratification is genesis (it authorizes the run), then a lifecycle record follows.
    chain: list[dict] = [append([], _ratification_body(**over))]
    chain.append(append(chain, _body(phase="provision")))
    return _chain_file(chain)


def test_chain_with_ratification_record_validates_clean():
    """A typed ``runtime_ratification`` record is schema-valid + chain-clean."""
    doc = _chain_with_ratification()
    errors = validate_runtime_evidence_chain(doc, Path("ratification-chain.yml"))
    assert errors == []
    assert verify_chain(doc["records"]) == []
    genesis = doc["records"][0]
    assert genesis["record_type"] == RATIFICATION_RECORD_TYPE
    assert "lifecycle_phase" not in genesis  # ratification is NOT a lifecycle phase


def test_ratification_example_file_validates_clean():
    """The shipped well-formed ratification example passes the check (check-examples)."""
    example = (
        Path(__file__).resolve().parents[3]
        / "examples"
        / "well-formed"
        / "runtime-evidence"
        / "example-runtime-evidence-chain-ratified.yml"
    )
    data = yaml.safe_load(example.read_text(encoding="utf-8"))
    assert validate_runtime_evidence_chain(data, example) == []


def test_ratification_missing_approver_ref_is_schema_violation():
    body = _ratification_body()
    del body["approver_ref"]
    doc = _chain_file([append([], body)])
    assert CODE_SCHEMA in _codes(validate_runtime_evidence_chain(doc, Path("bad.yml")))


def test_ratification_non_hex_approver_ref_is_schema_violation():
    doc = _chain_with_ratification(approver_ref="chmod735")  # a raw account, not an opaque digest
    assert CODE_SCHEMA in _codes(validate_runtime_evidence_chain(doc, Path("bad.yml")))


def test_ratification_non_hex_prompt_sha_is_schema_violation():
    doc = _chain_with_ratification(prompt_sha="not-a-64-hex-digest")
    assert CODE_SCHEMA in _codes(validate_runtime_evidence_chain(doc, Path("bad.yml")))


def test_ratification_spine_constants():
    assert RATIFICATION_RECORD_KIND == "runtime-ratification"
    assert RATIFICATION_RECORD_TYPE == "runtime_ratification"


# ---------------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------------
def test_check_registered():
    checks = registered_checks()
    assert CHECK_NAME in checks
    frs = checks[CHECK_NAME].frs
    assert CODE_SCHEMA in frs
    assert CODE_CONTENT_ADDRESS in frs
    assert CODE_CHAIN_LINK in frs
    assert CODE_SEQUENCE in frs
    assert CODE_POLICY_UNBOUND in frs


# ---------------------------------------------------------------------------
# Substrate — append
# ---------------------------------------------------------------------------
def test_append_genesis_sets_sentinel_and_sequence_zero():
    r0 = append([], _body())
    assert r0["sequence"] == 0
    assert r0["prev_hash"] == GENESIS_PREV_HASH
    assert r0["content_hash"] == canonical_content_hash(r0)


def test_append_links_to_prior_content_hash():
    chain = [append([], _body())]
    r1 = append(chain, _body(phase="teardown"))
    assert r1["sequence"] == 1
    assert r1["prev_hash"] == chain[-1]["content_hash"]
    assert r1["content_hash"] == canonical_content_hash(r1)


def test_append_is_pure_does_not_mutate_inputs():
    chain = [append([], _body())]
    chain_snapshot = [dict(record) for record in chain]
    body = _body(phase="run")
    body_snapshot = dict(body)
    append(chain, body)
    assert chain == chain_snapshot
    assert body == body_snapshot  # no sequence/prev_hash/content_hash leaked back


def test_canonical_content_hash_excludes_content_hash_and_is_deterministic():
    r0 = append([], _body())
    baseline = canonical_content_hash(r0)
    mutated_hash_only = dict(r0)
    mutated_hash_only["content_hash"] = "f" * 64  # excluded from the material
    assert canonical_content_hash(mutated_hash_only) == baseline
    assert canonical_content_hash(dict(r0)) == baseline  # deterministic


# ---------------------------------------------------------------------------
# Substrate — verify_chain (reorder / truncation / mutation / link / binding)
# ---------------------------------------------------------------------------
def test_verify_chain_clean():
    assert verify_chain(_good_chain(3)) == []


def test_verify_chain_detects_mutation():
    chain = _good_chain(2)
    chain[1] = {**chain[1], "classification": "denied"}  # content_hash now stale
    assert "content_address" in _kinds(verify_chain(chain))


def test_verify_chain_detects_truncation():
    chain = _good_chain(3)
    del chain[1]  # sequences become 0, 2 — a gap
    assert "sequence" in _kinds(verify_chain(chain))


def test_verify_chain_detects_reorder():
    chain = _good_chain(3)
    chain[1], chain[2] = chain[2], chain[1]
    kinds = _kinds(verify_chain(chain))
    assert "sequence" in kinds or "chain_link" in kinds


def test_verify_chain_detects_broken_link():
    chain = _good_chain(2)
    bad = dict(chain[1])
    bad["prev_hash"] = "d" * 64
    bad["content_hash"] = canonical_content_hash(bad)  # internally consistent
    chain[1] = bad
    assert _kinds(verify_chain(chain)) == ["chain_link"]


def test_verify_chain_detects_genesis_sentinel_violation():
    bad = dict(_good_chain(1)[0])
    bad["prev_hash"] = "e" * 64
    bad["content_hash"] = canonical_content_hash(bad)
    assert _kinds(verify_chain([bad])) == ["chain_link"]


def test_verify_chain_detects_policy_unbound():
    chain = [append([], _body(policy="not-a-sha"))]
    assert "policy_unbound" in _kinds(verify_chain(chain))


def test_verify_chain_never_raises_on_non_mapping():
    findings = verify_chain(["nope"])
    assert findings and findings[0].kind == "content_address"


def test_is_policy_sha():
    assert is_policy_sha("a" * 64)
    assert not is_policy_sha("A" * 64)  # uppercase is not allowed
    assert not is_policy_sha("a" * 63)
    assert not is_policy_sha(None)
    assert not is_policy_sha(123)


# ---------------------------------------------------------------------------
# Purity guards — no live runtime, no disk write
# ---------------------------------------------------------------------------
def test_spine_makes_no_subprocess_or_socket(monkeypatch):
    def explode(*args, **kwargs):  # pragma: no cover - must never run
        raise AssertionError("the pure evidence spine must not touch a live runtime")

    monkeypatch.setattr(subprocess, "run", explode)
    monkeypatch.setattr(subprocess, "Popen", explode)
    monkeypatch.setattr(socket, "socket", explode)
    chain = _good_chain(3)
    assert verify_chain(chain) == []


def test_spine_writes_no_files(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    chain = _good_chain(3)
    verify_chain(chain)
    canonical_content_hash(chain[0])
    assert list(tmp_path.iterdir()) == []


# ---------------------------------------------------------------------------
# Check — validate_runtime_evidence_chain + run()
# ---------------------------------------------------------------------------
def test_check_well_formed_chain_passes(tmp_path):
    assert validate_runtime_evidence_chain(_chain_file(_good_chain(2)), tmp_path / "c.yml") == []


def test_check_flags_schema_violation_missing_records(tmp_path):
    bad = {"kind": CHAIN_KIND, "record_type": "runtime_evidence_chain", "schema_version": "1"}
    assert CODE_SCHEMA in _codes(validate_runtime_evidence_chain(bad, tmp_path / "c.yml"))


def test_check_flags_chain_link_only(tmp_path):
    chain = _good_chain(2)
    bad = dict(chain[1])
    bad["prev_hash"] = "d" * 64
    bad["content_hash"] = canonical_content_hash(bad)
    chain[1] = bad
    assert _codes(validate_runtime_evidence_chain(_chain_file(chain), tmp_path / "c.yml")) == {CODE_CHAIN_LINK}


def test_check_flags_policy_unbound(tmp_path):
    chain = [append([], _body(policy="0000"))]
    assert CODE_POLICY_UNBOUND in _codes(validate_runtime_evidence_chain(_chain_file(chain), tmp_path / "c.yml"))


def test_run_passes_well_formed_written_chain(tmp_path):
    path = tmp_path / "good.yml"
    path.write_text(yaml.safe_dump(_chain_file(_good_chain(2))), encoding="utf-8")
    result = run([path])
    assert result.ok
    assert result.name == CHECK_NAME


def test_run_flags_written_malformed_chain(tmp_path):
    chain = _good_chain(2)
    bad = dict(chain[1])
    bad["prev_hash"] = "d" * 64
    bad["content_hash"] = canonical_content_hash(bad)
    chain[1] = bad
    path = tmp_path / "bad.yml"
    path.write_text(yaml.safe_dump(_chain_file(chain)), encoding="utf-8")
    result = run([path])
    assert not result.ok
    assert CODE_CHAIN_LINK in _codes(result.errors)


def test_run_ignores_non_evidence_yaml(tmp_path):
    path = tmp_path / "other.yml"
    path.write_text(yaml.safe_dump({"kind": "runtime-policy-record"}), encoding="utf-8")
    result = run([path])
    assert result.ok  # not a runtime-evidence-chain → not a candidate
