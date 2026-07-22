"""Tests for the standalone public-docs confidentiality check + CLI subcommand.

This locks the optional local diagnostic surface: the same single-sourced rule
the CI guard uses is exposed as ``scan-public-docs-confidentiality`` and runs
in the optional ``ce validate-pr`` diagnostic.
"""
from __future__ import annotations

import io
import subprocess
from pathlib import Path

from creator_engine_validator import cli
from creator_engine_validator import public_docs_confidentiality as guard


def _git(repo: Path, *args: str) -> None:
    subprocess.run(
        ["git", *args],
        cwd=repo,
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )


def _git_stdout(repo: Path, *args: str) -> str:
    return subprocess.run(
        ["git", *args],
        cwd=repo,
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    ).stdout.strip()


def _write_tracked(repo: Path, rel: str, text: str) -> Path:
    target = repo / rel
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(text, encoding="utf-8")
    _git(repo, "add", "--", rel)
    return target


def _commit(repo: Path, message: str = "test commit") -> str:
    _git(
        repo,
        "-c",
        "user.email=test@example.invalid",
        "-c",
        "user.name=CE Test",
        "commit",
        "-m",
        message,
    )
    return _git_stdout(repo, "rev-parse", "HEAD")


def _make_repo(tmp_path: Path) -> Path:
    """A minimal repo whose internal-tree guard is satisfied.

    Materializes exactly the ce-ops#283 exception files (so neither
    ``unreviewed`` net-new files nor ``stale`` missing exceptions fire), leaving
    the confidentiality pattern scan as the only variable under test.
    """
    _git(tmp_path, "init")
    (tmp_path / "docs").mkdir()
    (tmp_path / "README.md").write_text("# Clean product front door.\n", encoding="utf-8")
    for rel in (*guard.KNOWN_OPERATIONS_EXCEPTIONS, *guard.KNOWN_DELIVERY_EXCEPTIONS):
        target = tmp_path / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("Internal protocol doc.\n", encoding="utf-8")
    _git(tmp_path, "add", "--", "README.md", "docs")
    return tmp_path


def _confidentiality_errors(result) -> list[str]:
    return [e.format() for e in result.errors if "CE-CONFIDENTIALITY" in e.code]


def test_run_passes_on_clean_repo(tmp_path: Path):
    repo = _make_repo(tmp_path)
    _write_tracked(repo, "docs/guide.md", "Public, product-lens prose.\n")

    result = guard.run([repo])

    assert result.ok
    assert result.name == guard.CHECK_NAME


def test_run_fails_on_planted_ce_ops_ref(tmp_path: Path):
    repo = _make_repo(tmp_path)
    _write_tracked(repo, "docs/leak.md", "Tracked in ce-ops#999.\n")

    result = guard.run([repo])

    assert not result.ok
    confidential = _confidentiality_errors(result)
    assert len(confidential) == 1
    rendered = confidential[0]
    assert "docs/leak.md" in rendered
    assert "ce-ops#999" in rendered
    # The standing reminder is surfaced verbatim in the remediation.
    assert guard.REMINDER in rendered


def test_run_fails_on_internal_host_marker(tmp_path: Path):
    repo = _make_repo(tmp_path)
    _write_tracked(repo, "docs/topology.md", "Runs on Hetzner.\n")

    result = guard.run([repo])

    assert not result.ok
    assert any("internal hosting-provider name" in e.format() for e in result.errors)


def test_run_fails_on_net_new_internal_tree_file(tmp_path: Path):
    """A net-new docs/operations file (not on the ratchet) is flagged."""
    repo = _make_repo(tmp_path)
    _write_tracked(
        repo,
        "docs/operations/BRAND_NEW_INTERNAL_PROTOCOL.md",
        "Net-new internal protocol.\n",
    )

    result = guard.run([repo])

    assert not result.ok
    tree_errors = [e.format() for e in result.errors if "CE-INTERNAL-TREE" in e.code]
    assert any("BRAND_NEW_INTERNAL_PROTOCOL.md" in e for e in tree_errors)


