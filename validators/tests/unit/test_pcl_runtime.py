"""Unit tests for the G2.004.1 PCL runtime (RV2-004-runtime).

Drives ``creator_engine_validator.pcl_runtime`` directly. Asserts:

* ``append`` builds a genesis record (``sequence 0`` / ``parent_hash null``) and a
  linked record (``parent_hash`` = prior ``content_hash``) under the **tracked**
  ``records/<ledger>/`` home, with a monotonic sequence and an agreeing head;
* the runtime ``content_hash`` is byte-identical to the G2.004.0 ``pcl_record``
  canonical-hash rule, and a produced record passes the unchanged validator;
* every refusal (role floor, unknown mode, unknown record_kind, ``.hermes`` record
  root / body write-freeze, non-reserved signature value) raises **before any
  write**, leaving the records dir byte-identical;
* ``verify`` accepts a good chain and rejects forged hashes / broken links;
* ``replay`` / ``index`` are deterministic; the ``index``/``merge`` cache must be
  git-ignored when inside a repo while records stay tracked;
* ``merge`` deterministically unions verified ledgers and fails closed on a fork;
* the runtime imports no CE-event or distributed-identity code (decoupling).
"""
from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from creator_engine_validator import pcl_runtime as rt
from creator_engine_validator.checks import pcl_record as pcl_check

RECORDED = "2026-05-31T16:48:41Z"


def _pcl_root(tmp_path: Path) -> Path:
    root = tmp_path / ".ce" / "pcl"
    (root / "records").mkdir(parents=True, exist_ok=True)
    return root


def _body(**override) -> dict:
    base = {"lane_id": "g20041-pcl-runtime", "summary": "unit"}
    base.update(override)
    return base


def _append(root: Path, seq: int, *, ledger: str = "demo", **override) -> rt.AppendResult:
    kwargs = dict(
        ledger=ledger,
        pcl_root=root,
        record_id=f"pcl-demo-{seq:04d}",
        record_kind="lane_claim",
        emitting_role="controller",
        operating_mode="strict",
        body=_body(),
        recorded_at=RECORDED,
    )
    kwargs.update(override)
    return rt.append(**kwargs)


def _ledger_dir(root: Path, ledger: str = "demo") -> Path:
    return root / "records" / ledger


def _snapshot(root: Path) -> dict[str, bytes]:
    return {p.relative_to(root).as_posix(): p.read_bytes() for p in sorted(root.rglob("*")) if p.is_file()}


# --- append: chain construction ---------------------------------------------
def test_genesis_append_is_sequence_zero_with_null_parent(tmp_path):
    root = _pcl_root(tmp_path)
    result = _append(root, 0)
    assert result.sequence == 0
    assert result.parent_hash is None
    assert result.record["parent_hash"] is None
    assert result.record_path.is_file()
    assert result.record_path.parent == _ledger_dir(root)


def test_linked_append_links_parent_hash_and_advances_sequence(tmp_path):
    root = _pcl_root(tmp_path)
    genesis = _append(root, 0)
    linked = _append(root, 1)
    assert linked.sequence == 1
    assert linked.parent_hash == genesis.content_hash
    assert linked.record["parent_hash"] == genesis.content_hash


def test_head_manifest_agrees_with_last_record(tmp_path):
    root = _pcl_root(tmp_path)
    _append(root, 0)
    linked = _append(root, 1)
    head = json.loads(linked.head_path.read_text(encoding="utf-8"))
    assert head["sequence"] == 1
    assert head["head_content_hash"] == linked.content_hash
    assert head["record_count"] == 2


def test_content_hash_matches_record_substrate_canonical_rule(tmp_path):
    root = _pcl_root(tmp_path)
    result = _append(root, 0)
    assert result.content_hash == pcl_check._canonical_hash(result.record)
    assert result.record["content_hash"] == result.content_hash


