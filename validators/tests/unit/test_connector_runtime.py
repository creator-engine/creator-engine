"""Unit tests for the G2.005.1 connector read-only runtime.

Fully offline: the network is reached only through an injected fake opener/client.
Asserts read-only enforcement, credential-by-reference (value never exposed),
redaction-safe receipts, and fail-closed transport.
"""
from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from creator_engine_validator import connector_runtime as rt


def _valid_connector(**override) -> dict:
    rec = {
        "connector_id": "conn-tmp-0001",
        "connector_kind": "tracker",
        "provider_class": "issue-tracker",
        "capability": {"scope": "read_only", "verbs": ["issue-read"]},
        "credential_ref": {"ref_kind": "env_var_name", "ref_name": "CE_TEST_CONNECTOR_TOKEN"},
        "emitting_role": "operator",
        "operating_mode": "strict",
        "recorded_at": "2026-06-01T03:59:51Z",
    }
    rec.update(override)
    return rec


def _valid_brief(**override) -> dict:
    rec = {
        "brief_id": "mb-tmp-0001",
        "assignment_ref": "lane:tmp",
        "declared_mutation_classes": ["tracker_mirror"],
        "capability_scope": "read_only",
        "emitting_role": "controller",
        "operating_mode": "strict",
        "recorded_at": "2026-06-01T03:59:51Z",
        "signature": {"scheme": "reserved-shape-only", "key_id": "operator-reserved", "value": "reserved-inactive"},
    }
    rec.update(override)
    return rec


def _write(tmp_path: Path, key: str, rec: dict, name: str) -> Path:
    p = tmp_path / name
    p.write_text(yaml.safe_dump({key: rec}), encoding="utf-8")
    return p


@pytest.fixture()
def conn_path(tmp_path: Path) -> Path:
    return _write(tmp_path, "connector", _valid_connector(), "c.ce.yml")


@pytest.fixture()
def brief_path(tmp_path: Path) -> Path:
    return _write(tmp_path, "mission_brief", _valid_brief(), "m.ce.yml")


class _FakeResponse:
    def __init__(self, body: bytes, status: int = 200):
        self._body = body
        self.status = status

    def read(self) -> bytes:
        return self._body


# --- credential by reference -------------------------------------------------
def test_resolve_credential_present_but_value_never_exposed(monkeypatch):
    monkeypatch.setenv("CE_TEST_CONNECTOR_TOKEN", "ghp_SECRETxxxxxxxxxxxxxxxxxxxxxxxx")
    handle = rt.resolve_credential(_valid_connector())
    assert handle.present is True
    # The value must never appear in repr/str.
    assert "ghp_SECRET" not in repr(handle) and "ghp_SECRET" not in str(handle)
    # It is available only to build the request header.
    assert handle.auth_header()["Authorization"].startswith("Bearer ")


def test_resolve_credential_absent_env(monkeypatch):
    monkeypatch.delenv("CE_TEST_CONNECTOR_TOKEN", raising=False)
    handle = rt.resolve_credential(_valid_connector())
    assert handle.present is False
    assert handle.auth_header() == {}


def test_resolve_credential_none_kind_is_anonymous():
    handle = rt.resolve_credential(_valid_connector(credential_ref={"ref_kind": "none", "ref_name": "unused"}))
    assert handle.present is False and handle.auth_header() == {}


# --- read plan / read-only enforcement --------------------------------------
def test_build_read_plan_accepts_read_only():
    plan = rt.build_read_plan(_valid_connector(), _valid_brief())
    assert plan.capability_scope == "read_only"
    assert plan.read_verbs == ("issue-read",)


def test_build_read_plan_refuses_write_scope():
    conn = _valid_connector(capability={"scope": "write", "verbs": ["issue-create"]})
    with pytest.raises(rt.WriteRefused):
        rt.build_read_plan(conn, _valid_brief())


def test_build_read_plan_refuses_non_read_verb():
    conn = _valid_connector(capability={"scope": "read_only", "verbs": ["issue-create"]})
    with pytest.raises(rt.ConnectorScopeError):
        rt.build_read_plan(conn, _valid_brief())


def test_build_read_plan_refuses_write_brief_scope():
    with pytest.raises(rt.WriteRefused):
        rt.build_read_plan(_valid_connector(), _valid_brief(capability_scope="write"))


