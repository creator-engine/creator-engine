from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[3]
PARSER_PATH = REPO_ROOT / "tools" / "ce-ops-autoclose" / "parse_issue_refs.py"
SCRIPT_PATH = REPO_ROOT / ".github" / "scripts" / "ceops_autoclose.py"
CE_REF = "ce-ops" + "#7"


def _load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _load_parser():
    return _load_module(PARSER_PATH, "parse_issue_refs")


def _load_autoclose():
    return _load_module(SCRIPT_PATH, "ceops_autoclose")


def _context(body: str) -> dict[str, str]:
    return {
        "body": body,
        "merge_commit_sha": "abc123",
        "number": "42",
        "repository": "creator-engine/creator-engine",
        "title": f"feat({CE_REF}): evidence gate",
        "url": "https://github.com/creator-engine/creator-engine/pull/42",
    }


def test_parse_acceptance_evidence_returns_value_when_present():
    refs = _load_parser()

    assert (
        refs.parse_acceptance_evidence(
            "Summary\n\nAcceptance-Evidence: validators/tests/unit/test_p2_acceptance_evidence.py\n"
        )
        == "validators/tests/unit/test_p2_acceptance_evidence.py"
    )


def test_parse_acceptance_evidence_returns_none_when_absent():
    refs = _load_parser()

    assert refs.parse_acceptance_evidence(f"Closes {CE_REF}\nNo evidence field here.") is None


def test_parse_acceptance_evidence_is_whitespace_tolerant():
    refs = _load_parser()

    assert refs.parse_acceptance_evidence("   Acceptance-Evidence:   pytest path::test_name   ") == (
        "pytest path::test_name"
    )


def test_directive_issue_without_evidence_posts_warning_comment_and_does_not_close(monkeypatch):
    autoclose = _load_autoclose()
    calls = []

    def fake_api_json(method, path, token, payload=None):
        calls.append((method, path, token, payload))
        if method == "GET":
            return {"state": "open", "labels": [{"name": "directive"}]}
        return None

    monkeypatch.setattr(autoclose, "_api_json", fake_api_json)

    autoclose.close_issue_if_open(7, "token", _context(f"Closes {CE_REF}"))

    post_calls = [call for call in calls if call[0] == "POST"]
    patch_calls = [call for call in calls if call[0] == "PATCH"]
    assert len(post_calls) == 1
    assert patch_calls == []
    assert "Acceptance-Evidence required" in post_calls[0][3]["body"]
    assert "https://github.com/creator-engine/creator-engine/pull/42" in post_calls[0][3]["body"]


def test_warn_comment_post_failure_leaves_issue_open(monkeypatch):
    autoclose = _load_autoclose()
    calls = []

    def fake_api_json(method, path, token, payload=None):
        calls.append((method, path, token, payload))
        if method == "GET" and path.endswith("/issues/7"):
            return {"state": "open", "labels": [{"name": "directive"}]}
        if method == "GET" and path.endswith("/issues/7/comments"):
            return []
        if method == "POST" and path.endswith("/issues/7/comments"):
            raise RuntimeError("simulated API failure: 503 Service Unavailable")
        if method == "PATCH":
            raise AssertionError("close must not be called when warn POST fails")
        return None

    monkeypatch.setattr(autoclose, "_api_json", fake_api_json)

    autoclose.close_issue_if_open(7, "token", _context(f"Closes {CE_REF}"))

    assert not any(call[0] == "PATCH" for call in calls)


def test_directive_issue_with_evidence_closes_normally(monkeypatch):
    autoclose = _load_autoclose()
    calls = []

    def fake_api_json(method, path, token, payload=None):
        calls.append((method, path, token, payload))
        if method == "GET":
            return {"state": "open", "labels": [{"name": "directive"}]}
        return None

    monkeypatch.setattr(autoclose, "_api_json", fake_api_json)

    autoclose.close_issue_if_open(
        7,
        "token",
        _context(
            f"Closes {CE_REF}\n"
            "Acceptance-Evidence: validators/tests/unit/test_p2_acceptance_evidence.py"
        ),
    )

    assert any(call[0] == "POST" for call in calls)
    assert any(
        call[0] == "PATCH" and call[3] == {"state": "closed", "state_reason": "completed"}
        for call in calls
    )


def test_non_directive_issue_without_evidence_closes_normally(monkeypatch):
    autoclose = _load_autoclose()
    calls = []

    def fake_api_json(method, path, token, payload=None):
        calls.append((method, path, token, payload))
        if method == "GET":
            return {"state": "open", "labels": [{"name": "bug"}]}
        return None

    monkeypatch.setattr(autoclose, "_api_json", fake_api_json)

    autoclose.close_issue_if_open(7, "token", _context(f"Closes {CE_REF}"))

    assert any(call[0] == "PATCH" for call in calls)


@pytest.mark.parametrize("context_source", ["event", "env"])
def test_token_absent_returns_1_and_logs_error(tmp_path, monkeypatch, capsys, context_source):
    autoclose = _load_autoclose()
    monkeypatch.delenv("CE_CROSS_REPO_TOKEN", raising=False)
    monkeypatch.delenv("CE_OPS_TOKEN", raising=False)

    if context_source == "event":
        event_path = tmp_path / "event.json"
        event_path.write_text(
            json.dumps(
                {
                    "repository": {"full_name": "creator-engine/creator-engine"},
                    "pull_request": {
                        "merged": True,
                        "number": 42,
                        "title": f"feat({CE_REF}): evidence gate",
                        "body": f"Closes {CE_REF}",
                        "base": {"ref": "main"},
                    },
                }
            ),
            encoding="utf-8",
        )
        monkeypatch.setenv("GITHUB_EVENT_PATH", str(event_path))
    else:
        monkeypatch.delenv("GITHUB_EVENT_PATH", raising=False)
        monkeypatch.setenv("PR_TITLE", f"feat({CE_REF}): evidence gate")
        monkeypatch.setenv("PR_BODY", f"Closes {CE_REF}")
        monkeypatch.setenv("PR_BASE_REF", "main")

    assert autoclose.main() == 1
    out = capsys.readouterr().out
    assert "::error::" in out
    assert "::warning::" not in out
