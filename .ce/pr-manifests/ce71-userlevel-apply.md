# PR path manifest — ce71-userlevel-apply · ce-ops#71 = #223 (ce34 RS resolver seam) ⊕ #71 (user-level `--apply`), rebased on main `ac513c4f`

Per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`, the ce-ops#21 convention). CI runs:

```bash
verify-path-manifest --base <PR base sha> --manifest-dir .ce/pr-manifests --head-ref ce71-userlevel-apply
```

and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below
(the carrier lists itself); the repo-wide fidelity scan requires the declared count and
SHA256 to match the fenced block.

## Merge-train collapse (read this first)

The morning merge train landed **#225 (`ce43` seat-reaper) separately on `main`** (squash-merge;
`origin/main = ac513c4f`). This PR is the **collapse of #226 = #223 ⊕ #71**, rebased onto that new main:

1. **#223 `ce34-rs-resolver-seam`** — the AuthorityResolver seam (`authority_resolver.py`,
   `forge/plan_approval.py`, its tests + carrier).
2. **#71 G71.2 + G71-CORE + round-2** — the tier-aware pure installer planner, the backend-driven
   `onboard --apply` decoupling (`os-native` fail-closed scaffold + validate-at-provision invariant),
   and the round-2 re-review fixes (honest held `verify_runtime`, the orchestrator omitted-backend guard).

**The #225/reaper content is NOT in this diff** — it is already in `main` (landed via #225), so the
`origin/main..HEAD` path-set below excludes every reaper path (`ce43-seat-reaper.md`, `seat_reaper.py`,
`reaper_executors.py`, `SEAT_REAPER_PROTOCOL.md`, `dispatch-record.schema.yaml`, and the reaper test
files). The collapse was tree-equivalent (zero conflicts): the desired tree = the reviewed round-2 tip
`2bbb5ae` placed on top of `origin/main`; only the four base-dependent artifacts (`_version.py`
`BUILD_GIT_SHA`, the wheel, `SHA256SUMS`, this carrier) were regenerated for the new base.

## What G71.2 changed

Per the ratified direction paper §A.1–A.3 (the gVisor→opt-in demotion), the **pure installer planner**
became tier-aware: `TIER_DEPS {0,1,2}`, `_SUDO_TOOLS` shrunk to `{runsc, proxy}` (git/python/uv
user-level ALWAYS), polymorphic `plan_dependencies(tier|iterable, probe)`, `InstallerProfile.isolation_tier`,
tier-conditional `build_install_plan` seam, and the §A.3 three-tier fail-closed walk.

## What G71-CORE adds

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
  now also accepts a **str backend key**; `tier_for_backend` carries the resolved tier onto the plan.
- **Edit C (solo-pilot leak) — `onboard_apply.py`:** the `runtime_posture` leg materializes the PROFILE's
  resolved backend (`solo-pilot → os-native`), so the governance-only install stops dragging gVisor+proxy.
  `resolve_isolation_backend(profile, explicit)` precedence: explicit > profile > schema default
  `gvisor-proxy`. `PROFILE_DEFAULT_BACKEND = {solo-pilot: os-native, team: gvisor-proxy}` — `team` left
  conservative (OQ-4 ESCALATED, NOT hardcoded). The CLI preflight resolves the backend BEFORE the
  sudo-grant gate (MAJOR-1), so a no-root solo-pilot install is no longer falsely refused.
- **Edit D + req-3 (validate-at-provision invariant) — `runner/backend.py`:** `RunnerBackend.provision` is a
  CONCRETE template method that validates the policy FIRST (`PolicyRejected` on a dirty record) then
  delegates to the abstract `_provision`; `__init_subclass__` STRUCTURALLY forbids overriding `provision`
  (MAJOR-4). `noop`/`gvisor`/`openshell`/`audit_overlay` backends refactored `provision → _provision`.
- **req-4 (gate the default-flip) — `schemas/runtime-policy.schema.yaml`:** `isolation_backend` enum gains
  `os-native`; `default:` STAYS `gvisor-proxy`; the field is made OPTIONAL (not `required`) so a Draft
  2020-12 validator (which does not inject defaults) lets a pre-#71 omitting record validate, with the
  fail-closed default supplied at resolution time (MINOR-A).
- **req-5 (fallback FAIL-CLOSED) — `runner/os_native_backend.py` (NEW):** the unprivileged `os-native`
  backend scaffold — registered + deny-surface-enforcing, but `_provision` refuses live provisioning with
  `BackendUnavailable` and a NAMED missing-primitive list (`LINUX_SANDBOX_PRIMITIVES = bwrap,proxy`); the
  mechanism (srt vs CE-native jail, OQ-1) is HELD.

## Round 2 — independent re-review (CHANGES-REQUIRED → addressed)

- **`onboard_apply.py`:** MAJOR-2 honest held runtime — `verify_runtime` for a held backend returns primary
  `ok:False` + `held:True` (keeps `posture_applied`/`runtime_available:False`/reason/prereqs); `_run_leg`
  does NOT `ApplyFailed` on a held leg (no-root `--apply` still exits 0), records the distinct `held` status;
  `_empty_summary`/`_fold_counters` count `held` as non-failed but NOT runtime-verified.
- **`orchestrator.py`:** NEW BLOCKING regression — `run_plan` routed a MISSING `isolation_backend` through
  the fail-closed default instead of `KeyError`-indexing the record (`:352`); a present-but-unregistered key
  still raises `UnknownBackend`; `:304` docstring synced.
- **tests:** held-shape assertions; the omitted-backend `run_plan` regression test; a REAL end-to-end
  CLI→apply test (no `apply_onboard` monkeypatch).

## Build artifacts (regenerated for the new base `ac513c4f`)

`runner.os_native_backend` is in `V3_RUNTIME` (`42`); `+0` validator checks (`register_backend` is the
backend registry, not `@register`; `--list-checks` byte-identical at 53). The app wheel was **rebuilt from
the final collapsed source** (sha256 `1698e604…`); `validators/build` cleaned before staging
([[ce-wheel-rebuild-build-leak-footgun]]); `verify-wheel-matches-source` byte-clean;
`validators/wheelhouse/SHA256SUMS` re-pinned (the 6 dependency wheels byte-unchanged). `_version.py`
`BUILD_GIT_SHA` set to the new base **`ac513c4f`** (`verify_generated_version` clean — a valid HEAD
ancestor).

## Per-file purpose (the `origin/main..HEAD` union — #223 ⊕ #71)

#223 (ce34 RS resolver seam):
- **`validators/creator_engine_validator/authority_resolver.py`**, **`forge/plan_approval.py`** *(M)* — the
  AuthorityResolver seam; **`validators/tests/unit/test_authority_resolver.py`** *(M)* — its tests. #223's
  standalone carrier `.ce/pr-manifests/ce34-rs-resolver-seam.md` is **removed** (deleted from the tree): on
  collapse, #226 carries exactly ONE per-PR carrier (this file), which subsumes #223's path-set —
  `path_manifest_fidelity` requires a single carrier in `base..HEAD` (one PR = one carrier; Operator-ratified).

#71 (user-level `--apply`):
- **`schemas/runtime-policy.schema.yaml`** *(M)* — enum `+os-native`; default stays gvisor-proxy; field made optional.
- **`docs/contracts/runtime-policy.md`**, **`docs/contracts/orchestrator.md`** *(M)* — enum/backend/optional-field doc sync.
- **`validators/creator_engine_validator/v3_installer.py`** *(M)* — `BACKEND_DEPS`/`resolve_isolation_backend`/
  `BACKEND_TIER`/`tier_for_backend`; backend-key `plan_dependencies`.
- **`validators/creator_engine_validator/onboard_apply.py`** *(M)* — Edits A+C, MAJOR-2 honest held verify/leg/counters.
- **`validators/creator_engine_validator/orchestrator.py`** *(M)* — round-2 omitted-backend resolution guard.
- **`validators/creator_engine_validator/runner/backend.py`** *(M)* — `provision` template + `__init_subclass__` guard.
- **`validators/creator_engine_validator/runner/{noop,gvisor_proxy,openshell,audit_overlay}_backend.py`**,
  **`runner/__init__.py`** *(M)* — `provision → _provision`; os-native exports.
- **`validators/creator_engine_validator/runner/os_native_backend.py`** *(A)* — the fail-closed scaffold.
- **`validators/creator_engine_validator/v3_cli.py`** *(M)* — MAJOR-1 backend-aware onboard preflight.
- **`validators/creator_engine_validator/_versions.py`** *(M)* — `V3_RUNTIME` includes `runner.os_native_backend`.
- **`validators/creator_engine_validator/_version.py`** *(M)* — `BUILD_GIT_SHA` → new base `ac513c4f`.
- **`validators/wheelhouse/creator_engine_validator-0.2.0-py3-none-any.whl`**, **`…/SHA256SUMS`** *(M)* —
  wheel rebuilt from final source (sha256 `1698e604…`) + re-pinned.
- **`validators/tests/unit/{test_runner_backend,test_v3_installer,test_ce_runtime_policy,test_onboard_apply,
  test_version_boundary,test_audit_overlay,test_openshell_backend,test_orchestrator,test_run_assembly,
  test_app_jwt_runner,test_change_status,test_credential_runner,test_evidence_sink,test_merge,
  test_open_change,test_redact,test_v3_cli}.py`** *(M)* — os-native/registry/back-compat/solo-pilot/held
  tests + the registry-pin tuple bumps + the test-fake `provision → _provision` renames + the round-2
  held-shape, orchestrator-regression, and real-e2e CLI-apply tests.

**Deferred (NOT in this scope):** the functional `os-native` sandbox mechanism (srt / CE-native jail), the
live OpenShell wiring + NemoClaw on-ramp (Tranche 2), the `--sandbox` CLI selector + an explicit answers-file
`isolation_backend` field, the team-profile default decision, and the AppArmor/Windows/macOS reach (the 9 OQs).

Posture: the seat committed LOCALLY only — NO `git push`, NO `gh pr`, NO merge. The orchestrator stages and
`--force-with-lease` pushes after independent verify; the Operator merges.

Canonicalization:
`sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=39

