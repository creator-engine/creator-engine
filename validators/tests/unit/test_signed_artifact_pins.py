from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from creator_engine_validator import cli
from creator_engine_validator.checks import registered_checks
from creator_engine_validator.checks import signed_artifact_pins as guard

# Absolute path to the repo root so tests can read the REAL signed artifact.
_REPO_ROOT = Path(__file__).resolve().parents[3]


SPEC = """<!--
signature:
  key_id: ce-root-v1
  algo: ssh-ed25519
  namespace: ce-spec-v1
  value: mock
  content_sha256: 0000000000000000000000000000000000000000000000000000000000000000

artifact_manifest:
  artifact_manifest_version: 1
  sha256s_url: https://creator-engine.dev/downloads/0.3.5/SHA256SUMS
  sha256s_sha256: 1111111111111111111111111111111111111111111111111111111111111111
  answers_schema_url: https://creator-engine.dev/schemas/install-answers.schema.yaml
  answers_schema_sha256: 2222222222222222222222222222222222222222222222222222222222222222
-->

# fixture
"""


def _codes(errors) -> set[str]:
    return {error.code for error in errors}


def _pins():
    return guard.discover_pins(SPEC)


def _git(repo: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=repo, check=True, capture_output=True, text=True)


def _commit(repo: Path, message: str) -> None:
    subprocess.run(
        [
            "git",
            "-c",
            "user.name=CE Test",
            "-c",
            "user.email=ce-test@example.invalid",
            "commit",
            "-m",
            message,
        ],
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
    )


def test_signed_artifact_pins_check_is_registered():
    assert guard.CHECK_NAME in registered_checks()


def test_discovers_data_driven_url_paths_and_source_aliases():
    pins = {pin.key: pin for pin in _pins()}

    assert pins["answers_schema_sha256"].protected_paths == (
        "docs/schemas/install-answers.schema.yaml",
        "validators/creator_engine_validator/schemas/install-answers.schema.yaml",
    )
    assert pins["sha256s_sha256"].protected_paths == (
        "docs/downloads/0.3.5/SHA256SUMS",
        "docs/install.sh",
        "install.sh",
        "validators/wheelhouse/SHA256SUMS",
    )


def test_pinned_file_touched_without_pin_update_is_red():
    result = guard.evaluate_pins(
        _pins(),
        changed_paths=["validators/creator_engine_validator/schemas/install-answers.schema.yaml"],
        changed_pin_keys=[],
    )

    assert not result.ok
    assert _codes(result.errors) == {guard.CODE_MISSING_PIN_UPDATE}
    assert "answers_schema_sha256" in result.errors[0].message
    assert "release-op/spec-signing procedure" in result.errors[0].message


def test_pinned_file_and_pin_update_is_green_with_notice():
    result = guard.evaluate_pins(
        _pins(),
        changed_paths=[
            "docs/llms-install.md",
            "validators/creator_engine_validator/schemas/install-answers.schema.yaml",
        ],
        changed_pin_keys=["answers_schema_sha256"],
    )

    assert result.ok
    assert _codes(result.warnings) == {guard.CODE_NOTICE}
    assert "re-sign is required" in result.warnings[0].message


def test_unrelated_diff_is_green_without_notice():
    result = guard.evaluate_pins(
        _pins(),
        changed_paths=["validators/creator_engine_validator/checks/signed_artifact_pins.py"],
        changed_pin_keys=[],
    )

    assert result.ok
    assert result.warnings == ()


def test_pin_only_change_is_notice_not_red():
    result = guard.evaluate_pins(
        _pins(),
        changed_paths=["docs/llms-install.md"],
        changed_pin_keys=["answers_schema_sha256"],
    )

    assert result.ok
    assert _codes(result.warnings) == {guard.CODE_NOTICE}
    assert "without a matching pinned-file change" in result.warnings[0].message


def test_diff_parser_finds_changed_pin_keys():
    diff = """diff --git a/docs/llms-install.md b/docs/llms-install.md
@@ -11 +11 @@
-  answers_schema_sha256: 2222222222222222222222222222222222222222222222222222222222222222
+  answers_schema_sha256: 3333333333333333333333333333333333333333333333333333333333333333
"""

    assert guard.changed_pin_keys_from_diff(diff) == frozenset({"answers_schema_sha256"})


