"""Unit tests for the ``ce connector`` CLI family (G2.005.1). Fully offline."""
from __future__ import annotations

import json
import urllib.error
from pathlib import Path

import pytest
import yaml

from creator_engine_validator import ce_cli
from creator_engine_validator import connector_runtime


def _conn(tmp_path: Path, **override) -> Path:
    rec = {
        "connector_id": "conn-cli-0001",
        "connector_kind": "tracker",
        "provider_class": "issue-tracker",
        "capability": {"scope": "read_only", "verbs": ["issue-read"]},
        "credential_ref": {"ref_kind": "none", "ref_name": "unused"},
        "emitting_role": "operator",
        "operating_mode": "strict",
        "recorded_at": "2026-06-01T03:59:51Z",
    }
    rec.update(override)
    p = tmp_path / "c.ce.yml"
    p.write_text(yaml.safe_dump({"connector": rec}), encoding="utf-8")
    return p


def _brief(tmp_path: Path, **override) -> Path:
    rec = {
        "brief_id": "mb-cli-0001",
        "assignment_ref": "lane:cli",
        "declared_mutation_classes": ["tracker_mirror"],
        "capability_scope": "read_only",
        "emitting_role": "controller",
        "operating_mode": "strict",
        "recorded_at": "2026-06-01T03:59:51Z",
        "signature": {"scheme": "reserved-shape-only", "key_id": "operator-reserved", "value": "reserved-inactive"},
    }
    rec.update(override)
    p = tmp_path / "m.ce.yml"
    p.write_text(yaml.safe_dump({"mission_brief": rec}), encoding="utf-8")
    return p


class _FakeResponse:
    status = 200

    def read(self) -> bytes:
        return b'[{"id": 1, "number": 2, "title": "t", "state": "open"}]'


@pytest.mark.parametrize("argv", [
    ["connector", "--help"],
    ["connector", "verify", "--help"],
    ["connector", "plan", "--help"],
    ["connector", "fetch", "--help"],
])
def test_connector_help_reachable(argv):
    with pytest.raises(SystemExit) as exc:
        ce_cli.main(argv)
    assert exc.value.code == 0


def test_connector_verify_ok(tmp_path, capsys):
    rc = ce_cli.main(["connector", "verify", "--connector", str(_conn(tmp_path)), "--mission-brief", str(_brief(tmp_path))])
    assert rc == 0
    assert "OK" in capsys.readouterr().out


def test_connector_verify_refuses_write(tmp_path, capsys):
    conn = _conn(tmp_path, capability={"scope": "write", "verbs": ["issue-create"]})
    rc = ce_cli.main(["connector", "verify", "--connector", str(conn), "--mission-brief", str(_brief(tmp_path))])
    assert rc == 1
    assert "G2-CONN-WRITE-REFUSED" in capsys.readouterr().err


def test_connector_plan_json(tmp_path, capsys):
    rc = ce_cli.main(["connector", "plan", "--connector", str(_conn(tmp_path)), "--mission-brief", str(_brief(tmp_path)), "--json"])
    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["capability_scope"] == "read_only"
    assert payload["read_verbs"] == ["issue-read"]


def test_connector_fetch_offline_via_monkeypatched_opener(tmp_path, capsys, monkeypatch):
    monkeypatch.setattr(connector_runtime, "_default_opener", lambda: (lambda request: _FakeResponse()))
    rc = ce_cli.main([
        "connector", "fetch", "--connector", str(_conn(tmp_path)), "--mission-brief", str(_brief(tmp_path)),
        "--resource", "repos/o/r/issues", "--json",
    ])
    assert rc == 0
    receipt = json.loads(capsys.readouterr().out)
    assert receipt["status"] == 200 and receipt["result_count"] == 1


def test_connector_fetch_failclosed_offline(tmp_path, capsys, monkeypatch):
    def offline():
        def _o(request):
            raise urllib.error.URLError("offline")
        return _o

    monkeypatch.setattr(connector_runtime, "_default_opener", offline)
    rc = ce_cli.main([
        "connector", "fetch", "--connector", str(_conn(tmp_path)), "--mission-brief", str(_brief(tmp_path)),
        "--resource", "repos/o/r/issues",
    ])
    assert rc == 1
    assert "G2-CONN-NETWORK" in capsys.readouterr().err


def test_existing_ce_groups_intact():
    for argv in (["pcl", "--help"], ["event", "--help"], ["lane", "--help"]):
        with pytest.raises(SystemExit) as exc:
            ce_cli.main(argv)
        assert exc.value.code == 0
