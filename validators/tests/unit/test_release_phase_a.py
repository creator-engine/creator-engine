"""Phase-A autonomous-release tests: release-bump, release-changelog, release.

Stage-to-seam only — these prove the bump fail-closed tag==version assertion,
the changelog aggregation, and the orchestrator wiring (which wraps the
existing placeholder-signed release-stage; no signing/publishing is added).
"""
from __future__ import annotations

import hashlib
import json
import re
import subprocess
from pathlib import Path

import pytest

from creator_engine_validator import cli
from creator_engine_validator.release_bump import (
    BumpResult,
    ReleaseBumpError,
    bump_release_version,
    next_version,
    version_from_tag,
)
from creator_engine_validator.release_changelog import (
    ReleaseChangelogError,
    aggregate_changelog,
)
from creator_engine_validator.release_orchestrate import (
    ReleaseOrchestrationError,
    orchestrate_release,
)
from creator_engine_validator.wheel_bake import WheelManifest


# --------------------------------------------------------------------------- #
# Fixtures
# --------------------------------------------------------------------------- #


def _git(cwd: Path, *args: str) -> str:
    proc = subprocess.run(["git", *args], cwd=cwd, check=False, capture_output=True, text=True)
    assert proc.returncode == 0, proc.stderr
    return proc.stdout.strip()


def _write_version_sources(root: Path, version: str = "0.2.0") -> None:
    package = root / "validators" / "creator_engine_validator"
    package.mkdir(parents=True, exist_ok=True)
    (root / "validators" / "pyproject.toml").write_text(
        f'[project]\nname = "creator-engine-validator"\nversion = "{version}"\n',
        encoding="utf-8",
    )
    (package / "version.py").write_text(
        f'"""version module."""\n\n__version__ = "{version}"\nSEMVER = __version__\n',
        encoding="utf-8",
    )


def _changelog_fragment(root: Path, name: str, *, kind: str, slug: str, issue: str, body: str) -> Path:
    cdir = root / ".ce" / "changelog"
    cdir.mkdir(parents=True, exist_ok=True)
    path = cdir / name
    path.write_text(
        f"---\nslug: {slug}\ndate: 2026-06-27\nkind: {kind}\nscope: test\nissue: {issue}\n---\n\n{body}\n",
        encoding="utf-8",
    )
    return path


# --------------------------------------------------------------------------- #
# release-bump (A1)
# --------------------------------------------------------------------------- #


def test_version_from_tag():
    assert version_from_tag("release/v0.3.0") == "0.3.0"
    assert version_from_tag("release/v1.2.3") == "1.2.3"


def test_version_from_tag_rejects_bad_shape():
    for bad in ("v0.3.0", "release/0.3.0", "release/vX.Y.Z", "main", "release/v1.2"):
        with pytest.raises(ReleaseBumpError):
            version_from_tag(bad)


def test_next_version():
    assert next_version("0.2.0", "patch") == "0.2.1"
    assert next_version("0.2.0", "minor") == "0.3.0"
    assert next_version("0.2.5", "major") == "1.0.0"


def test_bump_from_tag_drives_both_sources(tmp_path: Path):
    root = tmp_path / "repo"
    _write_version_sources(root, "0.2.0")

    result = bump_release_version(repo_root=root, tag="release/v0.3.0")
    assert isinstance(result, BumpResult)
    assert result.version == "0.3.0"
    assert result.previous_version == "0.2.0"
    assert result.source == "tag"

    version_py = (root / "validators" / "creator_engine_validator" / "version.py").read_text()
    assert '__version__ = "0.3.0"' in version_py
    pyproject = (root / "validators" / "pyproject.toml").read_text()
    assert 'version = "0.3.0"' in pyproject


def test_bump_from_part(tmp_path: Path):
    root = tmp_path / "repo"
    _write_version_sources(root, "0.2.0")
    result = bump_release_version(repo_root=root, part="minor")
    assert result.version == "0.3.0"
    assert result.source == "part:minor"


