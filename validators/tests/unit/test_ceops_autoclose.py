from __future__ import annotations

import importlib.util
import json
import urllib.request
from pathlib import Path
from types import SimpleNamespace

import pytest


SCRIPT_PATH = Path(__file__).resolve().parents[3] / ".github" / "scripts" / "ceops_autoclose.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("ceops_autoclose", SCRIPT_PATH)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_refuses_when_shared_parser_shim_is_absent(monkeypatch):
    """A checkout missing the canonical parser shim must fail closed."""
    parser_path = (
        SCRIPT_PATH.parents[2]
        / "tools"
        / "ce-ops-autoclose"
        / "parse_issue_refs.py"
    )
    original_is_file = Path.is_file

    def is_file_except_parser_shim(path: Path) -> bool:
        if path == parser_path:
            return False
        return original_is_file(path)

    network_calls: list[object] = []

    def fail_if_networked(*args, **kwargs):
        network_calls.append((args, kwargs))
        raise AssertionError("missing parser shim must not make a network call")

    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    monkeypatch.setattr(Path, "is_file", is_file_except_parser_shim)
    monkeypatch.setattr(urllib.request, "urlopen", fail_if_networked)

    with pytest.raises(RuntimeError, match="issue-reference parser shim is unavailable"):
        _load_module()

    assert network_calls == []


def test_missing_parser_shim_alerts_before_failing_closed(monkeypatch):
    """A top-level shim refusal is surfaced through the non-blocking alert seam."""
    parser_path = (
        SCRIPT_PATH.parents[2]
        / "tools"
        / "ce-ops-autoclose"
        / "parse_issue_refs.py"
    )
    original_is_file = Path.is_file
    requests: list[tuple[urllib.request.Request, float]] = []

    def is_file_except_parser_shim(path: Path) -> bool:
        if path == parser_path:
            return False
        return original_is_file(path)

    class EmptyResponse:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, traceback):
            return False

        def read(self) -> bytes:
            return b""

    def capture_alert(request: urllib.request.Request, timeout: float):
        requests.append((request, timeout))
        return EmptyResponse()

    monkeypatch.setenv("GITHUB_TOKEN", "synthetic-alert-token")
    monkeypatch.setattr(Path, "is_file", is_file_except_parser_shim)
    monkeypatch.setattr(urllib.request, "urlopen", capture_alert)

    with pytest.raises(RuntimeError, match="^issue-reference parser shim is unavailable$"):
        _load_module()

    assert len(requests) == 1
    request, timeout = requests[0]
    assert request.get_method() == "POST"
    assert request.full_url.endswith("/repos/creator-engine/creator-engine/dispatches")
    assert timeout == 20
    assert json.loads(request.data.decode("utf-8")) == {
        "event_type": "governance-alert",
        "client_payload": {
            "source": "ceops_autoclose",
            "reason": "parser_shim_unavailable",
        },
    }


@pytest.mark.parametrize("failure_kind", ["execution", "binding"])
def test_broken_parser_shim_alerts_and_fails_closed_distinctly(monkeypatch, failure_kind):
    """Present-but-broken shims use the constant load-failed refusal path."""
    requests: list[tuple[urllib.request.Request, float]] = []

    class EmptyResponse:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, traceback):
            return False

        def read(self) -> bytes:
            return b""

    def capture_alert(request: urllib.request.Request, timeout: float):
        requests.append((request, timeout))
        return EmptyResponse()

    class BrokenLoader:
        def exec_module(self, module):
            if failure_kind == "execution":
                raise SyntaxError("synthetic broken shim")

    fake_spec = SimpleNamespace(loader=BrokenLoader())
    fake_module = (
        SimpleNamespace()
        if failure_kind == "binding"
        else SimpleNamespace(
            parse_title_refs=lambda text: [],
            parse_body_closing_refs=lambda text: [],
            parse_acceptance_evidence=lambda text: [],
            parse_all_refs=lambda title, body: [],
        )
    )
    outer_spec = importlib.util.spec_from_file_location("ceops_autoclose_broken_shim", SCRIPT_PATH)
    assert outer_spec is not None
    assert outer_spec.loader is not None
    outer_module = importlib.util.module_from_spec(outer_spec)

    monkeypatch.setenv("GITHUB_TOKEN", "synthetic-alert-token")
    monkeypatch.setattr(
        importlib.util,
        "spec_from_file_location",
        lambda *args, **kwargs: fake_spec,
    )
    monkeypatch.setattr(importlib.util, "module_from_spec", lambda spec: fake_module)
    monkeypatch.setattr(urllib.request, "urlopen", capture_alert)

    with pytest.raises(RuntimeError, match="^issue-reference parser shim failed to load$"):
        outer_spec.loader.exec_module(outer_module)

    assert len(requests) == 1
    request, timeout = requests[0]
    assert timeout == 20
    assert json.loads(request.data.decode("utf-8")) == {
        "event_type": "governance-alert",
        "client_payload": {
            "source": "ceops_autoclose",
            "reason": "parser_shim_load_failed",
        },
    }


