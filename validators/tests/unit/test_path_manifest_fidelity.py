import hashlib
import subprocess
from pathlib import Path

from creator_engine_validator.checks import registered_checks
from creator_engine_validator.checks.path_manifest_fidelity import (
    CHECK_NAME,
    MANIFEST_DIR,
    PEDAGOGICAL_SENTINEL,
    SLUG_PATTERN,
    CarrierIdentity,
    branch_slug,
    parse_carrier,
    parse_carrier_file,
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


# ----------------------------------------------------------- F6 structured carrier identity
def test_parse_carrier_returns_structured_identity():
    paths = ["b/y.py", "a/x.py", ".ce/pr-manifests/c.md"]
    ident = parse_carrier(_build_doc(paths, prefix="AUTHORIZED"))
    assert isinstance(ident, CarrierIdentity)
    assert ident.declared_count == 3
    assert ident.paths == (".ce/pr-manifests/c.md", "a/x.py", "b/y.py")  # sorted-unique
    assert ident.consistent is True
    # normalized hash is the carrier canonicalization rule
    count, sha = _normalized_hash(paths)
    assert ident.normalized_sha256 == sha


def test_parse_carrier_path_set_hash_stable_across_mechanical_prose():
    # two carriers with the SAME path-set but different prose share the normalized hash.
    paths = ["a/x.py", "a/y.py"]
    doc_a = "# base OLD\n\n" + _build_doc(paths, prefix="AUTHORIZED")
    doc_b = "# base NEW (re-pinned)\n\n" + _build_doc(paths, prefix="AUTHORIZED")
    ia, ib = parse_carrier(doc_a), parse_carrier(doc_b)
    assert ia.normalized_sha256 == ib.normalized_sha256
    # a real path-set change DOES move the hash
    ic = parse_carrier(_build_doc(paths + ["a/z.py"], prefix="AUTHORIZED"))
    assert ic.normalized_sha256 != ia.normalized_sha256


def test_parse_carrier_flags_inconsistent_declaration():
    ident = parse_carrier(_build_doc(["a/x.py", "a/y.py"], declared_count=99, prefix="AUTHORIZED"))
    assert ident is not None and ident.consistent is False


def test_parse_carrier_none_without_manifest_block():
    assert parse_carrier("# just prose, no manifest\n") is None


def test_parse_carrier_file_roundtrip(tmp_path):
    p = tmp_path / "carrier.md"
    p.write_text(_build_doc(["a/x.py"], prefix="AUTHORIZED"), encoding="utf-8")
    ident = parse_carrier_file(p)
    assert ident is not None and ident.paths == ("a/x.py",)
    assert parse_carrier_file(tmp_path / "absent.md") is None


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


# --- branch_slug id-shape (ce-ops#21, esc-14-L7 lesson) -------------------
#
# Every branch_slug output must satisfy the repo's canonical id pattern
# `^[a-z][a-z0-9-]{2,63}$` (the literal at schemas/scope.schema.yaml:58) so a
# carrier stem can later be embedded in a schema-constrained id without defect.


def test_branch_slug_corpus_is_canonical_id_shape():
    corpus = [
        "v31-g2b-revid-fix",            # plain
        "ce21-per-pr-carrier",          # the gate's own branch
        "fix-20260612T101530Z",         # uppercase UTC stamp (esc-14-L7)
        "Feature/Foo_Bar.x",            # mixed case + separators
        "a" * 100,                      # over-length
        "1abc",                         # leading digit
        "-lead",                        # leading separator
        "caféμ",                   # unicode
        "",                             # empty
        "-",                            # degenerate
        "ab",                           # too short
        "a",                            # single char
    ]
    for branch in corpus:
        slug = branch_slug(branch)
        assert SLUG_PATTERN.fullmatch(slug), f"{branch!r} -> {slug!r} is not a canonical id"
        assert 3 <= len(slug) <= 64, f"{branch!r} -> {slug!r} len {len(slug)} out of 3..64"


def test_branch_slug_over_length_is_truncated_with_hash():
    slug = branch_slug("z" * 100)
    assert len(slug) == 64
    assert slug == branch_slug("z" * 100)  # deterministic
    assert "-" in slug and len(slug.rsplit("-", 1)[-1]) == 8  # 8-hex disambiguator present


def test_branch_slug_distinct_for_shared_long_prefix():
    base = "shared-prefix-" + "a" * 60
    assert branch_slug(base + "-one") != branch_slug(base + "-two")


def test_branch_slug_is_idempotent_on_canonical_input():
    for branch in ("ce21-per-pr-carrier", "v31-g2b-revid-fix", "a-b-c"):
        assert branch_slug(branch) == branch
        assert branch_slug(branch_slug(branch)) == branch_slug(branch)


# --- per-PR carrier diff-gate (ce-ops#21) ---------------------------------


def _write_repo_file(repo: Path, rel: str, content: str = "# x\n") -> None:
    target = repo / rel
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content)


