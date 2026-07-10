from __future__ import annotations

import subprocess
from pathlib import Path

from creator_engine_validator import cli
from creator_engine_validator.checks import registered_checks
from creator_engine_validator.checks import signed_artifact_pins as guard


SPEC = """<!--
signature:
  key_id: ce-root-v1
  algo: ssh-ed25519
  namespace: ce-spec-v1
  value: mock
  content_sha256: 0000000000000000000000000000000000000000000000000000000000000000

artifact_manifest:
  artifact_manifest_version: 1
  sha256s_url: https://creator-engine.dev/downloads/0.3.4/SHA256SUMS
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
        "docs/downloads/0.3.4/SHA256SUMS",
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