def test_closing_keyword_with_separator_closes_ceops_ref():
    autoclose = _load_module()

    assert autoclose.parse_closing_ceops_refs("Closes ce-ops#5") == [5]


def test_closing_keyword_without_separator_does_not_close():
    autoclose = _load_module()

    assert autoclose.parse_closing_ceops_refs("Closesce-ops#5") == []


def test_bare_ceops_mentions_do_not_close():
    autoclose = _load_module()

    assert autoclose.parse_closing_ceops_refs("bare ce-ops#5mention") == []
    assert autoclose.parse_closing_ceops_refs("Related to ce-ops#5") == []
    assert autoclose.parse_closing_ceops_refs("Does not close ce-ops#13") == []


def test_multiple_refs_after_one_or_more_closing_keywords():
    autoclose = _load_module()

    assert autoclose.parse_closing_ceops_refs(
        "Closes ce-ops#5, ce-ops#6\nFixes ce-ops#7"
    ) == [5, 6, 7]


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("Fixes ce-ops#11", [11]),
        ("fixed creator-engine/ce-ops#12", [12]),
        ("RESOLVES ce-ops#13", [13]),
        ("resolve ce-ops#14", [14]),
        ("Closed ce-ops#15", [15]),
    ],
)
def test_closing_keyword_variants_are_case_insensitive(text, expected):
    autoclose = _load_module()

    assert autoclose.parse_closing_ceops_refs(text) == expected


def test_duplicate_refs_are_returned_once_in_first_seen_order():
    autoclose = _load_module()

    assert autoclose.parse_closing_ceops_refs(
        "Closes ce-ops#5, ce-ops#6. Resolves CE-OPS#5"
    ) == [5, 6]


def test_non_main_base_ref_is_noop(tmp_path, monkeypatch, capsys):
    autoclose = _load_module()
    event_path = tmp_path / "event.json"
    event_path.write_text(
        json.dumps(
            {
                "repository": {"full_name": "creator-engine/creator-engine"},
                "pull_request": {
                    "merged": True,
                    "number": 289,
                    "title": "Fix review",
                    "body": "Closes ce-ops#5",
                    "base": {"ref": "release/v3.5"},
                },
            }
        ),
        encoding="utf-8",
    )

    def fail_if_called(*args, **kwargs):
        raise AssertionError("non-main base must not call ce-ops API")

    monkeypatch.setenv("GITHUB_EVENT_PATH", str(event_path))
    monkeypatch.setenv("CE_OPS_TOKEN", "unused")
    monkeypatch.setattr(autoclose, "close_issue_if_open", fail_if_called)

    assert autoclose.main() == 0
    assert "not main" in capsys.readouterr().out


def test_title_bare_ce_num_egress_format():
    """[ce-egress] ce-NNN titles must be parsed from title."""
    from pathlib import Path
    import importlib.util
    parser_path = Path(__file__).resolve().parents[3] / "tools" / "ce-ops-autoclose" / "parse_issue_refs.py"
    spec = importlib.util.spec_from_file_location("parse_issue_refs", parser_path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    # bare ce-NNN in title
    assert mod.parse_title_refs("[ce-egress] ce-271 deploy broker fix") == [271]
    # standard ce-ops#NNN still works
    assert mod.parse_title_refs("feat(ce-ops#296): close-bot fix") == [296]
    # both in same title -> deduped, title order
    assert mod.parse_title_refs("feat(ce-ops#296): ce-296 also here") == [296]


def test_body_bare_ce_num_not_matched_without_keyword():
    """bare ce-NNN in body (no keyword) must NOT be parsed (false-positive guard)."""
    from pathlib import Path
    import importlib.util
    parser_path = Path(__file__).resolve().parents[3] / "tools" / "ce-ops-autoclose" / "parse_issue_refs.py"
    spec = importlib.util.spec_from_file_location("parse_issue_refs", parser_path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    # bare mention in body -- must NOT close
    assert mod.parse_body_closing_refs("Related to ce-271") == []
    assert mod.parse_body_closing_refs("[ce-egress] ce-271 was merged") == []
