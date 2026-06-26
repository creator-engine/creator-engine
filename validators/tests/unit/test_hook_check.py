"""Unit tests for the CC-G-B validator-backed hook bridge (``hook_check``).

These tests pin the deterministic decision logic that a future Claude
``command``-type hook (CC-G-C) will call via
``creator_engine_validator hook-check``. They exercise the pure
``evaluate(event, context)`` surface plus the posture predicate, scope,
mechanics, secret, and Stop/closeout semantics required by
``docs/operations/CLAUDE_CODE_CONTROLLER_SEAT_CONTRACT.md`` §5-§7.

Scope discipline: these tests never launch Claude, never spawn a pane,
never write ``.claude/**``, and never read real credential bytes.
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from creator_engine_validator import hook_check, worker_spawn
from creator_engine_validator.checks import mutation_class
from creator_engine_validator.checks import pane_registry


REPO_ROOT = Path(__file__).resolve().parents[3]
EXAMPLES = REPO_ROOT / "examples"


def _edit_event(file_path: str, tool: str = "Edit") -> dict:
    return {
        "hook_event_name": "PreToolUse",
        "tool_name": tool,
        "tool_input": {"file_path": file_path},
    }


def _bash_event(command: str) -> dict:
    return {
        "hook_event_name": "PreToolUse",
        "tool_name": "Bash",
        "tool_input": {"command": command},
    }


def _read_event(file_path: str, tool_input_extra: dict | None = None) -> dict:
    tool_input = {"file_path": file_path}
    if tool_input_extra:
        tool_input.update(tool_input_extra)
    return {
        "hook_event_name": "PreToolUse",
        "tool_name": "Read",
        "tool_input": tool_input,
    }


MANIFEST = ("validators/creator_engine_validator/hook_check.py", "schemas/completion-report.schema.yaml")


# --- Scope (PreToolUse Edit/Write/MultiEdit) -------------------------------


def test_governed_out_of_manifest_edit_is_advisory_allow():
    # G-i (v3 kickoff): a governed path-manifest mismatch is now ADVISORY
    # (allow-with-warning), not a hard deny — scope containment moved to the
    # PR-diff gate. Secret/mechanic denies stay hard (see below).
    ctx = hook_check.HookContext(posture="governed", manifest_paths=MANIFEST)
    decision = hook_check.evaluate(_edit_event("README.md"), ctx)
    assert decision.posture == "governed"
    assert decision.decision == "allow"
    assert decision.advisory is True
    assert decision.would_have_denied is True
    assert decision.hook_specific_output["permissionDecision"] == "allow"
    assert "manifest" in decision.reason.lower()
    assert decision.ok is True


def test_governed_in_manifest_edit_allows():
    ctx = hook_check.HookContext(
        posture="governed", manifest_paths=MANIFEST, seat_class="worker"
    )
    decision = hook_check.evaluate(
        _edit_event("validators/creator_engine_validator/hook_check.py"), ctx
    )
    assert decision.decision == "allow"
    assert decision.hook_specific_output["permissionDecision"] == "allow"


def test_governed_write_in_manifest_allows():
    ctx = hook_check.HookContext(
        posture="governed", manifest_paths=MANIFEST, seat_class="worker"
    )
    decision = hook_check.evaluate(
        _edit_event("schemas/completion-report.schema.yaml", tool="Write"), ctx
    )
    assert decision.decision == "allow"


def test_governed_multiedit_out_of_manifest_is_advisory_allow():
    # G-i: governed manifest mismatch is advisory for MultiEdit too.
    ctx = hook_check.HookContext(posture="governed", manifest_paths=MANIFEST)
    decision = hook_check.evaluate(_edit_event("src/app.py", tool="MultiEdit"), ctx)
    assert decision.decision == "allow"
    assert decision.advisory is True
    assert decision.would_have_denied is True


def test_ungoverned_out_of_manifest_edit_is_advisory_allow():
    ctx = hook_check.HookContext(posture="ungoverned", manifest_paths=MANIFEST)
    decision = hook_check.evaluate(_edit_event("README.md"), ctx)
    assert decision.decision == "allow"
    assert decision.advisory is True
    assert decision.would_have_denied is True
    # advisory must still report what would have been denied
    assert "manifest" in decision.reason.lower()


def test_governed_evidence_root_write_allows():
    ctx = hook_check.HookContext(
        posture="governed",
        manifest_paths=MANIFEST,
        evidence_root=".hermes/cc-g-b-hook-bridge-implementation/",
    )
    decision = hook_check.evaluate(
        _edit_event(".hermes/cc-g-b-hook-bridge-implementation/20260526T000000Z/x.txt", tool="Write"),
        ctx,
    )
    assert decision.decision == "allow"


# --- Mechanics (PreToolUse Bash) -------------------------------------------


def test_governed_bash_git_push_denies():
    ctx = hook_check.HookContext(posture="governed", manifest_paths=MANIFEST)
    decision = hook_check.evaluate(_bash_event("git push origin main"), ctx)
    assert decision.decision == "deny"
    assert decision.hook_specific_output["permissionDecision"] == "deny"


@pytest.mark.parametrize(
    ("command", "action"),
    [
        pytest.param(
            "cev3 configure-repo --app-config /tmp/app.yml --apply",
            "forge_configure_repo",
            id="configure_repo",
        ),
        pytest.param(
            "cev3 ruleset --app-config /tmp/app.yml --apply",
            "forge_ruleset",
            id="ruleset",
        ),
        pytest.param(
            "cev3 review-submit scope-1 --run run-1 --apply",
            "forge_review_submit",
            id="review_submit",
        ),
        pytest.param(
            "cev3 auto-merge scope-1 --run run-1 --apply",
            "forge_auto_merge",
            id="auto_merge",
        ),
    ],
)
def test_governed_bash_forge_ops_deny_under_sec7_context(command, action):
    ctx = hook_check.HookContext(posture="governed", manifest_paths=MANIFEST)

    assert hook_check.classify_mechanics(command) == action
    decision = hook_check.evaluate(_bash_event(command), ctx)

    assert decision.decision == "deny"
    assert decision.hook_specific_output["permissionDecision"] == "deny"
    assert f"restricted mechanic ({action})" in decision.reason


@pytest.mark.parametrize(
    "command",
    [
        pytest.param("ce configure-repo --app-config /tmp/app.yml --apply", id="ce_configure_repo"),
        pytest.param("cev3 ruleset --app-config /tmp/app.yml --apply", id="cev3_ruleset"),
        pytest.param(
            "python -m creator_engine_validator.v3_cli review-submit scope-1 --run run-1 --apply",
            id="python_module_review_submit",
        ),
        pytest.param("cev3 auto-merge scope-1 --run run-1 --apply", id="cev3_auto_merge"),
    ],
)
def test_non_governed_controller_context_allows_forge_ops(command):
    ctx = hook_check.HookContext(posture="ungoverned", manifest_paths=MANIFEST)

    decision = hook_check.evaluate(_bash_event(command), ctx)

    assert decision.decision == "allow"
    assert decision.hook_specific_output["permissionDecision"] == "allow"


@pytest.mark.parametrize(
    "command",
    [
        pytest.param("git commit -m x", id="commit"),
        pytest.param("git add -A", id="add_all"),
        pytest.param("git checkout -b f", id="checkout_branch"),
        pytest.param("git switch main", id="switch"),
        pytest.param("git restore .", id="restore"),
        pytest.param("git fetch origin", id="fetch"),
        pytest.param("git pull", id="pull"),
        pytest.param("git merge f", id="merge"),
        pytest.param("git rebase main", id="rebase"),
        pytest.param("git reset --hard", id="reset_hard"),
        pytest.param("git stash", id="stash"),
        pytest.param("git tag v", id="tag"),
        pytest.param("git cherry-pick a", id="cherry_pick"),
        pytest.param("git revert a", id="revert"),
        pytest.param("git mv a b", id="mv"),
        pytest.param("git rm f", id="rm"),
        pytest.param("git worktree add ../x", id="worktree_add"),
        pytest.param("git submodule update", id="submodule_update"),
        pytest.param("git config user.name x", id="config"),
        pytest.param("git remote -v", id="remote"),
        pytest.param("git reflog", id="reflog"),
        pytest.param("git -C . status", id="global_C_status"),
        pytest.param("git -C . log", id="global_C_log"),
    ],
)
def test_git_grammar_local_subcommands_allow(command):
    ctx = hook_check.HookContext(
        posture="governed", manifest_paths=MANIFEST, seat_class="worker"
    )
    assert hook_check.classify_mechanics(command) is None
    assert hook_check.evaluate(_bash_event(command), ctx).decision == "allow"


@pytest.mark.parametrize(
    ("command", "action"),
    [
        pytest.param("git -c alias.push=status push origin main", "deploy", id="alias_cannot_shadow_push"),
        pytest.param("git -c alias.push=log push", "deploy", id="alias_log_cannot_shadow_push"),
        pytest.param(
            "git -c alias.branch=status branch -D f",
            "alter_repo_settings",
            id="alias_cannot_shadow_branch_delete",
        ),
        pytest.param("git -C . -c alias.push=status push", "deploy", id="global_C_alias_cannot_shadow_push"),
    ],
)
def test_git_grammar_builtin_alias_shadowing_denies(command, action):
    ctx = hook_check.HookContext(posture="governed", manifest_paths=MANIFEST)
    assert hook_check.classify_mechanics(command) == action
    decision = hook_check.evaluate(_bash_event(command), ctx)
    assert decision.decision == "deny"
    assert decision.hook_specific_output["permissionDecision"] == "deny"
    assert f"restricted mechanic ({action})" in decision.reason


@pytest.mark.parametrize(
    "command",
    [
        pytest.param("git -c alias.commit=status commit -m x", id="alias_cannot_shadow_commit"),
        pytest.param("git -c alias.status=push status", id="alias_cannot_shadow_status"),
    ],
)
def test_git_grammar_builtin_alias_shadowing_allows_local_builtins(command):
    ctx = hook_check.HookContext(
        posture="governed", manifest_paths=MANIFEST, seat_class="worker"
    )
    assert hook_check.classify_mechanics(command) is None
    assert hook_check.evaluate(_bash_event(command), ctx).decision == "allow"


@pytest.mark.parametrize(
    "command",
    [
        pytest.param("git -C . push origin main", id="git_global_C_push"),
        pytest.param("git push origin main", id="git_plain_push"),
        pytest.param("git -c alias.p=push p origin main", id="git_alias_push"),
        pytest.param("git --git-dir=/x push", id="git_git_dir_push"),
        pytest.param("git --work-tree=/x -C / push", id="git_work_tree_C_push"),
        pytest.param("git -c http.x=y -C . push", id="git_config_C_push"),
    ],
)
def test_git_grammar_deploy_canaries_deny(command):
    ctx = hook_check.HookContext(posture="governed", manifest_paths=MANIFEST)
    assert hook_check.classify_mechanics(command) == "deploy"
    decision = hook_check.evaluate(_bash_event(command), ctx)
    assert decision.decision == "deny"
    assert decision.hook_specific_output["permissionDecision"] == "deny"
    assert "restricted mechanic (deploy)" in decision.reason


@pytest.mark.parametrize(
    "command",
    [
        pytest.param("git -c alias.x=!sh x", id="shell_alias"),
        pytest.param("git -c alias.x=not-a-git-command x", id="alias_unknown_target"),
    ],
)
def test_git_grammar_unresolvable_alias_is_opaque_deny(command):
    ctx = hook_check.HookContext(posture="governed", manifest_paths=MANIFEST)
    assert hook_check.classify_mechanics(command) == "git_opaque"
    decision = hook_check.evaluate(_bash_event(command), ctx)
    assert decision.decision == "deny"
    assert "restricted mechanic (git_opaque)" in decision.reason


def test_git_grammar_plain_unknown_subcommand_allows():
    ctx = hook_check.HookContext(
        posture="governed", manifest_paths=MANIFEST, seat_class="worker"
    )
    command = "git not-a-git-command"
    assert hook_check.classify_mechanics(command) is None
    assert hook_check.evaluate(_bash_event(command), ctx).decision == "allow"


# ce-ops#105 S1 — outward sub-verb bridges (send-pack / p4 submit / svn dcommit),
# the abbreviation guard (unique prefix of a restricted verb), and an alias that
# expands to a restricted verb must all classify outward => deploy (deny).
@pytest.mark.parametrize(
    ("command", "action"),
    [
        pytest.param("git send-pack origin main", "deploy", id="send_pack"),
        pytest.param("git p4 submit", "deploy", id="p4_submit"),
        pytest.param("git svn dcommit", "deploy", id="svn_dcommit"),
        pytest.param("git pus origin main", "deploy", id="unique_prefix_pus"),
        pytest.param(
            "git -c alias.ship=send-pack ship origin main",
            "deploy",
            id="alias_expands_to_send_pack",
        ),
        pytest.param("git p4", "deploy", id="p4_absent_subverb_conservative"),
        pytest.param("git svn", "deploy", id="svn_absent_subverb_conservative"),
    ],
)
def test_git_grammar_outward_bridges_and_prefix_deny(command, action):
    ctx = hook_check.HookContext(posture="governed", manifest_paths=MANIFEST)
    assert hook_check.classify_mechanics(command) == action
    decision = hook_check.evaluate(_bash_event(command), ctx)
    assert decision.decision == "deny"
    assert decision.hook_specific_output["permissionDecision"] == "deny"
    assert f"restricted mechanic ({action})" in decision.reason


# The inward (read) bridge sub-verbs and any unknown that is NOT a unique prefix
# of a restricted verb must stay allowed — the hardening adds no over-denial.
@pytest.mark.parametrize(
    "command",
    [
        pytest.param("git p4 sync", id="p4_sync_read"),
        pytest.param("git svn fetch", id="svn_fetch_read"),
        pytest.param("git status", id="status"),
        pytest.param("git log", id="log"),
        pytest.param("git renamed-thing", id="plain_unknown_non_prefix"),
    ],
)
def test_git_grammar_inward_bridges_and_nonprefix_allow(command):
    ctx = hook_check.HookContext(
        posture="governed", manifest_paths=MANIFEST, seat_class="worker"
    )
    assert hook_check.classify_mechanics(command) is None
    assert hook_check.evaluate(_bash_event(command), ctx).decision == "allow"


@pytest.mark.parametrize(
    "command",
    [
        "gh pr merge 72 --squash",
        "gh pr review 72 --approve",
        "gh pr comment 72 --body hi",
        "git push --force origin main",
        "git branch -D landing/x",
        "npm publish",
    ],
)
def test_governed_bash_restricted_mechanics_deny(command):
    ctx = hook_check.HookContext(posture="governed", manifest_paths=MANIFEST)
    decision = hook_check.evaluate(_bash_event(command), ctx)
    assert decision.decision == "deny", command


def test_governed_bash_safe_command_allows():
    ctx = hook_check.HookContext(posture="governed", manifest_paths=MANIFEST)
    decision = hook_check.evaluate(_bash_event("git status --porcelain -uall"), ctx)
    assert decision.decision == "allow"


def test_gh_api_delete_ref_matches_git_push_delete_class():
    ctx = hook_check.HookContext(posture="governed", manifest_paths=MANIFEST)
    expected = hook_check.classify_mechanics("git push --delete origin main")
    command = "gh api -X DELETE /repos/o/r/git/refs/heads/main"

    assert expected == "alter_repo_settings"
    assert hook_check.classify_mechanics(command) == expected
    decision = hook_check.evaluate(_bash_event(command), ctx)
    assert decision.decision == "deny"
    assert f"restricted mechanic ({expected})" in decision.reason


def test_gh_api_patch_repo_settings_classifies_alter_repo_settings():
    ctx = hook_check.HookContext(posture="governed", manifest_paths=MANIFEST)
    command = "gh api --method PATCH /repos/o/r"

    assert hook_check.classify_mechanics(command) == "alter_repo_settings"
    decision = hook_check.evaluate(_bash_event(command), ctx)
    assert decision.decision == "deny"
    assert "restricted mechanic (alter_repo_settings)" in decision.reason


def test_gh_api_field_after_endpoint_defaults_to_post():
    ctx = hook_check.HookContext(posture="governed", manifest_paths=MANIFEST)
    command = "gh api /repos/o/r -f private=true"

    assert hook_check.classify_mechanics(command) == "alter_repo_settings"
    decision = hook_check.evaluate(_bash_event(command), ctx)
    assert decision.decision == "deny"
    assert "restricted mechanic (alter_repo_settings)" in decision.reason


def test_gh_api_get_repo_allows():
    ctx = hook_check.HookContext(
        posture="governed", manifest_paths=MANIFEST, seat_class="worker"
    )
    command = "gh api /repos/o/r"

    assert hook_check.classify_mechanics(command) is None
    assert hook_check.evaluate(_bash_event(command), ctx).decision == "allow"


def test_curl_api_delete_ref_matches_git_push_delete_class():
    ctx = hook_check.HookContext(posture="governed", manifest_paths=MANIFEST)
    expected = hook_check.classify_mechanics("git push --delete origin main")
    command = "curl -X DELETE https://api.github.com/repos/o/r/git/refs/heads/main"

    assert expected == "alter_repo_settings"
    assert hook_check.classify_mechanics(command) == expected
    decision = hook_check.evaluate(_bash_event(command), ctx)
    assert decision.decision == "deny"
    assert f"restricted mechanic ({expected})" in decision.reason


def test_mechanics_classification_reuses_reserved_restricted():
    # The mechanics seam must anchor to the shared mutation-class
    # reserved-restricted vocabulary rather than a bespoke parallel list.
    action = hook_check.classify_mechanics("git push origin main")
    assert action in mutation_class.RESERVED_RESTRICTED
    assert hook_check.classify_mechanics("gh pr merge 1") in mutation_class.RESERVED_RESTRICTED
    assert hook_check.classify_mechanics("git status") is None


def test_governed_bash_with_reviewer_authority_envelope_allows_matching_pr_review():
    # G2.007.2: a bounded, validated reviewer-authority envelope opens exactly its mechanic on
    # exactly its PR — a raw loose token no longer authorizes anything, and the envelope does not
    # open an unrelated mechanic.
    envelope = {
        "mechanic": "pr_review",
        "pr_number": 106,
        "head_sha": "aa02b0ceb192b38f52da0d99f798e1e2710a8a22",
        "actor": "ubuntuaws745-cmyk",
        "ratified_prompt_sha": "ae1b9db11155f4ad841ef3fa399cd508c64d1ff184d1e0d1437e859c0dacfe27",
        "emitting_role": "operator",
        "operating_mode": "strict",
    }
    ctx = hook_check.HookContext(posture="governed", manifest_paths=MANIFEST, side_effect_authority=envelope)
    assert hook_check.evaluate(_bash_event("gh pr review 106 --approve"), ctx).decision == "allow"
    # the same pr_review envelope does NOT open an unrelated restricted mechanic
    assert hook_check.evaluate(_bash_event("git push origin main"), ctx).decision == "deny"


def test_ungoverned_bash_restricted_is_advisory_allow():
    ctx = hook_check.HookContext(posture="ungoverned", manifest_paths=MANIFEST)
    decision = hook_check.evaluate(_bash_event("git push origin main"), ctx)
    assert decision.decision == "allow"
    assert decision.would_have_denied is True


# --- Secrets (PreToolUse Read) ---------------------------------------------


@pytest.mark.parametrize(
    "file_path",
    [".env", ".env.production", "secrets/prod.yaml", "config/id_rsa", "app/credentials.json"],
)
def test_governed_secret_read_denies(file_path):
    ctx = hook_check.HookContext(posture="governed", manifest_paths=MANIFEST)
    decision = hook_check.evaluate(_read_event(file_path), ctx)
    assert decision.decision == "deny", file_path


def test_governed_normal_read_allows():
    ctx = hook_check.HookContext(posture="governed", manifest_paths=MANIFEST)
    decision = hook_check.evaluate(_read_event("README.md"), ctx)
    assert decision.decision == "allow"


def test_secret_reason_does_not_echo_tool_input_values():
    # The bridge must not reflect arbitrary tool_input fields (which a
    # caller might use to smuggle secret material) into the decision.
    ctx = hook_check.HookContext(posture="governed", manifest_paths=MANIFEST)
    event = _read_event(".env", tool_input_extra={"injected": "SUPER_SECRET_VALUE_42"})
    decision = hook_check.evaluate(event, ctx)
    assert decision.decision == "deny"
    serialized = json.dumps(decision.to_dict())
    assert "SUPER_SECRET_VALUE_42" not in serialized


def test_ungoverned_secret_read_is_advisory_allow():
    ctx = hook_check.HookContext(posture="ungoverned", manifest_paths=MANIFEST)
    decision = hook_check.evaluate(_read_event(".env"), ctx)
    assert decision.decision == "allow"
    assert decision.would_have_denied is True


# --- Foreman seat-class enforcement ----------------------------------------


def _write_worker_record(
    root: Path,
    *,
    worker_id: str = "worker-implementer-123",
    role: str = "implementer",
    lane_kind: str = "implementation",
    launch_state: str = "launched",
    worktree_path: Path | None = None,
    include_contract: bool = True,
) -> Path:
    import yaml

    surface_ref = worker_spawn.WORKER_TIER_ROLE_SURFACE_REFS.get(role)
    if surface_ref is not None:
        surface_path = root / surface_ref
        surface_path.parent.mkdir(parents=True, exist_ok=True)
        surface_path.write_text(f"# {role}\n", encoding="utf-8")

    path = root / ".ce" / "state" / "workers" / worker_id / "worker.yaml"
    path.parent.mkdir(parents=True, exist_ok=True)
    record = {
        "kind": "ce-worker-spawn-record",
        "schema_version": "1",
        "worker_id": worker_id,
        "role": role,
        "lane_kind": lane_kind,
        "harness": "claude",
        "scope_id": "ce-ops#163",
        "parent_id": "ce-dev-4",
        "worktree_path": str(worktree_path or root),
        "prompt": {"kind": "brief", "ref": "inline-brief", "sha256": "a" * 64},
        "depth": 1,
        "max_depth": 3,
        "record_path": str(path),
        "launch_command": ["ce", "launch"],
        "launch_command_sha256": "b" * 64,
        "scrubbed_env_names": [],
        "child_env_names": [],
        "dry_run": False,
        "launch_state": launch_state,
        "seat_refs": {"seat_lifecycle_state": "active"},
    }
    if include_contract:
        contract = worker_spawn.governed_worker_contract(role=role, max_depth=3)
        if contract is not None:
            record["governed_worker_contract"] = contract
    path.write_text(yaml.safe_dump(record, sort_keys=True), encoding="utf-8")
    return path


def test_foreman_implementation_work_denies_with_refusal_record(tmp_path):
    event = _edit_event("validators/creator_engine_validator/hook_check.py")
    event["ce"] = {"mutation_class": "code"}
    ctx = hook_check.HookContext(
        posture="governed",
        manifest_paths=MANIFEST,
        repo_root=str(tmp_path),
        seat_class="foreman",
        seat_class_policy={"delegation_required_mutation_classes": ["code"]},
    )

    decision = hook_check.evaluate(event, ctx)

    assert decision.decision == "deny"
    assert decision.advisory is False
    assert decision.would_have_denied is True
    assert decision.hook_specific_output["permissionDecision"] == "deny"
    assert "ce-ops#163 REQ-3" in decision.reason
    assert "foreman_delegation_required" in decision.reason
    assert "worker delegation" in decision.reason
    records = _load_refusal_records(tmp_path)
    assert len(records) == 1
    assert records[0]["op"] == "file"
    assert records[0]["mutation_class"] == "code"
    assert records[0]["target"] == "validators/creator_engine_validator/hook_check.py"
    assert "ce-ops#163 REQ-3" in records[0]["decision_reason"]
    assert "foreman_delegation_required" in records[0]["decision_reason"]


def test_foreman_implementation_work_without_mutation_class_denies():
    event = _edit_event("validators/creator_engine_validator/hook_check.py")
    ctx = hook_check.HookContext(
        posture="governed",
        manifest_paths=MANIFEST,
        seat_class="foreman",
    )

    decision = hook_check.evaluate(event, ctx)

    assert decision.decision == "deny"
    assert decision.advisory is False
    assert decision.would_have_denied is True
    assert "worker delegation" in decision.reason


def test_worker_implementation_work_allows(tmp_path):
    event = _edit_event("validators/creator_engine_validator/hook_check.py")
    event["ce"] = {"mutation_class": "code"}
    ctx = hook_check.HookContext(
        posture="governed",
        manifest_paths=MANIFEST,
        repo_root=str(tmp_path),
        seat_class="worker",
        seat_class_policy={"delegation_required_mutation_classes": ["code"]},
    )

    decision = hook_check.evaluate(event, ctx)

    assert decision.decision == "allow"
    assert decision.advisory is False
    assert decision.would_have_denied is False
    assert "worker delegation" not in decision.reason
    assert not _refusal_chain_file(tmp_path).exists()


def test_foreman_worker_routed_implementation_allows_with_valid_worker_artifact(tmp_path):
    worker_ref = _write_worker_record(tmp_path)
    event = _edit_event("validators/creator_engine_validator/hook_check.py")
    event["ce"] = {
        "posture": "governed",
        "manifest_paths": ["validators/creator_engine_validator/hook_check.py"],
        "mutation_class": "code",
        "seat_class": "foreman",
        "worker_record_ref": str(worker_ref),
    }

    ctx = hook_check.build_context(event, posture_root=str(tmp_path))
    decision = hook_check.evaluate(event, ctx)

    assert ctx.worker_delegation is not None
    assert ctx.worker_delegation["worker_id"] == "worker-implementer-123"
    assert decision.decision == "allow"
    assert decision.advisory is False
    assert decision.would_have_denied is False
    assert not _refusal_chain_file(tmp_path).exists()


def test_foreman_worker_routed_implementation_allows_with_worker_id_state_ref(tmp_path):
    _write_worker_record(tmp_path, worker_id="worker-from-env")
    event = _edit_event("validators/creator_engine_validator/hook_check.py")
    event["ce"] = {
        "posture": "governed",
        "manifest_paths": ["validators/creator_engine_validator/hook_check.py"],
        "mutation_class": "code",
        "seat_class": "foreman",
        "worker_id": "worker-from-env",
    }

    ctx = hook_check.build_context(event, posture_root=str(tmp_path))
    decision = hook_check.evaluate(event, ctx)

    assert ctx.worker_delegation is not None
    assert decision.decision == "allow"


def test_foreman_worker_routed_implementation_missing_worker_contract_fails_closed(tmp_path):
    worker_ref = _write_worker_record(tmp_path, include_contract=False)
    event = _edit_event("validators/creator_engine_validator/hook_check.py")
    event["ce"] = {
        "posture": "governed",
        "manifest_paths": ["validators/creator_engine_validator/hook_check.py"],
        "mutation_class": "code",
        "seat_class": "foreman",
        "worker_record_ref": str(worker_ref),
    }

    ctx = hook_check.build_context(event, posture_root=str(tmp_path))
    decision = hook_check.evaluate(event, ctx)

    assert ctx.worker_delegation is None
    assert decision.decision == "deny"
    assert "foreman_delegation_required" in decision.reason


@pytest.mark.parametrize(
    "record_kwargs",
    [
        pytest.param(None, id="missing"),
        pytest.param({"role": "reviewer", "lane_kind": "review"}, id="wrong_role"),
        pytest.param({"launch_state": "reserved"}, id="not_launched"),
        pytest.param({"worktree_path": Path("/tmp/not-this-worktree")}, id="wrong_worktree"),
    ],
)
def test_foreman_worker_context_missing_or_invalid_fails_closed(tmp_path, record_kwargs):
    worker_ref = tmp_path / ".ce" / "state" / "workers" / "worker-implementer-123" / "worker.yaml"
    if record_kwargs is not None:
        worker_ref = _write_worker_record(tmp_path, **record_kwargs)
    event = _edit_event("validators/creator_engine_validator/hook_check.py")
    event["ce"] = {
        "posture": "governed",
        "manifest_paths": ["validators/creator_engine_validator/hook_check.py"],
        "mutation_class": "code",
        "seat_class": "foreman",
        "worker_record_ref": str(worker_ref),
    }

    ctx = hook_check.build_context(event, posture_root=str(tmp_path))
    decision = hook_check.evaluate(event, ctx)

    assert ctx.worker_delegation is None
    assert decision.decision == "deny"
    assert "foreman_delegation_required" in decision.reason


def test_foreman_malformed_worker_context_fails_closed(tmp_path):
    worker_ref = tmp_path / ".ce" / "state" / "workers" / "broken" / "worker.yaml"
    worker_ref.parent.mkdir(parents=True)
    worker_ref.write_text("kind: [not valid enough\n", encoding="utf-8")
    event = _edit_event("validators/creator_engine_validator/hook_check.py")
    event["ce"] = {
        "posture": "governed",
        "manifest_paths": ["validators/creator_engine_validator/hook_check.py"],
        "mutation_class": "code",
        "seat_class": "foreman",
        "worker_record_ref": str(worker_ref),
    }

    ctx = hook_check.build_context(event, posture_root=str(tmp_path))
    decision = hook_check.evaluate(event, ctx)

    assert ctx.worker_delegation is None
    assert decision.decision == "deny"


def test_foreman_coordination_work_allows():
    event = _bash_event("git status --porcelain")
    event["ce"] = {"mutation_class": "code"}
    ctx = hook_check.HookContext(
        posture="governed",
        manifest_paths=MANIFEST,
        seat_class="foreman",
        seat_class_policy={"delegation_required_mutation_classes": ["code"]},
    )

    decision = hook_check.evaluate(event, ctx)

    assert decision.decision == "allow"
    assert decision.advisory is False
    assert decision.would_have_denied is False


def test_foreman_coordination_path_mutation_allows():
    event = _edit_event(".ce/changelog/ce186-g6-seat-class-enforce.md", tool="Write")
    event["ce"] = {"mutation_class": "code"}
    ctx = hook_check.HookContext(
        posture="governed",
        manifest_paths=(".ce/changelog/ce186-g6-seat-class-enforce.md",),
        seat_class="foreman",
        seat_class_policy={
            "delegation_required_mutation_classes": ["code"],
            "coordination_path_prefixes": [".ce/changelog/"],
        },
    )

    decision = hook_check.evaluate(event, ctx)

    assert decision.decision == "allow"
    assert decision.advisory is False
    assert decision.would_have_denied is False


def test_restricted_mechanic_still_hard_denies_before_foreman(tmp_path):
    event = _bash_event("git push origin main")
    event["ce"] = {"mutation_class": "deploy"}
    ctx = hook_check.HookContext(
        posture="governed",
        manifest_paths=MANIFEST,
        repo_root=str(tmp_path),
        seat_class="foreman",
        seat_class_policy={"delegation_required_mutation_classes": ["deploy"]},
    )

    decision = hook_check.evaluate(event, ctx)

    assert decision.decision == "deny"
    assert decision.advisory is False
    assert decision.hook_specific_output["permissionDecision"] == "deny"
    assert "restricted mechanic (deploy)" in decision.reason
    assert "worker delegation" not in decision.reason
    assert len(_load_refusal_records(tmp_path)) == 1


def test_build_context_resolves_seat_class_policy_and_fails_closed_to_foreman(tmp_path):
    event = _edit_event("validators/creator_engine_validator/hook_check.py")
    event["ce"] = {
        "posture": "governed",
        "seat_class": "nonsense",
        "seat_class_policy": {
            "seat_class": "worker",
            "delegation_required_mutation_classes": ["code"],
        },
        "manifest_paths": ["validators/creator_engine_validator/hook_check.py"],
        "mutation_class": "code",
    }

    ctx = hook_check.build_context(event, posture_root=str(tmp_path))

    assert ctx.seat_class == "foreman"
    assert ctx.seat_class_policy == event["ce"]["seat_class_policy"]
    decision = hook_check.evaluate(event, ctx)
    assert decision.decision == "deny"
    assert decision.advisory is False
    assert decision.hook_specific_output["permissionDecision"] == "deny"
    assert "worker delegation" in decision.reason


# --- Stop / completion-report closeout -------------------------------------


GOOD_CLOSEOUT = """## Summary

