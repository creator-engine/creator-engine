# PR path manifest — ce71-userlevel-apply · ce-ops#71 (G71.2 tier planner + G71-CORE backend-driven `--apply` decoupling) over the #225+#223 stack

Per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`, the ce-ops#21 convention). CI runs:

```bash
verify-path-manifest --base <PR base sha> --manifest-dir .ce/pr-manifests --head-ref ce71-userlevel-apply
```

and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below
(the carrier lists itself); the repo-wide fidelity scan requires the declared count and
SHA256 to match the fenced block.

## The stack (read this first)

This branch (`ce71-stack-base`) is a **STAGED INTEGRATION STACK**, built so the morning merge train is clean:

1. **#225 `ce43-seat-reaper`** (base of this branch).
2. **#223 `ce34-rs-resolver-seam`** merged over it (`integration base` commit).
3. **#71 G71.2** tier-aware pure installer planner committed on top.
4. **#71 G71-CORE** the backend-driven `onboard --apply` decoupling committed on top of G71.2 (this work).

The path-set below is `base..HEAD` against **`main` = `20c460c`** (current tip, before #225/#223
land), so it **legitimately includes the stacked #225 + #223 files + their two carriers** alongside
G71.2's + G71-CORE's own. Once the merge train lands #225 then #223 into `main`, this branch re-grounds
onto the new base and the path-set reduces to **the #71 (G71.2 + G71-CORE) paths + this carrier** (a
mechanical base-only re-ground under `ce-base-only-refresh-microauth`); the orchestrator re-pins at that
point. The post-hoc fidelity scan only requires this carrier's COUNT/SHA256 to match its own fenced block.

## What G71.2 changed (already committed in this branch)

Per the ratified direction paper §A.1–A.3 (the gVisor→opt-in demotion), the **pure installer planner**
became tier-aware: `TIER_DEPS {0,1,2}`, `_SUDO_TOOLS` shrunk to `{runsc, proxy}` (git/python/uv
user-level ALWAYS), polymorphic `plan_dependencies(tier|iterable, probe)`, `InstallerProfile.isolation_tier`,
tier-conditional `build_install_plan` seam, and the §A.3 three-tier fail-closed walk. (G71.2 carried `+0
checks / +0 V3_RUNTIME modules`.)

## What G71-CORE adds (the NEW work in this commit)

The ce-ops#71 Tranche-1 CORE decoupling, per the install/deploy architecture research §3/§5/§6 and the
four edits + three requirements. **STAGE-ONLY; the OpenShell/NemoClaw functional adapter is HELD; the
`os-native` backend is a FAIL-CLOSED scaffold; contested defaults (the 9 OQs) are ESCALATED, not pinned.**

- **Edit A (de-hardwire) — `onboard_apply.py`:** `provision_runtime`/`verify_runtime` take a `backend`
  param; `provision_runtime` writes the RESOLVED backend into `posture.json` (no longer the `gvisor-proxy`
  hardwire); `verify_runtime` dispatches the SELECTED backend's own availability check (gvisor → runsc+proxy;
  os-native → no privileged runtime, primitives surfaced as an informational probe; unknown → fail-closed).
- **Edit B (backend-driven deps) — `v3_installer.py`:** `BACKEND_DEPS` keyed by `isolation_backend`
  (`os-native`/`openshell` → core no-sudo `{git,python,uv}`; `gvisor-proxy` → `+{runsc,proxy}`), the
  re-frame of G71.2's numeric `TIER_DEPS` (both kept; the tiers stay back-compat). `plan_dependencies`
  now also accepts a **str backend key**. `_prepare`/the `host_dependencies` leg are backend-driven.
- **Edit C (solo-pilot leak) — `onboard_apply.py`:** the unconditional `runtime_posture` leg materializes
  the PROFILE's resolved backend (`solo-pilot → os-native`), so the governance-only install stops dragging
  gVisor+proxy. `resolve_isolation_backend(profile, explicit)` precedence: explicit > profile > schema
  default `gvisor-proxy`. `PROFILE_DEFAULT_BACKEND = {solo-pilot: os-native, team: gvisor-proxy}` — `team`
  left conservative (OQ-4 ESCALATED, NOT hardcoded to os-native).
- **Edit D + req-3 (validate-at-provision invariant) — `runner/backend.py`:** `RunnerBackend.provision`
  becomes a CONCRETE template method that validates the policy FIRST (`PolicyRejected` on a dirty record)
  then delegates to the abstract `_provision`; `noop`/`gvisor`/`openshell`/`audit_overlay` backends are
  refactored `provision → _provision` (deduplicated). A registry-level test asserts EVERY registered
  backend rejects a dirty record.
- **req-4 (gate the default-flip) — `schemas/runtime-policy.schema.yaml`:** `isolation_backend` enum gains
  `os-native`; `default:` STAYS `gvisor-proxy` so pre-#71 records/fixtures don't break. Back-compat tests
  added.
- **req-5 (fallback FAIL-CLOSED) — `runner/os_native_backend.py` (NEW):** the unprivileged `os-native`
  backend scaffold — registered + deny-surface-enforcing, but `_provision` refuses live provisioning with
  `BackendUnavailable` and a NAMED missing-primitive list (the mechanism — srt vs CE-native jail, OQ-1 — is
  HELD). Default fail-closed; the policy choice is the #1 morning ratification item, left OPEN.

`runner.os_native_backend` added to `V3_RUNTIME` (`41 → 42`); `+0` validator checks (`register_backend`
is the backend registry, not `@register`; `--list-checks` byte-identical). The app wheel was **rebuilt from
the final G71-CORE source** (sha256 `0f70124e…`); `validators/build` cleaned before staging
([[ce-wheel-rebuild-build-leak-footgun]]); `verify-wheel-matches-source` byte-clean; `validators/wheelhouse/SHA256SUMS`
re-pinned (the 6 dependency wheels byte-unchanged). `_version.py` `BUILD_GIT_SHA` left at the valid-ancestor
`0791fba` (G71.2 precedent; `verify_generated_version` clean).

**Deferred (NOT in this scope):** the functional `os-native` sandbox mechanism (srt / CE-native jail), the
live OpenShell wiring + NemoClaw on-ramp (Tranche 2), the `--sandbox` CLI selector + an explicit answers-file
`isolation_backend` field, the team-profile default decision, and the AppArmor/Windows/macOS reach (the 9 OQs).

## Per-file purpose

G71-CORE (new in this commit):
- **`schemas/runtime-policy.schema.yaml`** *(M)* — enum `+os-native`; default stays gvisor-proxy.
- **`docs/contracts/runtime-policy.md`**, **`docs/contracts/orchestrator.md`** *(M)* — enum/backend doc sync.
- **`validators/creator_engine_validator/v3_installer.py`** *(M)* — `BACKEND_DEPS`/`DEFAULT_ISOLATION_BACKEND`/
  `PROFILE_DEFAULT_BACKEND`/`resolve_isolation_backend`; backend-key `plan_dependencies`.
- **`validators/creator_engine_validator/onboard_apply.py`** *(M)* — Edits A+C: backend param on
  provision/verify_runtime, backend-driven `_prepare`/`host_dependencies`, profile-resolved `runtime_posture`.
- **`validators/creator_engine_validator/runner/backend.py`** *(M)* — `provision` template method (req-3).
- **`validators/creator_engine_validator/runner/{noop,gvisor_proxy,openshell,audit_overlay}_backend.py`**,
  **`runner/__init__.py`** *(M)* — `provision → _provision`; os-native exports.
- **`validators/creator_engine_validator/runner/os_native_backend.py`** *(A)* — the fail-closed scaffold.
- **`validators/creator_engine_validator/_versions.py`** *(M)* — `V3_RUNTIME += runner.os_native_backend`.
- **`validators/wheelhouse/creator_engine_validator-0.2.0-py3-none-any.whl`**, **`…/SHA256SUMS`** *(M)* —
  wheel rebuilt from final source (sha256 `0f70124e…`) + re-pinned.
- **`validators/tests/unit/{test_runner_backend,test_v3_installer,test_ce_runtime_policy,test_onboard_apply,
  test_version_boundary,test_audit_overlay,test_openshell_backend,test_orchestrator,test_run_assembly,
  test_app_jwt_runner,test_change_status,test_credential_runner,test_evidence_sink,test_merge,
  test_open_change,test_redact}.py`** *(M)* — new os-native/registry/back-compat/solo-pilot tests + the
  registry-pin 3-tuple → 4-tuple bumps + the test-fake `provision → _provision` renames.

G71.2 + integration-base + stacked #223/#225 (carried through, see git history):
- **`validators/creator_engine_validator/{v3_installer (also G71-CORE-touched),_version,_versions,v3_cli,
  authority_resolver,reaper_executors,seat_reaper}.py`**, **`forge/plan_approval.py`**, the two stacked
  carriers, **`docs/operations/SEAT_REAPER_PROTOCOL.md`**, **`schemas/dispatch-record.schema.yaml`**, and the
  stacked test files.

Posture: the seat committed LOCALLY only — NO `git push`, NO `gh pr`, NO merge. The orchestrator stages;
the Operator merges (morning session).

Canonicalization:
`sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=50