# --- read client (injected opener; no network) ------------------------------
def test_urllib_client_builds_get_with_auth_and_parses(monkeypatch):
    captured = {}

    def fake_opener(request):
        captured["url"] = request.full_url
        captured["method"] = request.get_method()
        captured["auth"] = request.headers.get("Authorization")
        return _FakeResponse(b'[{"id": 1, "number": 7, "title": "x", "state": "open"}]')

    client = rt.UrllibGitHubReadClient(base_url="https://api.example.test", opener=fake_opener)
    handle = rt.CredentialHandle(present=True, ref_kind="env_var_name", ref_name="X", _value="tok")
    resp = client.get("repos/o/r/issues", credential=handle)
    assert captured["url"] == "https://api.example.test/repos/o/r/issues"
    assert captured["method"] == "GET"
    assert captured["auth"] == "Bearer tok"
    assert resp.status == 200 and resp.body[0]["number"] == 7


def test_urllib_client_fails_closed_on_transport_error():
    import urllib.error

    def boom(request):
        raise urllib.error.URLError("offline")

    client = rt.UrllibGitHubReadClient(opener=boom)
    with pytest.raises(rt.ConnectorNetworkError):
        client.get("x", credential=rt.CredentialHandle(present=False, ref_kind="none", ref_name="n"))


def test_null_client_fails_closed():
    with pytest.raises(rt.ConnectorNetworkError):
        rt.NullReadClient().get("x", credential=rt.CredentialHandle(present=False, ref_kind="none", ref_name="n"))


# --- normalization (redaction-safe) -----------------------------------------
def test_normalize_drops_unbounded_and_secret_fields():
    body = [{"id": 1, "number": 7, "title": "t", "state": "open", "secret_token": "ghp_leak", "body": "x"}]
    out = rt.normalize_results(body)
    assert out == [{"id": 1, "number": 7, "title": "t", "state": "open"}]
    assert "secret_token" not in out[0] and "body" not in out[0]


# --- fetch (injected client; receipt carries no credential) -----------------
def test_fetch_returns_redaction_safe_receipt(conn_path, brief_path):
    class FakeClient:
        def get(self, resource, *, credential):
            assert resource == "repos/o/r/issues"
            return rt.ReadResponse(status=200, body=[{"id": 9, "number": 3, "title": "z", "state": "open", "token": "ghp_x"}])

    receipt = rt.fetch(connector_path=conn_path, mission_brief_path=brief_path, resource="repos/o/r/issues", client=FakeClient())
    d = receipt.to_dict()
    assert d["status"] == 200 and d["result_count"] == 1
    assert d["results"][0] == {"id": 9, "number": 3, "title": "z", "state": "open"}
    assert d["credential_ref_name"] == "CE_TEST_CONNECTOR_TOKEN"
    # No credential value anywhere in the serialized receipt.
    assert "ghp_x" not in str(d) and "token" not in d["results"][0]


def test_fetch_refuses_write_before_any_request(tmp_path):
    conn = _write(tmp_path, "connector", _valid_connector(capability={"scope": "write", "verbs": ["issue-create"]}), "c.ce.yml")
    brief = _write(tmp_path, "mission_brief", _valid_brief(), "m.ce.yml")

    class ExplodingClient:
        def get(self, resource, *, credential):
            raise AssertionError("client must not be called when write is refused")

    with pytest.raises(rt.WriteRefused):
        rt.fetch(connector_path=conn, mission_brief_path=brief, resource="x", client=ExplodingClient())


def test_fetch_default_client_is_offline_failclosed(conn_path, brief_path):
    # Default client with an opener that simulates offline -> fail closed, no exception leak of secrets.
    import urllib.error

    def offline(request):
        raise urllib.error.URLError("no network")

    with pytest.raises(rt.ConnectorNetworkError):
        rt.fetch(connector_path=conn_path, mission_brief_path=brief_path, resource="repos/o/r/issues", opener=offline)


# --- loading reuses the G2.005.0 validator ----------------------------------
def test_load_connector_rejects_invalid(tmp_path):
    bad = _write(tmp_path, "connector", _valid_connector(connector_kind="ci"), "bad.ce.yml")  # unknown kind
    with pytest.raises(rt.ConnectorValidationError):
        rt.load_connector(bad)


def test_runtime_does_not_import_other_feature_runtime():
    import ast

    tree = ast.parse(Path(rt.__file__).read_text(encoding="utf-8"))
    imported: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            base = node.module or ""
            imported.add(base)
            imported.update(f"{base}.{n.name}" for n in node.names)
        elif isinstance(node, ast.Import):
            imported.update(n.name for n in node.names)
    assert not any(("pcl" in m or "ce_event" in m or "distributed_identity" in m) for m in imported), imported
