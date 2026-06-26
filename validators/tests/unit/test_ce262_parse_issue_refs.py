"""Unit tests for tools/ce-ops-autoclose/parse_issue_refs.py (ce-ops#262).

Covers:
- Title-only refs (CE convention: feat(ce-ops#N): ...)
- Body closing-keyword refs (Closes/Fixes/Resolves ce-ops#N)
- Bare body mentions are NOT collected (body scan is keyword-gated)
- Multiple refs from both sources
- Deduplication across title + body
- Cross-repo form (creator-engine/ce-ops#N) in both positions
- none-found returns empty list
- parse_title_refs and parse_body_closing_refs individually
"""
from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

_MODULE_PATH = (
    Path(__file__).resolve().parents[3]
    / "tools"
    / "ce-ops-autoclose"
    / "parse_issue_refs.py"
)


def _load() -> object:
    spec = importlib.util.spec_from_file_location("parse_issue_refs", _MODULE_PATH)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)  # type: ignore[union-attr]
    return mod


@pytest.fixture(scope="module")
def refs():
    return _load()


# ---------------------------------------------------------------------------
# parse_title_refs — title scan (no keyword required)
# ---------------------------------------------------------------------------

class TestParseTitleRefs:
    def test_standard_ce_title_format(self, refs):
        """feat(ce-ops#262): ... → [262]"""
        assert refs.parse_title_refs("feat(ce-ops#262): cross-repo autoclose bot") == [262]

    def test_fix_title(self, refs):
        assert refs.parse_title_refs("fix(ce-ops#100): correct something") == [100]

    def test_bare_ref_in_title(self, refs):
        assert refs.parse_title_refs("Improve ce-ops#55 handling") == [55]

    def test_multiple_refs_in_title(self, refs):
        assert refs.parse_title_refs("feat(ce-ops#10): also fixes ce-ops#11") == [10, 11]

    def test_cross_repo_form_in_title(self, refs):
        assert refs.parse_title_refs("feat(creator-engine/ce-ops#77): something") == [77]

    def test_no_refs_in_title(self, refs):
        assert refs.parse_title_refs("chore: update README") == []

    def test_case_insensitive(self, refs):
        assert refs.parse_title_refs("feat(CE-OPS#300): upper case") == [300]

    def test_duplicate_in_title_deduped(self, refs):
        assert refs.parse_title_refs("ce-ops#5 and CE-OPS#5 again") == [5]


# ---------------------------------------------------------------------------
# parse_body_closing_refs — body keyword-gated scan
# ---------------------------------------------------------------------------

class TestParseBodyClosingRefs:
    def test_closes_keyword(self, refs):
        assert refs.parse_body_closing_refs("Closes ce-ops#5") == [5]

    def test_fixes_keyword(self, refs):
        assert refs.parse_body_closing_refs("Fixes ce-ops#11") == [11]

    def test_resolves_keyword(self, refs):
        assert refs.parse_body_closing_refs("Resolves ce-ops#13") == [13]

    def test_bare_mention_not_collected(self, refs):
        """Body bare mentions without a closing keyword must be ignored."""
        assert refs.parse_body_closing_refs("See ce-ops#42 for context") == []
        assert refs.parse_body_closing_refs("Related to ce-ops#42") == []
        assert refs.parse_body_closing_refs("Does not close ce-ops#42") == []

    def test_multiple_refs_on_one_line(self, refs):
        assert refs.parse_body_closing_refs("Closes ce-ops#5, ce-ops#6") == [5, 6]

    def test_multiple_keyword_lines(self, refs):
        assert refs.parse_body_closing_refs(
            "Closes ce-ops#5\nFixes ce-ops#7"
        ) == [5, 7]

    def test_cross_repo_form_in_body(self, refs):
        assert refs.parse_body_closing_refs(
            "Closes creator-engine/ce-ops#99"
        ) == [99]

    def test_closing_keyword_variants(self, refs):
        cases = [
            ("Close ce-ops#1", [1]),
            ("Closed ce-ops#2", [2]),
            ("Closes ce-ops#3", [3]),
            ("Fix ce-ops#4", [4]),
            ("Fixed ce-ops#5", [5]),
            ("Fixes ce-ops#6", [6]),
            ("Resolve ce-ops#7", [7]),
            ("Resolved ce-ops#8", [8]),
            ("Resolves ce-ops#9", [9]),
        ]
        for text, expected in cases:
            assert refs.parse_body_closing_refs(text) == expected, f"Failed for: {text!r}"

    def test_no_closing_refs_in_body(self, refs):
        assert refs.parse_body_closing_refs("No issue references here at all.") == []

    def test_duplicate_body_refs_deduped(self, refs):
        assert refs.parse_body_closing_refs(
            "Closes ce-ops#5, ce-ops#6. Resolves CE-OPS#5"
        ) == [5, 6]


# ---------------------------------------------------------------------------
# parse_all_refs — combined title + body with deduplication
# ---------------------------------------------------------------------------

class TestParseAllRefs:
    def test_title_only_no_body(self, refs):
        assert refs.parse_all_refs("feat(ce-ops#262): desc", "") == [262]

    def test_body_only_no_title_refs(self, refs):
        assert refs.parse_all_refs(
            "chore: misc",
            "Closes ce-ops#10\nFixes ce-ops#11",
        ) == [10, 11]

    def test_title_and_body_combined(self, refs):
        result = refs.parse_all_refs(
            "feat(ce-ops#262): bot",
            "Closes ce-ops#154\nFixes ce-ops#65",
        )
        assert result == [262, 154, 65]

    def test_title_ref_deduped_against_body(self, refs):
        """If ce-ops#262 appears in both title and body, it should appear once."""
        result = refs.parse_all_refs(
            "feat(ce-ops#262): bot",
            "Closes ce-ops#262\nFixes ce-ops#100",
        )
        assert result == [262, 100]

    def test_title_refs_come_before_body_refs(self, refs):
        """Title refs precede body refs in the result list."""
        result = refs.parse_all_refs(
            "feat(ce-ops#50): desc",
            "Closes ce-ops#10",
        )
        assert result == [50, 10]

    def test_none_found(self, refs):
        assert refs.parse_all_refs("chore: update docs", "No references here.") == []

    def test_bare_body_mention_not_collected(self, refs):
        """Bare mentions in body must not be collected even via parse_all_refs."""
        result = refs.parse_all_refs(
            "chore: something",
            "See ce-ops#99 for background.",
        )
        assert result == []

    def test_multiple_title_refs(self, refs):
        result = refs.parse_all_refs(
            "feat(ce-ops#1): also ce-ops#2 something",
            "Closes ce-ops#3",
        )
        assert result == [1, 2, 3]

    def test_case_insensitive_cross_repo(self, refs):
        result = refs.parse_all_refs(
            "feat(CREATOR-ENGINE/CE-OPS#500): upper",
            "Fixes creator-engine/ce-ops#501",
        )
        assert result == [500, 501]
