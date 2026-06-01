"""Integration tests for the ``ce connector`` read-only runtime end-to-end (G2.005.1).

Exercises `ce connector verify` -> `plan` -> `fetch` through `ce_cli.main` with the
network seam monkeypatched to a fake opener, so the test is fully network-free.
Asserts read-only enforcement, credential-by-reference (no value leaks), and that
the `ce connector` group co-exists with the other `ce` groups.
"""
from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from creator_engine_validator import ce_cli
from creator_engine_validator import connector_runtime


def _connector(tmp_path: Path, **override) -> Path:
    rec = {
        "connector_id": "conn-it-0001",
        "connector_kind": "source_host",
        "provider_class": "git-host",
        "capability": {"scope": "read_only", "verbs": ["repo-read"]},
        "credential_ref": {"ref_kind": "env_var_name", "ref_name": "CE_IT_CONNECTOR_TOKEN"},
        "emitting_role": "operator",
        "operating_mode": "strict",
        "recorded_at": "2026-06-01T03:59:51Z",
    }
    rec.update(override)
    p = tmp_path / "connector.ce.yml"
    p.write_text(yaml.safe_dump({"connector": rec}), encoding="utf-8")
    return p


def _brief(tmp_path: Path, **override) -> Path:
    rec = {
        "brief_id": "mb-it-0001",
        "assignment_ref": "lane:it",
        "declared_mutation_classes": ["docs", "tracker_mirror"],
        "capability_scope": "read_only",
        "emitting_role": "controller",
        "operating_mode": "strict",
        "recorded_at": "2026-06-01T03:59:51Z",
        "signature": {"scheme": "reserved-shape-only", "key_id": "operator-reserved", "value": "reserved-inactive"},
    }
    rec.update(override)
    p = tmp_path / "brief.ce.yml"
    p.write_text(yaml.safe_dump({"mission_brief": rec}), encoding="utf-8")
    return p


class _FakeResponse:
    status = 200

    def __init__(self, captured):
        self._captured = captured

    def read(self) -> bytes:
        return b'[{"id": 5, "number": 11, "title": "repo", "state": "open", "access_token": "ghp_leak"}]'


def test_verify_plan_fetch_roundtrip_offline(tmp_path, capsys, monkeypatch):
    conn = _connector(tmp_path)
    brief = _brief(tmp_path)
    monkeypatch.setenv("CE_IT_CONNECTOR_TOKEN", "ghp_SECRETvaluexxxxxxxxxxxxxxxxxx")

    captured = {}

    def fake_opener_factory():
        def opener(request):
            captured["url"] = request.full_url
            captured["method"] = request.get_method()
            captured["auth_present"] = "Authorization" in request.headers
            return _FakeResponse(captured)
        return opener

    monkeypatch.setattr(connector_runtime, "_default_opener", fake_opener_factory)

    assert ce_cli.main(["connector", "verify", "--connector", str(conn), "--mission-brief", str(brief)]) == 0
    assert ce_cli.main(["connector", "plan", "--connector", str(conn), "--mission-brief", str(brief)]) == 0
    capsys.readouterr()
    rc = ce_cli.main([
        "connector", "fetch", "--connector", str(conn), "--mission-brief", str(brief),
        "--resource", "repos/o/r", "--json",
    ])
    out = capsys.readouterr().out
    assert rc == 0
    # GET only, credential applied to the request, but its value never surfaces in output.
    assert captured["method"] == "GET"
    assert captured["auth_present"] is True
    assert "ghp_SECRET" not in out
    assert "access_token" not in out  # normalized away


def test_fetch_refuses_write_connector_offline(tmp_path, capsys, monkeypatch):
    conn = _connector(tmp_path, capability={"scope": "write", "verbs": ["issue-create"]})
    brief = _brief(tmp_path)

    def exploding_factory():
        def opener(request):
            raise AssertionError("no request may be issued when write is refused")
        return opener

    monkeypatch.setattr(connector_runtime, "_default_opener", exploding_factory)
    rc = ce_cli.main([
        "connector", "fetch", "--connector", str(conn), "--mission-brief", str(brief), "--resource", "repos/o/r",
    ])
    assert rc == 1
    assert "G2-CONN-WRITE-REFUSED" in capsys.readouterr().err


def test_connector_group_coexists():
    for argv in (["connector", "--help"], ["pcl", "--help"], ["event", "--help"]):
        with pytest.raises(SystemExit) as exc:
            ce_cli.main(argv)
        assert exc.value.code == 0