def _carrier_rel(slug: str) -> str:
    return f"{MANIFEST_DIR}/{slug}.md"


def _commit_per_pr(repo: Path, slug: str, manifest_paths: list[str]) -> str:
    """Create every manifest path + a self-inclusive carrier, then commit one change."""
    carrier_rel = _carrier_rel(slug)
    for rel in manifest_paths:
        if rel == carrier_rel:
            continue
        _write_repo_file(repo, rel)
    _write_repo_file(repo, carrier_rel, _build_doc(sorted(set(manifest_paths)), prefix="AUTHORIZED"))
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "per-pr change")
    return carrier_rel


def test_per_pr_zero_carrier_is_neutral(tmp_path: Path):
    repo, base = _init_repo(tmp_path)
    _write_repo_file(repo, "src/app.py")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "no carrier")
    result = run_with_base([repo], base, manifest_dir=MANIFEST_DIR, head_ref="some-branch")
    assert result.ok, [e.format() for e in result.errors]
    assert result.errors == ()


def test_per_pr_active_pass_self_inclusive(tmp_path: Path):
    repo, base = _init_repo(tmp_path)
    slug = branch_slug("ce21-feature")
    manifest = [_carrier_rel(slug), "src/app.py", "src/util.py"]
    _commit_per_pr(repo, slug, manifest)
    result = run_with_base([repo], base, manifest_dir=MANIFEST_DIR, head_ref="ce21-feature")
    assert result.ok, [e.format() for e in result.errors]


def test_per_pr_diff_outside_manifest_fails(tmp_path: Path):
    repo, base = _init_repo(tmp_path)
    slug = branch_slug("ce21-feature")
    carrier_rel = _carrier_rel(slug)
    # Carrier authorizes only itself + app.py, but the diff also touches rogue.py.
    _write_repo_file(repo, "src/app.py")
    _write_repo_file(repo, "rogue.py")
    _write_repo_file(repo, carrier_rel, _build_doc(sorted([carrier_rel, "src/app.py"]), prefix="AUTHORIZED"))
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "overrun")
    result = run_with_base([repo], base, manifest_dir=MANIFEST_DIR, head_ref="ce21-feature")
    assert not result.ok
    codes = {e.code for e in result.errors}
    assert "path_manifest_diff_outside_manifest" in codes, [e.format() for e in result.errors]
    assert "rogue.py" in "\n".join(e.format() for e in result.errors)


def test_per_pr_unfulfilled_manifest_path_fails(tmp_path: Path):
    repo, base = _init_repo(tmp_path)
    slug = branch_slug("ce21-feature")
    carrier_rel = _carrier_rel(slug)
    # Carrier authorizes a path the diff never touches.
    _write_repo_file(repo, "src/app.py")
    _write_repo_file(repo, carrier_rel, _build_doc(sorted([carrier_rel, "src/app.py", "src/missing.py"]), prefix="AUTHORIZED"))
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "under-deliver")
    result = run_with_base([repo], base, manifest_dir=MANIFEST_DIR, head_ref="ce21-feature")
    assert not result.ok
    codes = {e.code for e in result.errors}
    assert "path_manifest_unfulfilled_manifest_path" in codes, [e.format() for e in result.errors]
    assert "src/missing.py" in "\n".join(e.format() for e in result.errors)


