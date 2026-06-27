from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest


SCRIPT_PATH = Path(__file__).resolve().parents[3] / ".github" / "scripts" / "ceops_autoclose.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("ceops_autoclose", SCRIPT_PATH)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


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
