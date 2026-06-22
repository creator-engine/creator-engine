from __future__ import annotations

from pathlib import Path

import pytest

from creator_engine_validator.checks import registered_checks
from creator_engine_validator.checks import operator_runbook_refusal_sync as chk


def _table(clauses: list[str]) -> str:
    rows = "\n".join(
        f"| {clause} | Harness | surface | remedy |"
        for clause in clauses
    )
    return (
        "# Test Runbook\n\n"
        f"{chk.START_MARKER}\n"
        "| Clause ID | Harness | Refused surface | Operator remedy |\n"
        "|---|---|---|---|\n"
        f"{rows}\n"
        f"{chk.END_MARKER}\n"
    )


def _write_runbook(tmp_path: Path, text: str) -> Path:
    path = tmp_path / chk.RUNBOOK_NAME
    path.write_text(text, encoding="utf-8")
    return path


def _codes(errors) -> set[str]:
    return {error.code for error in errors}


def test_registered_check_present():
    checks = registered_checks()
    assert chk.CHECK_NAME in checks
    assert chk.CODE_MISSING in checks[chk.CHECK_NAME].frs
    assert chk.CODE_EXTRA in checks[chk.CHECK_NAME].frs


def test_current_runbook_passes():
    result = chk.run([Path(".")])
    assert result.ok, [error.format() for error in result.errors]


def test_unrelated_directory_noops(monkeypatch, tmp_path: Path):
    example_dir = tmp_path / "examples" / "well-formed"
    example_dir.mkdir(parents=True)
    monkeypatch.chdir(tmp_path)

    assert chk._candidate_runbooks([Path("examples/well-formed")]) == ()
    result = chk.run([Path("examples/well-formed")])

    assert result.ok
    assert result.errors == ()


@pytest.mark.parametrize(
    "target",
    [
        Path("."),
        Path("docs"),
        Path("docs/operations"),
        chk.RUNBOOK_RELATIVE,
    ],
)
def test_missing_intended_runbook_fails(monkeypatch, tmp_path: Path, target: Path):
    (tmp_path / "docs" / "operations").mkdir(parents=True)
    monkeypatch.chdir(tmp_path)

    result = chk.run([target])

    assert _codes(result.errors) == {chk.CODE_UNREADABLE}
    assert str(chk.RUNBOOK_RELATIVE) in result.errors[0].path


def test_missing_clause_fails(tmp_path: Path):
    expected = list(chk.expected_clause_ids())
    removed = expected.pop()
    path = _write_runbook(tmp_path, _table(expected))

    errors = chk.validate_runbook(path)

    assert chk.CODE_MISSING in _codes(errors)
    assert removed in "\n".join(error.format() for error in errors)


def test_extra_unknown_clause_fails(tmp_path: Path):
    clauses = [*chk.expected_clause_ids(), "CC-D-99"]
    path = _write_runbook(tmp_path, _table(list(clauses)))

    errors = chk.validate_runbook(path)

    assert chk.CODE_EXTRA in _codes(errors)
    assert "CC-D-99" in "\n".join(error.format() for error in errors)


def test_malformed_no_clause_block_fails(tmp_path: Path):
    path = _write_runbook(tmp_path, "# Test Runbook\n\nNo synced clause block.\n")

    errors = chk.validate_runbook(path)

    assert _codes(errors) == {chk.CODE_MALFORMED}
