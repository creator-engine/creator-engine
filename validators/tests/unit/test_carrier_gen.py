import hashlib
from pathlib import Path

from creator_engine_validator.carrier_gen import (
    CarrierSpec,
    compute_path_set,
    render_changelog,
    render_manifest,
    write_carriers,
)
from creator_engine_validator.checks.path_manifest_fidelity import MANIFEST_DIR, branch_slug, parse_carrier


def _sha(paths):
    normalized = "\n".join(sorted(set(paths))) + "\n"
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def test_compute_path_set_uses_injected_runner_and_canonicalizes(tmp_path: Path):
    calls = []

    def fake_git(argv, cwd):
        calls.append((list(argv), cwd))
        return 0, "z.py\na.py\na.py\n\n", ""

    paths, count, sha = compute_path_set(tmp_path, "ce-test", base="base-sha", git_runner=fake_git)

    assert calls == [(["diff", "--name-only", "--find-renames", "base-sha..HEAD"], tmp_path)]
    assert paths == (f"{MANIFEST_DIR}/ce-test.md", "a.py", "z.py")
    assert count == 3
    assert sha == _sha(paths)


def test_compute_path_set_manifest_self_inclusion_is_deterministic(tmp_path: Path):
    def fake_git(argv, cwd):
        return 0, "b.py\n.ce/pr-manifests/ce-test.md\na.py\n", ""

    first = compute_path_set(tmp_path, "ce-test", git_runner=fake_git)
    second = compute_path_set(tmp_path, "ce-test", git_runner=fake_git)

    assert first == second
    assert first[0] == (f"{MANIFEST_DIR}/ce-test.md", "a.py", "b.py")
    assert first[1] == len(first[0])


def test_compute_path_set_excludes_generated_build_artifacts(tmp_path: Path, recwarn):
    def fake_git(argv, cwd):
        return (
            0,
            "\n".join(
                [
                    "build/lib/generated.py",
                    "creator_engine_validator.egg-info/PKG-INFO",
                    "validators/build/lib/generated.py",
                    "validators/x.egg-info/SOURCES.txt",
                    "validators/tests/unit/test_carrier_gen.py",
                ]
            )
            + "\n",
            "",
        )

    paths, count, sha = compute_path_set(tmp_path, "ce-test", git_runner=fake_git)

    assert paths == (f"{MANIFEST_DIR}/ce-test.md", "validators/tests/unit/test_carrier_gen.py")
    assert count == 2
    assert sha == _sha(paths)
    warning = recwarn.pop(RuntimeWarning)
    assert "excluded generated build artifact path(s) from carrier manifest" in str(warning.message)
    assert "build/lib/generated.py" in str(warning.message)
    assert "validators/x.egg-info/SOURCES.txt" in str(warning.message)


def test_render_manifest_round_trips_through_verifier_parser():
    paths = ("b.py", f"{MANIFEST_DIR}/ce-test.md", "a.py")
    count = len(set(paths))
    sha = _sha(paths)

    text = render_manifest("ce-test", "ce-ops#1", "Carrier generator", paths, count, sha)
    identity = parse_carrier(text)

    assert text == (
        "# PR path manifest — ce-ops#1 · Carrier generator\n\n"
        "This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed "
        "authorized path-set for this PR. CI runs "
        "`verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce-test` "
        "and requires this PR's `base..HEAD` diff to equal exactly the authorized "
        "path-set below; this carrier lists itself.\n\n"
        'Canonicalization: `sha256("\\n".join(sorted(unique_paths)) + "\\n")`.\n\n'
        "AUTHORIZED_PATHS_COUNT=3\n\n"
        f"AUTHORIZED_PATHS_SHA256={sha}\n\n"
        "```text\n"
        ".ce/pr-manifests/ce-test.md\n"
        "a.py\n"
        "b.py\n"
        "```\n"
    )
    assert "Declared work class" not in text
    assert "Base:" not in text
    assert identity is not None
    assert identity.name == "AUTHORIZED"
    assert identity.consistent is True
    assert identity.declared_count == count
    assert identity.declared_sha256 == sha
    assert identity.paths == (f"{MANIFEST_DIR}/ce-test.md", "a.py", "b.py")


def test_render_manifest_can_include_declared_work_class_without_affecting_path_identity():
    paths = ("b.py", f"{MANIFEST_DIR}/ce-test.md", "a.py")
    count = len(set(paths))
    sha = _sha(paths)

    text = render_manifest(
        "ce-test",
        "ce-ops#1",
        "Carrier generator",
        paths,
        count,
        sha,
        declared_work_class="M",
    )
    identity = parse_carrier(text)

    assert text.count("- **Declared work class:** feature") == 1
    assert identity is not None
    assert identity.consistent is True
    assert identity.paths == (f"{MANIFEST_DIR}/ce-test.md", "a.py", "b.py")