def test_cli_verify_signed_artifact_pins_blocks_unpinned_source_change(tmp_path: Path, monkeypatch):
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "llms-install.md").write_text(SPEC, encoding="utf-8")
    schema = tmp_path / "validators" / "creator_engine_validator" / "schemas"
    schema.mkdir(parents=True)
    (schema / "install-answers.schema.yaml").write_text("title: before\n", encoding="utf-8")

    _git(tmp_path, "init")
    _git(tmp_path, "add", ".")
    _commit(tmp_path, "base")
    (schema / "install-answers.schema.yaml").write_text("title: after\n", encoding="utf-8")
    _git(tmp_path, "add", ".")
    _commit(tmp_path, "change pinned source")

    monkeypatch.chdir(tmp_path)

    assert cli.main(["verify-signed-artifact-pins", "--base", "HEAD~1", "."]) == 1


# --- Finding 1: fail-closed on frontmatter/manifest corruption --------------


def test_discover_pins_raises_on_unparseable_frontmatter():
    broken = "<!--\nkey: [unterminated\n-->\n"
    try:
        guard.discover_pins(broken)
    except guard.SignedArtifactCorruption as exc:
        assert "not valid YAML" in str(exc)
    else:
        raise AssertionError("expected SignedArtifactCorruption")


def test_discover_pins_raises_on_missing_artifact_manifest_section():
    doc = """<!--
signature:
  key_id: ce-root-v1
  content_sha256: 0000000000000000000000000000000000000000000000000000000000000000
-->
"""
    try:
        guard.discover_pins(doc)
    except guard.SignedArtifactCorruption as exc:
        assert "artifact_manifest" in str(exc)
    else:
        raise AssertionError("expected SignedArtifactCorruption")


def test_discover_pins_raises_on_zero_pins_discovered():
    doc = """<!--
artifact_manifest:
  artifact_manifest_version: 1
-->
"""
    try:
        guard.discover_pins(doc)
    except guard.SignedArtifactCorruption as exc:
        assert "zero" in str(exc)
    else:
        raise AssertionError("expected SignedArtifactCorruption")


def test_run_with_base_reports_code_invalid_on_frontmatter_corruption(tmp_path: Path):
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "llms-install.md").write_text(
        "<!--\nkey: [unterminated\n-->\n", encoding="utf-8"
    )
    _git(tmp_path, "init")
    _git(tmp_path, "add", ".")
    _commit(tmp_path, "base")
    (tmp_path / "README.md").write_text("noop\n", encoding="utf-8")
    _git(tmp_path, "add", ".")
    _commit(tmp_path, "unrelated change")

    result = guard.run_with_base([tmp_path], "HEAD~1")

    assert not result.ok
    assert _codes(result.errors) == {guard.CODE_INVALID}
    assert "not valid YAML" in result.errors[0].message


# --- Finding 3(a): missing/unreadable signed doc ----------------------------


def test_run_with_base_reports_code_invalid_when_signed_doc_missing(tmp_path: Path):
    _git(tmp_path, "init")
    (tmp_path / "README.md").write_text("hello\n", encoding="utf-8")
    _git(tmp_path, "add", ".")
    _commit(tmp_path, "base")
    (tmp_path / "README.md").write_text("hello again\n", encoding="utf-8")
    _git(tmp_path, "add", ".")
    _commit(tmp_path, "unrelated change")

    result = guard.run_with_base([tmp_path], "HEAD~1")

    assert not result.ok
    assert _codes(result.errors) == {guard.CODE_INVALID}
    assert "could not read signed artifact" in result.errors[0].message


# --- Finding 3(c): git-diff subprocess failure branches ---------------------