AUTHORIZED_PATHS_SHA256=7c5459e560dc29dfa5ba825319730222e6ea0c92d2438aee14c8f47f61f28dd5

```text
.ce/pr-manifests/ce71-userlevel-apply.md
docs/contracts/orchestrator.md
docs/contracts/runtime-policy.md
schemas/runtime-policy.schema.yaml
validators/creator_engine_validator/_version.py
validators/creator_engine_validator/_versions.py
validators/creator_engine_validator/authority_resolver.py
validators/creator_engine_validator/forge/plan_approval.py
validators/creator_engine_validator/onboard_apply.py
validators/creator_engine_validator/orchestrator.py
validators/creator_engine_validator/runner/__init__.py
validators/creator_engine_validator/runner/audit_overlay.py
validators/creator_engine_validator/runner/backend.py
validators/creator_engine_validator/runner/gvisor_proxy_backend.py
validators/creator_engine_validator/runner/noop_backend.py
validators/creator_engine_validator/runner/openshell_backend.py
validators/creator_engine_validator/runner/os_native_backend.py
validators/creator_engine_validator/v3_cli.py
validators/creator_engine_validator/v3_installer.py
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
validators/tests/unit/test_redact.py
validators/tests/unit/test_run_assembly.py
validators/tests/unit/test_runner_backend.py
validators/tests/unit/test_v3_cli.py
validators/tests/unit/test_v3_installer.py
validators/tests/unit/test_version_boundary.py
validators/wheelhouse/SHA256SUMS
validators/wheelhouse/creator_engine_validator-0.2.0-py3-none-any.whl
```