def test_render_manifest_canonicalizes_retired_work_class_aliases_without_changing_canonical_inputs():
    paths = (f"{MANIFEST_DIR}/ce-test.md", "a.py")
    count = len(paths)
    sha = _sha(paths)

    for supplied, expected in (
        ("XS", "tiny"),
        ("S", "story"),
        ("M", "feature"),
        ("L", "epic"),
        ("tiny", "tiny"),
        ("story", "story"),
        ("feature", "feature"),
        ("epic", "epic"),
    ):
        text = render_manifest(
            "ce-test",
            "ce-ops#536",
            "Canonical carrier work class",
            paths,
            count,
            sha,
            declared_work_class=supplied,
        )

        assert f"- **Declared work class:** {expected}" in text


def test_render_changelog_frontmatter_and_body():
    text = render_changelog(
        "ce-test",
        "ce-ops#1",
        "Carrier generator",
        "added",
        "validator tooling",
        "- Added carrier generation helpers.",
        "2026-06-24",
    )

    assert text == (
        "---\n"
        "slug: ce-test\n"
        "date: 2026-06-24\n"
        "kind: added\n"
        "scope: validator tooling\n"
        "issue: ce-ops#1\n"
        "---\n\n"
        "**Carrier generator.**\n\n"
        "- Added carrier generation helpers.\n"
    )


def test_render_changelog_does_not_double_terminal_punctuation():
    text = render_changelog(
        "ce-test",
        "ce-ops#1",
        "Carrier generator!",
        "added",
        "validator tooling",
        "- Added carrier generation helpers.",
        "2026-06-24",
    )

    assert "\n\n**Carrier generator!**\n\n" in text
    assert "Carrier generator!." not in text


def test_write_carriers_writes_changelog_before_manifest_and_uses_diff_paths(tmp_path: Path):
    spec = CarrierSpec(
        head_ref="CE/Test",
        issue="ce-ops#1",
        title="Carrier generator",
        kind="added",
        scope="validator tooling",
        body="- Added carrier generation helpers.",
        date="2026-06-24",
        base="origin/main",
        declared_work_class="S",
    )
    slug = branch_slug(spec.head_ref)
    events = []

    def fake_git(argv, cwd):
        changelog = cwd / ".ce" / "changelog" / f"{slug}.md"
        manifest = cwd / MANIFEST_DIR / f"{slug}.md"
        events.append(
            {
                "argv": list(argv),
                "changelog_exists": changelog.exists(),
                "manifest_exists": manifest.exists(),
            }
        )
        return 0, "validators/creator_engine_validator/carrier_gen.py\n", ""

    written = write_carriers(tmp_path, spec, git_runner=fake_git)

    assert events == [
        {
            "argv": ["diff", "--name-only", "--find-renames", "origin/main..HEAD"],
            "changelog_exists": True,
            "manifest_exists": False,
        }
    ]
    assert written.slug == slug
    assert written.changelog_path == tmp_path / ".ce" / "changelog" / f"{slug}.md"
    assert written.manifest_path == tmp_path / MANIFEST_DIR / f"{slug}.md"
    assert written.paths == (
        f".ce/changelog/{slug}.md",
        f"{MANIFEST_DIR}/{slug}.md",
        "validators/creator_engine_validator/carrier_gen.py",
    )

    identity = parse_carrier(written.manifest_path.read_text(encoding="utf-8"))
    assert identity is not None
    assert identity.consistent is True
    assert identity.paths == written.paths
    assert written.manifest_path.read_text(encoding="utf-8").count("- **Declared work class:** story") == 1


def test_write_carriers_excludes_stale_artifacts_from_manifest(tmp_path: Path, recwarn):
    spec = CarrierSpec(
        head_ref="ce-test-artifacts",
        issue="ce-ops#456",
        title="Carrier artifact self-clean",
        kind="fixed",
        scope="validator tooling",
        body="- Exclude stale build artifacts from generated path manifests.",
        date="2026-07-05",
        base="origin/main",
        declared_work_class="story",
    )

    def fake_git(argv, cwd):
        return (
            0,
            "\n".join(
                [
                    "validators/build/lib/creator_engine_validator/carrier_gen.py",
                    "validators/creator_engine_validator.egg-info/PKG-INFO",
                    "validators/creator_engine_validator/carrier_gen.py",
                    "validators/tests/unit/test_carrier_gen.py",
                ]
            )
            + "\n",
            "",
        )

    written = write_carriers(tmp_path, spec, git_runner=fake_git)

    assert "validators/build/lib/creator_engine_validator/carrier_gen.py" not in written.paths
    assert "validators/creator_engine_validator.egg-info/PKG-INFO" not in written.paths
    assert written.paths == (
        ".ce/changelog/ce-test-artifacts.md",
        f"{MANIFEST_DIR}/ce-test-artifacts.md",
        "validators/creator_engine_validator/carrier_gen.py",
        "validators/tests/unit/test_carrier_gen.py",
    )
    warning = recwarn.pop(RuntimeWarning)
    assert "validators/build/lib/creator_engine_validator/carrier_gen.py" in str(warning.message)
    identity = parse_carrier(written.manifest_path.read_text(encoding="utf-8"))
    assert identity is not None
    assert identity.paths == written.paths
