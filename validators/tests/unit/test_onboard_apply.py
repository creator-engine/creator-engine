"""Unit tests for the E2 onboard apply executor."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
import yaml

from creator_engine_validator import onboard_apply, v3_installer


def _schema() -> dict[str, Any]:
    return yaml.safe_load(Path("schemas/install-answers.schema.yaml").read_text(encoding="utf-8"))


def _signed_spec(*, value: str = "c2ln") -> bytes:
    canonical = """\
kind: ce-install-spec
schema_version: 1
signature:
  key_id: ce-root-v1
  algo: ssh-ed25519
  namespace: ce-spec-v1
  value: <published-with-this-spec>
  content_sha256: <published-with-this-spec>
steps:
  - verify
  - apply
"""
    digest = v3_installer.content_digest(v3_installer.canonical_spec_bytes(canonical))
    return canonical.replace("  value: <published-with-this-spec>", f"  value: {value}").replace(
        "  content_sha256: <published-with-this-spec>",
        f"  content_sha256: {digest}",
    ).encode("utf-8")


def _verifier(ok: bool = True):
    def verify(algo: str, raw: bytes, value: Any, key_material: Any) -> bool:
        return (
            ok
            and algo == v3_installer.SSH_ED25519_ALGO
            and raw == v3_installer.canonical_spec_bytes(_signed_spec())
            and value == "c2ln"
            and isinstance(key_material, str)
            and key_material.startswith("ce-root-v1 ")
        )

    return verify


def _answers(tmp_path: Path, *, mode: str = "new", repo: str = "octo/greenfield") -> dict[str, Any]:
    github: dict[str, Any] = {
        "mode": mode,
        "repo": repo,
        "bootstrap_token": "env://CE_BOOTSTRAP",
        "app": {"kind": "shared", "installation_id": 12345},
        "actions": {"install_validate_workflow": True},
        "protections": "reference",
        "reviewer": "human-reviewer",
    }
    if mode == "new":
        github["new_repo"] = {
            "visibility": "private",
            "default_branch": "main",
            "description": "CE greenfield",
        }
    return {
        "answers_version": 1,
        "host": {
            "sudo_grant": ["git", "python", "runsc", "proxy"],
            "userspace_install": True,
            "workspace_root": str(tmp_path / "workspaces"),
        },
        "provider": {"harness": "codex"},
        "github": github,
        "pilot": {"target_repo": repo},
    }


def _request(
    tmp_path: Path,
    *,
    answers: dict[str, Any] | None = None,
    probes: dict[str, bool] | None = None,
    spec: bytes | None = None,
    spawn_smoke: bool = False,
) -> onboard_apply.ApplyRequest:
    answer_doc = answers if answers is not None else _answers(tmp_path)
    answer_bytes = yaml.safe_dump(answer_doc, sort_keys=True).encode("utf-8")
    return onboard_apply.ApplyRequest(
        spec_bytes=spec or _signed_spec(),
        schema=_schema(),
        answers=answer_doc,
        answers_sha256=v3_installer.content_digest(answer_bytes),
        state_root=tmp_path / "state",
        dependency_probe=probes or {tool: True for tool in v3_installer.REQUIRED_DEPENDENCIES},
        non_interactive=True,
        spawn_smoke=spawn_smoke,
    )


class FakeDriver(onboard_apply.ApplyDriver):
    def __init__(
        self,
        *,
        repo_exists: bool = False,
        created_by_e2: bool = False,
        app_click_required: bool = False,
        workflow_digest_ok: bool = True,
        runtime_ok: bool = True,
        host_install_ok: bool = True,
        scope_sets: tuple[str, ...] | None = None,
        branch_protection_ok: bool = True,
        existing_protection_contexts: tuple[str, ...] = (),
        token_type: str = "classic",
    ):
        self.calls: list[str] = []
        self.tools = {tool: True for tool in v3_installer.REQUIRED_DEPENDENCIES}
        self.repo_exists_flag = repo_exists
        self.created_by_e2 = created_by_e2
        self.app_click_required = app_click_required
        self.workflow_digest_ok = workflow_digest_ok
        self.runtime_ok = runtime_ok
        self.host_install_ok = host_install_ok
        self.scope_sets = scope_sets
        self.token_type = token_type
        # ce-ops#85 plain-join detection/reconcile knobs: whether the live branch
        # protection floor verifies, and the live required-check contexts the
        # reconcile must PRESERVE (never drop).
        self.branch_protection_ok = branch_protection_ok
        self.existing_protection_contexts = existing_protection_contexts
        self.captured_policy = None

    def probe_tool(self, name: str) -> bool:
        self.calls.append(f"probe_tool:{name}")
        return self.tools.get(name, False)

    def install_dependencies(self, tools, *, sudo_tools, userspace_tools):
        self.calls.append("install_dependencies")
        if not self.host_install_ok:
            return {"ok": False, "reason": "host_failed", "manual_rollback_required": True}
        for tool in tools:
            self.tools[tool] = True
        return {"ok": True, "installed": list(tools)}

    def verify_tool(self, name: str) -> bool:
        self.calls.append(f"verify_tool:{name}")
        return self.tools.get(name, False)

    def provision_runtime(self, *, state_root, workspace_root, provider, backend=v3_installer.DEFAULT_ISOLATION_BACKEND):
        self.calls.append("provision_runtime")
        self.provisioned_backend = backend
        # Delegate to the real (pure file-write) provision so posture.json records
        # the resolved backend — exercises ce-ops#71 Edit A end-to-end.
        return super().provision_runtime(
            state_root=state_root, workspace_root=workspace_root, provider=provider, backend=backend
        )

    def verify_runtime(self, *, state_root, workspace_root, provider, backend=v3_installer.DEFAULT_ISOLATION_BACKEND):
        self.calls.append("verify_runtime")
        self.verified_backend = backend
        # Delegate to the real dispatch so the os-native path (no runsc/proxy) and
        # the gvisor-proxy path are both exercised honestly against the live tools.
        result = super().verify_runtime(
            state_root=state_root, workspace_root=workspace_root, provider=provider, backend=backend
        )
        if backend == "gvisor-proxy":
            # The fake host has the gVisor tools; preserve the historical green path.
            return {"ok": self.runtime_ok, "backend": backend, "runsc": True, "proxy": True, "provider_transport": provider == "codex"}
        return result

    def expose_cli(self, *, state_root, command, via):
        self.calls.append("expose_cli")
        return {"ok": True, "created": True, "path": str(state_root / "onboard" / "bin" / command)}

    def verify_cli(self, *, state_root, command):
        self.calls.append("verify_cli")
        return {"ok": True, "command": command}

    def resolve_secret(self, ref):
        self.calls.append("resolve_secret")
        return "secret-token"

    def probe_bootstrap_token(self, *, token, repo, org_create_needed):
        self.calls.append("probe_bootstrap_token")
        result = {"ok": True, "login": "human-reviewer", "token_type": self.token_type}
        # ce-ops#94: only a classic token reports a derived scope set; a fine-grained / unknown
        # token reports none (capability is gated by token_type + right-sized requirement).
        if self.token_type == "classic":
            scopes = self.scope_sets
            if scopes is None:
                scopes = v3_installer.REQUIRED_BOOTSTRAP_SCOPES + (
                    (v3_installer.ORG_CREATE_SCOPE,) if org_create_needed else ()
                )
            result["scopes"] = scopes
        return result

    def repo_exists(self, repo: str) -> bool:
        self.calls.append("repo_exists")
        return self.repo_exists_flag

    def create_repo(self, *, repo, visibility, default_branch, description, token):
        self.calls.append("create_repo")
        self.repo_exists_flag = True
        self.created_by_e2 = True
        return {"ok": True, "url": f"https://github.com/{repo}"}

    def verify_repo(self, *, repo, default_branch, visibility, spec_digest, ledger):
        self.calls.append("verify_repo")
        return {
            "ok": True,
            "default_branch": default_branch,
            "visibility": visibility,
            "created_by_e2": self.created_by_e2,
        }

    def wait_for_app_installation(self, *, app_plan, repo):
        self.calls.append("wait_for_app_installation")
        if self.app_click_required:
            return {"ok": False, "reason": "click_required", "install_url": "https://github.com/apps/ce/installations/new"}
        return {"ok": True, "installation_id": app_plan.get("installation_id") or 12345, "detected": True}

    def verify_app_installation(self, *, installation_id, repo, bot_identity):
        self.calls.append("verify_app_installation")
        return {"ok": True, "bot_identity": bot_identity}

    def install_workflow(self, *, repo, branch, path, content, token):
        self.calls.append("install_workflow")
        return {"ok": True, "path": path}

    def verify_workflow(self, *, repo, branch, path, digest):
        self.calls.append("verify_workflow")
        return {"ok": self.workflow_digest_ok, "sha256": digest}

    def configure_branch_protection(self, *, repo, branch, policy, token):
        self.calls.append("configure_branch_protection")
        self.captured_policy = policy
        return {"ok": True}

    def verify_branch_protection(self, *, repo, branch, policy):
        self.calls.append("verify_branch_protection")
        return {"ok": self.branch_protection_ok, "contexts": list(policy.required_status_check_contexts)}

    def existing_branch_protection_contexts(self, *, repo, branch):
        self.calls.append("existing_branch_protection_contexts")
        return self.existing_protection_contexts

    def checkout_workspace(self, *, repo, branch, workspace_root):
        self.calls.append("checkout_workspace")
        path = workspace_root / repo.split("/", 1)[1]
        path.mkdir(parents=True, exist_ok=True)
        return {"ok": True, "path": str(path)}

    def verify_checkout(self, *, repo, branch, path):
        self.calls.append("verify_checkout")
        return {"ok": True, "branch": branch}

    def run_first_project_smoke(self, *, state_root, workspace_path, scope_id, target_repo, spawn_smoke):
        self.calls.append("run_first_project_smoke")
        return super().run_first_project_smoke(
            state_root=state_root,
            workspace_path=workspace_path,
            scope_id=scope_id,
            target_repo=target_repo,
            spawn_smoke=spawn_smoke,
        )


def _apply(tmp_path: Path, driver: FakeDriver, **request_kwargs):
    return onboard_apply.apply_onboard(
        _request(tmp_path, **request_kwargs),
        verifier=_verifier(),
        driver=driver,
        invocation_id="test-invocation",
    )


def _leg(summary: dict[str, Any], leg_id: str) -> dict[str, Any]:
    return next(leg for leg in summary["legs"] if leg["id"] == leg_id)


def test_apply_refuses_self_attested_spec_before_side_effects(tmp_path):
    driver = FakeDriver()
    request = _request(tmp_path, spec=b"kind: unsigned\n")
    request = onboard_apply.ApplyRequest(
        **{**request.__dict__, "explicit_signature": {
            "key_id": "ce-root-v1",
            "algo": v3_installer.CONTENT_ALGO,
            "value": v3_installer.content_digest(b"kind: unsigned\n"),
        }}
    )
    with pytest.raises(onboard_apply.ApplyRefused, match="ssh-ed25519"):
        onboard_apply.apply_onboard(request, verifier=_verifier(), driver=driver)
    assert driver.calls == []


def test_real_sshsig_must_verify_before_any_driver_call(tmp_path):
    driver = FakeDriver()
    with pytest.raises(onboard_apply.ApplyRefused) as exc:
        onboard_apply.apply_onboard(_request(tmp_path), verifier=_verifier(False), driver=driver)
    assert exc.value.code == "signed_spec_verify_failed"
    assert driver.calls == []


def test_non_interactive_missing_answers_refuses_before_mutation(tmp_path):
    driver = FakeDriver()
    with pytest.raises(onboard_apply.ApplyRefused, match="unresolved inputs"):
        onboard_apply.apply_onboard(
            _request(tmp_path, answers={"answers_version": 1}),
            verifier=_verifier(),
            driver=driver,
        )
    assert driver.calls == []
    assert not (tmp_path / "state" / "onboard" / "ledger.ndjson").exists()


def test_sudo_grant_hole_refuses_before_mutation(tmp_path):
    driver = FakeDriver()
    answers = _answers(tmp_path)
    answers["host"]["sudo_grant"] = ["runsc"]
    probes = {tool: True for tool in v3_installer.REQUIRED_DEPENDENCIES}
    probes["proxy"] = False
    with pytest.raises(onboard_apply.ApplyRefused) as exc:
        onboard_apply.apply_onboard(
            _request(tmp_path, answers=answers, probes=probes),
            verifier=_verifier(),
            driver=driver,
        )
    assert exc.value.code == "sudo_grant_uncovered"
    assert driver.calls == []
    assert not (tmp_path / "state" / "onboard" / "ledger.ndjson").exists()


def test_greenfield_success_writes_ledger_and_honest_counters(tmp_path):
    driver = FakeDriver()
    summary = _apply(tmp_path, driver)
    assert summary["failed"] == 0
    assert summary["refused"] == 0
    assert summary["legs_total"] == len(onboard_apply.LEG_IDS)
    assert len(summary["legs"]) == len(onboard_apply.LEG_IDS)
    assert summary["applied"] + summary["already_satisfied"] == len(onboard_apply.LEG_IDS)
    assert summary["greenfield_repos_created"] == 1
    ledger_lines = (tmp_path / "state" / "onboard" / "ledger.ndjson").read_text(encoding="utf-8").splitlines()
    assert len(ledger_lines) == len(onboard_apply.LEG_IDS)
    assert {json.loads(line)["leg_id"] for line in ledger_lines} == set(onboard_apply.LEG_IDS)


def test_secret_ref_resolves_only_at_token_probe_and_never_enters_summary(tmp_path):
    driver = FakeDriver()
    summary = _apply(tmp_path, driver)
    assert driver.calls.index("resolve_secret") > driver.calls.index("verify_cli")
    assert driver.calls.index("resolve_secret") < driver.calls.index("probe_bootstrap_token")
    rendered = json.dumps(summary, sort_keys=True)
    assert "secret-token" not in rendered
    assert "env://CE_BOOTSTRAP" in rendered


def test_host_dependencies_are_idempotent_when_probe_is_green(tmp_path):
    driver = FakeDriver()
    summary = _apply(tmp_path, driver)
    assert "install_dependencies" not in driver.calls
    assert _leg(summary, "host_dependencies")["status"] == "already_satisfied"


def test_sudo_install_records_manual_rollback_when_it_mutates(tmp_path):
    driver = FakeDriver()
    probes = {tool: False for tool in v3_installer.REQUIRED_DEPENDENCIES}
    summary = _apply(tmp_path, driver, probes=probes)
    host_leg = _leg(summary, "host_dependencies")
    assert host_leg["status"] == "applied"
    assert host_leg["manual_rollback_required"] is True
    assert summary["manual_rollback_required"] >= 2


def test_runtime_posture_failure_stops_before_github(tmp_path):
    driver = FakeDriver(runtime_ok=False)
    summary = _apply(tmp_path, driver)
    assert _leg(summary, "runtime_posture")["status"] == "failed"
    assert "resolve_secret" not in driver.calls
    assert _leg(summary, "github_bootstrap_token_probe")["status"] == "skipped"


# ---------------------------------------------------------------------------
# ce-ops#71 Edits A+C — the solo-pilot leak fix. The governance-only profile
# materializes the unprivileged os-native backend and stops dragging gVisor:
# NO runsc/proxy in the dependency plan or the runtime-posture verification,
# and it SUCCEEDS with an EMPTY sudo grant on a host without runsc/proxy.
# ---------------------------------------------------------------------------
def test_solo_pilot_materializes_os_native_with_no_runsc_or_proxy(tmp_path):
    answers = _answers(tmp_path)
    answers["profile"] = "solo-pilot"
    answers["host"]["sudo_grant"] = []  # governance-only: zero privileged installs
    # a host WITHOUT the gVisor pairing — os-native must not need it
    probes = {"git": True, "python": True, "uv": True, "runsc": False, "proxy": False}
    driver = FakeDriver()
    summary = _apply(tmp_path, driver, answers=answers, probes=probes)

    assert summary["failed"] == 0
    assert summary["refused"] == 0

    # the runtime posture is os-native: the apply SUCCEEDS (exit 0, failed==0) while
    # the runtime is HONESTLY recorded as held, NOT verified (#71 MAJOR-2 round 2).
    assert driver.provisioned_backend == "os-native"
    assert driver.verified_backend == "os-native"
    posture = _leg(summary, "runtime_posture")
    # the held mechanism gets the distinct `held` status — non-failed, but NOT folded
    # into applied/verified_count; so the run record never claims it was verified.
    assert posture["status"] == "held"
    assert summary["held"] == 1
    assert summary["verified_count"] == summary["legs_total"] - 1  # the held leg is excluded
    verification = posture["verification"]
    # PRIMARY ok is honest-False (the live runtime is NOT verified); `held` flags it
    # as accepted (posture applied), never a bare ok=True implying the sandbox works.
    assert verification["ok"] is False
    assert verification["held"] is True
    assert verification["backend"] == "os-native"
    assert verification["posture_applied"] is True
    assert verification["runtime_available"] is False
    assert verification["runtime_held_reason"]
    assert verification.get("privileged_runtime_required") is False
    # the gVisor-only privileged runtime never appears for os-native
    assert "runsc" not in json.dumps(verification)
    # MAJOR-3: the held-mechanism PREREQUISITES surface informationally (bwrap+proxy)
    # — distinct from the no-sudo installable deps plan, which has neither.
    assert set(verification["held_mechanism_prerequisites"]) == {"bwrap", "proxy"}

    # the host-dependency plan is backend-driven: NO privileged runsc/proxy step
    host_leg = _leg(summary, "host_dependencies")
    assert host_leg["status"] == "already_satisfied"
    assert "install_dependencies" not in driver.calls
    # the materialized posture.json records os-native (not the old gVisor hardwire)
    posture_json = json.loads(
        (tmp_path / "state" / "onboard" / "runtime" / "posture.json").read_text(encoding="utf-8")
    )
    assert posture_json["isolation_backend"] == "os-native"


def test_default_profile_preserves_gvisor_proxy_posture(tmp_path):
    # back-compat (req-4): the default install (no profile) keeps gvisor-proxy.
    driver = FakeDriver()
    summary = _apply(tmp_path, driver)
    assert summary["failed"] == 0
    assert driver.provisioned_backend == "gvisor-proxy"
    assert driver.verified_backend == "gvisor-proxy"
    posture_json = json.loads(
        (tmp_path / "state" / "onboard" / "runtime" / "posture.json").read_text(encoding="utf-8")
    )
    assert posture_json["isolation_backend"] == "gvisor-proxy"


def test_cli_exposure_records_owned_rollback(tmp_path):
    driver = FakeDriver()
    summary = _apply(tmp_path, driver)
    leg = _leg(summary, "cli_exposure")
    assert leg["status"] == "applied"
    assert "E2-owned shim" in leg["rollback"]["automatic"]


def test_greenfield_repo_create_is_idempotent_on_rerun_via_ledger_provenance(tmp_path):
    first = FakeDriver()
    first_summary = _apply(tmp_path, first)
    assert first_summary["greenfield_repos_created"] == 1
    second = FakeDriver(repo_exists=True, created_by_e2=False)
    second_summary = _apply(tmp_path, second)
    assert _leg(second_summary, "github_repo_create")["status"] == "already_satisfied"
    assert second_summary["repos_already_satisfied"] == 1


def test_existing_repo_is_deferred_to_brownfield_gate(tmp_path):
    # ce-ops#85: a genuine brownfield repo — it EXISTS but is NOT already-CE (no CE
    # validate workflow at the pinned digest). Plain-join detection fails-closed, so
    # it stays E3-deferred (UNCHANGED behavior); no mutation occurs.
    driver = FakeDriver(repo_exists=True, workflow_digest_ok=False)
    summary = _apply(tmp_path, driver, answers=_answers(tmp_path, mode="existing"))
    assert _leg(summary, "github_repo_create")["status"] == "refused"
    assert _leg(summary, "github_repo_create")["verification"]["code"] == "brownfield_deferred"
    assert summary["brownfield_deferred"] == 1
    assert _leg(summary, "github_app_install")["status"] == "skipped"
    # fail-closed: the genuine-brownfield refuse mutates nothing downstream
    assert "configure_branch_protection" not in driver.calls
    assert "install_workflow" not in driver.calls


def test_plain_join_existing_already_ce_repo_converges(tmp_path):
    # ce-ops#85 — a new dev JOINING an ALREADY-CE repo (CE workflow + protection
    # floor present) is a plain-join: it CONVERGES via the idempotent verify/reconcile
    # legs instead of refusing brownfield.
    driver = FakeDriver(repo_exists=True)
    summary = _apply(tmp_path, driver, answers=_answers(tmp_path, mode="existing"))
    assert summary["failed"] == 0
    assert summary["refused"] == 0
    assert summary["brownfield_deferred"] == 0
    assert summary["greenfield_repos_created"] == 0
    assert summary["repos_already_satisfied"] == 1
    repo_leg = _leg(summary, "github_repo_create")
    assert repo_leg["status"] == "already_satisfied"
    assert repo_leg["action"] == "join_existing_ce_repo"
    assert repo_leg["verification"]["plain_join"] is True
    # the CE repo is NOT (re)created and its workflow is NOT overwritten
    assert "create_repo" not in driver.calls
    assert "install_workflow" not in driver.calls
    workflow_leg = _leg(summary, "github_workflow_install")
    assert workflow_leg["status"] == "already_satisfied"
    # verify-only, no overwrite: the install driver leg is never invoked
    assert workflow_leg["action"] == "verify_existing_ce_workflow"
    # every leg converged (applied or already_satisfied); none refused/failed/skipped
    assert summary["applied"] + summary["already_satisfied"] == len(onboard_apply.LEG_IDS)


def test_plain_join_branch_protection_preserves_existing_checks(tmp_path):
    # ce-ops#85 HARD requirement — the reconcile ADDS the CE floor check and NEVER
    # drops a check the live repo already enforces.
    driver = FakeDriver(
        repo_exists=True,
        existing_protection_contexts=("Existing CI", "Lint"),
    )
    summary = _apply(tmp_path, driver, answers=_answers(tmp_path, mode="existing"))
    assert summary["failed"] == 0
    assert _leg(summary, "github_branch_protection")["status"] in {"applied", "already_satisfied"}
    contexts = set(driver.captured_policy.required_status_check_contexts)
    # the CE floor was ADDED ...
    assert "Validate governance artifacts" in contexts
    # ... and the live checks were PRESERVED (never removed)
    assert {"Existing CI", "Lint"}.issubset(contexts)


def test_plain_join_is_idempotent_on_rerun(tmp_path):
    # ce-ops#85 — re-running plain-join against the same already-CE repo converges
    # again with no fresh mutation (already_satisfied across the join legs).
    first = FakeDriver(repo_exists=True)
    first_summary = _apply(tmp_path, first, answers=_answers(tmp_path, mode="existing"))
    assert first_summary["repos_already_satisfied"] == 1
    second = FakeDriver(repo_exists=True)
    second_summary = _apply(tmp_path, second, answers=_answers(tmp_path, mode="existing"))
    assert second_summary["refused"] == 0 and second_summary["failed"] == 0
    assert _leg(second_summary, "github_repo_create")["status"] == "already_satisfied"
    assert _leg(second_summary, "github_workflow_install")["status"] == "already_satisfied"


def test_plain_join_detection_fail_closed_when_protection_floor_missing(tmp_path):
    # ce-ops#85 fail-closed — an existing repo with the CE workflow but NO branch
    # protection floor is AMBIGUOUS → NOT plain-join → refuse, with NO mutation.
    driver = FakeDriver(repo_exists=True, branch_protection_ok=False)
    summary = _apply(tmp_path, driver, answers=_answers(tmp_path, mode="existing"))
    assert _leg(summary, "github_repo_create")["status"] == "refused"
    assert _leg(summary, "github_repo_create")["verification"]["code"] == "brownfield_deferred"
    assert summary["repos_already_satisfied"] == 0
    assert "configure_branch_protection" not in driver.calls
    assert "install_workflow" not in driver.calls


def test_github_app_click_requirement_is_explicit_refusal(tmp_path):
    driver = FakeDriver(app_click_required=True)
    summary = _apply(tmp_path, driver)
    assert _leg(summary, "github_app_install")["status"] == "refused"
    assert "click_required" in _leg(summary, "github_app_install")["detail"]


def test_branch_protection_uses_reference_check_floor(tmp_path):
    driver = FakeDriver()
    summary = _apply(tmp_path, driver)
    assert summary["failed"] == 0
    assert driver.captured_policy is not None
    assert "Validate governance artifacts" in driver.captured_policy.required_status_check_contexts


def test_workflow_install_verifies_digest(tmp_path):
    driver = FakeDriver(workflow_digest_ok=False)
    summary = _apply(tmp_path, driver)
    leg = _leg(summary, "github_workflow_install")
    assert leg["status"] == "failed"
    assert leg["verification"]["code"] == "workflow_digest_verify_failed"


def test_first_project_smoke_files_scope_and_optional_spawn_preflight(tmp_path):
    driver = FakeDriver()
    summary = _apply(tmp_path, driver, spawn_smoke=True)
    leg = _leg(summary, "first_project_smoke")
    assert leg["status"] == "applied"
    assert Path(leg["verification"]["scope_path"]).is_file()
    assert leg["verification"]["drive"]["action"] == "dispatch_assembled"
    assert leg["verification"]["spawn"]["attempted"] is True
    assert leg["verification"]["spawn"]["reason"] == "spawn_smoke_driver_not_configured"


def test_bootstrap_token_scope_table_fail_closed(tmp_path):
    driver = FakeDriver(scope_sets=("contents:write",))
    summary = _apply(tmp_path, driver)
    leg = _leg(summary, "github_bootstrap_token_probe")
    assert leg["status"] == "refused"
    assert leg["verification"]["code"] == "bootstrap_token_scope_refused"
    assert "missing bootstrap scopes" in leg["detail"]


def test_plain_join_finegrained_pat_passes_identity_only(tmp_path):
    # ce-ops#94 / #90 end-to-end: ce-dev-3 joining an already-CE repo with a FINE-GRAINED PAT.
    # Plain-join writes NOTHING with the PAT (forge ops ride the App token; protection is
    # verify-first/defer-not-mutate) -> identity-only -> the probe passes and the onboard
    # converges with NO PAT broadening and NO admin role.
    driver = FakeDriver(repo_exists=True, token_type="fine_grained")
    summary = _apply(tmp_path, driver, answers=_answers(tmp_path, mode="existing"))
    assert summary["refused"] == 0 and summary["failed"] == 0
    leg = _leg(summary, "github_bootstrap_token_probe")
    assert leg["status"] == "already_satisfied"
    assert leg["verification"]["token_type"] == "fine_grained"
    assert leg["verification"]["capability"]["mode"] == "identity_only_plain_join"
    assert summary["repos_already_satisfied"] == 1


def test_greenfield_finegrained_pat_probe_defers_capability_to_write_legs(tmp_path):
    # ce-ops#94: greenfield with a fine-grained PAT (GitHub's recommended default). Its write
    # capability is NOT introspectable pre-flight, so the probe accepts on identity/validity and
    # the greenfield write legs are the fail-closed enforcement point. The probe must NOT refuse.
    driver = FakeDriver(token_type="fine_grained")
    summary = _apply(tmp_path, driver)  # default mode="new"
    leg = _leg(summary, "github_bootstrap_token_probe")
    assert leg["status"] == "already_satisfied"
    assert leg["verification"]["capability"]["mode"] == "fine_grained_enforced_at_write_legs"


def test_greenfield_unknown_token_type_is_fail_closed(tmp_path):
    # Unknown token type AND no classic X-OAuth-Scopes -> the greenfield requirement cannot be
    # verified -> refuse (never silent-pass).
    driver = FakeDriver(token_type="unknown")
    summary = _apply(tmp_path, driver)
    leg = _leg(summary, "github_bootstrap_token_probe")
    assert leg["status"] == "refused"
    assert leg["verification"]["code"] == "bootstrap_token_unverifiable"


def test_bootstrap_invalid_token_is_refused_distinctly(tmp_path):
    # An invalid token (GET /user fails) refuses with a DISTINCT code, separate from scope refusal.
    class _InvalidProbe(FakeDriver):
        def probe_bootstrap_token(self, *, token, repo, org_create_needed):
            self.calls.append("probe_bootstrap_token")
            return {"ok": False, "reason": "bootstrap_probe_failed"}

    summary = _apply(tmp_path, _InvalidProbe())
    leg = _leg(summary, "github_bootstrap_token_probe")
    assert leg["status"] == "refused"
    assert leg["verification"]["code"] == "bootstrap_token_invalid"
