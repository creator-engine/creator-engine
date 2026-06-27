"""Tests for the standalone public-docs confidentiality check + CLI subcommand.

This locks the pre-push half of the root fix: the same single-sourced rule the
CI guard uses is exposed as ``scan-public-docs-confidentiality`` and runs in
``ce validate-pr`` before push.
"""
from __future__ import annotations

from pathlib import Path

from creator_engine_validator import cli
from creator_engine_validator import public_docs_confidentiality as guard


def _make_repo(tmp_path: Path) -> Path:
    """A minimal repo whose internal-tree guard is satisfied.

    Materializes exactly the ce-ops#283 exception files (so neither
    ``unreviewed`` net-new files nor ``stale`` missing exceptions fire), leaving
    the confidentiality pattern scan as the only variable under test.
    """
    (tmp_path / ".git").mkdir()
    (tmp_path / "docs").mkdir()
    (tmp_path / "README.md").write_text("# Clean product front door.\n", encoding="utf-8")
    for rel in (*guard.KNOWN_OPERATIONS_EXCEPTIONS, *guard.KNOWN_DELIVERY_EXCEPTIONS):
        target = tmp_path / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("Internal protocol doc.\n", encoding="utf-8")
    return tmp_path


def _confidentiality_errors(result) -> list[str]:
    return [e.format() for e in result.errors if "CE-CONFIDENTIALITY" in e.code]


def test_run_passes_on_clean_repo(tmp_path: Path):
    repo = _make_repo(tmp_path)
    (repo / "docs" / "guide.md").write_text("Public, product-lens prose.\n", encoding="utf-8")

    result = guard.run([repo])

    assert result.ok
    assert result.name == guard.CHECK_NAME


def test_run_fails_on_planted_ce_ops_ref(tmp_path: Path):
    repo = _make_repo(tmp_path)
    (repo / "docs" / "leak.md").write_text("Tracked in ce-ops#999.\n", encoding="utf-8")

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
    (repo / "docs" / "topology.md").write_text("Runs on Hetzner.\n", encoding="utf-8")

    result = guard.run([repo])

    assert not result.ok
    assert any("internal hosting-provider name" in e.format() for e in result.errors)


def test_run_fails_on_net_new_internal_tree_file(tmp_path: Path):
    """A net-new docs/operations file (not on the ratchet) is flagged."""
    repo = _make_repo(tmp_path)
    netnew = repo / "docs" / "operations" / "BRAND_NEW_INTERNAL_PROTOCOL.md"
    netnew.write_text("Net-new internal protocol.\n", encoding="utf-8")

    result = guard.run([repo])

    assert not result.ok
    tree_errors = [e.format() for e in result.errors if "CE-INTERNAL-TREE" in e.code]
    assert any("BRAND_NEW_INTERNAL_PROTOCOL.md" in e for e in tree_errors)


def test_known_pending_file_is_not_flagged(tmp_path: Path):
    """A repo-relative path on the allowlist is skipped even if it offends."""
    # Use a real allowlisted path so the rule (single-sourced) recognizes it.
    allowlisted = next(iter(sorted(guard.KNOWN_PENDING)))
    repo = _make_repo(tmp_path)
    target = repo / allowlisted
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("Tracked in ce-ops#999.\n", encoding="utf-8")

    result = guard.run([repo])

    assert result.ok, [e.format() for e in result.errors]


def test_cli_subcommand_clean_exits_zero(tmp_path: Path, capsys):
    repo = _make_repo(tmp_path)
    (repo / "docs" / "ok.md").write_text("All clean.\n", encoding="utf-8")

    rc = cli.main(["scan-public-docs-confidentiality", str(repo)])

    assert rc == 0


def test_cli_subcommand_leak_exits_nonzero(tmp_path: Path, capsys):
    repo = _make_repo(tmp_path)
    (repo / "docs" / "leak.md").write_text("Tracked in ce-ops#1234.\n", encoding="utf-8")

    rc = cli.main(["scan-public-docs-confidentiality", str(repo)])

    assert rc != 0
    out = capsys.readouterr().out
    assert "ce-ops#1234" in out
    assert guard.REMINDER in out
