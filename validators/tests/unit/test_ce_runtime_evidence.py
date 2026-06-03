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
