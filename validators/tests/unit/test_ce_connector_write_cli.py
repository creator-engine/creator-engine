"""Unit tests for the ``ce connector`` write family (G2.005.2). Fully offline."""
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
        "connector_id": "conn-wcli-0001",
        "connector_kind": "tracker",
        "provider_class": "issue-tracker",
        "capability": {"scope": "write", "verbs": ["issue-create", "issue-update", "pr-comment"]},
        "credential_ref": {"ref_kind": "env_var_name", "ref_name": "CE_TEST_CONNECTOR_TOKEN"},
        "emitting_role": "operator",
        "operating_mode": "strict",
        "recorded_at": "2026-06-01T05:16:58Z",
    }
    rec.update(override)
    p = tmp_path / "c.ce.yml"
    p.write_text(yaml.safe_dump({"connector": rec}), encoding="utf-8")
    return p


def _brief(tmp_path: Path, **override) -> Path:
    rec = {
        "brief_id": "mb-wcli-0001",
        "assignment_ref": "lane:wcli",
        "declared_mutation_classes": ["tracker_mirror"],
        "capability_scope": "write",
        "emitting_role": "controller",
        "operating_mode": "strict",
        "recorded_at": "2026-06-01T05:16:58Z",
        "signature": {"scheme": "reserved-shape-only", "key_id": "operator-reserved", "value": "reserved-inactive"},
    }
    rec.update(override)
    p = tmp_path / "m.ce.yml"
    p.write_text(yaml.safe_dump({"mission_brief": rec}), encoding="utf-8")
    return p


class _FakeResponse:
    status = 201

    def read(self) -> bytes:
        return b'{"id": 1, "number": 2, "html_url": "https://x/2", "access_token": "ghp_leak"}'


@pytest.mark.parametrize("argv", [
    ["connector", "write-plan", "--help"],
    ["connector", "submit", "--help"],
])
def test_write_help_reachable(argv):
    with pytest.raises(SystemExit) as exc:
        ce_cli.main(argv)
    assert exc.value.code == 0


def test_write_plan_ok(tmp_path, capsys):
    rc = ce_cli.main(["connector", "write-plan", "--connector", str(_conn(tmp_path)), "--mission-brief", str(_brief(tmp_path))])
    assert rc == 0
    assert "OK" in capsys.readouterr().out


def test_write_plan_json(tmp_path, capsys):
    rc = ce_cli.main(["connector", "write-plan", "--connector", str(_conn(tmp_path)), "--mission-brief", str(_brief(tmp_path)), "--json"])
    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["capability_scope"] == "write" and payload["operating_mode"] == "strict"
    assert payload["write_verbs"] == ["issue-create", "issue-update", "pr-comment"]


def test_write_plan_refuses_read_only(tmp_path, capsys):
    conn = _conn(tmp_path, capability={"scope": "read_only", "verbs": ["issue-read"]})
    rc = ce_cli.main(["connector", "write-plan", "--connector", str(conn), "--mission-brief", str(_brief(tmp_path))])
    assert rc == 1
    assert "G2-CONN-READONLY-REFUSED" in capsys.readouterr().err


def test_write_plan_refuses_non_strict(tmp_path, capsys):
    conn = _conn(tmp_path, operating_mode="auto")
    rc = ce_cli.main(["connector", "write-plan", "--connector", str(conn), "--mission-brief", str(_brief(tmp_path))])
    assert rc == 1
    assert "G2-CONN-MODE-REFUSED" in capsys.readouterr().err


def test_submit_offline_via_monkeypatched_opener(tmp_path, capsys, monkeypatch):
    monkeypatch.setenv("CE_TEST_CONNECTOR_TOKEN", "ghp_SECRETvaluexxxxxxxxxxxxxxxxxx")
    monkeypatch.setattr(connector_runtime, "_default_opener", lambda: (lambda request: _FakeResponse()))
    rc = ce_cli.main([
        "connector", "submit", "--connector", str(_conn(tmp_path)), "--mission-brief", str(_brief(tmp_path)),
        "--verb", "issue-create", "--resource", "repos/o/r/issues", "--json",
    ])
    assert rc == 0
    out = capsys.readouterr().out
    receipt = json.loads(out)
    assert receipt["status"] == 201 and receipt["verb"] == "issue-create"
    assert receipt["result"] == {"id": 1, "number": 2, "html_url": "https://x/2"}
    # No credential/secret value or unbounded field in the output.
    assert "ghp_SECRET" not in out and "access_token" not in out


def test_submit_failclosed_without_credential(tmp_path, capsys, monkeypatch):
    monkeypatch.delenv("CE_TEST_CONNECTOR_TOKEN", raising=False)

    def exploding():
        def _o(request):
            raise AssertionError("no request without a present credential")
        return _o

    monkeypatch.setattr(connector_runtime, "_default_opener", exploding)
    rc = ce_cli.main([
        "connector", "submit", "--connector", str(_conn(tmp_path)), "--mission-brief", str(_brief(tmp_path)),
        "--verb", "issue-create", "--resource", "repos/o/r/issues",
    ])
    assert rc == 1
    assert "G2-CONN-CREDENTIAL-MISSING" in capsys.readouterr().err


def test_submit_failclosed_offline(tmp_path, capsys, monkeypatch):
    monkeypatch.setenv("CE_TEST_CONNECTOR_TOKEN", "tok")

    def offline():
        def _o(request):
            raise urllib.error.URLError("offline")
        return _o

    monkeypatch.setattr(connector_runtime, "_default_opener", offline)
    rc = ce_cli.main([
        "connector", "submit", "--connector", str(_conn(tmp_path)), "--mission-brief", str(_brief(tmp_path)),
        "--verb", "issue-create", "--resource", "repos/o/r/issues",
    ])
    assert rc == 1
    assert "G2-CONN-NETWORK" in capsys.readouterr().err


def test_read_path_and_other_groups_intact():
    # The G2.005.1 read verbs and other ce groups remain reachable alongside the write verbs.
    for argv in (["connector", "fetch", "--help"], ["connector", "verify", "--help"], ["pcl", "--help"]):
        with pytest.raises(SystemExit) as exc:
            ce_cli.main(argv)
        assert exc.value.code == 0
