import hashlib
import subprocess
from pathlib import Path

from creator_engine_validator.checks import registered_checks
from creator_engine_validator.checks.path_manifest_fidelity import (
    CHECK_NAME,
    PEDAGOGICAL_SENTINEL,
    run,
    run_with_base,
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


def test_pedagogical_sentinel_suppresses_free_text_corruption():
    # Same-line HTML sentinel opts a pedagogical reference out of the
    # init-py-corruption check.
    text = (
        "Pasted relays may transform `__init__.py` into the corrupted form "
        "`validators/creator_engine_validator/checks/init.py`. "
        f"{PEDAGOGICAL_SENTINEL}\n"
    )
    errors = scan_document(text, "fake.md")
    codes = {e.code for e in errors}
    assert "path_manifest_init_py_corruption" not in codes, [e.format() for e in errors]
    assert errors == [], [e.format() for e in errors]


def test_sentinel_less_free_text_corruption_still_errors():
    # Without the sentinel, the same pedagogical wording still fails.
    text = (
        "Pasted relays may transform `__init__.py` into the corrupted form "
        "`validators/creator_engine_validator/checks/init.py`.\n"
    )
    errors = scan_document(text, "fake.md")
    codes = {e.code for e in errors}
    assert "path_manifest_init_py_corruption" in codes, [e.format() for e in errors]


def test_sentinel_does_not_suppress_fenced_manifest_corruption():
    # Corruption inside a ```text fenced block is a manifest surface and
    # still errors even when a sentinel appears on adjacent lines.
    text = (
        f"Pedagogical preamble. {PEDAGOGICAL_SENTINEL}\n"
        "\n"
        "```text\n"
        "validators/creator_engine_validator/checks/init.py\n"
        "```\n"
        f"\nTrailing prose. {PEDAGOGICAL_SENTINEL}\n"
    )
    errors = scan_document(text, "fake.md")
    codes = {e.code for e in errors}
    assert "path_manifest_init_py_corruption" in codes, [e.format() for e in errors]


def test_sentinel_only_applies_on_same_line():
    # A sentinel on a line above the corruption does not suppress it; the
    # opt-out is deliberately same-line only.
    text = (
        f"{PEDAGOGICAL_SENTINEL}\n"
        "Quoting `validators/creator_engine_validator/checks/init.py` here.\n"
    )
    errors = scan_document(text, "fake.md")
    codes = {e.code for e in errors}
    assert "path_manifest_init_py_corruption" in codes, [e.format() for e in errors]


def test_cli_scan_path_manifest_flags_init_py_corruption(capsys, tmp_path: Path):
    doc = _build_doc(["validators/creator_engine_validator/checks/init.py"])
    path = tmp_path / "handoff.md"
    path.write_text(doc)
    exit_code = main(["scan-path-manifest", str(path)])
    assert exit_code == 1
    out = capsys.readouterr().out
    assert "FAIL path_manifest_fidelity" in out
    assert "path_manifest_init_py_corruption" in out


# --- PR-diff gate (run_with_base / verify-path-manifest) — G-ii -----------


def _git(repo: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=repo, check=True, capture_output=True, text=True)


def _init_repo(tmp_path: Path) -> tuple[Path, str]:
    """Create a real git repo with one base commit; return (repo, base_sha)."""
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init", "-q")
    _git(repo, "config", "user.email", "test@example.com")
    _git(repo, "config", "user.name", "Test")
    (repo / "seed.txt").write_text("seed\n")
    _git(repo, "add", "seed.txt")
    _git(repo, "commit", "-q", "-m", "base")
    base = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=repo, check=True, capture_output=True, text=True
    ).stdout.strip()
    return repo, base


def _write_manifest(repo: Path, paths: list[str]) -> Path:
    """Write a fenced path-manifest doc OUTSIDE the diff (committed in base)."""
    doc = repo / "pr-manifest.md"
    doc.write_text(_build_doc(paths, prefix="AUTHORIZED"))
    return doc