def test_per_pr_multiple_carriers_fails_reporting_each(tmp_path: Path):
    repo, base = _init_repo(tmp_path)
    slug = branch_slug("ce21-feature")
    other = f"{MANIFEST_DIR}/other-slug.md"
    carrier_rel = _carrier_rel(slug)
    _write_repo_file(repo, carrier_rel, _build_doc([carrier_rel], prefix="AUTHORIZED"))
    _write_repo_file(repo, other, _build_doc([other], prefix="AUTHORIZED"))
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "two carriers")
    result = run_with_base([repo], base, manifest_dir=MANIFEST_DIR, head_ref="ce21-feature")
    assert not result.ok
    codes = {e.code for e in result.errors}
    assert codes == {"path_manifest_multiple_carriers"}, [e.format() for e in result.errors]
    rendered = "\n".join(e.format() for e in result.errors)
    assert carrier_rel in rendered and other in rendered


def test_per_pr_foreign_merged_carrier_edit_alongside_own_is_reported(tmp_path: Path):
    repo, base = _init_repo(tmp_path)
    foreign = f"{MANIFEST_DIR}/old-merged.md"
    # A merged ledger entry exists on base.
    _write_repo_file(repo, foreign, _build_doc([foreign], prefix="AUTHORIZED"))
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "merged ledger entry")
    merged_base = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=repo, check=True, capture_output=True, text=True
    ).stdout.strip()
    # The PR edits the foreign carrier AND adds its own.
    slug = branch_slug("ce21-feature")
    carrier_rel = _carrier_rel(slug)
    _write_repo_file(repo, foreign, _build_doc([foreign, "x.py"], prefix="AUTHORIZED"))
    _write_repo_file(repo, carrier_rel, _build_doc([carrier_rel], prefix="AUTHORIZED"))
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "edit foreign + add own")
    result = run_with_base([repo], merged_base, manifest_dir=MANIFEST_DIR, head_ref="ce21-feature")
    assert not result.ok
    codes = {e.code for e in result.errors}
    assert "path_manifest_multiple_carriers" in codes, [e.format() for e in result.errors]
    assert foreign in "\n".join(e.format() for e in result.errors)


def test_per_pr_slug_mismatch_fails(tmp_path: Path):
    repo, base = _init_repo(tmp_path)
    # Carrier stem does not match branch_slug(head_ref).
    wrong = f"{MANIFEST_DIR}/not-the-right-slug.md"
    _write_repo_file(repo, wrong, _build_doc([wrong], prefix="AUTHORIZED"))
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "wrong slug")
    result = run_with_base([repo], base, manifest_dir=MANIFEST_DIR, head_ref="ce21-feature")
    assert not result.ok
    codes = {e.code for e in result.errors}
    assert codes == {"path_manifest_carrier_slug_mismatch"}, [e.format() for e in result.errors]


def test_per_pr_own_slug_modified_not_added_fails(tmp_path: Path):
    repo, base = _init_repo(tmp_path)
    slug = branch_slug("ce21-feature")
    carrier_rel = _carrier_rel(slug)
    # The carrier already exists on base (a merged ledger entry).
    _write_repo_file(repo, carrier_rel, _build_doc([carrier_rel], prefix="AUTHORIZED"))
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "carrier already merged")
    merged_base = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=repo, check=True, capture_output=True, text=True
    ).stdout.strip()
    # The PR MODIFIES it rather than adding it.
    _write_repo_file(repo, carrier_rel, _build_doc([carrier_rel, "y.py"], prefix="AUTHORIZED"))
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "modify merged carrier")
    result = run_with_base([repo], merged_base, manifest_dir=MANIFEST_DIR, head_ref="ce21-feature")
    assert not result.ok
    codes = {e.code for e in result.errors}
    assert "path_manifest_carrier_not_added" in codes, [e.format() for e in result.errors]


