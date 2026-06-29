from __future__ import annotations

import io
import importlib.util
import json
from pathlib import Path


SCRIPT = (
    Path(__file__).resolve().parents[3]
    / "tools"
    / "support-agent"
    / "openrouter_model_cmd.py"
)


def _load_adapter():
    spec = importlib.util.spec_from_file_location("openrouter_model_cmd", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec is not None
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def _support_request_json(question: str = "How do I verify an install?") -> str:
    return json.dumps(
        {
            "question": question,
            "model": "claude-sonnet-4-6",
            "system_prompt": "Cite or refuse.",
            "bundle": {
                "version": 1,
                "corpus_sha256": "abc123",
                "eligible_paths": ["README.md"],
                "rejected": [],
                "missing": [],
                "skills": [
                    {
                        "name": "ce-support-install",
                        "family": "install",
                        "description": "Install docs.",
                        "sources": [
                            {
                                "path": "README.md",
                                "sha256": "def456",
                                "bytes": 42,
                                "lines": 2,
                            }
                        ],
                        "skill_md": "# ce-support-install",
                        "files": [
                            {
                                "path": "sources/README.md",
                                "content": "Run `ce verify-install`. Citation: README.md",
                            }
                        ],
                    }
                ],
            },
            "profile_contract": {"posture": "read-only"},
        },
        sort_keys=True,
    )


class _FakeResponse:
    status = 200

    def __enter__(self):
        return self

    def __exit__(self, _exc_type, _exc, _tb):
        return False

    def read(self):
        return json.dumps(
            {
                "choices": [
                    {
                        "message": {
                            "content": "Run `ce verify-install`. Citation: README.md"
                        }
                    }
                ]
            }
        ).encode("utf-8")


def test_success_prints_answer_and_exits_zero(monkeypatch):
    adapter = _load_adapter()
    seen = {}

    def fake_urlopen(req, timeout):
        seen["authorization"] = req.headers.get("Authorization")
        seen["timeout"] = timeout
        seen["body"] = json.loads(req.data.decode("utf-8"))
        return _FakeResponse()

    monkeypatch.setenv("CE_OPENROUTER_API_KEY", "sk-test-secret")
    monkeypatch.setattr(adapter.request, "urlopen", fake_urlopen)
    stdout = io.StringIO()
    stderr = io.StringIO()

    code = adapter.main(io.StringIO(_support_request_json()), stdout, stderr)

    assert code == 0
    assert stdout.getvalue() == "Run `ce verify-install`. Citation: README.md\n"
    assert stderr.getvalue() == ""
    assert seen["authorization"] == "Bearer sk-test-secret"
    assert seen["timeout"] == 120.0
    assert seen["body"]["model"] == adapter.DEFAULT_MODEL
    assert "How do I verify an install?" in seen["body"]["messages"][1]["content"]
    assert "README.md" in seen["body"]["messages"][1]["content"]


def test_missing_key_exits_nonzero(monkeypatch):
    adapter = _load_adapter()
    monkeypatch.delenv("CE_OPENROUTER_API_KEY", raising=False)
    stdout = io.StringIO()
    stderr = io.StringIO()

    code = adapter.main(io.StringIO(_support_request_json()), stdout, stderr)

    assert code != 0
    assert stdout.getvalue() == ""
    assert "CE_OPENROUTER_API_KEY is required" in stderr.getvalue()


def test_http_non_200_exits_nonzero(monkeypatch):
    adapter = _load_adapter()

    class ErrorResponse(_FakeResponse):
        status = 500

    monkeypatch.setenv("CE_OPENROUTER_API_KEY", "sk-test-secret")
    monkeypatch.setattr(adapter.request, "urlopen", lambda _req, timeout: ErrorResponse())
    stdout = io.StringIO()
    stderr = io.StringIO()

    code = adapter.main(io.StringIO(_support_request_json()), stdout, stderr)

    assert code != 0
    assert stdout.getvalue() == ""
    assert "OpenRouter HTTP error: 500" in stderr.getvalue()


def test_key_is_never_written_to_stdout(monkeypatch):
    adapter = _load_adapter()
    secret = "sk-test-never-print"
    monkeypatch.setenv("CE_OPENROUTER_API_KEY", secret)
    monkeypatch.setattr(adapter.request, "urlopen", lambda _req, timeout: _FakeResponse())
    stdout = io.StringIO()
    stderr = io.StringIO()

    code = adapter.main(io.StringIO(_support_request_json()), stdout, stderr)

    assert code == 0
    assert secret not in stdout.getvalue()
    assert secret not in stderr.getvalue()
