"""Unit tests for the G2.005.3 read-only tracker adapters (Jira + GitLab).

Fully offline: the network is reached only through an injected fake opener/client.
Asserts the provider registry + selection, per-provider request shaping + redaction-safe
normalization, read-only enforcement across providers, and fail-closed transport. The
GitHub read/write paths are exercised by their own test files (untouched canaries).
"""
from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from creator_engine_validator import connector_runtime as rt


def _conn(**override) -> dict:
    rec = {
        "connector_id": "conn-trk-0001",
        "connector_kind": "tracker",
        "provider_class": "issue-tracker",
        "capability": {"scope": "read_only", "verbs": ["issue-read"]},
        "credential_ref": {"ref_kind": "env_var_name", "ref_name": "CE_TEST_CONNECTOR_TOKEN"},
        "emitting_role": "operator",
        "operating_mode": "strict",
        "recorded_at": "2026-06-01T06:28:39Z",
    }
    rec.update(override)
    return rec


def _brief(**override) -> dict:
    rec = {
        "brief_id": "mb-trk-0001",
        "assignment_ref": "lane:g20053",
        "declared_mutation_classes": ["tracker_mirror"],
        "capability_scope": "read_only",
        "emitting_role": "controller",
        "operating_mode": "strict",
        "recorded_at": "2026-06-01T06:28:39Z",
        "signature": {"scheme": "reserved-shape-only", "key_id": "operator-reserved", "value": "reserved-inactive"},
    }
    rec.update(override)
    return rec


def _file(tmp_path: Path, key: str, rec: dict, name: str) -> Path:
    p = tmp_path / name
    p.write_text(yaml.safe_dump({key: rec}), encoding="utf-8")
    return p


@pytest.fixture()
def conn_path(tmp_path: Path) -> Path:
    return _file(tmp_path, "connector", _conn(), "c.ce.yml")


@pytest.fixture()
def brief_path(tmp_path: Path) -> Path:
    return _file(tmp_path, "mission_brief", _brief(), "m.ce.yml")


class _FakeResponse:
    def __init__(self, body: bytes, status: int = 200):
        self._body = body
        self.status = status

    def read(self) -> bytes:
        return self._body


# --- provider registry + selection ------------------------------------------
def test_registry_and_default():
    assert rt.DEFAULT_PROVIDER == "github"
    assert set(rt.PROVIDER_READ_CLIENTS) == {"github", "jira", "gitlab"}


def test_read_client_for_selects_each_provider():
    assert rt._read_client_for("github", base_url=None, opener=None).name == "urllib-github"
    assert rt._read_client_for("jira", base_url=None, opener=None).name == "urllib-jira"
    assert rt._read_client_for("gitlab", base_url=None, opener=None).name == "urllib-gitlab"
    # case/space-insensitive selection
    assert rt._read_client_for(" GitLab ", base_url=None, opener=None).name == "urllib-gitlab"


def test_read_client_for_unknown_provider_fails_closed():
    with pytest.raises(rt.ProviderError) as exc:
        rt._read_client_for("bitbucket", base_url=None, opener=None)
    assert exc.value.code == "G2-CONN-PROVIDER"


def test_auth_header_for_raw_scheme_sets_bare_value():
    h = rt.CredentialHandle(present=True, ref_kind="env_var_name", ref_name="X", _value="tok")
    assert h.auth_header_for(header="PRIVATE-TOKEN", scheme="raw") == {"PRIVATE-TOKEN": "tok"}
    assert h.auth_header_for() == {"Authorization": "Bearer tok"}
    assert rt.CredentialHandle(present=False, ref_kind="none", ref_name="n").auth_header_for() == {}


# --- Jira adapter (injected opener; no network) -----------------------------
def test_jira_client_builds_get_with_bearer_and_parses():
    captured = {}

    def fake_opener(request):
        captured["url"] = request.full_url
        captured["method"] = request.get_method()
        captured["auth"] = request.headers.get("Authorization")
        return _FakeResponse(b'{"id": 3, "number": 9, "title": "t", "state": "open"}')

    client = rt.UrllibJiraReadClient(base_url="https://acme.atlassian.net/rest/api/3", opener=fake_opener)
    handle = rt.CredentialHandle(present=True, ref_kind="env_var_name", ref_name="X", _value="jtok")
    resp = client.get("issue/PROJ-1", credential=handle)
    assert captured["url"] == "https://acme.atlassian.net/rest/api/3/issue/PROJ-1"
    assert captured["method"] == "GET"
    assert captured["auth"] == "Bearer jtok"
    assert resp.status == 200 and resp.body["number"] == 9