def test_baseline_allowed_file_and_token_class_is_not_flagged(tmp_path: Path):
    """A repo-relative file/token-class baseline entry is skipped."""
    allowlisted = next(
        rel
        for rel, label in sorted(guard.ALLOWED_OFFENSES)
        if label == "confidential ce-ops# ticket reference"
    )
    repo = _make_repo(tmp_path)
    _write_tracked(repo, allowlisted, "Tracked in ce-ops#999.\n")

    result = guard.run([repo])

    assert result.ok, [e.format() for e in result.errors]


def test_run_passes_on_structural_carrier_metadata_with_empty_allowlist(
    tmp_path: Path, monkeypatch
):
    repo = _make_repo(tmp_path)
    monkeypatch.setattr(guard, "ALLOWED_OFFENSES", {})
    ticket_prefix = "ce-" "ops"
    slug = f"{ticket_prefix}-777-routine-carrier"
    issue = f"{ticket_prefix}#777"
    _write_tracked(
        repo,
        f".ce/changelog/{slug}.md",
        f"""---
slug: {slug}
date: 2026-07-02
kind: fix
scope: validators
issue: {issue}
---

Routine public changelog prose.
""",
    )
    _write_tracked(
        repo,
        f".ce/pr-manifests/{slug}.md",
        f"""# PR path manifest — {issue} · Routine carrier

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref {slug}` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

AUTHORIZED_PATHS_COUNT=2

```text
.ce/changelog/{slug}.md
.ce/pr-manifests/{slug}.md
```
""",
    )

    result = guard.run([repo])

    assert result.ok, [e.format() for e in result.errors]


def test_run_passes_on_qualified_changelog_issue_with_empty_allowlist(
    tmp_path: Path, monkeypatch
):
    repo = _make_repo(tmp_path)
    monkeypatch.setattr(guard, "ALLOWED_OFFENSES", {})
    ticket_prefix = "ce-" "ops"
    slug = f"{ticket_prefix}-780-qualified-changelog"
    issue = f"creator-engine/{ticket_prefix}#780"
    _write_tracked(
        repo,
        f".ce/changelog/{slug}.md",
        f"""---
slug: {slug}
date: 2026-07-02
kind: fix
scope: validators
issue: {issue}
---

Routine public changelog prose.
""",
    )

    result = guard.run([repo])

    assert result.ok, [e.format() for e in result.errors]


def test_run_fails_on_duplicate_changelog_issue_lines_with_empty_allowlist(
    tmp_path: Path, monkeypatch
):
    repo = _make_repo(tmp_path)
    monkeypatch.setattr(guard, "ALLOWED_OFFENSES", {})
    ticket_prefix = "ce-" "ops"
    slug = f"{ticket_prefix}-783-duplicate-issue"
    issue = f"{ticket_prefix}#783"
    _write_tracked(
        repo,
        f".ce/changelog/{slug}.md",
        f"""---
slug: {slug}
date: 2026-07-02
kind: fix
scope: validators
issue: {issue}
issue: {issue}
---

Routine public changelog prose.
""",
    )

    result = guard.run([repo])

    assert not result.ok
    confidential = _confidentiality_errors(result)
    assert len(confidential) == 2
    assert all(f"issue: {issue}" in item for item in confidential)


def test_run_passes_on_qualified_pr_manifest_header_with_empty_allowlist(
    tmp_path: Path, monkeypatch
):
    repo = _make_repo(tmp_path)
    monkeypatch.setattr(guard, "ALLOWED_OFFENSES", {})
    ticket_prefix = "ce-" "ops"
    issue = f"creator-engine/{ticket_prefix}#781"
    _write_tracked(
        repo,
        f".ce/pr-manifests/{ticket_prefix}-781-qualified-manifest.md",
        f"""# PR path manifest — {issue} · Qualified carrier

AUTHORIZED_PATHS_COUNT=1

```text
.ce/pr-manifests/{ticket_prefix}-781-qualified-manifest.md
```
""",
    )

    result = guard.run([repo])

    assert result.ok, [e.format() for e in result.errors]


