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
        self.captured_merge_settings = None

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
            return {"ok": self.runtime_ok, "backend": backend, "runsc": True, "gvproxy": True, "provider_transport": provider == "codex"}
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
        # ce-ops#94: classic tokens report derived OAuth scopes; fine-grained tokens report identity
        # only (never a fabricated classic scope set or unsafe permission-introspection result).
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

    def configure_merge_settings(self, *, repo, squash_only, token):
        self.calls.append("configure_merge_settings")
        self.captured_merge_settings = {"squash_only": squash_only}
        return {"ok": True}

    def verify_branch_protection(self, *, repo, branch, policy):
        self.calls.append("verify_branch_protection")
        return {"ok": self.branch_protection_ok, "contexts": list(policy.required_status_check_contexts)}

    def verify_merge_settings(self, *, repo, squash_only):
        self.calls.append("verify_merge_settings")
        return {"ok": True, "settings": {"squash_only": squash_only}}

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
    # ce-ops#85: the 7 adoption legs SKIP in a greenfield run; the 12 greenfield legs converge.
    assert summary["skipped"] == len(onboard_apply.ADOPTION_LEG_IDS)
    assert (
        summary["applied"] + summary["already_satisfied"] + summary["skipped"]
        == len(onboard_apply.LEG_IDS)
    )
    assert summary["greenfield_repos_created"] == 1
    assert summary["brownfield_adopted"] == 0
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
    # the held leg is excluded from verified_count; the 7 adoption legs SKIP in greenfield, so
    # verified_count = the greenfield legs minus the one held leg (ce-ops#85 grew LEG_IDS).
    assert summary["skipped"] == len(onboard_apply.ADOPTION_LEG_IDS)
    assert summary["verified_count"] == len(onboard_apply.GREENFIELD_LEG_IDS) - 1
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
    # every greenfield leg converged (applied or already_satisfied); the 7 adoption legs
    # SKIP (plain-join is not adoption); none refused/failed.
    assert summary["skipped"] == len(onboard_apply.ADOPTION_LEG_IDS)
    assert (
        summary["applied"] + summary["already_satisfied"] + summary["skipped"]
        == len(onboard_apply.LEG_IDS)
    )


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
    assert driver.captured_merge_settings == {"squash_only": True}


def test_branch_protection_unenforceable_refuses_with_remediation(tmp_path):
    class UnenforceableProtectionDriver(FakeDriver):
        def configure_branch_protection(self, *, repo, branch, policy, token):
            self.calls.append("configure_branch_protection")
            return {
                "ok": False,
                "reason": onboard_apply.PROTECTION_FLOOR_UNENFORCEABLE_CODE,
                "message": "Upgrade to GitHub Pro or make this repository public to enable this feature.",
                "remediation": onboard_apply.PROTECTION_FLOOR_REMEDIATION,
            }

    driver = UnenforceableProtectionDriver()
    summary = _apply(tmp_path, driver)
    leg = _leg(summary, "github_branch_protection")
    assert leg["status"] == "refused"
    assert leg["verification"]["code"] == onboard_apply.PROTECTION_FLOOR_UNENFORCEABLE_CODE
    assert "GitHub Team/Pro" in leg["detail"]
    assert _leg(summary, "workspace_checkout")["status"] == "skipped"


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


def test_greenfield_finegrained_pat_probe_accepts_identity_and_defers_write_capability(tmp_path):
    # ce-ops#94: greenfield with a fine-grained PAT (GitHub's recommended default) is identity-only
    # at the probe. Capability is enforced fail-closed by the actual greenfield write legs.
    driver = FakeDriver(token_type="fine_grained")
    summary = _apply(tmp_path, driver)  # default mode="new"
    leg = _leg(summary, "github_bootstrap_token_probe")
    assert leg["status"] == "already_satisfied"
    assert leg["verification"]["capability"]["mode"] == "fine_grained_identity_only_write_legs_fail_closed"
    assert set(leg["verification"]["capability"]["required_at_write_legs"]) == {
        *v3_installer.REQUIRED_BOOTSTRAP_SCOPES,
        v3_installer.ORG_CREATE_SCOPE,
    }
    assert summary["failed"] == 0 and summary["refused"] == 0


def test_plain_join_unknown_token_type_is_fail_closed(tmp_path):
    driver = FakeDriver(repo_exists=True, token_type="unknown")
    summary = _apply(tmp_path, driver, answers=_answers(tmp_path, mode="existing"))
    leg = _leg(summary, "github_bootstrap_token_probe")
    assert leg["status"] == "refused"
    assert leg["verification"]["code"] == "bootstrap_token_unverifiable"


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


