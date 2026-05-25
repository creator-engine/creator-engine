"""Unit tests for the Gate 7 local read-only evidence fan-in runtime (RV1-070/071).

Drives ``creator_engine_validator.fanin_runtime`` directly. Asserts:

* ``build`` aggregates evidence manifests into a deterministic, content-hashed
  stdlib-JSON packet written only under an ignored ``.hermes/fan-in/`` root;
* the packet is byte-identical and content-addressed for identical inputs
  (idempotent);
* ``build`` refuses (fail-closed, no packet written) on stale evidence, entry
  SHA mismatch, a missing Source-ratification ref, any authority action, and an
  un-ignored packet root inside a repository;
* ``inspect`` verifies the deterministic content hash + packet shape read-only
  and flags a tampered packet.
"""
from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path

import pytest
import yaml

from creator_engine_validator import fanin_runtime


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _write(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def _make_evidence(tmp_path: Path) -> Path:
    """Write two evidence files + a SHA256SUMS manifest referencing them."""
    a = _write(tmp_path / "ev" / "a.txt", "alpha\n")
    b = _write(tmp_path / "ev" / "b.txt", "beta\n")
    manifest = tmp_path / "ev" / "SHA256SUMS.txt"
    _write(manifest, f"{_sha256_file(a)}  {a}\n{_sha256_file(b)}  {b}\n")
    return manifest


def _request(tmp_path: Path, manifest: Path, **override) -> Path:
    req = {
        "kind": "evidence-fan-in-request",
        "schema_version": "1",
        "packet_id": "pco-v1-g7-local",
        "source_ratification": {
            "prompt_ref": ".hermes/research/x/PROMPT.md",
            "sha256": "a" * 64,
        },
        "evidence_manifests": [
            {"manifest_ref": str(manifest), "manifest_sha256": _sha256_file(manifest)}
        ],
    }
    req.update(override)
    path = tmp_path / "request.yaml"
    return _write(path, yaml.safe_dump(req, sort_keys=True))


def _packet_root(tmp_path: Path) -> Path:
    root = tmp_path / ".hermes" / "fan-in"
    root.mkdir(parents=True, exist_ok=True)
    return root


def _packets(root: Path) -> list[Path]:
    return sorted(root.glob("*.json"))


# ---------------------------------------------------------------------------
# build — deterministic, content-hashed, idempotent
# ---------------------------------------------------------------------------


def test_build_writes_content_hashed_packet_under_root(tmp_path):
    manifest = _make_evidence(tmp_path)
    req = _request(tmp_path, manifest)
    root = _packet_root(tmp_path)

    result = fanin_runtime.build(request=req, packet_root=root)

    assert result.packet_path.is_file()
    assert result.packet_path.parent == root
    assert result.content_hash in result.packet_path.name
    assert result.packet["kind"] == "evidence-fan-in-packet"
    assert result.packet["has_authority"] is False
    assert result.packet["content_hash"] == result.content_hash


def test_build_is_deterministic_and_idempotent(tmp_path):
    manifest = _make_evidence(tmp_path)
    req = _request(tmp_path, manifest)
    root = _packet_root(tmp_path)

    first = fanin_runtime.build(request=req, packet_root=root)
    second = fanin_runtime.build(request=req, packet_root=root)

    assert first.content_hash == second.content_hash
    assert first.packet_path == second.packet_path
    assert first.packet_path.read_bytes() == second.packet_path.read_bytes()
    assert len(_packets(root)) == 1


def test_build_aggregates_evidence_entries_sorted(tmp_path):
    manifest = _make_evidence(tmp_path)
    req = _request(tmp_path, manifest)
    root = _packet_root(tmp_path)

    result = fanin_runtime.build(request=req, packet_root=root)

    assert result.evidence_count == 1
    evidence = result.packet["evidence"][0]
    assert evidence["entry_count"] == 2
    paths = [entry["path"] for entry in evidence["entries"]]
    assert paths == sorted(paths)


def test_build_packet_passes_inspect(tmp_path):
    manifest = _make_evidence(tmp_path)
    req = _request(tmp_path, manifest)
    root = _packet_root(tmp_path)
    result = fanin_runtime.build(request=req, packet_root=root)

    inspected = fanin_runtime.inspect(packet=result.packet_path)
    assert inspected.ok is True
    assert inspected.content_hash == result.content_hash
    assert inspected.issues == ()


# ---------------------------------------------------------------------------
# build — fail-closed refusals (no packet written)
# ---------------------------------------------------------------------------


def test_build_refuses_entry_sha_mismatch(tmp_path):
    manifest = _make_evidence(tmp_path)
    # Corrupt a referenced file after the manifest was authored: the manifest
    # file itself is unchanged, so this is an entry SHA mismatch, not staleness.
    (tmp_path / "ev" / "a.txt").write_text("CORRUPTED\n", encoding="utf-8")
    req = _request(tmp_path, manifest)
    root = _packet_root(tmp_path)

    with pytest.raises(fanin_runtime.EvidenceShaMismatch):
        fanin_runtime.build(request=req, packet_root=root)
    assert _packets(root) == []


def test_build_refuses_stale_manifest(tmp_path):
    manifest = _make_evidence(tmp_path)
    req = _request(
        tmp_path,
        manifest,
        evidence_manifests=[{"manifest_ref": str(manifest), "manifest_sha256": "0" * 64}],
    )
    root = _packet_root(tmp_path)

    with pytest.raises(fanin_runtime.StaleEvidence):
        fanin_runtime.build(request=req, packet_root=root)
    assert _packets(root) == []


def test_build_refuses_missing_source_ratification(tmp_path):
    manifest = _make_evidence(tmp_path)
    req = _request(tmp_path, manifest, source_ratification={})
    root = _packet_root(tmp_path)

    with pytest.raises(fanin_runtime.MissingSourceRatification):
        fanin_runtime.build(request=req, packet_root=root)
    assert _packets(root) == []


def test_build_refuses_authority_action(tmp_path):
    manifest = _make_evidence(tmp_path)
    req = _request(tmp_path, manifest)
    root = _packet_root(tmp_path)

    for action in ("ratify", "enqueue", "land"):
        with pytest.raises(fanin_runtime.AuthorityRefused):
            fanin_runtime.build(request=req, packet_root=root, authority_action=action)
    assert _packets(root) == []


def test_build_refuses_unignored_packet_root_in_repo(tmp_path):
    manifest = _make_evidence(tmp_path)
    req = _request(tmp_path, manifest)
    repo = tmp_path / "repo"
    (repo / ".git").mkdir(parents=True)
    root = repo / "not-ignored"
    root.mkdir()

    def not_ignored_runner(argv):
        return subprocess.CompletedProcess(list(argv), 1)  # check-ignore -> not ignored

    with pytest.raises(fanin_runtime.PacketRootNotIgnored):
        fanin_runtime.build(request=req, packet_root=root, repo_root=repo, git_runner=not_ignored_runner)
    assert _packets(root) == []


# ---------------------------------------------------------------------------
# build — side-effect ledger section
# ---------------------------------------------------------------------------


def test_build_without_ledger_root_has_empty_ledger_section(tmp_path):
    manifest = _make_evidence(tmp_path)
    req = _request(tmp_path, manifest)
    root = _packet_root(tmp_path)

    result = fanin_runtime.build(request=req, packet_root=root)

    assert result.packet["side_effect_ledger"]["root_ref"] is None
    assert result.packet["side_effect_ledger"]["chains"] == []
    assert result.ledger_chain_count == 0


# ---------------------------------------------------------------------------
# inspect — read-only verification
# ---------------------------------------------------------------------------


def test_inspect_detects_tampered_packet(tmp_path):
    manifest = _make_evidence(tmp_path)
    req = _request(tmp_path, manifest)
    root = _packet_root(tmp_path)
    result = fanin_runtime.build(request=req, packet_root=root)

    data = json.loads(result.packet_path.read_text(encoding="utf-8"))
    data["evidence"][0]["entry_count"] = 999  # mutate payload, leave content_hash stale
    result.packet_path.write_text(json.dumps(data, sort_keys=True, indent=2) + "\n", encoding="utf-8")

    inspected = fanin_runtime.inspect(packet=result.packet_path)
    assert inspected.ok is False
    assert inspected.issues


def test_inspect_missing_packet_raises(tmp_path):
    with pytest.raises(fanin_runtime.FaninInspectError):
        fanin_runtime.inspect(packet=tmp_path / "nope.json")
