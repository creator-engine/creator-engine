# PR path manifest — ce71-userlevel-apply · ce-ops#71 user-level governance-only `--apply` (G71.2 tier-aware planner) over the #225+#223 stack

Per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`, the ce-ops#21 convention). CI runs:

```bash
verify-path-manifest --base <PR base sha> --manifest-dir .ce/pr-manifests --head-ref ce71-userlevel-apply
```

and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below
(the carrier lists itself); the repo-wide fidelity scan requires the declared count and
SHA256 to match the fenced block.

## The stack (read this first)

This branch is a **STAGED INTEGRATION STACK**, built so the morning merge train is clean:

1. **#225 `ce43-seat-reaper`** (base of this branch).
2. **#223 `ce34-rs-resolver-seam`** merged over it (`integration base` commit) — `_versions.py`
   and `v3_cli.py` auto-merged clean; `test_version_boundary.py` resolved **additively**
   (combined `V3_RUNTIME` count `38 → 40` (ce43) `→ 41` (ce34)); the wheelhouse resolved by
   **rebuilding the app wheel from the combined source**.
3. **#71 G71.2** tier-aware planner committed on top.

The path-set below is `base..HEAD` against **`main` = `20c460c`** (current tip, before #225/#223
land), so it **legitimately includes the stacked #225 + #223 files + their two carriers** alongside
G71.2's own. Once the merge train lands #225 then #223 into `main`, this branch re-grounds onto the
new base and the path-set reduces to **G71.2's own paths + this carrier** (a mechanical base-only
re-ground under `ce-base-only-refresh-microauth`); the orchestrator re-pins at that point. The
post-hoc fidelity scan only requires this carrier's COUNT/SHA256 to match its own fenced block.

## What G71.2 changes (the only NEW work in this PR beyond the stack)

Per the ratified direction paper `ce-user-level-apply-and-substrate-direction-20260613.md`
§A.1–A.3 (the gVisor→opt-in demotion), the **pure installer planner** becomes tier-aware:

- `TIER_DEPS = {0:(git,python,uv), 1:(git,python,uv + probe-only sandbox primitives),
  2:(git,python,uv,runsc,proxy)}`; `_SUDO_TOOLS` shrinks to `{runsc, proxy}` — **git/python/uv are
  user-level ALWAYS** (the §A.1 intended change).
- `plan_dependencies(tier, probe)` selects `TIER_DEPS[tier]` (polymorphic: an int tier, or an
  explicit dep-name iterable for the pre-tier flat callers — `onboard_apply.py`/`v3_cli.py` are
  untouched and keep working). **Default `tier = 2`** preserves today's behavior.
- `InstallPlan.needs_sudo` is True only when a Tier-2 plan is selected (it falls out of the shrunk
  `_SUDO_TOOLS`). `InstallerProfile` gains `isolation_tier` (default 2); `build_install_plan(tier=2)`
  threads it and emits the "gVisor runsc + egress proxy" deferred seam **tier-conditionally (Tier 2
  only)**. Tier-1 sandbox primitives are **PROBE-ONLY, never auto-sudo** (keeps Tier 1 zero-root).
- The §A.3 three-tier fail-closed proof-walk: Tier 0/1 **converge** with `sudo_grant: []` (no
  privileged installs); Tier 2 with `sudo_grant: []` is **uncovered → refuses** — through the SAME
  `sudo_grant_diff` path, no new fail-closed machinery.

**Deferred (NOT in this scope):** G71.1 schema (`host.sandbox_tier` + re-sign), G71.3 CLI seam
(`--sandbox=`, `solo-pilot→tier1` default-flip, AppArmor one-time grant), G71.4 Tier-1
`RunnerBackend` (srt) + `runtime-policy` enum + `V3_RUNTIME` module. This PR touches **no**
`v3_cli.py`/`onboard_apply.py`/schema *installer* semantics (the `v3_cli.py` change in the diff is
the stacked #223+#225 work, not G71.2) and adds **+0 checks / +0 V3_RUNTIME modules**.

## Per-file purpose (the closed path-set — 25 paths)

G71.2 (new in this PR):
- **`.ce/pr-manifests/ce71-userlevel-apply.md`** *(A)* — this carrier (self-inclusive).
- **`validators/creator_engine_validator/v3_installer.py`** *(M)* — `TIER_DEPS`/`DEFAULT_ISOLATION_TIER`;
  `_SUDO_TOOLS` shrink to `{runsc,proxy}`; tier-aware `plan_dependencies`; `InstallerProfile.isolation_tier`
  + `build_profile(isolation_tier=…)`; tier-conditional `build_install_plan(tier=…)` deferred seam.
- **`validators/tests/unit/test_v3_installer.py`** *(M)* — the §A.3 three-tier fail-closed walk
  (Tier 0/1 converge with `sudo_grant:[]`; Tier 2 refuses) + tier-deps shape, default-tier-preserves-today,
  back-compat iterable, unknown-tier refusal, tier-conditional seam, profile isolation_tier; the existing
  sudo-drift test re-scoped to the user-level reality (only runsc/proxy privileged).

Integration-base (rebuilt from the COMBINED source for this stack):
- **`validators/creator_engine_validator/_version.py`** *(M)* — re-baked `BUILD_GIT_SHA` to the
  stack's merge-parent HEAD (`packaging_runtime.verify_wheel_matches_source` byte-parity).
- **`validators/creator_engine_validator/_versions.py`** *(M)* — `V3_RUNTIME` gains `authority_resolver`
  (#223) + `seat_reaper`/`reaper_executors` (#225): `38 → 41` (auto-merged additively).
- **`validators/tests/unit/test_version_boundary.py`** *(M)* — combined `V3_RUNTIME == 41` (both
  comment trails kept) + #225's classify/§10.14 AST boundary tests.
- **`validators/wheelhouse/creator_engine_validator-0.2.0-py3-none-any.whl`** *(M)* — the app wheel
  **rebuilt from the final combined G71.2 source** (sha256 `c6f1d4bd…`); `validators/build` cleaned
  before staging ([[ce-wheel-rebuild-build-leak-footgun]]); `verify-wheel-matches-source` byte-clean.
- **`validators/wheelhouse/SHA256SUMS`** *(M)* — re-pinned app-wheel digest (the 6 dependency wheels
  byte-unchanged).

Stacked #223 `ce34-rs-resolver-seam` (AuthorityResolver seam — carried through, unchanged):
- **`.ce/pr-manifests/ce34-rs-resolver-seam.md`** *(A)*, **`validators/creator_engine_validator/authority_resolver.py`** *(A)*,
  **`validators/creator_engine_validator/forge/plan_approval.py`** *(M)*, **`validators/tests/unit/test_authority_resolver.py`** *(A)*.

Stacked #225 `ce43-seat-reaper` (retirement reaper — carried through, unchanged):
- **`.ce/pr-manifests/ce43-seat-reaper.md`** *(A)*, **`docs/operations/SEAT_REAPER_PROTOCOL.md`** *(A)*,
  **`schemas/dispatch-record.schema.yaml`** *(M)*, **`validators/creator_engine_validator/reaper_executors.py`** *(A)*,
  **`validators/creator_engine_validator/seat_reaper.py`** *(A)*,
  **`validators/tests/integration/test_pco_allocator_cli.py`** *(M)*,
  **`validators/tests/unit/test_pane_registry.py`** *(M)*, **`validators/tests/unit/test_pco_allocator.py`** *(M)*,
  **`validators/tests/unit/test_seat_reaper.py`** *(A)*, **`validators/tests/unit/test_transcript_archive.py`** *(M)*,
  **`validators/tests/unit/test_v3_seat_bridge.py`** *(M)*.

Shared by both stacked PRs (carried through):
- **`validators/creator_engine_validator/v3_cli.py`** *(M)* — #225's `cev3 reap …` + #223's resolver
  CLI wiring (auto-merged clean; **no G71.2 installer change here**).
- **`validators/tests/unit/test_v3_cli.py`** *(M)* — #225's `reap` CLI tests.

Posture: the seat committed LOCALLY only — NO `git push`, NO `gh pr`, NO merge. The orchestrator
stages; the Operator merges (morning session).

Canonicalization:
`sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=25

