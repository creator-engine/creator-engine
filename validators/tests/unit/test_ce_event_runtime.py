"""Unit tests for the G2.003.1 CE-event runtime (RV2-003-011..017).

Drives ``creator_engine_validator.ce_event_runtime`` directly. Asserts:

* ``append`` builds a genesis block (``sequence 0`` / ``parent_hash null``) and a
  linked block (``parent_hash`` = prior ``content_hash``) under the ignored
  ``.ce/ce-events/spool/<stream>/`` root, with a monotonic sequence and an
  agreeing head manifest;
* the runtime ``content_hash`` is byte-identical to the G2.003.0
  ``ce_event_block`` canonical-hash rule;
* every refusal (``agent_ratifier``/``source`` role floor, unknown operating
  mode, ``.hermes/ce-events`` write-freeze, un-ignored spool root, non-reserved
  signature value, corrupt head chain link) is raised **before any write**, so a
  refused call leaves the spool byte-identical;
* ``verify`` accepts a good chain and rejects forged hashes, broken links,
  unknown modes, and activated signatures by delegating shape to the landed
  ``ce_event_block`` validator;
* ``replay`` / ``index`` are deterministic (byte-identical across runs);
* a runtime-produced block passes the **unchanged** ``ce_event_block`` validator
  (backward-compat canary);
* the transport seam is injectable and the default performs local writes only.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml

from creator_engine_validator import ce_event_runtime as rt
from creator_engine_validator.checks import ce_event_block as block_check

RECORDED = "2026-05-30T16:00:00Z"


def _event_root(tmp_path: Path) -> Path:
    root = tmp_path / ".ce" / "ce-events"
    (root / "spool").mkdir(parents=True, exist_ok=True)
    return root


def _event(summary: str = "unit", **override) -> dict:
    base = {"kind": "gate_progress", "subject": "G2.003.1", "summary": summary}
    base.update(override)
    return base


def _append(root: Path, seq: int, *, stream: str = "demo", **override) -> rt.AppendResult:
    kwargs = dict(
        stream=stream,
        event_root=root,
        block_id=f"ceevt-demo-{seq:04d}",
        emitting_role="controller",
        operating_mode="strict",
        event=_event(),
        recorded_at=RECORDED,
    )
    kwargs.update(override)
    return rt.append(**kwargs)


def _spool(root: Path, stream: str = "demo") -> Path:
    return root / "spool" / stream


def _snapshot(root: Path) -> dict[str, bytes]:
    return {p.relative_to(root).as_posix(): p.read_bytes() for p in sorted(root.rglob("*")) if p.is_file()}


# ---------------------------------------------------------------------------
# append — chain construction
# ---------------------------------------------------------------------------


def test_genesis_append_is_sequence_zero_with_null_parent(tmp_path):
    root = _event_root(tmp_path)
    result = _append(root, 0)

    assert result.sequence == 0
    assert result.parent_hash is None
    assert result.block["parent_hash"] is None
    assert result.block["sequence"] == 0
    assert result.block_path.is_file()
    assert result.block_path.parent == _spool(root)


def test_linked_append_links_parent_hash_and_advances_sequence(tmp_path):
    root = _event_root(tmp_path)
    genesis = _append(root, 0)
    linked = _append(root, 1)

    assert linked.sequence == 1
    assert linked.parent_hash == genesis.content_hash
    assert linked.block["parent_hash"] == genesis.content_hash


def test_head_manifest_agrees_with_last_block(tmp_path):
    root = _event_root(tmp_path)
    _append(root, 0)
    linked = _append(root, 1)

    head = json.loads(linked.head_path.read_text(encoding="utf-8"))
    assert head["sequence"] == 1
    assert head["head_content_hash"] == linked.content_hash
    assert head["block_count"] == 2


def test_content_hash_matches_block_substrate_canonical_rule(tmp_path):
    root = _event_root(tmp_path)
    result = _append(root, 0)
    # Cross-check against the G2.003.0 validator's canonical-hash function on the
    # very same produced block: the runtime must not diverge by one byte.
    assert result.content_hash == block_check._canonical_hash(result.block)
    assert result.block["content_hash"] == result.content_hash


def test_produced_block_has_reserved_inactive_signature(tmp_path):
    root = _event_root(tmp_path)
    result = _append(root, 0)
    sig = result.block["signature"]
    assert sig["scheme"] == "reserved-shape-only"
    assert sig["value"] == "reserved-inactive"
    assert sig["key_id"]


# ---------------------------------------------------------------------------
# append — fail-closed refusals (no write, byte-identical spool)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("role", ["agent_ratifier", "source", "agent-ratifier"])
def test_append_refuses_role_floor(tmp_path, role):
    root = _event_root(tmp_path)
    before = _snapshot(root)
    with pytest.raises(rt.RoleFloorRefused):
        _append(root, 0, emitting_role=role)
    assert _snapshot(root) == before


def test_append_refuses_unknown_operating_mode(tmp_path):
    root = _event_root(tmp_path)
    before = _snapshot(root)
    with pytest.raises(rt.ModeInvalid):
        _append(root, 0, operating_mode="hyperdrive")
    assert _snapshot(root) == before


def test_append_refuses_hermes_event_write_freeze(tmp_path):
    root = _event_root(tmp_path)
    before = _snapshot(root)
    event = _event(payload={"target": ".hermes/ce-events/stream/x.ce.yml"})
    with pytest.raises(rt.WriteFreezeRefused):
        _append(root, 0, event=event)
    assert _snapshot(root) == before


def test_append_refuses_nonreserved_signature_value(tmp_path):
    root = _event_root(tmp_path)
    before = _snapshot(root)
    with pytest.raises(rt.SignatureReserved):
        _append(root, 0, signature_value="active")
    assert _snapshot(root) == before


def test_append_refuses_unignored_spool_root_in_repo(tmp_path):
    import subprocess

    repo = tmp_path / "repo"
    (repo / ".git").mkdir(parents=True)
    root = repo / ".ce" / "ce-events"
    (root / "spool").mkdir(parents=True)

    def not_ignored(argv):
        return subprocess.CompletedProcess(list(argv), 1)

    with pytest.raises(rt.EventRootNotIgnored):
        _append(root, 0, repo_root=repo, git_runner=not_ignored)
    assert list((root / "spool").rglob("*")) == []


def test_append_refuses_corrupt_head_chain_link(tmp_path):
    root = _event_root(tmp_path)
    _append(root, 0)
    # Corrupt the head manifest: a non-genesis append can no longer safely link.
    head_path = _spool(root) / rt.HEAD_FILENAME
    head_path.write_text("{ not json", encoding="utf-8")
    with pytest.raises(rt.ChainLinkError):
        _append(root, 1)


def test_append_refuses_overwriting_existing_block(tmp_path):
    root = _event_root(tmp_path)
    _append(root, 0)
    # Re-create a head pointing back to sequence -1 so the next append would
    # collide with the existing genesis file; the runtime must refuse.
    (_spool(root) / rt.HEAD_FILENAME).unlink()
    with pytest.raises(rt.CeEventAppendError):
        rt.append(
            stream="demo",
            event_root=root,
            block_id="ceevt-demo-0000",
            emitting_role="controller",
            operating_mode="strict",
            event=_event(),
            recorded_at=RECORDED,
        )


# ---------------------------------------------------------------------------
# verify — delegates shape to the landed ce_event_block validator
# ---------------------------------------------------------------------------


def test_verify_accepts_a_good_chain(tmp_path):
    root = _event_root(tmp_path)
    _append(root, 0)
    _append(root, 1)
    result = rt.verify(stream="demo", event_root=root)
    assert result.ok, result.errors
    assert result.summary["block_count"] == 2


def _tamper(root: Path, seq: int, mutate) -> None:
    path = next(p for p in _spool(root).glob(f"{seq:06d}-*.json"))
    data = json.loads(path.read_text(encoding="utf-8"))
    mutate(data)
    path.write_text(json.dumps(data, sort_keys=True, indent=2) + "\n", encoding="utf-8")


def test_verify_rejects_forged_content_hash(tmp_path):
    root = _event_root(tmp_path)
    _append(root, 0)
    _tamper(root, 0, lambda d: d.__setitem__("content_hash", "0" * 64))
    result = rt.verify(stream="demo", event_root=root)
    assert not result.ok
    assert any("content_hash" in e or "content-address" in e.lower() for e in result.errors)


def test_verify_rejects_broken_chain(tmp_path):
    root = _event_root(tmp_path)
    _append(root, 0)
    _append(root, 1)
    _tamper(root, 1, lambda d: d.__setitem__("parent_hash", "f" * 64))
    result = rt.verify(stream="demo", event_root=root)
    assert not result.ok


def test_verify_rejects_unknown_mode(tmp_path):
    root = _event_root(tmp_path)
    _append(root, 0)
    _tamper(root, 0, lambda d: d.__setitem__("operating_mode", "hyperdrive"))
    result = rt.verify(stream="demo", event_root=root)
    assert not result.ok


def test_verify_rejects_activated_signature(tmp_path):
    root = _event_root(tmp_path)
    _append(root, 0)
    _tamper(root, 0, lambda d: d["signature"].__setitem__("value", "active"))
    result = rt.verify(stream="demo", event_root=root)
    assert not result.ok


def test_verify_rejects_head_disagreement(tmp_path):
    root = _event_root(tmp_path)
    _append(root, 0)
    head_path = _spool(root) / rt.HEAD_FILENAME
    head = json.loads(head_path.read_text(encoding="utf-8"))
    head["head_content_hash"] = "0" * 64
    head_path.write_text(json.dumps(head, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    result = rt.verify(stream="demo", event_root=root)
    assert not result.ok


# ---------------------------------------------------------------------------
# replay / index — deterministic read-only projections
# ---------------------------------------------------------------------------


def test_replay_is_deterministic(tmp_path):
    root = _event_root(tmp_path)
    _append(root, 0)
    _append(root, 1)
    first = rt.replay(stream="demo", event_root=root)
    second = rt.replay(stream="demo", event_root=root)
    assert first.content_hash == second.content_hash
    assert [b["sequence"] for b in first.blocks] == [0, 1]


def test_index_is_deterministic_and_counts_blocks(tmp_path):
    root = _event_root(tmp_path)
    _append(root, 0)
    _append(root, 1)
    first = rt.index(stream="demo", event_root=root)
    second = rt.index(stream="demo", event_root=root)
    assert first.content_hash == second.content_hash
    assert first.index["block_count"] == 2
    assert first.index["head_content_hash"]


# ---------------------------------------------------------------------------
# backward-compat canary — produced chain passes the unchanged validator
# ---------------------------------------------------------------------------


def test_runtime_chain_passes_ce_event_block_validator(tmp_path):
    root = _event_root(tmp_path)
    _append(root, 0)
    _append(root, 1)
    blocks = list(rt.replay(stream="demo", event_root=root).blocks)

    # Dump the runtime chain to an in-scope ce-event-block path and validate it
    # with the *unchanged* G2.003.0 validator — no errors permitted.
    canary = tmp_path / "ce-event-block" / "runtime-chain.ce.yml"
    canary.parent.mkdir(parents=True, exist_ok=True)
    canary.write_text(yaml.safe_dump({"ce_event_chain": blocks}, sort_keys=True), encoding="utf-8")
    errors = block_check.validate_file(canary)
    assert errors == [], [e.format() for e in errors]


# ---------------------------------------------------------------------------
# sign — shape-only signature + content hash, no cryptography
# ---------------------------------------------------------------------------


def test_sign_sets_reserved_inactive_signature_and_content_hash():
    draft = {
        "block_id": "ceevt-demo-0000",
        "sequence": 0,
        "parent_hash": None,
        "emitting_role": "controller",
        "operating_mode": "strict",
        "recorded_at": RECORDED,
        "event": _event(),
    }
    signed = rt.sign(block=draft)
    assert signed["signature"]["scheme"] == "reserved-shape-only"
    assert signed["signature"]["value"] == "reserved-inactive"
    assert signed["content_hash"] == block_check._canonical_hash(signed)


def test_sign_refuses_nonreserved_value():
    draft = {
        "block_id": "ceevt-demo-0000",
        "sequence": 0,
        "parent_hash": None,
        "emitting_role": "controller",
        "operating_mode": "strict",
        "recorded_at": RECORDED,
        "event": _event(),
    }
    with pytest.raises(rt.SignatureReserved):
        rt.sign(block=draft, signature_value="active")


# ---------------------------------------------------------------------------
# transport seam — injectable, default is local filesystem only
# ---------------------------------------------------------------------------


class _RecordingTransport:
    def __init__(self):
        self.head_doc = None
        self.blocks: dict[int, dict] = {}
        self.calls: list[str] = []

    def head(self, stream_dir):
        self.calls.append("head")
        return self.head_doc

    def write_block(self, stream_dir, seq, block_id, block):
        self.calls.append("write_block")
        self.blocks[seq] = block
        return Path(stream_dir) / f"{seq:06d}-{block_id}.json"

    def write_head(self, stream_dir, head):
        self.calls.append("write_head")
        self.head_doc = head
        return Path(stream_dir) / rt.HEAD_FILENAME

    def read_blocks(self, stream_dir):
        return [(Path(stream_dir) / f"{s:06d}-x.json", b) for s, b in sorted(self.blocks.items())]


def test_append_uses_injected_transport_without_touching_disk(tmp_path):
    root = _event_root(tmp_path)
    fake = _RecordingTransport()
    result = _append(root, 0, transport=fake)
    assert "write_block" in fake.calls and "write_head" in fake.calls
    assert result.content_hash == block_check._canonical_hash(result.block)
    # The fake never wrote real files; only the pre-created spool dir exists.
    assert list(_spool(root).rglob("*")) == []


def test_default_transport_writes_local_files(tmp_path):
    root = _event_root(tmp_path)
    result = _append(root, 0)
    assert result.block_path.is_file()
    assert (_spool(root) / rt.HEAD_FILENAME).is_file()