def test_run_fails_on_qualified_body_ticket_ref_with_empty_allowlist(
    tmp_path: Path, monkeypatch
):
    repo = _make_repo(tmp_path)
    monkeypatch.setattr(guard, "ALLOWED_OFFENSES", {})
    ticket_prefix = "ce-" "ops"
    slug = f"{ticket_prefix}-782-qualified-body-leak"
    issue = f"creator-engine/{ticket_prefix}#782"
    body_ref = f"creator-engine/{ticket_prefix}#1782"
    _write_tracked(
        repo,
        f".ce/changelog/{slug}.md",
        f"""---
slug: {slug}
date: 2026-07-02
kind: fix
scope: validators
issue: {issue}
---

Body prose must not mention {body_ref}.
""",
    )

    result = guard.run([repo])

    assert not result.ok
    confidential = _confidentiality_errors(result)
    assert len(confidential) == 1
    assert f"Body prose must not mention {body_ref}" in confidential[0]


def test_run_fails_on_changelog_body_ticket_ref_with_empty_allowlist(
    tmp_path: Path, monkeypatch
):
    repo = _make_repo(tmp_path)
    monkeypatch.setattr(guard, "ALLOWED_OFFENSES", {})
    ticket_prefix = "ce-" "ops"
    slug = f"{ticket_prefix}-778-body-leak"
    issue = f"{ticket_prefix}#778"
    body_ref = f"{ticket_prefix}#1778"
    _write_tracked(
        repo,
        f".ce/changelog/{slug}.md",
        f"""---
slug: {slug}
date: 2026-07-02
kind: fix
scope: validators
issue: {issue}
---

Body prose must not mention {body_ref}.
""",
    )

    result = guard.run([repo])

    assert not result.ok
    confidential = _confidentiality_errors(result)
    assert len(confidential) == 1
    assert f"Body prose must not mention {body_ref}" in confidential[0]


def test_run_fails_on_pr_manifest_extra_ticket_ref_with_empty_allowlist(
    tmp_path: Path, monkeypatch
):
    repo = _make_repo(tmp_path)
    monkeypatch.setattr(guard, "ALLOWED_OFFENSES", {})
    ticket_prefix = "ce-" "ops"
    issue = f"{ticket_prefix}#779"
    body_ref = f"{ticket_prefix}#1779"
    _write_tracked(
        repo,
        f".ce/pr-manifests/{ticket_prefix}-779-extra-ref.md",
        f"""# PR path manifest — {issue} · Extra ref

Body prose must not mention {body_ref} beyond the header.
""",
    )

    result = guard.run([repo])

    assert not result.ok
    confidential = _confidentiality_errors(result)
    assert len(confidential) == 1
    assert f"Body prose must not mention {body_ref}" in confidential[0]


def test_run_fails_without_allowlist_on_tracked_source_file(tmp_path: Path):
    """A fake internal identifier in any tracked source file fails the scan."""
    repo = _make_repo(tmp_path)
    _write_tracked(repo, "validators/fake_module.py", "Tracked in ce-ops#999.\n")

    result = guard.run([repo])

    assert not result.ok
    confidential = _confidentiality_errors(result)
    assert len(confidential) == 1
    assert "validators/fake_module.py" in confidential[0]


def test_run_passes_with_narrow_allowlist_on_tracked_source_file(
    tmp_path: Path, monkeypatch
):
    """The allowlist is file + token-class specific: fail without, pass with."""
    repo = _make_repo(tmp_path)
    rel = "validators/legacy_fixture.py"
    _write_tracked(repo, rel, "Tracked in ce-ops#999.\n")
    monkeypatch.setitem(
        guard.ALLOWED_OFFENSES,
        (rel, "confidential ce-ops# ticket reference"),
        "test-only narrow baseline exception",
    )

    result = guard.run([repo])

    assert result.ok, [e.format() for e in result.errors]


def test_run_ignores_untracked_source_file(tmp_path: Path):
    """Untracked files are outside the public-repo tracked-text surface."""
    repo = _make_repo(tmp_path)
    untracked = repo / "validators" / "scratch.py"
    untracked.parent.mkdir(parents=True, exist_ok=True)
    untracked.write_text("Tracked in ce-ops#999.\n", encoding="utf-8")

    result = guard.run([repo])

    assert result.ok, [e.format() for e in result.errors]


def test_run_fails_closed_on_unreadable_tracked_file(tmp_path: Path, monkeypatch):
    repo = _make_repo(tmp_path)
    unreadable = _write_tracked(repo, "validators/unreadable.py", "clean = True\n").resolve()
    original_read_bytes = Path.read_bytes

    def fail_for_unreadable(path: Path) -> bytes:
        if path.resolve() == unreadable:
            raise OSError("permission denied for test")
        return original_read_bytes(path)

    monkeypatch.setattr(Path, "read_bytes", fail_for_unreadable)

    result = guard.run([repo])

    assert not result.ok
    assert any("CE-CONFIDENTIALITY-SCAN" in e.code for e in result.errors)


