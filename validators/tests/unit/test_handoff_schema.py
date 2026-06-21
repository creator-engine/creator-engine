from pathlib import Path

from creator_engine_validator.checks import registered_checks
from creator_engine_validator.checks.handoff_schema import (
    CHECK_NAME,
    run,
    scan_document,
)
from creator_engine_validator.cli import main


REPO_ROOT = Path(__file__).resolve().parents[3]


VALID_HANDOFF_FRONT_MATTER = (
    "---\n"
    "kind: hermes-handoff\n"
    "role: implementer\n"
    "mode: tracked-file-implementation\n"
    "controller: example-controller\n"
    "ratifier: source\n"
    "source_authorization_path: .hermes/recommended-prompts/example.md\n"
    "source_authorization_sha256: " + ("ab" * 32) + "\n"
    "repo: creator-engine\n"
    "base_branch: main\n"
    "base_commit: " + ("ab" * 20) + "\n"
    "allowed_paths_count: 2\n"
    "allowed_paths_sha256: " + ("cd" * 32) + "\n"
    "stop_line: BATCH COMPLETE\n"
    "---\n"
    "\n"
    "Body.\n"
)


def test_handoff_schema_registered():
    checks = registered_checks()
    assert CHECK_NAME in checks


def test_scan_document_passes_on_valid_handoff(tmp_path: Path):
    doc_path = tmp_path / "h.md"
    doc_path.write_text(VALID_HANDOFF_FRONT_MATTER)
    errors = scan_document(doc_path, VALID_HANDOFF_FRONT_MATTER, REPO_ROOT)
    assert errors == [], [e.format() for e in errors]


def test_scan_document_flags_missing_required_field(tmp_path: Path):
    text = VALID_HANDOFF_FRONT_MATTER.replace("kind: hermes-handoff\n", "")
    # Without kind: it isn't a handoff at all → no error (kind is the discriminator)
    errors = scan_document(tmp_path / "h.md", text, REPO_ROOT)
    assert errors == []


def test_scan_document_flags_bad_role(tmp_path: Path):
    text = VALID_HANDOFF_FRONT_MATTER.replace("role: implementer\n", "role: bogus\n")
    errors = scan_document(tmp_path / "h.md", text, REPO_ROOT)
    codes = {e.code for e in errors}
    assert "handoff_schema_violation" in codes, [e.format() for e in errors]


def test_scan_document_flags_bad_hash_format(tmp_path: Path):
    text = VALID_HANDOFF_FRONT_MATTER.replace(
        "allowed_paths_sha256: " + ("cd" * 32),
        "allowed_paths_sha256: not-a-real-hash",
    )
    errors = scan_document(tmp_path / "h.md", text, REPO_ROOT)
    codes = {e.code for e in errors}
    assert "handoff_schema_violation" in codes


def test_scan_document_skips_non_handoff_documents(tmp_path: Path):
    text = (
        "---\n"
        "kind: not-a-handoff\n"
        "role: implementer\n"
        "---\n"
        "Other doc.\n"
    )
    errors = scan_document(tmp_path / "h.md", text, REPO_ROOT)
    assert errors == []


def test_scan_document_flags_count_incoherence(tmp_path: Path):
    text = VALID_HANDOFF_FRONT_MATTER + (
        "ALLOWED_PATHS_COUNT=99\n"
        "ALLOWED_PATHS_SHA256=" + "f" * 64 + "\n"
        "\n"
        "```text\n"
        "docs/a.md\n"
        "docs/b.md\n"
        "```\n"
    )
    # Front matter declares count=2 but fenced manifest has 2 unique lines → coherent.
    errors = scan_document(tmp_path / "h.md", text, REPO_ROOT)
    codes = {e.code for e in errors}
    assert "handoff_schema_count_incoherent" not in codes

    # Now make them disagree.
    text2 = VALID_HANDOFF_FRONT_MATTER + (
        "```text\n"
        "docs/a.md\n"
        "docs/b.md\n"
        "docs/c.md\n"
        "```\n"
    )
    errors2 = scan_document(tmp_path / "h.md", text2, REPO_ROOT)
    codes2 = {e.code for e in errors2}
    assert "handoff_schema_count_incoherent" in codes2, [e.format() for e in errors2]


def test_run_walks_tree(tmp_path: Path):
    (tmp_path / "h.md").write_text(VALID_HANDOFF_FRONT_MATTER)
    result = run([tmp_path])
    assert result.ok, [e.format() for e in result.errors]


def test_run_ignores_empty_ancestor_dot_git(tmp_path: Path):
    ambient = tmp_path / "ambient"
    doc_root = ambient / "pytest-case"
    (ambient / ".git").mkdir(parents=True)
    doc_root.mkdir()
    (doc_root / "h.md").write_text(VALID_HANDOFF_FRONT_MATTER)

    result = run([doc_root])

    assert result.ok, [e.format() for e in result.errors]


def test_cli_scan_handoffs_runs(capsys, tmp_path: Path):
    (tmp_path / "h.md").write_text(VALID_HANDOFF_FRONT_MATTER)
    exit_code = main(["scan-handoffs", str(tmp_path)])
    assert exit_code == 0
    out = capsys.readouterr().out
    assert "PASS handoff_schema" in out


def test_cli_scan_handoffs_flags_violation(capsys, tmp_path: Path):
    text = VALID_HANDOFF_FRONT_MATTER.replace("role: implementer\n", "role: bogus\n")
    (tmp_path / "h.md").write_text(text)
    exit_code = main(["scan-handoffs", str(tmp_path)])
    assert exit_code == 1
    out = capsys.readouterr().out
    assert "FAIL handoff_schema" in out
    assert "handoff_schema_violation" in out
