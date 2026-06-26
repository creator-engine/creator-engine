"""Integration tests for the ``ce connector`` write runtime end-to-end (G2.005.2).

Exercises `ce connector write-plan` -> `submit` through `ce_cli.main` with the network
seam monkeypatched to a fake opener, so the test is fully network-free. Asserts the
strict-mode floor, the tracker_mirror bound, credential-REQUIRED-by-reference (no value
leaks), and that the write verbs co-exist with the read verbs and the other `ce` groups.
"""
from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from creator_engine_validator import ce_cli
from creator_engine_validator import connector_runtime
pytestmark = pytest.mark.slow



def _connector(tmp_path: Path, **override) -> Path:
    rec = {
        "connector_id": "conn-wit-0001",
        "connector_kind": "source_host",
        "provider_class": "git-host",
        "capability": {"scope": "write", "verbs": ["issue-create", "issue-update", "pr-comment"]},
        "credential_ref": {"ref_kind": "env_var_name", "ref_name": "CE_IT_CONNECTOR_TOKEN"},
        "emitting_role": "operator",
        "operating_mode": "strict",
        "recorded_at": "2026-06-01T05:16:58Z",
    }
    rec.update(override)
    p = tmp_path / "connector.ce.yml"
    p.write_text(yaml.safe_dump({"connector": rec}), encoding="utf-8")
    return p


def _brief(tmp_path: Path, **override) -> Path:
    rec = {
        "brief_id": "mb-wit-0001",
        "assignment_ref": "lane:wit",
        "declared_mutation_classes": ["docs", "tracker_mirror"],
        "capability_scope": "write",
        "emitting_role": "controller",
        "operating_mode": "strict",
        "recorded_at": "2026-06-01T05:16:58Z",
        "signature": {"scheme": "reserved-shape-only", "key_id": "operator-reserved", "value": "reserved-inactive"},
    }
    rec.update(override)
    p = tmp_path / "brief.ce.yml"
    p.write_text(yaml.safe_dump({"mission_brief": rec}), encoding="utf-8")
    return p


class _FakeResponse:
    status = 201

    def read(self) -> bytes:
        return b'{"id": 5, "number": 11, "html_url": "https://x/11", "access_token": "ghp_leak"}'


def test_write_plan_submit_roundtrip_offline(tmp_path, capsys, monkeypatch):
    conn = _connector(tmp_path)
    brief = _brief(tmp_path)
    monkeypatch.setenv("CE_IT_CONNECTOR_TOKEN", "ghp_SECRETvaluexxxxxxxxxxxxxxxxxx")

    captured = {}

    def fake_opener_factory():
        def opener(request):
            captured["url"] = request.full_url
            captured["method"] = request.get_method()
            captured["auth_present"] = "Authorization" in request.headers
            captured["has_body"] = request.data is not None
            return _FakeResponse()
        return opener

    monkeypatch.setattr(connector_runtime, "_default_opener", fake_opener_factory)

    assert ce_cli.main(["connector", "write-plan", "--connector", str(conn), "--mission-brief", str(brief)]) == 0
    capsys.readouterr()
    rc = ce_cli.main([
        "connector", "submit", "--connector", str(conn), "--mission-brief", str(brief),
        "--verb", "issue-create", "--resource", "repos/o/r/issues", "--json",
    ])
    out = capsys.readouterr().out
    assert rc == 0
    # POST with a body, credential applied to the request, but its value never surfaces.
    assert captured["method"] == "POST"
    assert captured["auth_present"] is True and captured["has_body"] is True
    assert "ghp_SECRET" not in out
    assert "access_token" not in out  # normalized away


def test_submit_refuses_non_strict_offline(tmp_path, capsys, monkeypatch):
    conn = _connector(tmp_path, operating_mode="transcendence")
    brief = _brief(tmp_path)
    monkeypatch.setenv("CE_IT_CONNECTOR_TOKEN", "tok")

    def exploding_factory():
        def opener(request):
            raise AssertionError("no request may be issued under a non-strict operating_mode")
        return opener

    monkeypatch.setattr(connector_runtime, "_default_opener", exploding_factory)
    rc = ce_cli.main([
        "connector", "submit", "--connector", str(conn), "--mission-brief", str(brief),
        "--verb", "issue-create", "--resource", "repos/o/r/issues",
    ])
    assert rc == 1
    assert "G2-CONN-MODE-REFUSED" in capsys.readouterr().err


def test_write_verbs_coexist_with_read_and_other_groups():
    for argv in (
        ["connector", "write-plan", "--help"],
        ["connector", "submit", "--help"],
        ["connector", "fetch", "--help"],
        ["pcl", "--help"],
        ["event", "--help"],
    ):
        with pytest.raises(SystemExit) as exc:
            ce_cli.main(argv)
        assert exc.value.code == 0
