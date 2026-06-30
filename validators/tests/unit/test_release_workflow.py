"""Static contract tests for the W2d release workflow."""
from __future__ import annotations

from pathlib import Path

import yaml

_REPO_ROOT = Path(__file__).resolve().parents[3]
_WORKFLOW = _REPO_ROOT / ".github" / "workflows" / "release.yml"


def _load_release_workflow() -> dict:
    return yaml.safe_load(_WORKFLOW.read_text(encoding="utf-8"))


def _on_block(doc: dict) -> dict:
    if "on" in doc:
        return doc["on"]
    return doc[True]


def _steps(doc: dict) -> list[dict]:
    return doc["jobs"]["release"]["steps"]


def _step_named(doc: dict, name: str) -> dict:
    for step in _steps(doc):
        if step.get("name") == name:
            return step
    raise AssertionError(f"missing workflow step: {name}")


def _all_run_text(doc: dict) -> str:
    return "\n".join(str(step.get("run", "")) for step in _steps(doc))


def test_release_workflow_triggers_only_release_tags_and_manual_dispatch():
    on = _on_block(_load_release_workflow())

    assert on["push"]["tags"] == ["release/v*.*.*"]
    dispatch = on["workflow_dispatch"]["inputs"]
    assert dispatch["version"]["required"] is True
    assert dispatch["version"]["type"] == "string"
    assert dispatch["dry_run"]["default"] is True
    assert dispatch["dry_run"]["type"] == "boolean"


def test_release_workflow_checks_out_tag_ref_with_full_history():
    checkout = _step_named(_load_release_workflow(), "Checkout release tag")

    assert checkout["uses"] == "actions/checkout@93cb6efe18208431cddfb8368fd83d5badbf9bfd"
    with_block = checkout["with"]
    assert "github.ref" in with_block["ref"]
    assert "refs/tags/release/v{0}" in with_block["ref"]
    assert with_block["fetch-depth"] == 0
    assert with_block["persist-credentials"] is False


def test_release_workflow_requires_annotated_tag():
    run = _step_named(_load_release_workflow(), "Verify annotated release tag")["run"]

    assert 'git cat-file -t "${tag_name}"' in run
    assert '"${tag_type}" != "tag"' in run


def test_release_workflow_installs_validator_offline_like_validate():
    doc = _load_release_workflow()
    runtime = _step_named(doc, "Install validator (offline, from repo wheelhouse)")["run"]
    build = _step_named(doc, "Install validator build deps (offline, from dev wheelhouse)")["run"]

    assert "pip install --no-index" in runtime
    assert "--find-links validators/wheelhouse" in runtime
    assert "-r validators/requirements.txt" in runtime
    assert "pip install --no-index" in build
    assert "--find-links validators/wheelhouse" in build
    assert "--find-links validators/wheelhouse-dev" in build
    assert "-r validators/requirements-dev.txt" in build


def test_release_workflow_runs_release_orchestrator_to_runner_temp_only():
    run = _step_named(_load_release_workflow(), "Run release orchestrator")["run"]

    assert 'packet_dir="${RUNNER_TEMP}/ce-ratification-packet-${VERSION}"' in run
    assert 'stage_dir="${RUNNER_TEMP}/ce-release-stage-${VERSION}"' in run
    assert "python -m creator_engine_validator" in run
    assert "--json" in run
    assert "release" in run
    assert '--tag "${TAG_NAME}"' in run
    assert '--out "${stage_dir}"' in run
    assert '--changelog-out "${packet_dir}/RELEASE-NOTES.md"' in run
    assert '--github-out "${packet_dir}/GITHUB-RELEASE-BODY.md"' in run
    assert "--preflight-mode release-tag" in run
    assert '--preflight-head-ref "${TAG_NAME}"' in run
    assert "args+=(--dry-run)" in run


def test_release_workflow_uploads_ratification_packet_artifact():
    upload = _step_named(_load_release_workflow(), "Upload ratification packet artifact")

    assert upload["uses"] == "actions/upload-artifact@ea165f8d65b6e75b540449e92b4886f43607fa02"
    assert upload["with"]["name"] == "ce-ratification-packet-${{ steps.release-inputs.outputs.version }}"
    assert "packet_tgz" in upload["with"]["path"]
    assert "packet_dir" in upload["with"]["path"]
    assert upload["with"]["if-no-files-found"] == "error"


def test_release_workflow_creates_draft_release_only():
    run = _step_named(_load_release_workflow(), "Create draft GitHub release")["run"]

    assert 'gh release create "${TAG_NAME}"' in run
    assert "--draft" in run
    assert "--verify-tag" in run
    assert "--notes-file" in run
    assert "--latest" not in run
    assert "--prerelease" not in run
    assert "gh release upload" not in run
    assert "gh release edit" not in run


def test_release_workflow_creates_awaiting_operator_issue_with_signing_surface():
    doc = _load_release_workflow()
    packet_run = _step_named(doc, "Run release orchestrator")["run"]
    issue_run = _step_named(doc, "Create operator sign surface issue")["run"]

    assert "AWAITING-OPERATOR" in packet_run
    assert "canonical_spec_sha256" in packet_run
    assert "signing_command" in packet_run
    assert "Exact offline signing command:" in packet_run
    assert "Verified post-sign finalize command:" in packet_run
    assert "release-finalize" in packet_run
    assert "--signature-file llms-install.md.sig.b64" in packet_run
    assert 'gh issue create' in issue_run
    assert 'AWAITING-OPERATOR ${TAG_NAME} signing surface' in issue_run
    assert '--body-file "${ISSUE_BODY}"' in issue_run


def test_release_workflow_permissions_are_least_for_draft_release_and_issue():
    perms = _load_release_workflow()["permissions"]

    assert perms == {"contents": "write", "issues": "write"}


def test_release_workflow_has_no_sign_publish_signature_intake_or_main_mutation():
    text = _all_run_text(_load_release_workflow())

    forbidden = (
        "ssh-keygen -Y sign",
        "gh release publish",
        "gh release edit",
        "gh release upload",
        "--latest",
        "git push",
        "git commit",
        "refs/heads/main",
        "git checkout main",
        "queue",
        "merge",
        "verify-signature",
        "signature-intake",
    )
    found = [token for token in forbidden if token in text]
    assert not found
