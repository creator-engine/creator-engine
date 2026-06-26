"""Integration tests for the ``ce fanin`` runtime end-to-end (RV1-070/071).

Exercises the full ``ce fanin build`` -> ``ce fanin inspect`` flow through
``ce_cli.main``, including Side-Effect Ledger reference aggregation, fail-closed
refusal on tampered evidence, the committed well-formed/malformed example
packets, and ``ce`` group co-existence.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest
import yaml

from creator_engine_validator import ce_cli
pytestmark = pytest.mark.slow


REPO_ROOT = Path(__file__).resolve().parents[3]
WELL_FORMED = REPO_ROOT / "examples" / "well-formed" / "evidence-fan-in"
MALFORMED = REPO_ROOT / "examples" / "malformed" / "evidence-fan-in"

CONTROLLER = "hermes-primary"
LANE = "pco-g7-fanin"


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _write(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def _claim(awl: Path) -> None:
    record = {
        "kind": "active-work-ledger-record",
        "record_type": "claim",
        "schema_version": "1",
        "controller_id": CONTROLLER,
        "lane_id": LANE,
        "record_timestamp": f"source-controlled:claims/{CONTROLLER}/{LANE}.yaml",
        "worktree_path": "/worktrees/pco-g7-fanin",
        "envelope_ref": ".hermes/envelopes/pco-g7.md",
        "lease_seconds": 3600,
        "claimed_at": f"source-controlled:claims/{CONTROLLER}/{LANE}.yaml",
        "last_heartbeat_at": f"source-controlled:claims/{CONTROLLER}/{LANE}.yaml",
    }
    _write(awl / "claims" / CONTROLLER / f"{LANE}.yaml", yaml.safe_dump(record, sort_keys=True))


def _build_side_effect_ledger(tmp_path: Path) -> Path:
    from creator_engine_validator import side_effect_ledger_runtime

    sel = tmp_path / "side-effect-ledger"
    awl = tmp_path / ".hermes" / "active-work-ledger"
    awl.mkdir(parents=True, exist_ok=True)
    _claim(awl)
    side_effect_ledger_runtime.record(
        controller_id=CONTROLLER,
        lane_id=LANE,
        claim_ref=f"claims/{CONTROLLER}/{LANE}.yaml",
        effect_id="effect-a",
        effect_kind="tracked_file_change",
        effect_status="succeeded",
        summary="Authored a fan-in protocol doc.",
        occurred_at="2026-05-25T12:10:00Z",
        repo_root=tmp_path,
        side_effect_ledger_root=sel,
        active_work_ledger_root=awl,
    )
    return sel


def _make_request(tmp_path: Path, *, ledger_root: Path | None = None) -> tuple[Path, Path]:
    a = _write(tmp_path / "ev" / "a.txt", "alpha\n")
    manifest = _write(tmp_path / "ev" / "SHA256SUMS.txt", f"{_sha256_file(a)}  {a}\n")
    req: dict = {
        "kind": "evidence-fan-in-request",
        "schema_version": "1",
        "packet_id": "pco-v1-g7-local",
        "source_ratification": {"prompt_ref": ".hermes/x/PROMPT.md", "sha256": "a" * 64},
        "evidence_manifests": [
            {"manifest_ref": str(manifest), "manifest_sha256": _sha256_file(manifest)}
        ],
    }
    if ledger_root is not None:
        req["side_effect_ledger"] = {"root_ref": str(ledger_root)}
    request_path = _write(tmp_path / "request.yaml", yaml.safe_dump(req, sort_keys=True))
    root = tmp_path / ".hermes" / "fan-in"
    root.mkdir(parents=True, exist_ok=True)
    return request_path, root


def _packets(root: Path) -> list[Path]:
    return sorted(root.glob("*.json"))


def test_build_then_inspect_with_ledger_refs(tmp_path, capsys):
    sel = _build_side_effect_ledger(tmp_path)
    request, root = _make_request(tmp_path, ledger_root=sel)

    assert ce_cli.main([
        "fanin", "build", "--request", str(request), "--packet-root", str(root), "--json",
    ]) == 0
    payload = json.loads(capsys.readouterr().out)
    packet = Path(payload["packet_path"])
    data = json.loads(packet.read_text(encoding="utf-8"))

    chains = data["side_effect_ledger"]["chains"]
    assert len(chains) == 1
    assert chains[0]["controller_id"] == CONTROLLER
    assert chains[0]["lane_id"] == LANE
    assert chains[0]["record_count"] == 1
    assert len(chains[0]["head_sha256"]) == 64

    assert ce_cli.main(["fanin", "inspect", "--packet", str(packet)]) == 0


def test_build_refuses_tampered_ledger_evidence(tmp_path):
    sel = _build_side_effect_ledger(tmp_path)
    # Tamper with a ledger record so chain verification fails.
    target = sorted(p for p in sel.rglob("*.json") if p.name != "_head.json")[0]
    record = json.loads(target.read_text(encoding="utf-8"))
    record["summary"] = "tampered"
    target.write_text(json.dumps(record, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    request, root = _make_request(tmp_path, ledger_root=sel)

    assert ce_cli.main([
        "fanin", "build", "--request", str(request), "--packet-root", str(root),
    ]) != 0
    assert _packets(root) == []


def test_well_formed_example_packets_inspect_ok():
    packets = sorted(WELL_FORMED.glob("*.json"))
    assert packets, f"expected well-formed example packets under {WELL_FORMED}"
    for packet in packets:
        assert ce_cli.main(["fanin", "inspect", "--packet", str(packet)]) == 0, packet


def test_malformed_example_packets_inspect_nonzero():
    packets = sorted(MALFORMED.glob("*.json"))
    assert packets, f"expected malformed example packets under {MALFORMED}"
    for packet in packets:
        assert ce_cli.main(["fanin", "inspect", "--packet", str(packet)]) != 0, packet


def test_ce_fanin_coexists_with_other_groups():
    for argv in (["fanin", "build", "--help"], ["ledger", "verify", "--help"], ["lane", "verify", "--help"]):
        with pytest.raises(SystemExit) as exc:
            ce_cli.main(argv)
        assert exc.value.code == 0