# ===========================================================================
# ce-ops#85 E3 brownfield ADOPTION-APPLY (the join-PR layer) — §10 test plan.
# ===========================================================================
def _brownfield_probe(*, dirty: bool = False, scanner_clean: bool = True) -> dict[str, Any]:
    secrets = {
        "preflight": "required",
        "status": "clean" if scanner_clean else "not_run",
        "scanner_available": True if scanner_clean else None,
        "findings": [],
    }
    return {
        "enabled": True,
        "project_root": ".",
        "history": {
            "mode": "git_history_present",
            "head_sha": "a" * 40,
            "default_branch": "main",
            "commit_count": 3,
            "dirty": dirty,
        },
        "github": {"origin_remote": "octo/greenfield"},
        "ci": {
            "workflows": [
                {
                    "path": ".github/workflows/ci.yml",
                    "name": "CI",
                    "jobs": ["test"],
                    "check_names": ["CI / test"],
                }
            ],
            "current_required_checks": ["lint"],
        },
        "tests": {"commands": [{"command": "python -m pytest", "source": "pyproject.toml"}]},
        "conventions": {"branch_patterns": [], "commit_styles": []},
        "secrets": secrets,
    }


def _adoption_plan(tmp_path: Path, probe: dict[str, Any]) -> dict[str, Any]:
    return v3_installer.build_brownfield_adoption_plan(
        _answers(tmp_path, mode="existing"), schema=_schema(), probe=probe
    )


class FakeAdoptionDriver(FakeDriver):
    """A unit fake for the adoption legs — local legs from FakeDriver, adoption legs here."""

    def __init__(
        self,
        *,
        scrub_result: dict[str, Any] | None = None,
        push_result: dict[str, Any] | None = None,
        pr_result: dict[str, Any] | None = None,
        preserved_result: dict[str, Any] | None = None,
        scaffold_ok: bool = True,
        scaffold_workflow_sha: str | None = None,
    ):
        super().__init__(repo_exists=True)
        # NOTE: ``is not None`` (not ``or``) — an empty {} scrub_result is a DELIBERATE
        # fail-closed case, not "use the default".
        self._scrub_result = scrub_result if scrub_result is not None else {
            "scanners": {
                "gitleaks": {"ran": True, "exit_code": 0, "findings": []},
                "trufflehog": {"ran": True, "exit_code": 0, "findings": []},
            }
        }
        self._push_result = push_result if push_result is not None else {
            "ok": True, "pushed": True, "up_to_date": False,
            "local_head": "f" * 40, "remote_head": None,
        }
        self._pr_result = pr_result if pr_result is not None else {
            "ok": True, "pr_number": 7, "head_sha": "f" * 40, "verified": True, "claimed": False,
        }
        self._preserved_result = preserved_result if preserved_result is not None else {
            "ok": True, "existing_checks": ["CI / test", "lint"], "dropped": [],
        }
        self._scaffold_ok = scaffold_ok
        self._scaffold_workflow_sha = (
            scaffold_workflow_sha if scaffold_workflow_sha is not None else onboard_apply.CE_WORKFLOW_SHA256
        )
        self.scaffold_artifacts: list[dict[str, Any]] | None = None

    def secret_preflight_scan(self, *, scan_root, scaffold):
        self.calls.append("secret_preflight_scan")
        return self._scrub_result

    def build_adoption_scaffold(self, *, repo, base, branch, workspace_root, artifacts):
        self.calls.append("build_adoption_scaffold")
        self.scaffold_artifacts = list(artifacts)
        if not self._scaffold_ok:
            return {"ok": False, "reason": "adoption_branch_checkout_failed"}
        return {
            "ok": True,
            "source_dir": str(workspace_root / repo.split("/", 1)[1]),
            "head_sha": "f" * 40,
            "scaffold_paths": [a["path"] for a in artifacts],
            "workflow_sha256": self._scaffold_workflow_sha,
            "already": False,
        }

    def push_adoption_branch(self, *, repo, branch, source_dir):
        self.calls.append("push_adoption_branch")
        return self._push_result

    def open_adoption_pr(self, *, repo, branch, base, manifest_paths, plan_ref):
        self.calls.append("open_adoption_pr")
        self.opened_with = {"manifest_paths": list(manifest_paths), "plan_ref": plan_ref, "base": base}
        return self._pr_result

    def read_preserved_checks(self, *, repo, base, expected_checks):
        self.calls.append("read_preserved_checks")
        return self._preserved_result