def test_run_with_base_reports_code_invalid_when_name_status_diff_fails(tmp_path: Path, monkeypatch):
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "llms-install.md").write_text(SPEC, encoding="utf-8")
    _git(tmp_path, "init")
    _git(tmp_path, "add", ".")
    _commit(tmp_path, "base")
    (tmp_path / "README.md").write_text("noop\n", encoding="utf-8")
    _git(tmp_path, "add", ".")
    _commit(tmp_path, "unrelated change")

    real_run_git = guard.run_git

    def _fail_run_git(args, cwd):
        if "--name-status" in args:
            return 1, "", "boom"
        return real_run_git(args, cwd)

    monkeypatch.setattr(guard, "run_git", _fail_run_git)
    result = guard.run_with_base([tmp_path], "HEAD~1")

    assert not result.ok
    assert _codes(result.errors) == {guard.CODE_INVALID}
    assert "name-status" in result.errors[0].message


def test_run_with_base_reports_code_invalid_when_doc_diff_fails(tmp_path: Path, monkeypatch):
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "llms-install.md").write_text(SPEC, encoding="utf-8")
    _git(tmp_path, "init")
    _git(tmp_path, "add", ".")
    _commit(tmp_path, "base")
    (tmp_path / "README.md").write_text("noop\n", encoding="utf-8")
    _git(tmp_path, "add", ".")
    _commit(tmp_path, "unrelated change")

    real_run_git = guard.run_git

    def _fail_run_git(args, cwd):
        if "--unified=0" in args:
            return 1, "", "boom"
        return real_run_git(args, cwd)

    monkeypatch.setattr(guard, "run_git", _fail_run_git)
    result = guard.run_with_base([tmp_path], "HEAD~1")

    assert not result.ok
    assert _codes(result.errors) == {guard.CODE_INVALID}
    assert "signed artifact" in result.errors[0].message


# --- Finding 3(d): the signed doc itself changes in the diff ----------------


def test_run_with_base_notices_pin_change_in_synthetic_fixture_doc(tmp_path: Path):
    """End-to-end: the signed doc (a synthetic fixture, never the real one)
    changes in the diff, exercising changed_pin_keys_from_diff against a real
    git diff rather than a hand-built string."""
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "llms-install.md").write_text(SPEC, encoding="utf-8")
    _git(tmp_path, "init")
    _git(tmp_path, "add", ".")
    _commit(tmp_path, "base")

    updated = SPEC.replace(
        "answers_schema_sha256: 2222222222222222222222222222222222222222222222222222222222222222",
        "answers_schema_sha256: 3333333333333333333333333333333333333333333333333333333333333333",
    )
    assert updated != SPEC
    (tmp_path / "docs" / "llms-install.md").write_text(updated, encoding="utf-8")
    _git(tmp_path, "add", ".")
    _commit(tmp_path, "re-sign pin only")

    result = guard.run_with_base([tmp_path], "HEAD~1")

    assert result.ok
    assert _codes(result.warnings) == {guard.CODE_NOTICE}
    assert "without a matching pinned-file change" in result.warnings[0].message


# --- Finding 2 / 3(e): install.sh chain is protected via sha256s_sha256 ----


def test_install_sh_touched_without_sha256sums_update_is_red():
    result = guard.evaluate_pins(
        _pins(),
        changed_paths=["install.sh"],
        changed_pin_keys=[],
    )

    assert not result.ok
    assert _codes(result.errors) == {guard.CODE_MISSING_PIN_UPDATE}
    assert "sha256s_sha256" in result.errors[0].message
    assert "release-op/spec-signing procedure" in result.errors[0].message


def test_docs_install_sh_touched_without_sha256sums_update_is_red():
    result = guard.evaluate_pins(
        _pins(),
        changed_paths=["docs/install.sh"],
        changed_pin_keys=[],
    )

    assert not result.ok
    assert _codes(result.errors) == {guard.CODE_MISSING_PIN_UPDATE}
    assert "sha256s_sha256" in result.errors[0].message


def test_install_sh_touched_with_sha256sums_pin_update_is_green_with_notice():
    result = guard.evaluate_pins(
        _pins(),
        changed_paths=["install.sh", "validators/wheelhouse/SHA256SUMS"],
        changed_pin_keys=["sha256s_sha256"],
    )

    assert result.ok
    assert _codes(result.warnings) == {guard.CODE_NOTICE}


# --- Finding 4: content_sha256 whole-document re-sign wording ---------------