def test_jira_client_default_base_and_failclosed():
    import urllib.error

    assert rt.UrllibJiraReadClient().base_url == rt.DEFAULT_JIRA_API_BASE.rstrip("/")

    def boom(request):
        raise urllib.error.URLError("offline")

    with pytest.raises(rt.ConnectorNetworkError):
        rt.UrllibJiraReadClient(opener=boom).get("x", credential=rt.CredentialHandle(present=False, ref_kind="none", ref_name="n"))


# --- GitLab adapter (injected opener; no network) ---------------------------
def test_gitlab_client_builds_get_with_private_token_and_parses():
    captured = {}

    def fake_opener(request):
        captured["url"] = request.full_url
        captured["method"] = request.get_method()
        captured["private_token"] = request.headers.get("Private-token")  # urllib title-cases header keys
        captured["auth"] = request.headers.get("Authorization")
        return _FakeResponse(b'[{"id": 5, "name": "proj", "state": "opened"}]')

    client = rt.UrllibGitLabReadClient(opener=fake_opener)
    handle = rt.CredentialHandle(present=True, ref_kind="env_var_name", ref_name="X", _value="gltok")
    resp = client.get("projects/1/issues", credential=handle)
    assert captured["url"] == "https://gitlab.com/api/v4/projects/1/issues"
    assert captured["method"] == "GET"
    assert captured["private_token"] == "gltok"        # GitLab native header
    assert captured["auth"] is None                    # not a Bearer
    assert resp.status == 200 and resp.body[0]["id"] == 5


def test_gitlab_client_failclosed_on_transport_error():
    import urllib.error

    def boom(request):
        raise urllib.error.URLError("offline")

    with pytest.raises(rt.ConnectorNetworkError):
        rt.UrllibGitLabReadClient(opener=boom).get("x", credential=rt.CredentialHandle(present=True, ref_kind="env_var_name", ref_name="X", _value="t"))


# --- fetch() provider routing -----------------------------------------------
def test_fetch_via_jira_returns_redaction_safe_receipt(monkeypatch, conn_path, brief_path):
    monkeypatch.setenv("CE_TEST_CONNECTOR_TOKEN", "ghp_SECRETxxxxxxxxxxxxxxxxxxxxxxxx")

    def fake_opener(request):
        assert request.full_url.endswith("/issue/PROJ-1")
        return _FakeResponse(b'{"id": 1, "number": 2, "title": "z", "state": "open", "token": "leak"}')

    receipt = rt.fetch(
        connector_path=conn_path, mission_brief_path=brief_path, resource="issue/PROJ-1",
        provider="jira", opener=fake_opener,
    )
    d = receipt.to_dict()
    assert d["status"] == 200 and d["result_count"] == 1
    assert d["results"][0] == {"id": 1, "number": 2, "title": "z", "state": "open"}
    assert "ghp_SECRET" not in str(d) and "token" not in d["results"][0]


def test_fetch_unknown_provider_fails_closed_before_request(monkeypatch, conn_path, brief_path):
    monkeypatch.setenv("CE_TEST_CONNECTOR_TOKEN", "tok")
    with pytest.raises(rt.ProviderError):
        rt.fetch(connector_path=conn_path, mission_brief_path=brief_path, resource="x", provider="bitbucket")


def test_fetch_refuses_write_scope_regardless_of_provider(tmp_path):
    conn = _file(tmp_path, "connector", _conn(capability={"scope": "write", "verbs": ["issue-create"]}), "c.ce.yml")
    brief = _file(tmp_path, "mission_brief", _brief(), "m.ce.yml")

    def exploding(request):
        raise AssertionError("no request may be issued when write is refused")

    with pytest.raises(rt.WriteRefused):
        rt.fetch(connector_path=conn, mission_brief_path=brief, resource="x", provider="gitlab", opener=exploding)


def test_fetch_default_provider_github_unchanged(monkeypatch, conn_path, brief_path):
    monkeypatch.setenv("CE_TEST_CONNECTOR_TOKEN", "tok")
    captured = {}

    def fake_opener(request):
        captured["url"] = request.full_url
        return _FakeResponse(b'[{"id": 1, "number": 2, "title": "t", "state": "open"}]')

    receipt = rt.fetch(connector_path=conn_path, mission_brief_path=brief_path, resource="repos/o/r/issues", opener=fake_opener)
    assert captured["url"].startswith(rt.DEFAULT_GITHUB_API_BASE)  # github is the default provider
    assert receipt.status == 200 and receipt.result_count == 1