def _adoption_apply(tmp_path: Path, driver: FakeAdoptionDriver, *, plan=None, probe=None, plan_override=None):
    probe = probe if probe is not None else _brownfield_probe()
    plan = plan if plan is not None else _adoption_plan(tmp_path, probe)
    if plan_override:
        plan = {**plan, **plan_override}
    answers = _answers(tmp_path, mode="existing")
    answer_bytes = yaml.safe_dump(answers, sort_keys=True).encode("utf-8")
    request = onboard_apply.ApplyRequest(
        spec_bytes=_signed_spec(),
        schema=_schema(),
        answers=answers,
        answers_sha256=v3_installer.content_digest(answer_bytes),
        state_root=tmp_path / "state",
        dependency_probe={tool: True for tool in v3_installer.REQUIRED_DEPENDENCIES},
        non_interactive=True,
        adoption_apply=True,
        brownfield_plan=plan,
        brownfield_probe=probe,
    )
    return onboard_apply.apply_onboard(
        request, verifier=_verifier(), driver=driver, invocation_id="test-adoption"
    )


def test_adoption_opens_join_pr_and_skips_greenfield_forge_legs(tmp_path):
    # §10.6/§10.11 — the happy path: the 7 adoption legs run, the greenfield forge legs skip,
    # exactly one verified join PR is counted, and the ledger carries value-free evidence.
    driver = FakeAdoptionDriver()
    summary = _adoption_apply(tmp_path, driver)
    assert summary["refused"] == 0 and summary["failed"] == 0
    assert summary["brownfield_adopted"] == 1
    assert summary["brownfield_adoption_pr"]["pr_number"] == 7
    assert summary["brownfield_deferred"] == 0
    # the greenfield forge legs are skipped under brownfield_adoption_mode
    for leg_id in onboard_apply.ADOPTION_SKIPPED_GREENFIELD_LEG_IDS:
        assert _leg(summary, leg_id)["status"] == "skipped"
        assert _leg(summary, leg_id)["action"] == "brownfield_adoption_mode"
    # all 7 adoption legs converged
    for leg_id in onboard_apply.ADOPTION_LEG_IDS:
        assert _leg(summary, leg_id)["status"] in {"applied", "already_satisfied"}
    # never created a repo / installed a workflow directly / mutated protection
    assert "create_repo" not in driver.calls
    assert "install_workflow" not in driver.calls
    assert "configure_branch_protection" not in driver.calls
    # the PR carried the scaffold paths + the inventory-sha plan ref
    plan = _adoption_plan(tmp_path, _brownfield_probe())
    assert driver.opened_with["plan_ref"] == plan["inventory_sha256"]
    assert onboard_apply.CE_WORKFLOW_PATH in driver.opened_with["manifest_paths"]


def test_adoption_drift_check_refuses_before_scrub_or_build(tmp_path):
    # §10.2 — a plan inventory sha that no longer matches the fresh recompute refuses
    # brownfield_inventory_drift before the scrub/build/push.
    driver = FakeAdoptionDriver()
    summary = _adoption_apply(tmp_path, driver, plan_override={"inventory_sha256": "0" * 64})
    drift = _leg(summary, "brownfield_inventory_drift_check")
    assert drift["status"] == "refused"
    assert drift["verification"]["code"] == "brownfield_inventory_drift"
    assert "secret_preflight_scan" not in driver.calls
    assert "build_adoption_scaffold" not in driver.calls
    assert summary["brownfield_adopted"] == 0


def test_adoption_scrub_finding_refuses_hard(tmp_path):
    # §10.3 — an unwaived finding from a scanner refuses brownfield_secret_findings; no build/push.
    driver = FakeAdoptionDriver(scrub_result={
        "scanners": {
            "gitleaks": {"ran": True, "exit_code": 1, "findings": ["gitleaks:cfg.py:3"]},
            "trufflehog": {"ran": True, "exit_code": 0, "findings": []},
        }
    })
    summary = _adoption_apply(tmp_path, driver)
    # exit 1 / a finding both make this non-clean; the scanner-unavailable check fires first on
    # the non-zero exit (affirmative fail-closed) — either way it refuses before any build/push.
    scrub = _leg(summary, "brownfield_secret_preflight")
    assert scrub["status"] == "refused"
    assert scrub["verification"]["code"] in {
        "brownfield_secret_findings", "brownfield_secret_scanner_unavailable"
    }
    assert "build_adoption_scaffold" not in driver.calls
    assert "push_adoption_branch" not in driver.calls
    assert summary["brownfield_adopted"] == 0