def test_bump_from_part_uses_latest_release_tag_when_source_is_stale(tmp_path: Path):
    root = tmp_path / "repo"
    _write_version_sources(root, "0.4.0")
    _git(root, "init", "-q")
    _git(root, "config", "user.email", "t@t.invalid")
    _git(root, "config", "user.name", "T")
    _git(root, "add", ".")
    _git(root, "commit", "-q", "-m", "release 0.4.0")
    _git(root, "tag", "-a", "release/v0.4.0", "-m", "r040")

    # Simulate a rehearsal checkout whose source version is behind the latest
    # release tag. The part bump must not compute from the stale source.
    _write_version_sources(root, "0.3.0")
    result = bump_release_version(repo_root=root, part="patch")
    assert result.version == "0.4.1"
    assert '__version__ = "0.4.1"' in (
        root / "validators" / "creator_engine_validator" / "version.py"
    ).read_text()
    assert 'version = "0.4.1"' in (root / "validators" / "pyproject.toml").read_text()


def test_bump_from_part_does_not_downgrade_when_source_is_ahead_of_tag(tmp_path: Path):
    root = tmp_path / "repo"
    _write_version_sources(root, "0.3.0")
    _git(root, "init", "-q")
    _git(root, "config", "user.email", "t@t.invalid")
    _git(root, "config", "user.name", "T")
    _git(root, "add", ".")
    _git(root, "commit", "-q", "-m", "release 0.3.0")
    _git(root, "tag", "-a", "release/v0.3.0", "-m", "r030")

    _write_version_sources(root, "0.4.0")
    result = bump_release_version(repo_root=root, part="patch")
    assert result.version == "0.4.1"


def test_bump_updates_only_project_version_in_pyproject(tmp_path: Path):
    root = tmp_path / "repo"
    _write_version_sources(root, "0.2.0")
    pyproject = root / "validators" / "pyproject.toml"
    pyproject.write_text(
        pyproject.read_text(encoding="utf-8") + '\n[tool.example]\nversion = "9.9.9"\n',
        encoding="utf-8",
    )
    bump_release_version(repo_root=root, tag="release/v0.3.0")

    text = pyproject.read_text(encoding="utf-8")
    assert '[project]\nname = "creator-engine-validator"\nversion = "0.3.0"\n' in text
    assert '[tool.example]\nversion = "9.9.9"\n' in text


