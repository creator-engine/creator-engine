from __future__ import annotations

from pathlib import Path

import yaml

from creator_engine_validator import brain_runtime as rt
from creator_engine_validator.checks import registered_checks
from creator_engine_validator.checks import ce_brain_doctrine_coverage as chk


def _write_doc(repo: Path, relative: str, text: str = "doctrine\n") -> Path:
    path = repo / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def _write_manifest(repo: Path, *, exceptions: list[str] | None = None, governed_trees: list[str] | None = None) -> Path:
    path = repo / ".ce" / "brain" / "doctrine-coverage.yaml"
    path.parent.mkdir(parents=True, exist_ok=True)
    doc: dict[str, object] = {
        "kind": "brain-doctrine-coverage-manifest",
        "schema_version": "1",
        "exceptions": exceptions or [],
    }
    if governed_trees is not None:
        doc["governed_trees"] = governed_trees
    path.write_text(yaml.safe_dump(doc, sort_keys=False), encoding="utf-8")
    return path


def _write_static_assertion(repo: Path, evidence_ref: str) -> Path:
    captured: list[str] = []
    rt.assert_claim(
        assertion_id="brain-assertion-doctrine-test-0001",
        claim={"subject": "doctrine", "predicate": "covers", "object": evidence_ref},
        scope="unit",
        evidence_ref=evidence_ref,
        records=[],
        write=lambda _path, text: captured.append(text),
    )
    path = repo / ".ce" / "brain" / "assertions.yaml"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(captured[-1], encoding="utf-8")
    return path


def _write_unrelated_ledger(repo: Path) -> Path:
    return _write_static_assertion(repo, "docs/architecture/unrelated.md")


def _codes(repo: Path) -> list[str]:
    return [error.code for error in chk.validate_repo(repo)]


def test_ce_brain_doctrine_coverage_is_registered():
    assert chk.CHECK_NAME in registered_checks()


def test_net_new_uncovered_file_fails_without_exception(tmp_path: Path):
    _write_doc(tmp_path, "docs/contracts/new-doctrine.md")
    _write_manifest(tmp_path, exceptions=[], governed_trees=["docs/contracts"])
    _write_unrelated_ledger(tmp_path)

    result = chk.run([tmp_path])

    assert chk.CODE_UNCOVERED in {error.code for error in result.errors}, [
        error.format() for error in result.errors
    ]


def test_net_new_uncovered_file_passes_with_seeded_exception(tmp_path: Path):
    _write_doc(tmp_path, "docs/contracts/new-doctrine.md")
    _write_manifest(
        tmp_path,
        exceptions=["docs/contracts/new-doctrine.md"],
        governed_trees=["docs/contracts"],
    )
    _write_unrelated_ledger(tmp_path)

    assert chk.run([tmp_path]).ok


def test_active_static_assertion_covering_file_passes_without_exception(tmp_path: Path):
    _write_doc(tmp_path, "docs/contracts/covered.md")
    _write_manifest(tmp_path, exceptions=[], governed_trees=["docs/contracts"])
    _write_static_assertion(tmp_path, "docs/contracts/covered.md")

    assert chk.run([tmp_path]).ok


def test_fragment_suffix_in_static_assertion_resolves_to_file(tmp_path: Path):
    _write_doc(tmp_path, "docs/contracts/covered.md")
    _write_manifest(tmp_path, exceptions=[], governed_trees=["docs/contracts"])
    _write_static_assertion(tmp_path, "docs/contracts/covered.md#section")

    assert chk.run([tmp_path]).ok


def test_exception_for_covered_file_fails_as_stale_exception(tmp_path: Path):
    _write_doc(tmp_path, "docs/contracts/covered.md")
    _write_manifest(
        tmp_path,
        exceptions=["docs/contracts/covered.md"],
        governed_trees=["docs/contracts"],
    )
    _write_static_assertion(tmp_path, "docs/contracts/covered.md")

    assert _codes(tmp_path) == [chk.CODE_STALE_EXCEPTION]


def test_exception_for_nonexistent_file_fails_as_stale_exception(tmp_path: Path):
    _write_doc(tmp_path, "docs/contracts/covered.md")
    _write_manifest(
        tmp_path,
        exceptions=["docs/contracts/missing.md"],
        governed_trees=["docs/contracts"],
    )
    _write_static_assertion(tmp_path, "docs/contracts/covered.md")

    assert _codes(tmp_path) == [chk.CODE_STALE_EXCEPTION]


def test_absent_authoritative_ledger_is_empty_coverage_not_unreadable(tmp_path: Path):
    _write_doc(tmp_path, "docs/contracts/new-doctrine.md")
    _write_manifest(tmp_path, exceptions=[], governed_trees=["docs/contracts"])

    errors = chk.validate_repo(tmp_path)

    assert [error.code for error in errors] == [chk.CODE_UNCOVERED]
    assert "unreadable" not in errors[0].message


def test_duplicate_exception_entry_fails_manifest_validation(tmp_path: Path):
    _write_doc(tmp_path, "docs/contracts/covered.md")
    _write_manifest(
        tmp_path,
        exceptions=["docs/contracts/covered.md", "docs/contracts/covered.md"],
        governed_trees=["docs/contracts"],
    )
    _write_unrelated_ledger(tmp_path)

    errors = chk.validate_repo(tmp_path)

    assert [error.code for error in errors] == [chk.CODE_MANIFEST_INVALID]
    assert "duplicate doctrine exception" in errors[0].message
    assert errors[0].path.endswith("doctrine-coverage.yaml:/exceptions/1")


def test_exception_outside_governed_trees_fails_as_stale_exception(tmp_path: Path):
    _write_doc(tmp_path, "docs/contracts/covered.md")
    _write_doc(tmp_path, "docs/other/outside.md")
    _write_manifest(
        tmp_path,
        exceptions=["docs/other/outside.md"],
        governed_trees=["docs/contracts"],
    )
    _write_unrelated_ledger(tmp_path)

    errors = chk.validate_repo(tmp_path)

    assert [error.code for error in errors] == [chk.CODE_STALE_EXCEPTION, chk.CODE_UNCOVERED]
    assert "outside governed_trees" in errors[0].message


def test_malformed_manifest_missing_governed_trees_fails_closed(tmp_path: Path):
    _write_doc(tmp_path, "docs/contracts/new-doctrine.md")
    _write_manifest(tmp_path, exceptions=[])
    _write_unrelated_ledger(tmp_path)

    assert _codes(tmp_path) == [chk.CODE_MANIFEST_INVALID]
