"""Static contract tests for the L7 release-finalize workflow."""
from __future__ import annotations

from pathlib import Path

import yaml

_REPO_ROOT = Path(__file__).resolve().parents[3]
_WORKFLOW = _REPO_ROOT / ".github" / "workflows" / "release-finalize.yml"


def _load_workflow() -> dict:
    return yaml.safe_load(_WORKFLOW.read_text(encoding="utf-8"))


def _on_block(doc: dict) -> dict:
    if "on" in doc:
        return doc["on"]
    return doc[True]


def _steps(doc: dict) -> list[dict]:
    return doc["jobs"]["finalize"]["steps"]


def _step_named(doc: dict, name: str) -> dict:
    for step in _steps(doc):
        if step.get("name") == name:
            return step
    raise AssertionError(f"missing workflow step: {name}")


def _all_run_text(doc: dict) -> str:
    return "\n".join(str(step.get("run", "")) for step in _steps(doc))


def test_release_finalize_workflow_dispatch_inputs_and_permissions():
    doc = _load_workflow()
    dispatch = _on_block(doc)["workflow_dispatch"]["inputs"]

    assert dispatch["version"]["required"] is True
    assert dispatch["version"]["type"] == "string"
    assert dispatch["signature_base64"]["required"] is True
    assert dispatch["signature_base64"]["type"] == "string"
    assert dispatch["dry_run"]["default"] is True
    assert dispatch["dry_run"]["type"] == "boolean"
    assert doc["permissions"] == {
        "contents": "write",
        "pull-requests": "write",
        "issues": "write",
    }


def test_release_finalize_checks_out_requested_release_tag_with_full_history():
    checkout = _step_named(_load_workflow(), "Checkout release tag")

    assert checkout["uses"] == "actions/checkout@93cb6efe18208431cddfb8368fd83d5badbf9bfd"
    with_block = checkout["with"]
    assert with_block["ref"] == "${{ format('refs/tags/release/v{0}', inputs.version) }}"
    assert with_block["fetch-depth"] == 0
    assert with_block["persist-credentials"] is True


def test_release_finalize_reruns_orchestrator_without_private_signing_or_dry_run_stage():
    run = _step_named(_load_workflow(), "Run release orchestrator")["run"]

    assert 'stage_dir="${RUNNER_TEMP}/ce-release-stage-${VERSION}"' in run
    assert "python -m creator_engine_validator" in run
    assert "release \\" in run
    assert '--tag "${TAG_NAME}"' in run
    assert '--out "${stage_dir}"' in run
    assert "--preflight-mode release-tag" in run
    assert '--preflight-head-ref "${TAG_NAME}"' in run
    assert "--dry-run" not in run
    assert "ssh-keygen -Y sign" not in run


def test_release_finalize_writes_signature_to_runner_temp_and_uses_signature_file():
    doc = _load_workflow()
    write_sig = _step_named(doc, "Write public detached signature")["run"]
    finalize = _step_named(doc, "Finalize signed release")["run"]

    assert 'signature_file="${RUNNER_TEMP}/llms-install.md.sig.b64"' in write_sig
    assert "printf '%s' \"${SIGNATURE_BASE64}\" > \"${signature_file}\"" in write_sig
    assert "release-finalize \\" in finalize
    assert '--signature-file "${SIGNATURE_FILE}"' in finalize
    assert '--stage "${STAGE_DIR}"' in finalize
    assert '--out "${signed_dir}"' in finalize


def test_release_finalize_prepares_docs_branch_and_generates_carriers():
    doc = _load_workflow()
    prepare = _step_named(doc, "Prepare release publish branch")["run"]
    docs_commit = _step_named(doc, "Commit finalized docs")["run"]
    carrier_step = _step_named(doc, "Generate carrier and changelog")
    carrier = carrier_step["run"]
    commit = _step_named(doc, "Commit release publish branch")["run"]

    assert 'publish_branch=release-publish/v${VERSION}' in _step_named(doc, "Resolve release inputs")["run"]
    assert 'git switch -C "${PUBLISH_BRANCH}" origin/main' in prepare
    assert 'cp -a "${SIGNED_DIR}/." docs/' in prepare
    assert "git add docs" in docs_commit
    assert 'git commit -m "Finalize signed Creator Engine v${VERSION} release"' in docs_commit
    assert "steps.commit-docs.outputs.has_changes == 'true'" in carrier_step["if"]
    assert "from creator_engine_validator.carrier_gen import CarrierSpec, write_carriers" in carrier
    assert "write_carriers(Path(\".\"), spec)" in carrier
    assert "- **Declared work class:** tiny" in carrier
    assert "git add .ce/changelog .ce/pr-manifests" in commit
    assert "git commit --amend --no-edit" in commit


def test_release_finalize_pushes_opens_pr_and_documents_work_class_and_secret():
    doc = _load_workflow()
    push = _step_named(doc, "Push release publish branch")
    open_pr = _step_named(doc, "Open release publish PR")

    assert "dry_run != 'true'" in push["if"]
    assert "git push --force-with-lease origin \"HEAD:${PUBLISH_BRANCH}\"" in push["run"]
    assert "dry_run != 'true'" in open_pr["if"]
    run = open_pr["run"]
    assert "- **Declared work class:** tiny" in run
    assert "CE_RELEASE_REVIEWER_TOKEN must be provisioned as a repository secret" in run
    assert "gh pr create" in run
    assert "--base main" in run
    assert '--head "${PUBLISH_BRANCH}"' in run


def test_release_finalize_approval_fails_visibly_without_secret_before_auto_merge():
    doc = _load_workflow()
    approve = _step_named(doc, "Approve release publish PR with reviewer token")
    merge = _step_named(doc, "Enable auto-merge for release publish PR")

    assert approve.get("continue-on-error") in (None, False)
    assert "dry_run != 'true'" in approve["if"]
    assert approve["env"]["REVIEWER_TOKEN"] == "${{ secrets.CE_RELEASE_REVIEWER_TOKEN }}"
    approve_run = approve["run"]
    assert 'if [[ -z "${REVIEWER_TOKEN}" ]]; then' in approve_run
    assert "CE_RELEASE_REVIEWER_TOKEN is required" in approve_run
    assert "exit 1" in approve_run
    assert "github-actions[bot]" in approve_run
    assert 'gh pr review "${PR_URL}"' in approve_run
    assert "--approve" in approve_run
    assert merge.get("continue-on-error") in (None, False)
    assert "gh pr merge \"${PR_URL}\" --auto --merge" in merge["run"]


def test_release_finalize_workflow_does_not_embed_signing_material_or_publish_directly():
    text = _all_run_text(_load_workflow())

    forbidden = (
        "ssh-keygen -Y sign",
        "private key",
        "--signature-base64",
        "gh release edit",
        "gh release upload",
        "gh release create",
        "git checkout main",
        "git push origin main",
    )
    found = [token for token in forbidden if token in text]
    assert not found
