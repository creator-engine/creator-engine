"""Unit tests for the ce-ops#216 deterministic conflict resolver library."""

from __future__ import annotations

from creator_engine_validator.forge import deterministic_resolvers as dr

_OURS = "<" * 7 + " ours"
_SEP = "=" * 7
_THEIRS = ">" * 7 + " theirs"


def _versions_conflict() -> str:
    return f'''"""taxonomy"""
from __future__ import annotations

V1_RUNTIME: frozenset[str] = frozenset(
    {{
        "lane_runtime",
{_OURS}
        "ce_profile_path",
{_SEP}
        "ce_provenance",
{_THEIRS}
    }}
)

V3_RUNTIME: frozenset[str] = frozenset(
    {{
        "forge",
{_OURS}
        "forge.re_review",
{_SEP}
        "forge.user_install_discovery",
{_THEIRS}
    }}
)
'''


def test_versions_registry_conflict_unions_module_entries_and_verifies():
    result = dr.resolve_conflict("validators/creator_engine_validator/_versions.py", _versions_conflict())

    assert result.applicable is True
    assert result.resolved is True
    assert result.unresolved is False
    assert result.changed_paths == ("validators/creator_engine_validator/_versions.py",)
    assert result.resolver == "versions_module_registry_union"
    assert '"ce_profile_path"' in result.content
    assert '"ce_provenance"' in result.content
    assert '"forge.re_review"' in result.content
    assert '"forge.user_install_discovery"' in result.content
    assert "<<<<<<<" not in result.content
    verified = dr.verify_resolution(result)
    assert verified.resolved is True
    assert "V1_RUNTIME=3" in verified.evidence
    assert "V3_RUNTIME=3" in verified.evidence


def test_versions_registry_conflict_fails_on_v1_v3_id_collision():
    text = f'''from __future__ import annotations
V1_RUNTIME = frozenset({{
{_OURS}
    "seat_pty_session",
{_SEP}
    "shared_name",
{_THEIRS}
}})
V3_RUNTIME = frozenset({{
{_OURS}
    "forge",
{_SEP}
    "shared_name",
{_THEIRS}
}})
'''

    result = dr.resolve_conflict("validators/creator_engine_validator/_versions.py", text)

    assert result.applicable is True
    assert result.resolved is False
    assert result.unresolved is True
    assert "module id collision" in result.reason


def test_versions_registry_conflict_fails_on_malformed_entries():
    text = f'''from __future__ import annotations
V1_RUNTIME = frozenset({{
{_OURS}
    "ce_cli",
{_SEP}
    dynamic_name,
{_THEIRS}
}})
V3_RUNTIME = frozenset({{"forge"}})
'''

    result = dr.resolve_conflict("validators/creator_engine_validator/_versions.py", text)

    assert result.applicable is True
    assert result.unresolved is True
    assert "malformed" in result.reason


def test_version_boundary_count_conflict_uses_post_merge_registry_total():
    versions = dr.resolve_conflict("validators/creator_engine_validator/_versions.py", _versions_conflict()).content
    count_conflict = f"""def test_taxonomy_counts_and_disjoint():
{_OURS}
    assert len(ver.V1_RUNTIME) == 2
{_SEP}
    assert len(ver.V1_RUNTIME) == 2
{_THEIRS}
{_OURS}
    assert len(ver.V3_RUNTIME) == 2
{_SEP}
    assert len(ver.V3_RUNTIME) == 2
{_THEIRS}
    assert ver.V1_RUNTIME.isdisjoint(ver.V3_RUNTIME)
"""

    result = dr.resolve_conflict(
        "validators/tests/unit/test_version_boundary.py",
        count_conflict,
        context_files={"validators/creator_engine_validator/_versions.py": versions},
    )

    assert result.applicable is True
    assert result.resolved is True
    assert "assert len(ver.V1_RUNTIME) == 3" in result.content
    assert "assert len(ver.V3_RUNTIME) == 3" in result.content
    assert "<<<<<<<" not in result.content


def test_version_boundary_count_conflict_without_resolved_registry_escalates():
    result = dr.resolve_conflict(
        "validators/tests/unit/test_version_boundary.py",
        f"{_OURS}\n    assert len(ver.V3_RUNTIME) == 49\n"
        f"{_SEP}\n    assert len(ver.V3_RUNTIME) == 49\n{_THEIRS}\n",
    )

    assert result.applicable is True
    assert result.unresolved is True
    assert "requires resolved _versions.py context" in result.reason


def test_non_overlapping_ce_changelog_and_manifest_additions_take_both():
    result = dr.resolve_non_overlapping_additions(
        base_paths={"README.md"},
        ours_paths={
            "README.md",
            ".ce/changelog/ce197-verify-install.md",
            ".ce/pr-manifests/ce197-verify-install.md",
        },
        theirs_paths={
            "README.md",
            ".ce/changelog/ce207-w2prime-pty-session.md",
            ".ce/pr-manifests/ce207-w2prime-pty-session.md",
        },
    )

    assert result.applicable is True
    assert result.resolved is True
    assert result.changed_paths == (
        ".ce/changelog/ce197-verify-install.md",
        ".ce/changelog/ce207-w2prime-pty-session.md",
        ".ce/pr-manifests/ce197-verify-install.md",
        ".ce/pr-manifests/ce207-w2prime-pty-session.md",
    )


def test_overlapping_ce_carrier_addition_escalates():
    result = dr.resolve_non_overlapping_additions(
        base_paths=set(),
        ours_paths={".ce/pr-manifests/same.md"},
        theirs_paths={".ce/pr-manifests/same.md"},
    )

    assert result.applicable is True
    assert result.unresolved is True
    assert "overlapping additions" in result.reason


def test_append_only_registry_conflict_unions_non_overlapping_lines():
    text = f"""existing
{_OURS}
beta
{_SEP}
alpha
{_THEIRS}
tail
"""

    result = dr.resolve_conflict(".ce/registries/append-only.txt", text)

    assert result.applicable is True
    assert result.resolved is True
    assert result.content == "existing\nalpha\nbeta\ntail\n"
    assert result.evidence == ("append_lines=2", "canonical_order=lexicographic")


def test_append_only_registry_conflict_escalates_when_overlap_or_unclear():
    overlap = f"before\n{_OURS}\nsame\n{_SEP}\nsame\n{_THEIRS}\n"
    result = dr.resolve_conflict(".ce/registries/append-only.txt", overlap)

    assert result.applicable is True
    assert result.unresolved is True
    assert "overlapping append entries" in result.reason

    unclear = (
        '{"lockfileVersion": 3,\n'
        f"{_OURS}\n"
        '"packages": {}\n'
        f"{_SEP}\n"
        '"dependencies": {}\n'
        f"{_THEIRS}\n"
        "}\n"
    )
    unclear_result = dr.resolve_conflict("package-lock.json", unclear)
    assert unclear_result.applicable is True
    assert unclear_result.unresolved is True
    assert "canonicalization is unclear" in unclear_result.reason


def test_unrecognized_conflict_is_not_applicable():
    result = dr.resolve_conflict("src/app.py", f"{_OURS}\nx\n{_SEP}\ny\n{_THEIRS}\n")

    assert result.applicable is False
    assert result.resolved is False
    assert result.unresolved is False