def test_run_with_base_no_manifest_is_neutral(tmp_path: Path):
    repo, base = _init_repo(tmp_path)
    # Make a change so HEAD != base, but supply no manifest.
    (repo / "changed.py").write_text("x = 1\n")
    _git(repo, "add", "changed.py")
    _git(repo, "commit", "-q", "-m", "change")
    result = run_with_base([repo], base, manifest=None)
    assert result.ok, [e.format() for e in result.errors]
    assert result.errors == ()


def test_run_with_base_diff_within_manifest_passes(tmp_path: Path):
    repo, base = _init_repo(tmp_path)
    manifest = _write_manifest(repo, ["src/app.py", "src/util.py"])
    # The diff exactly equals the manifest path-set.
    for rel in ("src/app.py", "src/util.py"):
        target = repo / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("# code\n")
    _git(repo, "add", "src/app.py", "src/util.py")
    _git(repo, "commit", "-q", "-m", "in-manifest change")
    result = run_with_base([repo], base, manifest=manifest)
    assert result.ok, [e.format() for e in result.errors]


def test_run_with_base_diff_outside_manifest_fails_listing_path(tmp_path: Path):
    repo, base = _init_repo(tmp_path)
    manifest = _write_manifest(repo, ["src/app.py"])
    # Change an in-manifest path AND an out-of-manifest path.
    (repo / "src").mkdir(parents=True, exist_ok=True)
    (repo / "src/app.py").write_text("# ok\n")
    (repo / "rogue.py").write_text("# not authorized\n")
    _git(repo, "add", "src/app.py", "rogue.py")
    _git(repo, "commit", "-q", "-m", "out-of-manifest change")
    result = run_with_base([repo], base, manifest=manifest)
    assert not result.ok
    codes = {e.code for e in result.errors}
    assert "path_manifest_diff_outside_manifest" in codes, [e.format() for e in result.errors]
    rendered = "\n".join(e.format() for e in result.errors)
    assert "rogue.py" in rendered


def test_run_with_base_manifest_path_not_changed_fails(tmp_path: Path):
    repo, base = _init_repo(tmp_path)
    # Manifest names a path the diff never touches → under-delivery flagged.
    manifest = _write_manifest(repo, ["src/app.py", "src/missing.py"])
    (repo / "src").mkdir(parents=True, exist_ok=True)
    (repo / "src/app.py").write_text("# only this one\n")
    _git(repo, "add", "src/app.py")
    _git(repo, "commit", "-q", "-m", "partial change")
    result = run_with_base([repo], base, manifest=manifest)
    assert not result.ok
    codes = {e.code for e in result.errors}
    assert "path_manifest_unfulfilled_manifest_path" in codes, [e.format() for e in result.errors]
    rendered = "\n".join(e.format() for e in result.errors)
    assert "src/missing.py" in rendered


def test_cli_verify_path_manifest_neutral_without_manifest(capsys, tmp_path: Path):
    repo, base = _init_repo(tmp_path)
    (repo / "changed.py").write_text("x = 1\n")
    _git(repo, "add", "changed.py")
    _git(repo, "commit", "-q", "-m", "change")
    exit_code = main(["verify-path-manifest", "--base", base, str(repo)])
    assert exit_code == 0
    out = capsys.readouterr().out
    assert "PASS path_manifest_fidelity" in out


def test_cli_verify_path_manifest_fails_on_out_of_manifest(capsys, tmp_path: Path):
    repo, base = _init_repo(tmp_path)
    manifest = _write_manifest(repo, ["src/app.py"])
    (repo / "src").mkdir(parents=True, exist_ok=True)
    (repo / "src/app.py").write_text("# ok\n")
    (repo / "rogue.py").write_text("# not authorized\n")
    _git(repo, "add", "src/app.py", "rogue.py")
    _git(repo, "commit", "-q", "-m", "out-of-manifest change")
    exit_code = main(
        ["verify-path-manifest", "--base", base, "--manifest", str(manifest), str(repo)]
    )
    assert exit_code == 1
    out = capsys.readouterr().out
    assert "FAIL path_manifest_fidelity" in out
    assert "path_manifest_diff_outside_manifest" in out
