"""Unit tests for the ``ce pcl`` CLI command family (G2.004.1).

Drives ``creator_engine_validator.ce_cli.main`` directly: asserts the
``ce pcl {append,verify,replay,index,merge}`` surface exists, appends a record
under the tracked ``.ce/pcl/records/<ledger>/`` home, round-trips append ->
verify, refuses floor violations non-zero with the stable code, and leaves the
existing ``ce`` groups intact.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from creator_engine_validator import ce_cli

RECORDED = "2026-05-31T16:48:41Z"
BODY_JSON = json.dumps({"lane_id": "g20041-pcl-runtime", "summary": "cli"})


def _pcl_root(tmp_path: Path) -> Path:
    root = tmp_path / ".ce" / "pcl"
    (root / "records").mkdir(parents=True, exist_ok=True)
    return root


def _append_argv(root: Path, record_id: str, **override) -> list[str]:
    return [
        "pcl", "append",
        "--ledger", override.get("ledger", "demo"),
        "--pcl-root", str(root),
        "--record-id", record_id,
        "--record-kind", override.get("record_kind", "lane_claim"),
        "--emitting-role", override.get("role", "controller"),
        "--operating-mode", override.get("mode", "strict"),
        "--recorded-at", RECORDED,
        "--body-json", override.get("body_json", BODY_JSON),
    ]


def _records(root: Path, ledger: str = "demo") -> list[Path]:
    return sorted(p for p in (root / "records" / ledger).glob("*.json") if p.name != "_head.json")


@pytest.mark.parametrize("argv", [
    ["pcl", "--help"],
    ["pcl", "append", "--help"],
    ["pcl", "verify", "--help"],
    ["pcl", "replay", "--help"],
    ["pcl", "index", "--help"],
    ["pcl", "merge", "--help"],
])
def test_pcl_help_is_reachable(argv):
    with pytest.raises(SystemExit) as exc:
        ce_cli.main(argv)
    assert exc.value.code == 0


def test_pcl_append_then_verify_roundtrips(tmp_path, capsys):
    root = _pcl_root(tmp_path)
    assert ce_cli.main(_append_argv(root, "pcl-demo-0000")) == 0
    assert ce_cli.main(_append_argv(root, "pcl-demo-0001")) == 0
    assert len(_records(root)) == 2
    assert ce_cli.main(["pcl", "verify", "--ledger", "demo", "--pcl-root", str(root)]) == 0
    out = capsys.readouterr().out
    assert "OK" in out


def test_pcl_append_json_output(tmp_path, capsys):
    root = _pcl_root(tmp_path)
    assert ce_cli.main(_append_argv(root, "pcl-demo-0000") + ["--json"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["sequence"] == 0
    assert payload["parent_hash"] is None
    assert len(payload["content_hash"]) == 64


def test_pcl_append_role_floor_refused_nonzero(tmp_path, capsys):
    root = _pcl_root(tmp_path)
    rc = ce_cli.main(_append_argv(root, "pcl-demo-0000", role="agent_ratifier"))
    assert rc == 1
    assert "G2-PCL-ROLE-FLOOR" in capsys.readouterr().err
    assert _records(root) == []


def test_pcl_append_bad_body_json_nonzero(tmp_path, capsys):
    root = _pcl_root(tmp_path)
    argv = _append_argv(root, "pcl-demo-0000")
    argv[argv.index("--body-json") + 1] = "{not json"
    assert ce_cli.main(argv) == 1
    assert "not valid JSON" in capsys.readouterr().err


def test_pcl_replay_and_index(tmp_path, capsys):
    root = _pcl_root(tmp_path)
    ce_cli.main(_append_argv(root, "pcl-demo-0000", record_kind="gate_opened"))
    ce_cli.main(_append_argv(root, "pcl-demo-0001"))
    capsys.readouterr()  # flush the human-readable append output before parsing JSON
    assert ce_cli.main(["pcl", "replay", "--ledger", "demo", "--pcl-root", str(root), "--json"]) == 0
    replay = json.loads(capsys.readouterr().out)
    assert replay["record_count"] == 2
    assert ce_cli.main(["pcl", "index", "--ledger", "demo", "--pcl-root", str(root), "--no-cache", "--json"]) == 0
    index = json.loads(capsys.readouterr().out)
    assert index["record_count"] == 2


def test_pcl_merge_clean_and_conflict(tmp_path, capsys):
    root = _pcl_root(tmp_path)
    ce_cli.main(_append_argv(root, "pcl-a-0000", ledger="a"))
    ce_cli.main(_append_argv(root, "pcl-a-0000", ledger="b"))  # identical genesis
    rc = ce_cli.main(["pcl", "merge", "--source", "a", "--source", "b", "--target", "m", "--pcl-root", str(root), "--no-cache"])
    assert rc == 0
    # Introduce a fork: divergent children of the same genesis.
    ce_cli.main(_append_argv(root, "pcl-a-child", ledger="a"))
    ce_cli.main(_append_argv(root, "pcl-b-child", ledger="b", body_json=json.dumps({"lane_id": "x", "summary": "divergent"})))
    rc = ce_cli.main(["pcl", "merge", "--source", "a", "--source", "b", "--target", "m", "--pcl-root", str(root), "--no-cache"])
    assert rc == 1
    assert "G2-PCL-MERGE-CONFLICT" in capsys.readouterr().err


def test_existing_ce_groups_intact():
    # The pcl group is additive; sibling groups still resolve their help cleanly.
    for argv in (["event", "--help"], ["ledger", "--help"], ["lane", "--help"]):
        with pytest.raises(SystemExit) as exc:
            ce_cli.main(argv)
        assert exc.value.code == 0
