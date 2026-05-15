import hashlib
from pathlib import Path

from creator_engine_validator.checks import registered_checks
from creator_engine_validator.checks.path_manifest_fidelity import (
    CHECK_NAME,
    run,
    scan_document,
)
from creator_engine_validator.cli import main


def _normalized_hash(paths: list[str]) -> tuple[int, str]:
    norm = "\n".join(sorted(set(paths))) + "\n"
    return len(paths), hashlib.sha256(norm.encode("utf-8")).hexdigest()


def _build_doc(paths: list[str], declared_count: int | None = None, declared_sha: str | None = None, prefix: str = "ALLOWED") -> str:
    count, sha = _normalized_hash(paths)
    if declared_count is None:
        declared_count = count
    if declared_sha is None:
        declared_sha = sha
    body = "\n".join(paths)
    return (
        f"# example\n\n"
        f"{prefix}_PATHS_COUNT={declared_count}\n"
        f"{prefix}_PATHS_SHA256={declared_sha}\n\n"
        "```text\n"
        f"{body}\n"
        "```\n"
    )


def test_path_manifest_fidelity_registered():
    checks = registered_checks()
    assert CHECK_NAME in checks


def test_scan_document_passes_on_well_formed_manifest():
    doc = _build_doc(["docs/a.md", "docs/b.md"])
    errors = scan_document(doc, "fake.md")
    assert errors == [], [e.format() for e in errors]


def test_scan_document_flags_count_mismatch():
    doc = _build_doc(["docs/a.md", "docs/b.md"], declared_count=99)
    errors = scan_document(doc, "fake.md")
    codes = {e.code for e in errors}
    assert "path_manifest_count_mismatch" in codes, [e.format() for e in errors]


def test_scan_document_flags_hash_mismatch():
    doc = _build_doc(["docs/a.md", "docs/b.md"], declared_sha="0" * 64)
    errors = scan_document(doc, "fake.md")
    codes = {e.code for e in errors}
    assert "path_manifest_hash_mismatch" in codes, [e.format() for e in errors]


def test_scan_document_flags_init_py_corruption():
    doc = _build_doc(["validators/creator_engine_validator/checks/init.py"])
    errors = scan_document(doc, "fake.md")
    codes = {e.code for e in errors}
    assert "path_manifest_init_py_corruption" in codes, [e.format() for e in errors]


def test_scan_document_well_formed_underscore_path_not_flagged():
    doc = _build_doc(["validators/creator_engine_validator/checks/__init__.py"])
    errors = scan_document(doc, "fake.md")
    codes = {e.code for e in errors}
    assert "path_manifest_init_py_corruption" not in codes, [e.format() for e in errors]
    assert errors == [], [e.format() for e in errors]


def test_scan_document_flags_init_py_in_free_text():
    # Corruption can appear anywhere in the document body.
    text = "Some prose mentioning validators/creator_engine_validator/checks/init.py inline.\n"
    errors = scan_document(text, "fake.md")
    codes = {e.code for e in errors}
    assert "path_manifest_init_py_corruption" in codes


def test_scan_document_flags_missing_block():
    text = (
        "ALLOWED_PATHS_COUNT=2\n"
        "ALLOWED_PATHS_SHA256=" + "a" * 64 + "\n"
        "(no fenced manifest block follows here)\n"
    )
    errors = scan_document(text, "fake.md")
    codes = {e.code for e in errors}
    assert "path_manifest_missing_block" in codes


def test_scan_document_flags_missing_declaration_for_orphan_count():
    text = (
        "ALLOWED_PATHS_COUNT=2\n"
        "```text\n"
        "docs/a.md\n"
        "docs/b.md\n"
        "```\n"
    )
    errors = scan_document(text, "fake.md")
    codes = {e.code for e in errors}
    assert "path_manifest_missing_declaration" in codes


def test_scan_document_flags_missing_declaration_for_orphan_hash():
    text = (
        "ALLOWED_PATHS_SHA256=" + "b" * 64 + "\n"
        "```text\n"
        "docs/a.md\n"
        "```\n"
    )
    errors = scan_document(text, "fake.md")
    codes = {e.code for e in errors}
    assert "path_manifest_missing_declaration" in codes


def test_run_on_well_formed_example(tmp_path: Path):
    repo = tmp_path
    (repo / ".git").mkdir()
    handoff_dir = repo / "handoffs"
    handoff_dir.mkdir()
    doc = _build_doc(["docs/a.md", "docs/b.md"])
    (handoff_dir / "handoff.md").write_text(doc)
    result = run([repo])
    assert result.ok, [e.format() for e in result.errors]


def test_run_on_malformed_count(tmp_path: Path):
    repo = tmp_path
    (repo / ".git").mkdir()
    doc = _build_doc(["docs/a.md", "docs/b.md"], declared_count=42)
    (repo / "handoff.md").write_text(doc)
    result = run([repo])
    assert not result.ok
    assert any(e.code == "path_manifest_count_mismatch" for e in result.errors)


def test_cli_scan_path_manifest_runs(capsys, tmp_path: Path):
    doc = _build_doc(["docs/a.md", "docs/b.md"])
    path = tmp_path / "handoff.md"
    path.write_text(doc)
    exit_code = main(["scan-path-manifest", str(path)])
    assert exit_code == 0
    out = capsys.readouterr().out
    assert "PASS path_manifest_fidelity" in out


def test_cli_scan_path_manifest_flags_init_py_corruption(capsys, tmp_path: Path):
    doc = _build_doc(["validators/creator_engine_validator/checks/init.py"])
    path = tmp_path / "handoff.md"
    path.write_text(doc)
    exit_code = main(["scan-path-manifest", str(path)])
    assert exit_code == 1
    out = capsys.readouterr().out
    assert "FAIL path_manifest_fidelity" in out
    assert "path_manifest_init_py_corruption" in out