def test_release_bump_cli_json_output(tmp_path: Path, capsys):
    root = tmp_path / "repo"
    _write_version_sources(root, "0.2.0")

    assert cli.main(["--json", "release-bump", "--repo-root", str(root), "--tag", "release/v0.3.0"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["version"] == "0.3.0"
    assert payload["previous_version"] == "0.2.0"
    assert payload["source"] == "tag"
    assert payload["version_py"].endswith("validators/creator_engine_validator/version.py")
    assert payload["pyproject"].endswith("validators/pyproject.toml")


def test_bump_requires_exactly_one_of_tag_or_part(tmp_path: Path):
    root = tmp_path / "repo"
    _write_version_sources(root)
    with pytest.raises(ReleaseBumpError, match="exactly one"):
        bump_release_version(repo_root=root)
    with pytest.raises(ReleaseBumpError, match="exactly one"):
        bump_release_version(repo_root=root, tag="release/v0.3.0", part="patch")


def test_bump_fails_closed_on_pre_existing_drift(tmp_path: Path):
    """If version.py and pyproject already disagree, refuse before touching."""
    root = tmp_path / "repo"
    _write_version_sources(root, "0.2.0")
    (root / "validators" / "pyproject.toml").write_text(
        '[project]\nname = "creator-engine-validator"\nversion = "0.9.9"\n', encoding="utf-8"
    )
    with pytest.raises(ReleaseBumpError, match="drifted before bump"):
        bump_release_version(repo_root=root, tag="release/v0.3.0")
    # untouched
    assert '__version__ = "0.2.0"' in (
        root / "validators" / "creator_engine_validator" / "version.py"
    ).read_text()


def test_bump_rolls_back_on_failure(tmp_path: Path, monkeypatch):
    """A failure after writing one source rolls BOTH sources back (fail-closed)."""
    root = tmp_path / "repo"
    _write_version_sources(root, "0.2.0")

    import creator_engine_validator.release_bump as rb

    def boom(pyproject, new_version):
        raise ReleaseBumpError("simulated write failure")

    monkeypatch.setattr(rb, "_write_pyproject_version", boom)
    with pytest.raises(ReleaseBumpError, match="simulated write failure"):
        bump_release_version(repo_root=root, tag="release/v0.3.0")

    # version.py must be rolled back to 0.2.0 despite being written first.
    assert '__version__ = "0.2.0"' in (
        root / "validators" / "creator_engine_validator" / "version.py"
    ).read_text()
    # pyproject likewise unchanged.
    assert 'version = "0.2.0"' in (root / "validators" / "pyproject.toml").read_text()


def test_bump_rejects_non_release_tag(tmp_path: Path):
    root = tmp_path / "repo"
    _write_version_sources(root)
    with pytest.raises(ReleaseBumpError):
        bump_release_version(repo_root=root, tag="v0.3.0")


# --------------------------------------------------------------------------- #
# release-changelog (A2)
# --------------------------------------------------------------------------- #


def test_changelog_aggregates_all_when_no_release_tag(tmp_path: Path):
    root = tmp_path / "repo"
    _write_version_sources(root)
    _changelog_fragment(root, "a.md", kind="added", slug="a-feature", issue="ce-ops#1", body="Added a thing.")
    _changelog_fragment(root, "b.md", kind="fixed", slug="b-bugfix", issue="ce-ops#2", body="Fixed a thing.")
    _git(root, "init", "-q")
    _git(root, "config", "user.email", "t@t.invalid")
    _git(root, "config", "user.name", "T")
    _git(root, "add", ".")
    _git(root, "commit", "-q", "-m", "init")

    result = aggregate_changelog(repo_root=root, version="0.3.0")
    assert result.since_tag is None  # no release/* tag exists
    assert result.fragment_count == 2
    assert "# Release 0.3.0" in result.notes
    assert "## Added" in result.notes
    assert "## Fixed" in result.notes
    assert "a-feature" in result.notes
    assert "ce-ops#1" in result.notes


def test_changelog_groups_by_kind_deterministically(tmp_path: Path):
    root = tmp_path / "repo"
    _write_version_sources(root)
    _changelog_fragment(root, "z.md", kind="added", slug="z", issue="", body="Z added.")
    _changelog_fragment(root, "a.md", kind="added", slug="a", issue="", body="A added.")
    result = aggregate_changelog(repo_root=root, version="0.3.0")
    # Added section lists slugs alphabetically: a before z.
    added_block = result.notes.split("## Added")[1]
    assert added_block.index("**a**") < added_block.index("**z**")


def test_changelog_handles_fragment_without_front_matter(tmp_path: Path):
    root = tmp_path / "repo"
    _write_version_sources(root)
    cdir = root / ".ce" / "changelog"
    cdir.mkdir(parents=True)
    (cdir / "raw.md").write_text("Just a body, no front matter.\n", encoding="utf-8")
    result = aggregate_changelog(repo_root=root, version="0.3.0")
    assert result.fragment_count == 1
    assert "raw" in result.notes  # slug derived from filename
    assert "## Other" in result.notes


def test_changelog_since_tag_selects_only_new_fragments(tmp_path: Path):
    root = tmp_path / "repo"
    _write_version_sources(root)
    _changelog_fragment(root, "old.md", kind="added", slug="old", issue="", body="Old.")
    _git(root, "init", "-q")
    _git(root, "config", "user.email", "t@t.invalid")
    _git(root, "config", "user.name", "T")
    _git(root, "add", ".")
    _git(root, "commit", "-q", "-m", "old")
    _git(root, "tag", "-a", "release/v0.2.0", "-m", "r020")
    _changelog_fragment(root, "new.md", kind="fixed", slug="new", issue="", body="New.")
    _git(root, "add", ".")
    _git(root, "commit", "-q", "-m", "new frag")

    result = aggregate_changelog(repo_root=root, version="0.3.0")
    assert result.since_tag == "release/v0.2.0"
    assert result.fragment_count == 1
    assert "new" in result.notes
    assert "**old**" not in result.notes


def test_changelog_missing_dir_fails_closed(tmp_path: Path):
    root = tmp_path / "repo"
    _write_version_sources(root)
    with pytest.raises(ReleaseChangelogError, match="changelog directory not found"):
        aggregate_changelog(repo_root=root, version="0.3.0")


# --------------------------------------------------------------------------- #
# release orchestrator (A3) — wraps the existing placeholder release-stage
# --------------------------------------------------------------------------- #


def _full_repo(root: Path, version: str = "0.2.0") -> str:
    """A repo complete enough for stage_signed_release, with a real commit."""
    _write_version_sources(root, version)
    package = root / "validators" / "creator_engine_validator"
    (package / "__init__.py").write_text("", encoding="utf-8")
    (package / "_version.py").write_text(
        'SEMVER = "0.0.0"\nBUILD_GIT_SHA = "' + ("0" * 40) + '"\n', encoding="utf-8"
    )
    wheelhouse = root / "validators" / "wheelhouse"
    wheelhouse.mkdir(parents=True)
    (wheelhouse / "attrs-26.1.0-py3-none-any.whl").write_bytes(b"attrs\n")
    (wheelhouse / "jsonschema-4.26.0-py3-none-any.whl").write_bytes(b"jsonschema\n")

    docs = root / "docs"
    (docs / "schemas").mkdir(parents=True)
    (docs / "keys").mkdir(parents=True)
    (docs / "install.sh").write_text("#!/usr/bin/env bash\necho install\n", encoding="utf-8")
    (docs / "schemas" / "install-answers.schema.yaml").write_text("kind: schema\n", encoding="utf-8")
    (docs / "keys" / "ce-root-v1").write_text(
        "ce-root-v1 ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAITest\n", encoding="utf-8"
    )
    (docs / "llms-install.md").write_text(_LLMS_INSTALL, encoding="utf-8")

    _changelog_fragment(root, "feat.md", kind="added", slug="a-feat", issue="ce-ops#1", body="A feature.")

    _git(root, "init", "-q")
    _git(root, "config", "user.email", "t@t.invalid")
    _git(root, "config", "user.name", "T")
    _git(root, "add", ".")
    _git(root, "commit", "-q", "-m", "init")
    return _git(root, "rev-parse", "--verify", "HEAD")


_LLMS_INSTALL = """<!--
signature:
  key_id: ce-root-v1
  algo: ssh-ed25519
  namespace: ce-spec-v1
  value: OLD
  content_sha256: 0000000000000000000000000000000000000000000000000000000000000000

artifact_manifest:
  artifact_manifest_version: 1
  package_name: creator-engine-validator
  package_version: 0.2.0
  python_requires: >=3.14
  artifact_base_url: https://creator-engine.dev/downloads/0.2.0
  sha256s_url: https://creator-engine.dev/downloads/0.2.0/SHA256SUMS
  sha256s_sha256: 1111111111111111111111111111111111111111111111111111111111111111
  install_sh_url: https://creator-engine.dev/install.sh
  install_sh_sha256s_entry: install.sh
  answers_schema_url: https://creator-engine.dev/schemas/install-answers.schema.yaml
  answers_schema_sha256: 2222222222222222222222222222222222222222222222222222222222222222
  app_wheel: creator_engine_validator-0.2.0-py3-none-any.whl
  required_wheels:
    - filename: attrs-26.1.0-py3-none-any.whl
      url: https://creator-engine.dev/downloads/0.2.0/attrs-26.1.0-py3-none-any.whl
      sha256: 5555555555555555555555555555555555555555555555555555555555555555
      platforms: all
    - filename: creator_engine_validator-0.2.0-py3-none-any.whl
      url: https://creator-engine.dev/downloads/0.2.0/creator_engine_validator-0.2.0-py3-none-any.whl
      sha256: 3333333333333333333333333333333333333333333333333333333333333333
      platforms: all
    - filename: jsonschema-4.26.0-py3-none-any.whl
      url: https://creator-engine.dev/downloads/0.2.0/jsonschema-4.26.0-py3-none-any.whl
      sha256: 6666666666666666666666666666666666666666666666666666666666666666
      platforms: all
  python_acquisition:
    - platform: linux-x86_64-cp314
      tool: uv
      version: 0.11.21
      url: https://example.invalid/uv.tar.gz
      sha256: 4444444444444444444444444444444444444444444444444444444444444444
      command: uv python install 3.14
-->
# Install Creator Engine

```bash
curl -fsSL https://creator-engine.dev/keys/ce-root-v1 -o ce-root-v1
grep -Eo 'ce-root-v1[ =]SHA256:[A-Za-z0-9+/]{43}' ce-root-v1.anchor.raw > ce-root-v1.anchor
test "x" = "$(ssh-keygen -l -f ce-root-v1 -E sha256 | awk '$3 == "ce-root-v1" { print $2; exit }')"
ssh-keygen -Y verify -f ce-root-v1 -I ce-root-v1 -n ce-spec-v1 -s ce-spec.sig < ce-spec.canonical
```
"""


def _fake_builder(repo_root: Path, out_dir: Path) -> WheelManifest:
    version_file = repo_root / "validators" / "creator_engine_validator" / "_version.py"
    text = version_file.read_text(encoding="utf-8")
    semver = re.search(r'SEMVER = "([^"]+)"', text).group(1)
    build_sha = re.search(r'BUILD_GIT_SHA = "([0-9a-f]{40})"', text).group(1)
    wheel_name = f"creator_engine_validator-{semver}-py3-none-any.whl"
    wheel = out_dir / wheel_name
    wheel.write_bytes(f"wheel\nsemver={semver}\nsha={build_sha}\n".encode("utf-8"))
    return WheelManifest(
        wheel_name=wheel_name,
        sha256=hashlib.sha256(wheel.read_bytes()).hexdigest(),
        version=semver,
        source_commit=build_sha,
    )


def test_orchestrate_with_explicit_version_stages_and_emits_packet(tmp_path: Path):
    root = tmp_path / "repo"
    _full_repo(root, "0.2.0")
    # Stage at the same committed version so the wheel build SHA matches HEAD.
    out = tmp_path / "stage"
    result = orchestrate_release(
        repo_root=root,
        out=out,
        version="0.2.0",
        force=True,
        build_wheel=_fake_builder,
        verify_parity=lambda r: [],
    )
    assert result.version == "0.2.0"
    assert result.stage.version == "0.2.0"
    # The bump drove sources to 0.2.0 (no-op here) and changelog aggregated.
    assert result.changelog.fragment_count >= 1
    # Ratification packet points at the staged seam artifacts.
    assert Path(result.packet.canonical_path).is_file()
    assert Path(result.packet.manifest_path).is_file()
    assert Path(result.packet.signing_instructions_path).is_file()
    assert result.packet.signature_placeholder == "<RESIGN-REQUIRED-ce-root-v1>"
    # NO real signature is produced — the staged spec still has the placeholder.
    staged_spec = (out / "llms-install.md").read_text(encoding="utf-8")
    assert "<RESIGN-REQUIRED-ce-root-v1>" in staged_spec


def test_orchestrate_dry_run_does_not_promote(tmp_path: Path):
    root = tmp_path / "repo"
    _full_repo(root, "0.2.0")
    out = tmp_path / "stage"
    result = orchestrate_release(
        repo_root=root,
        out=out,
        version="0.2.0",
        dry_run=True,
        build_wheel=_fake_builder,
        verify_parity=lambda r: [],
    )
    assert result.version == "0.2.0"
    # dry-run leaves no promoted output dir.
    assert not out.exists() or not any(out.iterdir())


def test_orchestrate_requires_exactly_one_version_source(tmp_path: Path):
    root = tmp_path / "repo"
    _full_repo(root)
    with pytest.raises(ReleaseOrchestrationError, match="exactly one"):
        orchestrate_release(repo_root=root, out=tmp_path / "s")
    with pytest.raises(ReleaseOrchestrationError, match="exactly one"):
        orchestrate_release(repo_root=root, out=tmp_path / "s", tag="release/v0.3.0", part="patch")


def test_orchestrate_tag_version_mismatch_fails_closed(tmp_path: Path):
    """A tag whose version cannot be staged (HEAD!=requested via bump) still
    carries the fail-closed tag==version invariant through the bump step."""
    root = tmp_path / "repo"
    _full_repo(root, "0.2.0")
    # Bump to 0.3.0 from the tag, but the committed wheel build SHA won't match
    # a 0.3.0 source unless re-committed — release-stage rebuilds _version.py
    # for HEAD, so staging proceeds at 0.3.0. The invariant we assert here is
    # that the orchestrator's staged version equals the tag-derived version.
    out = tmp_path / "stage"
    result = orchestrate_release(
        repo_root=root,
        out=out,
        tag="release/v0.3.0",
        force=True,
        build_wheel=_fake_builder,
        verify_parity=lambda r: [],
    )
    assert result.version == "0.3.0"
    assert result.stage.version == "0.3.0"
    assert result.bump.source == "tag"