def test_run_fails_closed_on_stat_level_error(tmp_path: Path, monkeypatch):
    repo = _make_repo(tmp_path)
    unreadable = _write_tracked(repo, "validators/stat_blocked.py", "clean = True\n").resolve()
    original_stat = Path.stat

    def fail_for_unreadable(path: Path, *args, **kwargs):
        if path == unreadable:
            raise OSError("stat permission denied for test")
        return original_stat(path, *args, **kwargs)

    monkeypatch.setattr(Path, "stat", fail_for_unreadable)

    result = guard.run([repo])

    assert not result.ok
    assert any("CE-CONFIDENTIALITY-SCAN" in e.code for e in result.errors)
    assert any("stat permission denied for test" in e.format() for e in result.errors)


def test_run_fails_closed_when_git_ls_files_fails(tmp_path: Path, monkeypatch):
    repo = _make_repo(tmp_path)

    def fail_git_ls_files(*_args, **_kwargs):
        raise subprocess.CalledProcessError(
            128,
            ["git", "ls-files", "-z"],
            stderr=b"fatal: unable to enumerate tracked files",
        )

    monkeypatch.setattr(guard.subprocess, "run", fail_git_ls_files)

    result = guard.run([repo])

    assert not result.ok
    assert any("CE-CONFIDENTIALITY-SCAN" in e.code for e in result.errors)
    assert any("could not enumerate tracked files" in e.format() for e in result.errors)


def test_run_fails_closed_on_empty_tracked_file_scan(tmp_path: Path, monkeypatch):
    repo = _make_repo(tmp_path)
    monkeypatch.setattr(guard, "_tracked_repo_paths", lambda _root: [])

    result = guard.run([repo])

    assert not result.ok
    assert any("CE-CONFIDENTIALITY-SCAN" in e.code for e in result.errors)
    assert any("tracked text scan found no files" in e.format() for e in result.errors)


def test_run_fails_closed_on_pattern_failure(tmp_path: Path, monkeypatch):
    repo = _make_repo(tmp_path)
    _write_tracked(repo, "validators/clean.py", "clean = True\n")

    class BrokenPattern:
        def search(self, _line: str):
            raise RuntimeError("pattern engine failed for test")

    monkeypatch.setattr(guard, "FORBIDDEN_PATTERNS", (("broken pattern", BrokenPattern()),))

    result = guard.run([repo])

    assert not result.ok
    assert any("CE-CONFIDENTIALITY-SCAN" in e.code for e in result.errors)


def test_cli_subcommand_clean_exits_zero(tmp_path: Path, capsys):
    repo = _make_repo(tmp_path)
    _write_tracked(repo, "docs/ok.md", "All clean.\n")

    rc = cli.main(["scan-public-docs-confidentiality", str(repo)])

    assert rc == 0


def test_cli_subcommand_leak_exits_nonzero(tmp_path: Path, capsys):
    repo = _make_repo(tmp_path)
    _write_tracked(repo, "docs/leak.md", "Tracked in ce-ops#1234.\n")

    rc = cli.main(["scan-public-docs-confidentiality", str(repo)])

    assert rc != 0
    out = capsys.readouterr().out
    assert "ce-ops#1234" in out
    assert guard.REMINDER in out


def test_push_guard_passes_clean_pre_push_ref(tmp_path: Path):
    repo = _make_repo(tmp_path)
    _write_tracked(repo, "docs/guide.md", "Public, product-lens prose.\n")
    head = _commit(repo)

    result = guard.run_push_guard(
        [f"refs/heads/feature {head} refs/heads/feature {guard.ZERO_OID}"],
        repo_root=repo,
    )

    assert result.ok, [e.format() for e in result.errors]