def test_produced_record_has_reserved_inactive_signature(tmp_path):
    root = _pcl_root(tmp_path)
    sig = _append(root, 0).record["signature"]
    assert sig["scheme"] == "reserved-shape-only"
    assert sig["value"] == "reserved-inactive"
    assert sig["key_id"]


def test_produced_record_passes_unchanged_validator(tmp_path):
    """Backward-compat canary: a runtime record is accepted by the G2.004.0 check."""
    root = _pcl_root(tmp_path)
    result = _append(root, 0)
    scope = tmp_path / "pcl-record"
    scope.mkdir()
    path = scope / "produced.ce.yml"
    path.write_text(json.dumps({"pcl_record": result.record}), encoding="utf-8")
    errors = pcl_check.validate_file(path)
    assert errors == [], [e.format() for e in errors]


def test_event_block_pointer_append_requires_opaque_hash(tmp_path):
    root = _pcl_root(tmp_path)
    good = "a" * 64
    res = _append(root, 0, record_kind="event_block_pointer", body={"ce_event_content_hash": good, "stream": "x"})
    assert res.record["record_kind"] == "event_block_pointer"
    with pytest.raises(rt.PclAppendError):
        _append(root, 1, record_kind="event_block_pointer", body={"ce_event_content_hash": "not-a-hash"})


# --- append: fail-closed refusals (no write) --------------------------------
@pytest.mark.parametrize(
    "override, exc",
    [
        ({"emitting_role": "agent_ratifier"}, rt.RoleFloorRefused),
        ({"emitting_role": "source"}, rt.RoleFloorRefused),
        ({"operating_mode": "permissive"}, rt.ModeInvalid),
        ({"record_kind": "frobnicate"}, rt.RecordKindInvalid),
        ({"signature_value": "active-bound"}, rt.SignatureReserved),
        ({"body": {"lane_id": "x", "target": ".hermes/pcl/foo"}}, rt.WriteFreezeRefused),
    ],
)
def test_append_refusals_raise_before_any_write(tmp_path, override, exc):
    root = _pcl_root(tmp_path)
    before = _snapshot(root)
    with pytest.raises(exc):
        _append(root, 0, **override)
    assert _snapshot(root) == before  # byte-identical: nothing was written


def test_append_under_legacy_hermes_root_is_write_frozen(tmp_path):
    bad_root = tmp_path / ".hermes" / "pcl"
    (bad_root / "records").mkdir(parents=True)
    with pytest.raises(rt.WriteFreezeRefused):
        _append(bad_root, 0)


# --- verify -----------------------------------------------------------------
def test_verify_accepts_good_chain(tmp_path):
    root = _pcl_root(tmp_path)
    _append(root, 0)
    _append(root, 1)
    result = rt.verify(ledger="demo", pcl_root=root)
    assert result.ok, result.errors
    assert result.summary["record_count"] == 2


def test_verify_rejects_forged_content_hash(tmp_path):
    root = _pcl_root(tmp_path)
    res = _append(root, 0)
    tampered = json.loads(res.record_path.read_text())
    tampered["content_hash"] = "0" * 64
    res.record_path.write_text(json.dumps(tampered, indent=2) + "\n", encoding="utf-8")
    result = rt.verify(ledger="demo", pcl_root=root)
    assert not result.ok
    assert any("VAL-PCL-CONTENT-ADDRESS" in e for e in result.errors)


def test_verify_rejects_broken_chain_link(tmp_path):
    root = _pcl_root(tmp_path)
    _append(root, 0)
    res1 = _append(root, 1)
    tampered = json.loads(res1.record_path.read_text())
    tampered["parent_hash"] = "f" * 64
    tampered["content_hash"] = pcl_check._canonical_hash({k: v for k, v in tampered.items() if k not in {"content_hash", "signature"}})
    res1.record_path.write_text(json.dumps(tampered, indent=2) + "\n", encoding="utf-8")
    result = rt.verify(ledger="demo", pcl_root=root)
    assert not result.ok
    assert any("VAL-PCL-CHAIN-LINK" in e for e in result.errors)


