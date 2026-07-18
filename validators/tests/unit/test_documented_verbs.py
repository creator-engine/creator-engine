from __future__ import annotations

from pathlib import Path

from creator_engine_validator import ce_cli
from creator_engine_validator.checks import registered_checks
from creator_engine_validator.checks import documented_verbs as chk


def _doc(root: Path, text: str) -> Path:
    path = root / "docs" / "guide.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def _codes(result) -> set[str]:
    return {error.code for error in result.errors}


def test_documented_verbs_is_registered():
    assert chk.CHECK_NAME in registered_checks()


def test_shipped_verb_in_code_fence_passes(tmp_path: Path):
    _doc(
        tmp_path,
        """# Guide

```bash
ce validate-pr --declared-work-class S
```
""",
    )

    result = chk.run([tmp_path])

    assert result.ok


def test_every_pre_argparse_dispatch_verb_is_shipped_and_documentable(tmp_path: Path):
    pre_argparse_verbs = ce_cli.PRE_ARGPARSE_DISPATCH_GROUPS
    _doc(
        tmp_path,
        "# Pre-argparse dispatch groups\n\n"
        + "\n".join(f"- `ce {verb} --help`" for verb in sorted(pre_argparse_verbs))
        + "\n",
    )

    result = chk.run([tmp_path])

    assert pre_argparse_verbs <= chk.shipped_verbs()
    assert result.ok


def test_unshipped_verb_fails_and_names_it(tmp_path: Path):
    _doc(tmp_path, "Run `ce future-verb --flag` from the repo root.\n")

    result = chk.run([tmp_path])

    assert not result.ok
    assert _codes(result) == {chk.CODE_UNSHIPPED}
    assert "future-verb" in result.errors[0].message
    assert result.errors[0].path.endswith("docs/guide.md:L1")


def test_placeholder_is_not_treated_as_a_verb(tmp_path: Path):
    _doc(
        tmp_path,
        """Use `ce <verb>` as a placeholder.

```text
ce <verb> --help
```
""",
    )

    result = chk.run([tmp_path])

    assert result.ok


def test_forward_teaching_allowlist_passes(monkeypatch, tmp_path: Path):
    monkeypatch.setattr(chk, "FORWARD_TEACHING_ALLOWLIST", frozenset({"future-verb"}))
    _doc(tmp_path, "Run `ce future-verb --flag` after the release.\n")

    result = chk.run([tmp_path])

    assert result.ok


def test_baseline_debt_warns_but_new_offense_fails(monkeypatch, tmp_path: Path):
    monkeypatch.setattr(
        chk,
        "BASELINE_OFFENSES",
        frozenset({("docs/guide.md", 1, "old-verb")}),
    )
    _doc(tmp_path, "`ce old-verb` is baseline debt, but `ce new-verb` is new.\n")

    result = chk.run([tmp_path])

    assert not result.ok
    assert _codes(result) == {chk.CODE_UNSHIPPED}
    assert result.warnings[0].code == chk.CODE_BASELINE
    assert "new-verb" in result.errors[0].message
