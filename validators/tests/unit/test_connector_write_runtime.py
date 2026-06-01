"""Unit tests for the G2.005.2 connector write runtime (strict mode).

Fully offline: the network is reached only through an injected fake opener/client.
Asserts CE operating_mode: strict enforcement, tracker_mirror-bounded capability,
credential-REQUIRED-by-reference (value never exposed), redaction-safe write-receipts,
and fail-closed transport. The G2.005.1 read path is exercised by its own test file
(left untouched as a canary).
"""
from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from creator_engine_validator import connector_runtime as rt


def _write_connector(**override) -> dict:
    rec = {
        "connector_id": "conn-write-0001",
        "connector_kind": "tracker",
        "provider_class": "issue-tracker",
        "capability": {"scope": "write", "verbs": ["issue-create", "issue-update", "pr-comment"]},
        "credential_ref": {"ref_kind": "env_var_name", "ref_name": "CE_TEST_CONNECTOR_TOKEN"},
        "emitting_role": "operator",
        "operating_mode": "strict",
        "recorded_at": "2026-06-01T05:16:58Z",
    }
    rec.update(override)
    return rec


def _write_brief(**override) -> dict:
    rec = {
        "brief_id": "mb-write-0001",
        "assignment_ref": "lane:g20052",
        "declared_mutation_classes": ["tracker_mirror"],
        "capability_scope": "write",
        "emitting_role": "controller",
        "operating_mode": "strict",
        "recorded_at": "2026-06-01T05:16:58Z",
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
    return _file(tmp_path, "connector", _write_connector(), "c.ce.yml")


@pytest.fixture()
def brief_path(tmp_path: Path) -> Path:
    return _file(tmp_path, "mission_brief", _write_brief(), "m.ce.yml")


class _FakeResponse:
    def __init__(self, body: bytes, status: int = 201):
        self._body = body
        self.status = status

    def read(self) -> bytes:
        return self._body


# --- write plan / strict + tracker_mirror enforcement -----------------------
def test_build_write_plan_accepts_strict_write():
    plan = rt.build_write_plan(_write_connector(), _write_brief())
    assert plan.capability_scope == "write"
    assert plan.operating_mode == "strict"
    assert plan.write_verbs == ("issue-create", "issue-update", "pr-comment")


def test_build_write_plan_refuses_read_only_connector():
    conn = _write_connector(capability={"scope": "read_only", "verbs": ["issue-read"]})
    with pytest.raises(rt.ReadOnlyRefused):
        rt.build_write_plan(conn, _write_brief())


def test_build_write_plan_refuses_verb_outside_tracker_mirror():
    conn = _write_connector(capability={"scope": "write", "verbs": ["issue-read"]})
    with pytest.raises(rt.ConnectorScopeError):
        rt.build_write_plan(conn, _write_brief())


def test_build_write_plan_refuses_auto_connector_mode():
    with pytest.raises(rt.ModeRefused):
        rt.build_write_plan(_write_connector(operating_mode="auto"), _write_brief())


def test_build_write_plan_refuses_transcendence_brief_mode():
    with pytest.raises(rt.ModeRefused):
        rt.build_write_plan(_write_connector(), _write_brief(operating_mode="transcendence"))


def test_build_write_plan_refuses_read_only_brief():
    with pytest.raises(rt.ReadOnlyRefused):
        rt.build_write_plan(_write_connector(), _write_brief(capability_scope="read_only"))


def test_build_write_plan_refuses_brief_without_tracker_mirror_class():
    with pytest.raises(rt.ConnectorScopeError):
        rt.build_write_plan(_write_connector(), _write_brief(declared_mutation_classes=["docs"]))


# --- write client (injected opener; no network) -----------------------------
@pytest.mark.parametrize(
    "verb,method", [("issue-create", "POST"), ("pr-comment", "POST"), ("issue-update", "PATCH")]
)
def test_urllib_write_client_builds_method_with_auth_body(verb, method):
    captured = {}

    def fake_opener(request):
        captured["url"] = request.full_url
        captured["method"] = request.get_method()
        captured["auth"] = request.headers.get("Authorization")
        captured["ctype"] = request.headers.get("Content-type")
        captured["data"] = request.data
        return _FakeResponse(b'{"id": 5, "number": 12, "html_url": "https://x/12"}')

    client = rt.UrllibGitHubWriteClient(base_url="https://api.example.test", opener=fake_opener)
    handle = rt.CredentialHandle(present=True, ref_kind="env_var_name", ref_name="X", _value="tok")
    resp = client.submit(verb, "repos/o/r/issues", {"title": "hi"}, credential=handle)
    assert captured["url"] == "https://api.example.test/repos/o/r/issues"
    assert captured["method"] == method
    assert captured["auth"] == "Bearer tok"
    assert captured["ctype"] == "application/json"
    assert b'"title"' in captured["data"]
    assert resp.status == 201 and resp.body["number"] == 12


def test_urllib_write_client_refuses_anonymous():
    client = rt.UrllibGitHubWriteClient(opener=lambda r: _FakeResponse(b"{}"))
    with pytest.raises(rt.CredentialMissing):
        client.submit("issue-create", "x", {}, credential=rt.CredentialHandle(present=False, ref_kind="none", ref_name="n"))


def test_urllib_write_client_refuses_unknown_verb():
    client = rt.UrllibGitHubWriteClient(opener=lambda r: _FakeResponse(b"{}"))
    handle = rt.CredentialHandle(present=True, ref_kind="env_var_name", ref_name="X", _value="tok")
    with pytest.raises(rt.ConnectorScopeError):
        client.submit("issue-delete", "x", {}, credential=handle)


def test_urllib_write_client_fails_closed_on_transport_error():
    import urllib.error

    def boom(request):
        raise urllib.error.URLError("offline")

    client = rt.UrllibGitHubWriteClient(opener=boom)
    handle = rt.CredentialHandle(present=True, ref_kind="env_var_name", ref_name="X", _value="tok")
    with pytest.raises(rt.ConnectorNetworkError):
        client.submit("issue-create", "x", {}, credential=handle)


def test_null_write_client_fails_closed():
    handle = rt.CredentialHandle(present=True, ref_kind="env_var_name", ref_name="X", _value="tok")
    with pytest.raises(rt.ConnectorNetworkError):
        rt.NullWriteClient().submit("issue-create", "x", {}, credential=handle)


# --- normalization (redaction-safe) -----------------------------------------
def test_normalize_write_result_drops_unbounded_and_secret_fields():
    body = {"id": 1, "number": 7, "html_url": "u", "state": "open", "token": "ghp_leak", "body": "x"}
    out = rt.normalize_write_result(body)
    assert out == {"id": 1, "number": 7, "html_url": "u", "state": "open"}
    assert "token" not in out and "body" not in out


# --- submit (injected client; receipt carries no credential) ----------------
def test_submit_returns_redaction_safe_receipt(monkeypatch, conn_path, brief_path):
    monkeypatch.setenv("CE_TEST_CONNECTOR_TOKEN", "ghp_SECRETxxxxxxxxxxxxxxxxxxxxxxxx")

    class FakeClient:
        def submit(self, verb, resource, payload, *, credential):
            assert verb == "issue-create" and resource == "repos/o/r/issues"
            assert payload == {"title": "hi"}
            return rt.WriteResponse(status=201, body={"id": 9, "number": 3, "html_url": "u", "token": "ghp_x"})

    receipt = rt.submit(
        connector_path=conn_path,
        mission_brief_path=brief_path,
        verb="issue-create",
        resource="repos/o/r/issues",
        payload={"title": "hi"},
        client=FakeClient(),
    )
    d = receipt.to_dict()
    assert d["status"] == 201 and d["verb"] == "issue-create" and d["operating_mode"] == "strict"
    assert d["result"] == {"id": 9, "number": 3, "html_url": "u"}
    assert d["credential_ref_name"] == "CE_TEST_CONNECTOR_TOKEN"
    # No credential/secret value anywhere in the serialized receipt.
    assert "ghp_SECRET" not in str(d) and "ghp_x" not in str(d) and "token" not in d["result"]


def test_submit_refuses_read_only_before_any_request(monkeypatch, tmp_path):
    monkeypatch.setenv("CE_TEST_CONNECTOR_TOKEN", "tok")
    conn = _file(tmp_path, "connector", _write_connector(capability={"scope": "read_only", "verbs": ["issue-read"]}), "c.ce.yml")
    brief = _file(tmp_path, "mission_brief", _write_brief(), "m.ce.yml")

    class ExplodingClient:
        def submit(self, *a, **k):
            raise AssertionError("client must not be called when the write is refused")

    with pytest.raises(rt.ReadOnlyRefused):
        rt.submit(connector_path=conn, mission_brief_path=brief, verb="issue-create", resource="x", client=ExplodingClient())


def test_submit_refuses_non_strict_before_any_request(monkeypatch, tmp_path):
    monkeypatch.setenv("CE_TEST_CONNECTOR_TOKEN", "tok")
    conn = _file(tmp_path, "connector", _write_connector(operating_mode="auto"), "c.ce.yml")
    brief = _file(tmp_path, "mission_brief", _write_brief(), "m.ce.yml")

    class ExplodingClient:
        def submit(self, *a, **k):
            raise AssertionError("client must not be called under a non-strict mode")

    with pytest.raises(rt.ModeRefused):
        rt.submit(connector_path=conn, mission_brief_path=brief, verb="issue-create", resource="x", client=ExplodingClient())


def test_submit_fails_closed_when_credential_absent(monkeypatch, conn_path, brief_path):
    monkeypatch.delenv("CE_TEST_CONNECTOR_TOKEN", raising=False)

    class ExplodingClient:
        def submit(self, *a, **k):
            raise AssertionError("client must not be called without a present credential")

    with pytest.raises(rt.CredentialMissing):
        rt.submit(connector_path=conn_path, mission_brief_path=brief_path, verb="issue-create", resource="x", client=ExplodingClient())


def test_submit_refuses_verb_not_permitted_by_connector(monkeypatch, tmp_path):
    monkeypatch.setenv("CE_TEST_CONNECTOR_TOKEN", "tok")
    conn = _file(tmp_path, "connector", _write_connector(capability={"scope": "write", "verbs": ["issue-create"]}), "c.ce.yml")
    brief = _file(tmp_path, "mission_brief", _write_brief(), "m.ce.yml")
    with pytest.raises(rt.ConnectorScopeError):
        rt.submit(connector_path=conn, mission_brief_path=brief, verb="pr-comment", resource="x")


def test_submit_default_client_is_offline_failclosed(monkeypatch, conn_path, brief_path):
    monkeypatch.setenv("CE_TEST_CONNECTOR_TOKEN", "tok")
    import urllib.error

    def offline(request):
        raise urllib.error.URLError("no network")

    with pytest.raises(rt.ConnectorNetworkError):
        rt.submit(connector_path=conn_path, mission_brief_path=brief_path, verb="issue-create", resource="x", opener=offline)


# --- loading reuses the G2.005.0 validator ----------------------------------
def test_load_rejects_write_connector_with_out_of_set_verb(tmp_path):
    # The substrate validator bounds write scope to tracker_mirror verbs; load must reject.
    bad = _file(tmp_path, "connector", _write_connector(capability={"scope": "write", "verbs": ["issue-read"]}), "bad.ce.yml")
    with pytest.raises(rt.ConnectorValidationError):
        rt.load_connector(bad)