def test_per_pr_legacy_carrier_deletion_is_allowed(tmp_path: Path):
    repo, base = _init_repo(tmp_path)
    # Base carries the retired shared carrier.
    _write_repo_file(repo, ".ce/pr-path-manifest.md", "# legacy\n")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "legacy carrier present")
    legacy_base = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=repo, check=True, capture_output=True, text=True
    ).stdout.strip()
    # The migration PR deletes the legacy carrier and adds its own; manifest lists both.
    slug = branch_slug("ce21-per-pr-carrier")
    carrier_rel = _carrier_rel(slug)
    (repo / ".ce/pr-path-manifest.md").unlink()
    _write_repo_file(repo, carrier_rel, _build_doc(sorted([carrier_rel, ".ce/pr-path-manifest.md"]), prefix="AUTHORIZED"))
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "migrate")
    result = run_with_base([repo], legacy_base, manifest_dir=MANIFEST_DIR, head_ref="ce21-per-pr-carrier")
    assert result.ok, [e.format() for e in result.errors]


def test_per_pr_legacy_carrier_add_is_denied(tmp_path: Path):
    repo, base = _init_repo(tmp_path)
    slug = branch_slug("ce21-feature")
    carrier_rel = _carrier_rel(slug)
    # The PR resurrects the retired shared carrier alongside its own.
    _write_repo_file(repo, ".ce/pr-path-manifest.md", "# resurrected\n")
    _write_repo_file(repo, carrier_rel, _build_doc(sorted([carrier_rel, ".ce/pr-path-manifest.md"]), prefix="AUTHORIZED"))
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "resurrect legacy")
    result = run_with_base([repo], base, manifest_dir=MANIFEST_DIR, head_ref="ce21-feature")
    assert not result.ok
    codes = {e.code for e in result.errors}
    assert "path_manifest_legacy_carrier_path" in codes, [e.format() for e in result.errors]


def test_per_pr_legacy_carrier_modify_is_denied(tmp_path: Path):
    repo, base = _init_repo(tmp_path)
    _write_repo_file(repo, ".ce/pr-path-manifest.md", "# legacy\n")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "legacy present")
    legacy_base = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=repo, check=True, capture_output=True, text=True
    ).stdout.strip()
    slug = branch_slug("ce21-feature")
    carrier_rel = _carrier_rel(slug)
    _write_repo_file(repo, ".ce/pr-path-manifest.md", "# legacy modified\n")
    _write_repo_file(repo, carrier_rel, _build_doc([carrier_rel], prefix="AUTHORIZED"))
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "modify legacy")
    result = run_with_base([repo], legacy_base, manifest_dir=MANIFEST_DIR, head_ref="ce21-feature")
    assert not result.ok
    codes = {e.code for e in result.errors}
    assert "path_manifest_legacy_carrier_path" in codes, [e.format() for e in result.errors]


def test_per_pr_head_ref_required(tmp_path: Path):
    repo, base = _init_repo(tmp_path)
    result = run_with_base([repo], base, manifest_dir=MANIFEST_DIR, head_ref=None)
    assert not result.ok
    codes = {e.code for e in result.errors}
    assert "path_manifest_carrier_head_ref_required" in codes, [e.format() for e in result.errors]


def test_cli_verify_path_manifest_dir_active_pass(capsys, tmp_path: Path):
    repo, base = _init_repo(tmp_path)
    slug = branch_slug("ce21-feature")
    manifest = [_carrier_rel(slug), "src/app.py"]
    _commit_per_pr(repo, slug, manifest)
    exit_code = main(
        [
            "verify-path-manifest", "--base", base,
            "--manifest-dir", MANIFEST_DIR, "--head-ref", "ce21-feature", str(repo),
        ]
    )
    assert exit_code == 0
    assert "PASS path_manifest_fidelity" in capsys.readouterr().out


def test_cli_verify_path_manifest_and_dir_are_mutually_exclusive(capsys, tmp_path: Path):
    repo, base = _init_repo(tmp_path)
    exit_code = main(
        [
            "verify-path-manifest", "--base", base,
            "--manifest", "x.md", "--manifest-dir", MANIFEST_DIR, str(repo),
        ]
    )
    assert exit_code == 2
    assert "mutually exclusive" in capsys.readouterr().err


def test_cli_verify_path_manifest_dir_requires_head_ref(capsys, tmp_path: Path):
    repo, base = _init_repo(tmp_path)
    exit_code = main(
        ["verify-path-manifest", "--base", base, "--manifest-dir", MANIFEST_DIR, str(repo)]
    )
    assert exit_code == 2
    assert "requires --head-ref" in capsys.readouterr().err
