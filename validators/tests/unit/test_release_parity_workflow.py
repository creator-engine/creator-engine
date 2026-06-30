"""Static contract tests for the L7-e release parity workflow."""
from __future__ import annotations

from pathlib import Path

import yaml

_REPO_ROOT = Path(__file__).resolve().parents[3]
_WORKFLOW = _REPO_ROOT / ".github" / "workflows" / "release-parity.yml"


def _load_workflow() -> dict:
    return yaml.safe_load(_WORKFLOW.read_text(encoding="utf-8"))


def _on_block(doc: dict) -> dict:
    if "on" in doc:
        return doc["on"]
    return doc[True]


def _steps(doc: dict) -> list[dict]:
    return doc["jobs"]["release-parity"]["steps"]


def _step_named(doc: dict, name: str) -> dict:
    for step in _steps(doc):
        if step.get("name") == name:
            return step
    raise AssertionError(f"missing workflow step: {name}")


def _all_run_text(doc: dict) -> str:
    return "\n".join(str(step.get("run", "")) for step in _steps(doc))


def test_release_parity_runs_after_successful_finalize_workflow():
    doc = _load_workflow()
    on = _on_block(doc)

    assert on["workflow_run"]["workflows"] == ["Release Finalize"]
    assert on["workflow_run"]["types"] == ["completed"]
    assert doc["jobs"]["release-parity"]["if"] == "${{ github.event.workflow_run.conclusion == 'success' }}"


def test_release_parity_permissions_only_release_and_issue_mutations():
    assert _load_workflow()["permissions"] == {"contents": "write", "issues": "write"}


def test_release_parity_waits_for_pages_before_checkout():
    doc = _load_workflow()
    first = _steps(doc)[0]

    assert first["name"] == "Wait for Pages propagation"
    assert first["run"] == "sleep 300"


def test_release_parity_checks_out_main_with_full_history_and_tags():
    doc = _load_workflow()
    checkout = _step_named(doc, "Checkout main after finalize")
    fetch = _step_named(doc, "Fetch release tags")["run"]

    assert checkout["uses"] == "actions/checkout@93cb6efe18208431cddfb8368fd83d5badbf9bfd"
    assert checkout["with"]["ref"] == "refs/heads/main"
    assert checkout["with"]["fetch-depth"] == 0
    assert checkout["with"]["persist-credentials"] is False
    assert "git fetch --force --tags origin" in fetch
    assert "refs/tags/release/v*" in fetch


def test_release_parity_installs_validator_offline_like_release_workflow():
    doc = _load_workflow()
    runtime = _step_named(doc, "Install validator (offline, from repo wheelhouse)")["run"]
    build = _step_named(doc, "Install validator build deps (offline, from dev wheelhouse)")["run"]

    assert "pip install --no-index" in runtime
    assert "--find-links validators/wheelhouse" in runtime
    assert "-r validators/requirements.txt" in runtime
    assert "pip install --no-index" in build
    assert "--find-links validators/wheelhouse" in build
    assert "--find-links validators/wheelhouse-dev" in build
    assert "-r validators/requirements-dev.txt" in build


def test_release_parity_reuses_live_release_and_local_guard_functions():
    run = _step_named(_load_workflow(), "Verify live signed release parity")["run"]

    assert "resolve_latest_signed_release" in run
    assert "release_artifact_parity_guard.validate_repo(root)" in run
    assert "install_spec_signature_guard.validate_repo(root)" in run
    assert "install_spec_signature_guard.canonical_spec_bytes" in run
    assert "site=site" in run
    assert "https://creator-engine.dev" in str(_step_named(_load_workflow(), "Verify live signed release parity")["env"])


def test_release_parity_asserts_version_tag_and_sha_chain_before_outputs():
    run = _step_named(_load_workflow(), "Verify live signed release parity")["run"]

    assert "manifest.package_version != version" in run
    assert "manifest.artifact_base_url.rstrip" in run
    assert "manifest.sha256s_url" in run
    assert "manifest.sha256s_sha256 != release.sha256s_sha256" in run
    assert "app_wheel.sha256 != release.identity.app_wheel_sha256" in run
    assert '["git", "rev-list", "-n", "1", tag_name]' in run
    assert "release.identity.build_git_sha != tag_sha" in run
    assert "local_canonical_sha != release.canonical_spec_sha256" in run
    assert "local_sha256s_sha != release.sha256s_sha256" in run
    assert "local_sha256s_text != release.sha256s_text" in run
    assert "tag_name=" in run
    assert "canonical_spec_sha256=" in run


def test_release_parity_publishes_only_after_parity_step_and_closes_operator_issue():
    doc = _load_workflow()
    names = [step["name"] for step in _steps(doc)]
    publish = _step_named(doc, "Publish draft release and close operator issue")
    run = publish["run"]

    assert names.index("Verify live signed release parity") < names.index("Publish draft release and close operator issue")
    assert publish["env"]["TAG_NAME"] == "${{ steps.parity.outputs.tag_name }}"
    assert 'gh release edit "${TAG_NAME}" --draft=false --latest' in run
    assert "AWAITING-OPERATOR ${TAG_NAME} signing surface in:title" in run
    assert 'gh issue close "${issue_number}"' in run
    assert "Release parity passed" in run


def test_release_parity_has_no_sign_push_approve_or_merge_actions():
    text = _all_run_text(_load_workflow())

    forbidden = (
        "ssh-keygen -Y sign",
        "gh pr review",
        "gh pr merge",
        "git push",
        "git commit",
        "queue",
        "approve",
    )
    found = [token for token in forbidden if token in text]
    assert not found
