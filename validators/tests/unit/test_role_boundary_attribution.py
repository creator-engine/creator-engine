from pathlib import Path

from creator_engine_validator.checks import registered_checks
from creator_engine_validator.checks.role_boundary_attribution import (
    CHECK_NAME,
    run,
    run_with_base,
    scan_document,
)


def test_role_boundary_attribution_registered():
    checks = registered_checks()
    assert CHECK_NAME in checks


def test_scan_document_warns_on_controller_role_with_manifest(tmp_path: Path):
    text = (
        "---\n"
        "kind: hermes-handoff\n"
        "role: controller\n"
        "---\n"
        "\n"
        "```text\n"
        "docs/a.md\n"
        "```\n"
    )
    warnings = scan_document(tmp_path / "h.md", text)
    codes = {w.code for w in warnings}
    assert "role_boundary_controller_manifest_shape" in codes, [w.format() for w in warnings]


def test_scan_document_silent_on_implementer_with_manifest(tmp_path: Path):
    text = (
        "---\n"
        "kind: hermes-handoff\n"
        "role: implementer\n"
        "---\n"
        "\n"
        "```text\n"
        "docs/a.md\n"
        "```\n"
    )
    warnings = scan_document(tmp_path / "h.md", text)
    assert warnings == []


def test_scan_document_silent_on_non_handoff(tmp_path: Path):
    text = (
        "---\n"
        "kind: other\n"
        "role: controller\n"
        "---\n"
        "\n"
        "```text\n"
        "docs/a.md\n"
        "```\n"
    )
    warnings = scan_document(tmp_path / "h.md", text)
    assert warnings == []


def test_run_walks_tree_warning_only(tmp_path: Path):
    bad = (
        "---\n"
        "kind: hermes-handoff\n"
        "role: controller\n"
        "---\n"
        "\n"
        "```text\n"
        "docs/a.md\n"
        "```\n"
    )
    (tmp_path / "h.md").write_text(bad)
    result = run([tmp_path])
    # Default mode emits warnings, NOT errors — overall result should still be ok.
    assert result.ok
    codes = {w.code for w in result.warnings}
    assert "role_boundary_controller_manifest_shape" in codes


def test_run_with_base_handles_missing_handoffs(tmp_path: Path):
    # No .hermes/handoffs/ → check emits role_boundary_no_active_handoff.
    (tmp_path / ".git").mkdir()
    (tmp_path / "validators").mkdir()  # so _repo_root_for picks this dir
    result = run_with_base([tmp_path], "HEAD~1")
    assert not result.ok
    codes = {e.code for e in result.errors}
    assert "role_boundary_no_active_handoff" in codes