def test_adoption_scrub_finding_with_clean_exit_refuses_secret_findings(tmp_path):
    # A finding reported with an affirmative zero-exit (the scanner ran clean-process but FOUND a
    # secret) refuses brownfield_secret_findings specifically.
    driver = FakeAdoptionDriver(scrub_result={
        "scanners": {
            "gitleaks": {"ran": True, "exit_code": 0, "findings": ["gitleaks:env:9"]},
            "trufflehog": {"ran": True, "exit_code": 0, "findings": []},
        }
    })
    summary = _adoption_apply(tmp_path, driver)
    scrub = _leg(summary, "brownfield_secret_preflight")
    assert scrub["status"] == "refused"
    assert scrub["verification"]["code"] == "brownfield_secret_findings"


def test_adoption_scrub_fail_closed_on_scanner_problems(tmp_path):
    # §10.3 / MAJOR-2 — EVERY non-affirmative-clean scanner state refuses
    # brownfield_secret_scanner_unavailable (absence of findings is NOT clean).
    cases = [
        {"gitleaks": {"ran": True, "exit_code": 0, "findings": []}},  # trufflehog MISSING
        {"gitleaks": {"ran": False, "exit_code": None, "findings": []},
         "trufflehog": {"ran": True, "exit_code": 0, "findings": []}},  # did not run
        {"gitleaks": {"ran": True, "exit_code": 2, "findings": []},
         "trufflehog": {"ran": True, "exit_code": 0, "findings": []}},  # non-zero exit
        {"gitleaks": {"ran": True, "exit_code": 0, "error": "timeout", "findings": []},
         "trufflehog": {"ran": True, "exit_code": 0, "findings": []}},  # error/timeout
        {"gitleaks": {"ran": True, "exit_code": 0, "findings": "oops"},
         "trufflehog": {"ran": True, "exit_code": 0, "findings": []}},  # unparseable findings
    ]
    for scanners in cases:
        driver = FakeAdoptionDriver(scrub_result={"scanners": scanners})
        summary = _adoption_apply(tmp_path, driver)
        scrub = _leg(summary, "brownfield_secret_preflight")
        assert scrub["status"] == "refused", scanners
        assert scrub["verification"]["code"] == "brownfield_secret_scanner_unavailable", scanners
        assert "build_adoption_scaffold" not in driver.calls


def test_adoption_scrub_empty_result_is_fail_closed(tmp_path):
    # A driver that returns NO scanners report is NOT clean (the fail-open seam this closes).
    driver = FakeAdoptionDriver(scrub_result={})
    summary = _adoption_apply(tmp_path, driver)
    scrub = _leg(summary, "brownfield_secret_preflight")
    assert scrub["status"] == "refused"
    assert scrub["verification"]["code"] == "brownfield_secret_scanner_unavailable"


def test_adoption_scrub_finding_passes_with_ratified_waiver(tmp_path):
    # §10.3 — a finding carrying a complete ratified waiver passes the scrub gate.
    probe = _brownfield_probe()
    answers = _answers(tmp_path, mode="existing")
    answers["brownfield"] = {
        "secrets": {
            "waivers": [
                {
                    "finding_id": "gitleaks:env:9",
                    "ratification": {
                        "ratified_prompt_sha": "b" * 64,
                        "approver_ref": "c" * 64,
                        "educate_acknowledged": True,
                    },
                }
            ]
        }
    }
    plan = v3_installer.build_brownfield_adoption_plan(answers, schema=_schema(), probe=probe)
    driver = FakeAdoptionDriver(scrub_result={
        "scanners": {
            "gitleaks": {"ran": True, "exit_code": 0, "findings": ["gitleaks:env:9"]},
            "trufflehog": {"ran": True, "exit_code": 0, "findings": []},
        }
    })
    answer_bytes = yaml.safe_dump(answers, sort_keys=True).encode("utf-8")
    request = onboard_apply.ApplyRequest(
        spec_bytes=_signed_spec(), schema=_schema(), answers=answers,
        answers_sha256=v3_installer.content_digest(answer_bytes),
        state_root=tmp_path / "state",
        dependency_probe={tool: True for tool in v3_installer.REQUIRED_DEPENDENCIES},
        non_interactive=True, adoption_apply=True, brownfield_plan=plan, brownfield_probe=probe,
    )
    summary = onboard_apply.apply_onboard(request, verifier=_verifier(), driver=driver)
    scrub = _leg(summary, "brownfield_secret_preflight")
    assert scrub["status"] == "already_satisfied"
    assert summary["brownfield_scrub_findings"] == 1
    assert summary["brownfield_scrub_findings_waived"] == 1
    assert summary["brownfield_adopted"] == 1


