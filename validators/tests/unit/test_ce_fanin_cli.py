"""Unit tests for the ``ce fanin`` CLI command family (RV1-070/071).

Drives ``creator_engine_validator.ce_cli.main`` directly. Asserts the
``ce fanin build`` / ``ce fanin inspect`` surface exists, writes a deterministic
packet under an ignored ``.hermes/fan-in/`` root, refuses authority actions and
malformed evidence non-zero, and leaves the existing ``ce`` groups intact.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest
import yaml

from creator_engine_validator import ce_cli


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _write(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def _make_request(tmp_path: Path, **override) -> tuple[Path, Path]:
    a = _write(tmp_path / "ev" / "a.txt", "alpha\n")
    b = _write(tmp_path / "ev" / "b.txt", "beta\n")
    manifest = _write(
        tmp_path / "ev" / "SHA256SUMS.txt",
        f"{_sha256_file(a)}  {a}\n{_sha256_file(b)}  {b}\n",
    )
    req = {
        "kind": "evidence-fan-in-request",
        "schema_version": "1",
        "packet_id": "pco-v1-g7-local",
        "source_ratification": {"prompt_ref": ".hermes/x/PROMPT.md", "sha256": "a" * 64},
        "evidence_manifests": [
            {"manifest_ref": str(manifest), "manifest_sha256": _sha256_file(manifest)}
        ],
    }
    req.update(override)
    request_path = _write(tmp_path / "request.yaml", yaml.safe_dump(req, sort_keys=True))
    root = tmp_path / ".hermes" / "fan-in"
    root.mkdir(parents=True, exist_ok=True)
    return request_path, root


def _packets(root: Path) -> list[Path]:
    return sorted(root.glob("*.json"))


# ---------------------------------------------------------------------------
# --help reachability (argparse wiring)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("argv", [
    ["fanin", "--help"],
    ["fanin", "build", "--help"],
    ["fanin", "inspect", "--help"],
])
def test_fanin_help_is_reachable(argv):
    with pytest.raises(SystemExit) as exc:
        ce_cli.main(argv)
    assert exc.value.code == 0


# ---------------------------------------------------------------------------
# ce fanin build
# ---------------------------------------------------------------------------


def test_ce_fanin_build_writes_packet(tmp_path):
    request, root = _make_request(tmp_path)
    ret = ce_cli.main([
        "fanin", "build",
        "--request", str(request),
        "--packet-root", str(root),
    ])
    assert ret == 0
    assert len(_packets(root)) == 1


def test_ce_fanin_build_json_reports_hash_and_path(tmp_path, capsys):
    request, root = _make_request(tmp_path)
    ret = ce_cli.main([
        "fanin", "build",
        "--request", str(request),
        "--packet-root", str(root),
        "--json",
    ])
    assert ret == 0
    payload = json.loads(capsys.readouterr().out)
    assert "content_hash" in payload and "packet_path" in payload
    assert payload["content_hash"] in payload["packet_path"]


@pytest.mark.parametrize("flag", ["--ratify", "--enqueue", "--land"])
def test_ce_fanin_build_refuses_authority_flag_nonzero_no_packet(tmp_path, flag):
    request, root = _make_request(tmp_path)
    ret = ce_cli.main([
        "fanin", "build",
        "--request", str(request),
        "--packet-root", str(root),
        flag,
    ])
    assert ret != 0
    assert _packets(root) == []


def test_ce_fanin_build_refuses_sha_mismatch_nonzero_no_packet(tmp_path):
    request, root = _make_request(tmp_path)
    (tmp_path / "ev" / "a.txt").write_text("CORRUPTED\n", encoding="utf-8")
    ret = ce_cli.main([
        "fanin", "build",
        "--request", str(request),
        "--packet-root", str(root),
    ])
    assert ret != 0
    assert _packets(root) == []


def test_ce_fanin_build_refuses_missing_ratification_nonzero(tmp_path):
    request, root = _make_request(tmp_path, source_ratification={})
    ret = ce_cli.main([
        "fanin", "build",
        "--request", str(request),
        "--packet-root", str(root),
    ])
    assert ret != 0
    assert _packets(root) == []


# ---------------------------------------------------------------------------
# ce fanin inspect
# ---------------------------------------------------------------------------


def test_ce_fanin_inspect_ok_after_build(tmp_path):
    request, root = _make_request(tmp_path)
    assert ce_cli.main(["fanin", "build", "--request", str(request), "--packet-root", str(root)]) == 0
    packet = _packets(root)[0]
    assert ce_cli.main(["fanin", "inspect", "--packet", str(packet)]) == 0


def test_ce_fanin_inspect_detects_tamper_nonzero(tmp_path):
    request, root = _make_request(tmp_path)
    ce_cli.main(["fanin", "build", "--request", str(request), "--packet-root", str(root)])
    packet = _packets(root)[0]
    data = json.loads(packet.read_text(encoding="utf-8"))
    data["packet_id"] = "tampered"
    packet.write_text(json.dumps(data, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    assert ce_cli.main(["fanin", "inspect", "--packet", str(packet)]) != 0


# ---------------------------------------------------------------------------
# Compatibility — existing ce groups unchanged
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("argv", [
    ["lane", "--help"],
    ["ledger", "--help"],
    ["worker", "--help"],
    ["check", "--help"],
    ["doctor", "--help"],
    ["init", "--help"],
    ["launch", "--help"],
    ["hud", "--help"],
])
def test_existing_groups_help_still_exits_zero(argv):
    with pytest.raises(SystemExit) as exc:
        ce_cli.main(argv)
    assert exc.value.code == 0
