"""Integration tests for `ce connector fetch --provider` (G2.005.3 tracker read).

Exercises the Jira and GitLab read adapters end-to-end through `ce_cli.main` with the
network seam monkeypatched to a fake opener, so the test is fully network-free. Asserts
provider selection, read-only enforcement, credential-by-reference (no value leaks),
unknown-provider fail-closed, and that the tracker providers co-exist with the GitHub
read/write verbs and the other `ce` groups.
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
        "connector_id": "conn-tit-0001",
        "connector_kind": "tracker",
        "provider_class": "issue-tracker",
        "capability": {"scope": "read_only", "verbs": ["issue-read"]},
        "credential_ref": {"ref_kind": "env_var_name", "ref_name": "CE_IT_CONNECTOR_TOKEN"},
        "emitting_role": "operator",
        "operating_mode": "strict",
        "recorded_at": "2026-06-01T06:28:39Z",
    }
    rec.update(override)
    p = tmp_path / "connector.ce.yml"
    p.write_text(yaml.safe_dump({"connector": rec}), encoding="utf-8")
    return p


def _brief(tmp_path: Path, **override) -> Path:
    rec = {
        "brief_id": "mb-tit-0001",
        "assignment_ref": "lane:tit",
        "declared_mutation_classes": ["docs", "tracker_mirror"],
        "capability_scope": "read_only",
        "emitting_role": "controller",
        "operating_mode": "strict",
        "recorded_at": "2026-06-01T06:28:39Z",
        "signature": {"scheme": "reserved-shape-only", "key_id": "operator-reserved", "value": "reserved-inactive"},
    }
    rec.update(override)
    p = tmp_path / "brief.ce.yml"
    p.write_text(yaml.safe_dump({"mission_brief": rec}), encoding="utf-8")
    return p


class _FakeResponse:
    status = 200

    def read(self) -> bytes:
        return b'[{"id": 5, "number": 11, "title": "issue", "state": "open", "access_token": "ghp_leak"}]'


@pytest.mark.parametrize("provider", ["jira", "gitlab"])
def test_fetch_provider_roundtrip_offline(tmp_path, capsys, monkeypatch, provider):
    conn = _connector(tmp_path)
    brief = _brief(tmp_path)
    monkeypatch.setenv("CE_IT_CONNECTOR_TOKEN", "ghp_SECRETvaluexxxxxxxxxxxxxxxxxx")

    captured = {}

    def fake_opener_factory():
        def opener(request):
            captured["url"] = request.full_url
            captured["method"] = request.get_method()
            captured["auth_present"] = ("Authorization" in request.headers) or ("Private-token" in request.headers)
            return _FakeResponse()
        return opener

    monkeypatch.setattr(connector_runtime, "_default_opener", fake_opener_factory)
    rc = ce_cli.main([
        "connector", "fetch", "--connector", str(conn), "--mission-brief", str(brief),
        "--resource", "issues", "--provider", provider, "--json",
    ])
    out = capsys.readouterr().out
    assert rc == 0
    assert captured["method"] == "GET"
    assert captured["auth_present"] is True
    assert "ghp_SECRET" not in out and "access_token" not in out  # no leak; normalized away


def test_fetch_unknown_provider_is_rejected_by_argparse(tmp_path, capsys):
    conn = _connector(tmp_path)
    brief = _brief(tmp_path)
    with pytest.raises(SystemExit) as exc:  # argparse choices reject before any work
        ce_cli.main([
            "connector", "fetch", "--connector", str(conn), "--mission-brief", str(brief),
            "--resource", "issues", "--provider", "bitbucket",
        ])
    assert exc.value.code == 2


def test_fetch_gitlab_refuses_write_scope_offline(tmp_path, capsys, monkeypatch):
    conn = _connector(tmp_path, capability={"scope": "write", "verbs": ["issue-create"]})
    brief = _brief(tmp_path)

    def exploding_factory():
        def opener(request):
            raise AssertionError("no request may be issued when write is refused")
        return opener

    monkeypatch.setattr(connector_runtime, "_default_opener", exploding_factory)
    rc = ce_cli.main([
        "connector", "fetch", "--connector", str(conn), "--mission-brief", str(brief),
        "--resource", "issues", "--provider", "gitlab",
    ])
    assert rc == 1
    assert "G2-CONN-WRITE-REFUSED" in capsys.readouterr().err


def test_tracker_providers_coexist_with_github_and_other_groups():
    for argv in (
        ["connector", "fetch", "--help"],
        ["connector", "write-plan", "--help"],
        ["connector", "submit", "--help"],
        ["pcl", "--help"],
        ["event", "--help"],
    ):
        with pytest.raises(SystemExit) as exc:
            ce_cli.main(argv)
        assert exc.value.code == 0