AUTHORIZED_PATHS_SHA256=ef9fbeae24508d137863eb0c689bace9edfd2b87a66c597e9ba8bb4d0d620f8e

```text
.ce/pr-manifests/ce34-rs-resolver-seam.md
.ce/pr-manifests/ce43-seat-reaper.md
.ce/pr-manifests/ce71-userlevel-apply.md
docs/operations/SEAT_REAPER_PROTOCOL.md
schemas/dispatch-record.schema.yaml
validators/creator_engine_validator/_version.py
validators/creator_engine_validator/_versions.py
validators/creator_engine_validator/authority_resolver.py
validators/creator_engine_validator/forge/plan_approval.py
validators/creator_engine_validator/reaper_executors.py
validators/creator_engine_validator/seat_reaper.py
validators/creator_engine_validator/v3_cli.py
validators/creator_engine_validator/v3_installer.py
validators/tests/integration/test_pco_allocator_cli.py
validators/tests/unit/test_authority_resolver.py
validators/tests/unit/test_pane_registry.py
validators/tests/unit/test_pco_allocator.py
validators/tests/unit/test_seat_reaper.py
validators/tests/unit/test_transcript_archive.py
validators/tests/unit/test_v3_cli.py
validators/tests/unit/test_v3_installer.py
validators/tests/unit/test_v3_seat_bridge.py
validators/tests/unit/test_version_boundary.py
validators/wheelhouse/SHA256SUMS
validators/wheelhouse/creator_engine_validator-0.2.0-py3-none-any.whl
```