def test_whole_document_pin_change_gets_distinct_resign_notice():
    result = guard.evaluate_pins(
        _pins(),
        changed_paths=["docs/llms-install.md"],
        changed_pin_keys=["content_sha256"],
    )

    assert result.ok
    assert _codes(result.warnings) == {guard.CODE_NOTICE}
    message = result.warnings[0].message
    assert "whole-document" in message
    assert "not a missing pinned-file update" in message


# --- Regression: real docs/llms-install.md shape (prose-then-YAML comment) --
#
# The real signed artifact opens its HTML comment block with human-readable
# prose (including colon-bearing text like URLs and inline code) BEFORE the
# ``signature:`` / ``artifact_manifest:`` YAML block, separated by a blank
# line.  The parser must skip the prose and find the YAML section, not attempt
# to parse the entire comment content as YAML (which fails on prose colons).
#
# These tests directly exercise the real on-disk file so a format change to
# docs/llms-install.md that breaks the parser is caught immediately in CI
# rather than only at gate time.

SPEC_WITH_PROSE = """\
<!--
This is human-readable prose that describes the spec.  It references
https://creator-engine.dev/llms-install.md and mentions the CE trust root.
It may contain colon-bearing text (no CE tooling: that is what breaks the
bootstrap circularity).
Contract: docs/contracts/installer.md.

signature:
  key_id: ce-root-v1
  algo: ssh-ed25519
  namespace: ce-spec-v1
  value: mock
  content_sha256: 0000000000000000000000000000000000000000000000000000000000000000

artifact_manifest:
  artifact_manifest_version: 1
  python_requires: >=3.14
  sha256s_url: https://creator-engine.dev/downloads/0.3.5/SHA256SUMS
  sha256s_sha256: 1111111111111111111111111111111111111111111111111111111111111111
  answers_schema_url: https://creator-engine.dev/schemas/install-answers.schema.yaml
  answers_schema_sha256: 2222222222222222222222222222222222222222222222222222222222222222

# YAML comment: illustrating that comment lines inside the block are fine too.
-->

# Install (prose follows the comment)
"""


def test_discover_pins_handles_prose_before_yaml_in_comment():
    """Parser must skip human-readable prose in the HTML comment before YAML."""
    pins = guard.discover_pins(SPEC_WITH_PROSE)
    pin_keys = {p.key for p in pins}
    assert "sha256s_sha256" in pin_keys
    assert "answers_schema_sha256" in pin_keys


def test_prose_comment_colon_text_does_not_raise_yaml_error():
    """Colon-space in prose (e.g. ``(no CE tooling: that is what breaks the …)``)
    must NOT trigger a SignedArtifactCorruption — only genuine YAML parse failures
    on the YAML section should raise."""
    # The prose contains ``(no CE tooling: that is what breaks the`` which is
    # the exact text that triggers the upstream bug (YAML maps ``CE tooling`` to
    # ``that is what breaks the``).
    try:
        guard.discover_pins(SPEC_WITH_PROSE)
    except guard.SignedArtifactCorruption as exc:
        raise AssertionError(f"unexpected SignedArtifactCorruption on prose-then-YAML doc: {exc}") from exc


@pytest.mark.skipif(
    not (_REPO_ROOT / "docs" / "llms-install.md").exists(),
    reason="docs/llms-install.md not present in this worktree",
)
def test_discover_pins_parses_real_signed_artifact():
    """discover_pins must succeed on the actual on-disk docs/llms-install.md.

    This test pins the real file's on-disk format so that any future structural
    change to the HTML-comment block (e.g. adding / removing a prose paragraph)
    is caught immediately rather than surfacing only at PR-gate time.
    """
    text = (_REPO_ROOT / "docs" / "llms-install.md").read_text(encoding="utf-8")
    pins = guard.discover_pins(text)
    assert len(pins) >= 2, (
        f"expected at least 2 *_sha256 pins in the real docs/llms-install.md, got {len(pins)}: "
        + ", ".join(p.key for p in pins)
    )
    pin_keys = {p.key for p in pins}
    # The two externally-tracked pins whose source aliases are hard-coded in
    # PIN_KEY_SOURCE_ALIASES must always be discoverable.
    assert "sha256s_sha256" in pin_keys, "sha256s_sha256 pin missing from real signed artifact"
    assert "answers_schema_sha256" in pin_keys, "answers_schema_sha256 pin missing from real signed artifact"