def test_push_guard_blocks_leaking_pre_push_ref_before_push(tmp_path: Path):
    repo = _make_repo(tmp_path)
    _write_tracked(repo, "docs/leak.md", "Tracked in ce-ops#999.\n")
    head = _commit(repo)

    result = guard.run_push_guard(
        [f"refs/heads/feature {head} refs/heads/feature {guard.ZERO_OID}"],
        repo_root=repo,
    )

    assert not result.ok
    rendered = "\n".join(e.format() for e in result.errors)
    assert "push guard refs/heads/feature@" in rendered
    assert "docs/leak.md" in rendered
    assert "ce-ops#999" in rendered
    assert guard.REMINDER in rendered


def test_push_guard_passes_clean_pre_receive_ref(tmp_path: Path):
    repo = _make_repo(tmp_path)
    _write_tracked(repo, "docs/guide.md", "Public, product-lens prose.\n")
    head = _commit(repo)

    result = guard.run_push_guard(
        [f"{guard.ZERO_OID} {head} refs/heads/feature"],
        repo_root=repo,
    )

    assert result.ok, [e.format() for e in result.errors]


def test_push_guard_blocks_leaking_pre_receive_ref(tmp_path: Path):
    repo = _make_repo(tmp_path)
    _write_tracked(repo, "docs/leak.md", "Tracked in ce-ops#888.\n")
    head = _commit(repo)

    result = guard.run_push_guard(
        [f"{guard.ZERO_OID} {head} refs/heads/feature"],
        repo_root=repo,
    )

    assert not result.ok
    rendered = "\n".join(e.format() for e in result.errors)
    assert "push guard refs/heads/feature@" in rendered
    assert "docs/leak.md" in rendered
    assert "ce-ops#888" in rendered
    assert guard.REMINDER in rendered


def test_push_guard_cli_passes_clean_pre_receive_stdin(
    tmp_path: Path, monkeypatch, capsys
):
    repo = _make_repo(tmp_path)
    _write_tracked(repo, "docs/guide.md", "Public, product-lens prose.\n")
    head = _commit(repo)
    monkeypatch.setattr(
        "sys.stdin", io.StringIO(f"{guard.ZERO_OID} {head} refs/heads/feature\n")
    )

    rc = cli.main(["guard-public-docs-confidentiality-push", str(repo)])

    assert rc == 0


def test_push_guard_cli_blocks_leaking_pre_receive_stdin(
    tmp_path: Path, monkeypatch, capsys
):
    repo = _make_repo(tmp_path)
    _write_tracked(repo, "docs/leak.md", "Tracked in ce-ops#666.\n")
    head = _commit(repo)
    monkeypatch.setattr(
        "sys.stdin", io.StringIO(f"{guard.ZERO_OID} {head} refs/heads/feature\n")
    )

    rc = cli.main(["guard-public-docs-confidentiality-push", str(repo)])

    assert rc != 0
    out = capsys.readouterr().out
    assert "docs/leak.md" in out
    assert "ce-ops#666" in out
    assert guard.REMINDER in out


def test_push_guard_skips_pre_receive_zero_oid_deletion(tmp_path: Path):
    repo = _make_repo(tmp_path)
    _write_tracked(repo, "docs/leak.md", "Tracked in ce-ops#444.\n")
    head = _commit(repo)

    result = guard.run_push_guard(
        [f"{head} {guard.ZERO_OID} refs/heads/feature"],
        repo_root=repo,
    )

    assert result.ok, [e.format() for e in result.errors]


def test_push_guard_fails_closed_on_malformed_ref_update(tmp_path: Path):
    repo = _make_repo(tmp_path)
    _write_tracked(repo, "docs/guide.md", "Public, product-lens prose.\n")
    _commit(repo)

    result = guard.run_push_guard(["malformed update"], repo_root=repo)

    assert not result.ok
    rendered = "\n".join(e.format() for e in result.errors)
    assert "CE-CONFIDENTIALITY-PUSH-SCAN" in rendered
    assert "malformed update" in rendered


def test_push_guard_cli_blocks_explicit_leaking_object(tmp_path: Path, capsys):
    repo = _make_repo(tmp_path)
    _write_tracked(repo, "docs/leak.md", "Tracked in ce-ops#777.\n")
    head = _commit(repo)

    rc = cli.main(
        ["guard-public-docs-confidentiality-push", str(repo), "--object", head]
    )

    assert rc != 0
    out = capsys.readouterr().out
    assert "docs/leak.md" in out
    assert "ce-ops#777" in out