Did the thing.

## Recommended immediate next step

Ratify the next gate.

## Exact next Source prompt pointer+SHA256

path: foo.md
sha256: """ + ("0" * 64)


NO_NEXT_GATE_CLOSEOUT = """## Summary

Done.

## Recommended immediate next step

Nothing further.

## Exact next Source prompt pointer+SHA256

No next gate: roadmap milestone complete; awaiting Source direction.
"""


def test_stop_without_closeout_blocks():
    ctx = hook_check.HookContext(posture="governed", closeout_text="just some text, no sections")
    decision = hook_check.evaluate({"hook_event_name": "Stop"}, ctx)
    assert decision.decision == "block"
    assert decision.hook_specific_output["hookEventName"] == "Stop"
    assert "Summary" in decision.reason


def test_stop_with_full_closeout_allows():
    ctx = hook_check.HookContext(posture="governed", closeout_text=GOOD_CLOSEOUT)
    decision = hook_check.evaluate({"hook_event_name": "Stop"}, ctx)
    assert decision.decision == "allow"


def test_stop_with_no_next_gate_statement_allows():
    ctx = hook_check.HookContext(posture="governed", closeout_text=NO_NEXT_GATE_CLOSEOUT)
    decision = hook_check.evaluate({"hook_event_name": "Stop"}, ctx)
    assert decision.decision == "allow"


def test_stop_blocks_on_malformed_completion_report():
    malformed = EXAMPLES / "malformed/completion-reports/missing-envelope-sha256.yaml"
    ctx = hook_check.HookContext(
        posture="governed",
        closeout_text=GOOD_CLOSEOUT,
        completion_report_path=str(malformed),
    )
    decision = hook_check.evaluate({"hook_event_name": "Stop"}, ctx)
    assert decision.decision == "block"
    assert "CR-001" in decision.reason


def test_stop_allows_well_formed_completion_report():
    well_formed = EXAMPLES / "well-formed/completion-reports/class-a-example.yaml"
    ctx = hook_check.HookContext(
        posture="governed",
        closeout_text=GOOD_CLOSEOUT,
        completion_report_path=str(well_formed),
    )
    decision = hook_check.evaluate({"hook_event_name": "Stop"}, ctx)
    assert decision.decision == "allow"


# --- Decision JSON shape ---------------------------------------------------


def test_pretooluse_decision_to_dict_shape():
    # Pin the deny-shaped to_dict() via a still-hard deny (restricted mechanic);
    # the manifest mismatch is advisory post-G-i, so a deny case must come from a
    # secret/mechanic reason.
    ctx = hook_check.HookContext(posture="governed", manifest_paths=MANIFEST)
    decision = hook_check.evaluate(_bash_event("git push origin main"), ctx)
    payload = decision.to_dict()
    assert payload["ok"] is True
    assert payload["hookEventName"] == "PreToolUse"
    assert payload["posture"] == "governed"
    assert payload["decision"] == "deny"
    assert payload["reason"]
    hso = payload["hookSpecificOutput"]
    assert hso["hookEventName"] == "PreToolUse"
    assert hso["permissionDecision"] == "deny"
    assert hso["permissionDecisionReason"] == payload["reason"]


# --- Posture predicate (reuse of pane_registry posture inputs) -------------


def test_posture_governed_from_live_pane_and_claim():
    result = pane_registry.evaluate_posture([EXAMPLES / "well-formed/pane-registry"])
    assert result.posture == "governed"


def test_posture_ungoverned_with_no_live_claim(tmp_path):
    result = pane_registry.evaluate_posture([tmp_path])
    assert result.posture == "ungoverned"


def test_posture_ambiguous_live_claim_falls_closed_to_governed(tmp_path):
    # A live unreleased claim with no resolvable bound live pane is the
    # ambiguous-inside-a-lane case: §7 requires failing closed (governed).
    claim_dir = tmp_path / ".hermes/active-work-ledger/claims/hermes-primary"
    claim_dir.mkdir(parents=True)
    (claim_dir / "lane.yaml").write_text(
        "kind: active-work-ledger-record\n"
        "record_type: claim\n"
        "schema_version: \"1\"\n"
        "controller_id: hermes-primary\n"
        "lane_id: orphan-lane\n"
        "record_timestamp: \"source-controlled:lane.yaml\"\n"
        "worktree_path: /worktrees/orphan-lane\n"
        "envelope_ref: .hermes/envelopes/orphan.md\n"
        "lease_seconds: 3600\n"
        "claimed_at: \"source-controlled:lane.yaml\"\n"
        "last_heartbeat_at: \"source-controlled:lane.yaml\"\n",
        encoding="utf-8",
    )
    result = pane_registry.evaluate_posture([tmp_path])
    assert result.posture == "governed"
    assert result.ambiguous_fell_closed is True


def test_envelope_ref_none_adds_no_write_authority_posture_note(tmp_path):
    claim_dir = tmp_path / ".hermes/active-work-ledger/claims/hermes-primary"
    claim_dir.mkdir(parents=True)
    (claim_dir / "lane.yaml").write_text(
        "kind: active-work-ledger-record\n"
        "record_type: claim\n"
        "schema_version: \"1\"\n"
        "controller_id: hermes-primary\n"
        "lane_id: no-authority-lane\n"
        "record_timestamp: \"source-controlled:lane.yaml\"\n"
        "worktree_path: /worktrees/no-authority-lane\n"
        "envelope_ref: none\n"
        "lease_seconds: 3600\n"
        "claimed_at: \"source-controlled:lane.yaml\"\n"
        "last_heartbeat_at: \"source-controlled:lane.yaml\"\n",
        encoding="utf-8",
    )

    event = _edit_event("docs/other.md")
    context = hook_check.build_context(event, posture_root=str(tmp_path))
    assert context.posture == "governed"
    assert context.manifest_paths == ()
    assert context.posture_note == hook_check.NO_WRITE_AUTHORITY_NOTE

    decision = hook_check.evaluate(event, context)
    assert decision.advisory is True
    assert hook_check.NO_WRITE_AUTHORITY_NOTE in decision.reason
# --- Gate B: posture-claim reachability (injection-first) ------------------
#
# The §7 hard-deny fires ONLY under posture=="governed" (see
# test_governed_bash_git_push_denies). Before Gate B a seat's posture was
# resolved by rglob-ing the WHOLE posture-root tree, which matched tracked
# examples/**/claims fixtures as live governing claims — load-bearing for
# worktree-seat governance, but a footgun. Gate B makes a seat's REAL ledger
# reachable via a launch-pinned --ledger-root (CE_LEDGER_ROOT) and scopes
# discovery to that ledger (else <posture_root>/.hermes/active-work-ledger),
# never the whole tree. The four tests below are the mandatory regression
# guards protecting the sacred push/deploy hard-deny.


def _write_real_ledger(ledger_root: Path, lane: str = "real-lane", controller: str = "hermes-primary") -> None:
    """Write a live claim + a cleanly-bound live tmux pane under a real ledger root.

    Mirrors the on-disk layout ``lane_runtime.launch`` writes: claims under
    ``claims/<controller>/<lane>.yaml`` and panes under ``panes/<controller>/<lane>.yaml``.
    """
    claims = ledger_root / "claims" / controller
    panes = ledger_root / "panes" / controller
    claims.mkdir(parents=True, exist_ok=True)
    panes.mkdir(parents=True, exist_ok=True)
    (claims / f"{lane}.yaml").write_text(
        "kind: active-work-ledger-record\n"
        "record_type: claim\n"
        'schema_version: "1"\n'
        f"controller_id: {controller}\n"
        f"lane_id: {lane}\n"
        f'record_timestamp: "source-controlled:claims/{controller}/{lane}.yaml"\n'
        f"worktree_path: /worktrees/{lane}\n"
        f"envelope_ref: .hermes/envelopes/{lane}.md\n"
        "lease_seconds: 3600\n"
        f'claimed_at: "source-controlled:claims/{controller}/{lane}.yaml"\n'
        f'last_heartbeat_at: "source-controlled:claims/{controller}/{lane}.yaml"\n',
        encoding="utf-8",
    )
    (panes / f"{lane}.yaml").write_text(
        "kind: pane-registry-record\n"
        "record_type: pane_identity\n"
        'schema_version: "1"\n'
        f"controller_id: {controller}\n"
        f"lane_id: {lane}\n"
        f"claim_ref: claims/{controller}/{lane}.yaml\n"
        "host_id: workstation-a\n"
        f"pane_id: pane-{lane}-001\n"
        "role: implementer\n"
        "status: active\n"
        'record_timestamp: "2026-05-26T00:00:00Z"\n'
        "visibility: operator_visible\n"
        "terminal:\n"
        "  kind: tmux\n"
        "  session_id: ce\n"
        "  window_id: w\n"
        "  pane_id: '1'\n"
        'registered_at: "2026-05-26T00:00:00Z"\n'
        "last_seen_at: source-controlled:pane.yaml\n",
        encoding="utf-8",
    )


def _worktree_with_examples_footgun(base: Path) -> Path:
    """A worktree-like checkout carrying the tracked examples/** fixtures but NO
    real local ledger — exactly the layout that used to flip a worktree seat to
    governed via a fixture. Returns the worktree root."""
    wt = base / "wt"
    wt.mkdir(parents=True, exist_ok=True)
    shutil.copytree(EXAMPLES / "well-formed/pane-registry", wt / "examples/well-formed/pane-registry")
    return wt


def test_gate_b_regression_1_real_ledger_pinned_seat_governed_via_real_claim(tmp_path):
    # (1) A real allocated (ledger-pinned) worktree seat resolves `governed` via
    # its REAL claim — not any examples/** fixture. The worktree tree even carries
    # the examples footgun, yet the pinned ledger wins.
    real_ledger = tmp_path / "root" / ".hermes" / "active-work-ledger"
    _write_real_ledger(real_ledger, lane="real-lane")
    wt = _worktree_with_examples_footgun(tmp_path)

    posture, claim = hook_check._resolve_posture(
        {}, "auto", str(wt), ledger_root=str(real_ledger)
    )
    assert posture == "governed"
    # The binding is the REAL claim, never the example "pco-slice3-impl" fixture.
    assert claim is not None
    assert claim.record["lane_id"] == "real-lane"

    # And the public build_context() path agrees.
    ctx = hook_check.build_context(
        _edit_event("README.md"), posture_root=str(wt), ledger_root=str(real_ledger)
    )
    assert ctx.posture == "governed"


def test_gate_b_regression_2_unpinned_seat_is_ungoverned(tmp_path):
    # (2) An unallocated / unpinned seat resolves `ungoverned` (advisory). The
    # worktree carries the examples footgun but, with no ledger pin and no real
    # local ledger, the fixtures can no longer flip it to governed.
    wt = _worktree_with_examples_footgun(tmp_path)

    posture, claim = hook_check._resolve_posture({}, "auto", str(wt), ledger_root=None)
    assert posture == "ungoverned"
    assert claim is None

    ctx = hook_check.build_context(_edit_event("README.md"), posture_root=str(wt))
    assert ctx.posture == "ungoverned"


def test_runner_governed_override_ignores_child_supplied_ungoverned(tmp_path):
    # Runner shims now pass `--posture governed` as an immutable rendered
    # constant; an in-band child event cannot downgrade that via ce.posture.
    attacker_ledger = tmp_path / "attacker-ledger"
    attacker_ledger.mkdir()

    posture, claim = hook_check._resolve_posture(
        {"posture": "ungoverned"},
        "governed",
        str(tmp_path),
        ledger_root=str(attacker_ledger),
    )

    assert posture == "governed"
    assert claim is None


def test_gate_b_regression_3_git_push_under_governed_seat_is_hard_denied(tmp_path):
    # (3) THE SACRED INVARIANT: `git push` under a real governed seat is still
    # HARD-DENIED (decision=="deny"). This exercises the full posture-resolution
    # path (ledger pin -> governed) feeding the restricted-mechanic hard deny, so
    # the Gate B scope-out cannot silently downgrade the hard-deny to advisory.
    real_ledger = tmp_path / "root" / ".hermes" / "active-work-ledger"
    _write_real_ledger(real_ledger, lane="real-lane")
    wt = _worktree_with_examples_footgun(tmp_path)

    ctx = hook_check.build_context(
        _bash_event("git push origin main"),
        posture_root=str(wt),
        ledger_root=str(real_ledger),
    )
    assert ctx.posture == "governed"
    decision = hook_check.evaluate(_bash_event("git push origin main"), ctx)
    assert decision.decision == "deny"
    assert decision.hook_specific_output["permissionDecision"] == "deny"


def test_gate_b_regression_4_examples_can_never_govern_over_root_checkout(tmp_path):
    # (4) No examples/** (or snapshot) path can ever be the governing claim,
    # evaluated over a root checkout — even when a real (but live-claim-free)
    # ledger directory is present. Discovery is scoped to the real ledger, so the
    # tracked fixtures are excluded by construction.
    root = tmp_path / "root-checkout"
    root.mkdir()
    # A real ledger dir that exists but holds no live claim.
    (root / ".hermes" / "active-work-ledger").mkdir(parents=True)
    shutil.copytree(EXAMPLES / "well-formed/pane-registry", root / "examples/well-formed/pane-registry")

    posture, claim = hook_check._resolve_posture({}, "auto", str(root), ledger_root=None)
    assert posture == "ungoverned"
    assert claim is None


def test_gate_b_ledger_root_via_ce_block_fallback(tmp_path):
    # The launch-pinned ledger root may also arrive in the event's ce extension
    # block (ce.ledger_root), mirroring ce.posture_root — build_context honors it.
    real_ledger = tmp_path / "root" / ".hermes" / "active-work-ledger"
    _write_real_ledger(real_ledger, lane="real-lane")
    wt = _worktree_with_examples_footgun(tmp_path)

    event = _edit_event("README.md")
    event["ce"] = {"ledger_root": str(real_ledger)}
    ctx = hook_check.build_context(event, posture_root=str(wt))
    assert ctx.posture == "governed"


# --- v3.5-B.3: the refusal-record spine seam (append-only observability) ----
#
# A governed hard deny (restricted mechanic / secret path) appends ONE
# ``runtime_agent_action{classification: denied}`` record to the instance-local
# refusal chain under the hook's own v1 root — via the SHARED
# ``runtime_evidence_spine`` (V1->shared is the allowed edge; ``evidence_sink``
# is v3 and is never imported here). Decide FIRST, record AFTER; the deny
# stands even when the writer fails; advisory/ungoverned paths record nothing.


def _refusal_chain_file(root: Path) -> Path:
    return root / ".hermes" / "cc-g-c-hook-observations" / "refusal-chain.yaml"


def _load_refusal_records(root: Path) -> list[dict]:
    import yaml

    doc = yaml.safe_load(_refusal_chain_file(root).read_text(encoding="utf-8"))
    assert isinstance(doc, dict) and doc.get("kind") == "runtime-evidence-chain"
    return doc["records"]


def _governed_ctx(tmp_path: Path) -> hook_check.HookContext:
    return hook_check.HookContext(
        posture="governed", manifest_paths=MANIFEST, repo_root=str(tmp_path)
    )


def test_governed_mechanic_deny_appends_denied_record(tmp_path):
    event = _bash_event("git push origin main")
    event["session_id"] = "seat-under-test"
    decision = hook_check.evaluate(event, _governed_ctx(tmp_path))
    assert decision.decision == "deny"  # the decision itself is unchanged

    records = _load_refusal_records(tmp_path)
    assert len(records) == 1
    record = records[0]
    assert record["record_type"] == "runtime_agent_action"
    assert record["classification"] == "denied"
    assert record["decision_mode"] == "deny"
    assert record["op"] == "vcs"
    assert record["mutation_class"] == "deploy"
    assert record["tool"] == "Bash:git"
    assert "git push" in record["target"]
    assert record["run_id"] == "seat-under-test"
    assert "G2.007.2" in record["decision_reason"]
    assert record["fidelity"] == "best_effort"
    assert record["timing"] == "pre"


def test_refusal_chain_grows_and_verifies_clean(tmp_path):
    from creator_engine_validator.runtime_evidence_spine import verify_chain

    ctx = _governed_ctx(tmp_path)
    hook_check.evaluate(_bash_event("git push origin main"), ctx)
    hook_check.evaluate(_bash_event("gh pr merge 72 --squash"), ctx)
    hook_check.evaluate(_read_event(".env"), ctx)

    records = _load_refusal_records(tmp_path)
    assert len(records) == 3
    assert verify_chain(records) == []
    assert [r["sequence"] for r in records] == [0, 1, 2]


def test_governed_secret_deny_appends_secret_record(tmp_path):
    decision = hook_check.evaluate(_read_event("config/.env"), _governed_ctx(tmp_path))
    assert decision.decision == "deny"
    record = _load_refusal_records(tmp_path)[0]
    assert record["op"] == "secret"
    assert record["mutation_class"] == "security"
    assert record["tool"] == "Read"
    assert "matched rule" in record["decision_reason"]


def test_deny_stands_when_refusal_writer_raises(tmp_path, monkeypatch):
    import creator_engine_validator.hook_check as hc

    def _boom(*_args, **_kwargs):
        raise RuntimeError("disk full")

    monkeypatch.setattr(hc, "_yaml_safe_dump_document", _boom)
    decision = hook_check.evaluate(_bash_event("git push origin main"), _governed_ctx(tmp_path))
    assert decision.decision == "deny"  # the deny STANDS; no exception escaped
    assert not _refusal_chain_file(tmp_path).exists()


def test_ungoverned_advisory_deny_records_nothing(tmp_path):
    ctx = hook_check.HookContext(
        posture="ungoverned", manifest_paths=MANIFEST, repo_root=str(tmp_path)
    )
    decision = hook_check.evaluate(_bash_event("git push origin main"), ctx)
    assert decision.decision == "allow"
    assert decision.advisory is True
    assert not _refusal_chain_file(tmp_path).exists()


def test_governed_manifest_advisory_records_nothing(tmp_path):
    decision = hook_check.evaluate(_edit_event("README.md"), _governed_ctx(tmp_path))
    assert decision.decision == "allow"
    assert decision.advisory is True
    assert not _refusal_chain_file(tmp_path).exists()


def test_no_repo_root_records_nothing_and_still_denies(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    ctx = hook_check.HookContext(posture="governed", manifest_paths=MANIFEST)
    decision = hook_check.evaluate(_bash_event("git push origin main"), ctx)
    assert decision.decision == "deny"
    assert not _refusal_chain_file(tmp_path).exists()


def test_hook_check_never_imports_v3_modules():
    # The keystone boundary: the seam rides V1->shared (runtime_evidence_spine);
    # the v3 evidence_sink must NEVER appear in this module's source.
    source = (
        REPO_ROOT / "validators" / "creator_engine_validator" / "hook_check.py"
    ).read_text(encoding="utf-8")
    assert "evidence_sink" not in source
    assert "runtime_evidence_spine" in source