def test_verify_missing_ledger_is_not_ok(tmp_path):
    root = _pcl_root(tmp_path)
    result = rt.verify(ledger="nope", pcl_root=root)
    assert not result.ok


# --- replay / index ---------------------------------------------------------
def test_replay_is_deterministic(tmp_path):
    root = _pcl_root(tmp_path)
    _append(root, 0)
    _append(root, 1)
    a = rt.replay(ledger="demo", pcl_root=root)
    b = rt.replay(ledger="demo", pcl_root=root)
    assert a.content_hash == b.content_hash
    assert a.projection["record_count"] == 2


def test_index_is_deterministic_and_counts_kinds(tmp_path):
    root = _pcl_root(tmp_path)
    _append(root, 0, record_kind="gate_opened")
    _append(root, 1, record_kind="lane_claim")
    a = rt.index(ledger="demo", pcl_root=root, write_cache=False)
    b = rt.index(ledger="demo", pcl_root=root, write_cache=False)
    assert a.content_hash == b.content_hash
    assert a.index["record_count"] == 2
    assert a.index["record_kind_counts"]["gate_opened"] == 1


# --- cache git-ignore guard (records tracked / cache ignored) ---------------
def _git(repo: Path, *argv: str) -> None:
    subprocess.run(["git", "-C", str(repo), *argv], check=True, capture_output=True, text=True)


def test_index_cache_must_be_ignored_inside_repo(tmp_path):
    repo = tmp_path
    _git(repo, "init", "-q")
    root = _pcl_root(repo)
    _append(root, 0)
    # No .gitignore for the cache -> the cache write must be refused.
    with pytest.raises(rt.CacheNotIgnored):
        rt.index(ledger="demo", pcl_root=root, write_cache=True, repo_root=repo)
    # Ignoring the cache makes the write succeed and records stay trackable.
    (repo / ".gitignore").write_text(".ce/pcl/cache/\n", encoding="utf-8")
    result = rt.index(ledger="demo", pcl_root=root, write_cache=True, repo_root=repo)
    assert result.cache_path is not None and result.cache_path.is_file()


# --- merge ------------------------------------------------------------------
def test_merge_unions_clean_segments(tmp_path):
    root = _pcl_root(tmp_path)
    # Ledger A: genesis + child. Ledger B: identical genesis (prefix).
    _append(root, 0, ledger="a")
    _append(root, 1, ledger="a")
    _append(root, 0, ledger="b")  # same inputs -> same genesis content_hash
    result = rt.merge(sources=["a", "b"], target="merged", pcl_root=root, write_cache=False)
    assert result.ok
    assert result.merged["record_count"] == 2


def test_merge_fails_closed_on_fork(tmp_path):
    root = _pcl_root(tmp_path)
    _append(root, 0, ledger="a")
    _append(root, 1, ledger="a", record_id="pcl-a-child")
    _append(root, 0, ledger="b")  # same genesis
    _append(root, 1, ledger="b", record_id="pcl-b-child", body=_body(summary="divergent"))
    with pytest.raises(rt.PclMergeError):
        rt.merge(sources=["a", "b"], target="merged", pcl_root=root, write_cache=False)


def test_merge_requires_two_sources(tmp_path):
    root = _pcl_root(tmp_path)
    _append(root, 0, ledger="a")
    with pytest.raises(rt.PclMergeError):
        rt.merge(sources=["a"], target="merged", pcl_root=root, write_cache=False)


# --- decoupling (S6) --------------------------------------------------------
def test_runtime_does_not_import_ce_event_or_distributed_identity():
    import ast

    tree = ast.parse(Path(rt.__file__).read_text(encoding="utf-8"))
    imported: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            base = node.module or ""
            imported.add(base)
            imported.update(f"{base}.{n.name}" for n in node.names)
        elif isinstance(node, ast.Import):
            imported.update(n.name for n in node.names)
    assert not any("ce_event" in m for m in imported), imported
    assert not any("distributed_identity" in m for m in imported), imported