AUTHORIZED_PATHS_SHA256=d9205e5978dfee8c159e05fea79b42227ab1d576c3c226496ac701c2ce55f38b

```text
.ce/pr-manifests/ce34-rs-resolver-seam.md
.ce/pr-manifests/ce43-seat-reaper.md
.ce/pr-manifests/ce71-userlevel-apply.md
docs/contracts/orchestrator.md
docs/contracts/runtime-policy.md
docs/operations/SEAT_REAPER_PROTOCOL.md
schemas/dispatch-record.schema.yaml
schemas/runtime-policy.schema.yaml
validators/creator_engine_validator/_version.py
validators/creator_engine_validator/_versions.py
validators/creator_engine_validator/authority_resolver.py
validators/creator_engine_validator/forge/plan_approval.py
validators/creator_engine_validator/onboard_apply.py
validators/creator_engine_validator/reaper_executors.py
validators/creator_engine_validator/runner/__init__.py
validators/creator_engine_validator/runner/audit_overlay.py
validators/creator_engine_validator/runner/backend.py
validators/creator_engine_validator/runner/gvisor_proxy_backend.py
validators/creator_engine_validator/runner/noop_backend.py
validators/creator_engine_validator/runner/openshell_backend.py
validators/creator_engine_validator/runner/os_native_backend.py
validators/creator_engine_validator/seat_reaper.py
validators/creator_engine_validator/v3_cli.py
validators/creator_engine_validator/v3_installer.py
validators/tests/integration/test_pco_allocator_cli.py
validators/tests/unit/test_app_jwt_runner.py
validators/tests/unit/test_audit_overlay.py
validators/tests/unit/test_authority_resolver.py
validators/tests/unit/test_ce_runtime_policy.py
validators/tests/unit/test_change_status.py
validators/tests/unit/test_credential_runner.py
validators/tests/unit/test_evidence_sink.py
validators/tests/unit/test_merge.py
validators/tests/unit/test_onboard_apply.py
validators/tests/unit/test_open_change.py
validators/tests/unit/test_openshell_backend.py
validators/tests/unit/test_orchestrator.py
validators/tests/unit/test_pane_registry.py
validators/tests/unit/test_pco_allocator.py
validators/tests/unit/test_redact.py
validators/tests/unit/test_run_assembly.py
validators/tests/unit/test_runner_backend.py
validators/tests/unit/test_seat_reaper.py
validators/tests/unit/test_transcript_archive.py
validators/tests/unit/test_v3_cli.py
validators/tests/unit/test_v3_installer.py
validators/tests/unit/test_v3_seat_bridge.py
validators/tests/unit/test_version_boundary.py
validators/wheelhouse/SHA256SUMS
validators/wheelhouse/creator_engine_validator-0.2.0-py3-none-any.whl
```
