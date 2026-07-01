"""Static contract tests for the release auto-tag workflow."""
from __future__ import annotations

from pathlib import Path

import yaml

_REPO_ROOT = Path(__file__).resolve().parents[3]
_WORKFLOW = _REPO_ROOT / ".github" / "workflows" / "release-auto-tag.yml"


def _load_workflow() -> dict:
    return yaml.safe_load(_WORKFLOW.read_text(encoding="utf-8"))


def _on_block(doc: dict) -> dict:
    if "on" in doc:
        return doc["on"]
    return doc[True]


def _steps(doc: dict) -> list[dict]:
    return doc["jobs"]["auto-tag"]["steps"]


def _step_named(doc: dict, name: str) -> dict:
    for step in _steps(doc):
        if step.get("name") == name:
            return step
    raise AssertionError(f"missing workflow step: {name}")


def test_release_auto_tag_runs_only_on_main_push_with_write_contents_permission():
    doc = _load_workflow()

    assert _on_block(doc) == {"push": {"branches": ["main"]}}
    assert doc["permissions"] == {"contents": "write"}


def test_release_auto_tag_checks_out_full_history_with_credentials_available():
    checkout = _step_named(_load_workflow(), "Checkout main")

    assert checkout["uses"] == "actions/checkout@93cb6efe18208431cddfb8368fd83d5badbf9bfd"
    assert checkout["with"]["fetch-depth"] == 0
    assert "persist-credentials" not in checkout["with"]


def test_release_auto_tag_reads_version_source_with_ast_without_importing_package():
    run = _step_named(_load_workflow(), "Resolve release version from source")["run"]

    assert "validators/creator_engine_validator/version.py" in run
    assert "ast.parse" in run
    assert "read_text" in run
    assert "__version__" in run
    assert "import creator_engine_validator" not in run
    assert "from creator_engine_validator" not in run
    assert "importlib" not in run
    assert "runpy" not in run


def test_release_auto_tag_skips_non_stable_semver_versions():
    run = _step_named(_load_workflow(), "Resolve release version from source")["run"]

    assert r"[0-9]+\.[0-9]+\.[0-9]+" in run
    assert "re.fullmatch" in run
    assert "should_tag={'true' if is_semver else 'false'}" in run
    assert "not stable semver X.Y.Z" in run


def test_release_auto_tag_checks_remote_tag_absence_before_push():
    run = _step_named(_load_workflow(), "Create annotated release tag")["run"]

    assert 'git ls-remote --exit-code --tags origin "refs/tags/${TAG_NAME}"' in run
    assert '"${remote_status}" -eq 0' in run
    assert "already exists" in run
    assert '"${remote_status}" -ne 2' in run
    assert "git ls-remote failed" in run


def test_release_auto_tag_creates_and_pushes_annotated_release_tag_only_when_semver():
    doc = _load_workflow()
    step = _step_named(doc, "Create annotated release tag")
    run = step["run"]

    assert step["if"] == "steps.release-version.outputs.should_tag == 'true'"
    assert step["env"]["TAG_NAME"] == "${{ steps.release-version.outputs.tag_name }}"
    assert step["env"]["VERSION"] == "${{ steps.release-version.outputs.version }}"
    assert 'git tag -a "${TAG_NAME}" -m "Creator Engine v${VERSION}" "${GITHUB_SHA}"' in run
    assert 'git push origin "refs/tags/${TAG_NAME}"' in run