def test_adoption_push_never_force_refuses_non_fast_forward(tmp_path):
    # §10.5 — a non-fast-forward push refuses brownfield_push_refused (never force); no PR opened.
    driver = FakeAdoptionDriver(push_result={"ok": False, "reason": "push_refused", "detail": "non-ff"})
    summary = _adoption_apply(tmp_path, driver)
    push = _leg(summary, "brownfield_push_branch")
    assert push["status"] == "refused"
    assert push["verification"]["code"] == "brownfield_push_refused"
    assert "open_adoption_pr" not in driver.calls
    assert summary["brownfield_adopted"] == 0


def test_adoption_idempotent_rerun_claims_existing_pr(tmp_path):
    # §10.6 — a re-run reconciles: up_to_date push + a CLAIMED existing PR, still adopted == 1.
    driver = FakeAdoptionDriver(
        push_result={"ok": True, "pushed": False, "up_to_date": True, "local_head": "f" * 40, "remote_head": "f" * 40},
        pr_result={"ok": True, "pr_number": 7, "head_sha": "f" * 40, "verified": True, "claimed": True},
    )
    summary = _adoption_apply(tmp_path, driver)
    assert summary["refused"] == 0 and summary["failed"] == 0
    assert _leg(summary, "brownfield_push_branch")["status"] == "already_satisfied"
    assert _leg(summary, "brownfield_open_join_pr")["status"] == "already_satisfied"
    assert summary["brownfield_adopted"] == 1


def test_adoption_unverified_pr_is_not_counted(tmp_path):
    # §10.6 counter-honesty — an unverified PR fails the leg and is NEVER counted adopted.
    driver = FakeAdoptionDriver(pr_result={"ok": True, "pr_number": None, "head_sha": None, "verified": False})
    summary = _adoption_apply(tmp_path, driver)
    pr = _leg(summary, "brownfield_open_join_pr")
    assert pr["status"] == "failed"
    assert pr["verification"]["code"] == "brownfield_open_pr_verify_failed"
    assert summary["brownfield_adopted"] == 0


def test_adoption_preserved_checks_loss_refuses(tmp_path):
    # §10.8 — leg 6 refuses brownfield_protection_loss if an existing check would be dropped.
    driver = FakeAdoptionDriver(
        preserved_result={"ok": True, "existing_checks": ["lint"], "dropped": ["CI / test"]}
    )
    summary = _adoption_apply(tmp_path, driver)
    leg = _leg(summary, "brownfield_verify_preserved_checks")
    assert leg["status"] == "refused"
    assert leg["verification"]["code"] == "brownfield_protection_loss"


def test_adoption_scaffold_workflow_digest_pinned(tmp_path):
    # §10.4 — the scaffold's workflow must verify at the pinned CE_WORKFLOW_SHA256.
    driver = FakeAdoptionDriver(scaffold_workflow_sha="dead" * 16)
    summary = _adoption_apply(tmp_path, driver)
    leg = _leg(summary, "brownfield_build_scaffold")
    assert leg["status"] == "failed"
    assert leg["verification"]["code"] == "brownfield_scaffold_verify_failed"


def test_adoption_scaffold_is_value_free(tmp_path):
    # §10.4 — the scaffold the join PR carries is value-free (skills + scope seed + workflow),
    # the workflow rides at the pinned digest, and the manifest paths are the four scaffold files.
    driver = FakeAdoptionDriver()
    summary = _adoption_apply(tmp_path, driver)
    assert summary["failed"] == 0
    paths = {a["path"] for a in driver.scaffold_artifacts}
    assert onboard_apply.CE_WORKFLOW_PATH in paths
    assert ".ce/state/scopes/ce-brownfield-adoption.scope.yaml" in paths
    assert any(p.startswith(".ce/skills/") for p in paths)
    rendered = json.dumps(summary, sort_keys=True)
    assert "secret-token" not in rendered  # no bootstrap secret (the probe leg is skipped)
    # ledger evidence is value-free
    record = _leg(summary, "brownfield_record_apply_evidence")["verification"]
    assert record["pr_number"] == 7
    assert "scrub" in record


def test_adoption_waiver_missing_ratification_rejected_at_schema(tmp_path):
    # §7 — a provided waiver missing the {ratified_prompt_sha, approver_ref,
    # educate_acknowledged} binding never reaches the leg: the answers schema rejects it
    # fail-closed at validation (the leg-side brownfield_waiver_unratified check is
    # defense-in-depth for that same invariant).
    answers = _answers(tmp_path, mode="existing")
    answers["brownfield"] = {"secrets": {"waivers": [{"finding_id": "f1"}]}}
    problems = v3_installer.validate_answers(answers, schema=_schema())
    assert any("ratification" in p for p in problems)
