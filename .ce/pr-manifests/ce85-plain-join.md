# PR path manifest — ce85-plain-join · onboard --apply plain-join for an already-CE repo

Per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`, the ce-ops#21 convention). CI runs:

    verify-path-manifest --base <PR base sha> --manifest-dir .ce/pr-manifests --head-ref ce85-plain-join

and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below (the carrier
lists itself); the repo-wide fidelity scan requires the declared count and SHA256 to match the fenced block.

Ratified:
Operator-ratified DESIGN + BUILD MANDATE in ce-ops#85 (2026-06-15) — plain-join path, Option A (auto-detect
already-CE). Built by a governed CE seat on base `431aeff` (#227); push/merge Operator-gated.

Base:
`431aeff` (`main` = #227, the 0.2.0 download-mirror republish).

The change (plain-join path for `onboard --apply`):
A new dev joining an ALREADY-CE repo (`github.mode == existing` + already-CE) is now a first-class
auto-detected **plain-join** (E2), distinct from brownfield *adoption* (NON-CE → E3, unchanged). Adds the
FAIL-CLOSED detector `repo_is_already_ce_governed` (repo reachable + CE workflow pinned digest + branch-
protection floor), routes already-CE through the gate and the `github_repo_create` leg to converge via the
idempotent verify/reconcile legs (workflow verified not overwritten; branch protection reconciled to ADD
missing CE checks while NEVER dropping existing ones), and surfaces the route at `--plan` for parity.
Genuine brownfield stays E3-deferred and mutates nothing.

Per-file purpose (the closed path-set — 10 paths):
- **`.ce/changelog/ce85-plain-join.md`** *(A)* — per-PR changelog fragment for the plain-join addition.
- **`.ce/pr-manifests/ce85-plain-join.md`** *(A)* — this carrier (self-inclusive).
- **`docs/contracts/brownfield-adoption.md`** *(M)* — cross-reference distinguishing brownfield adoption
  (E3) from plain-join (E2).
- **`docs/contracts/plain-join.md`** *(A)* — the new plain-join contract: detection, idempotent
  verify/reconcile legs, `--plan`/`--apply` parity.
- **`validators/creator_engine_validator/onboard_apply.py`** *(M)* — `repo_is_already_ce_governed`,
  `existing_branch_protection_contexts` driver method, and the plain-join `github_repo_create` /
  `github_workflow_install` / `github_branch_protection` leg branches.
- **`validators/creator_engine_validator/v3_cli.py`** *(M)* — `_onboard_apply_driver` seam + the apply
  gate routing (already-CE → plain-join; NOT already-CE → unchanged E3 refuse) + `--plan` parity surface.
- **`validators/tests/unit/test_onboard_apply.py`** *(M)* — plain-join converge / preserve-checks /
  idempotent / fail-closed tests; the brownfield-deferred test re-pointed to a NOT-already-CE repo.
- **`validators/tests/unit/test_v3_cli.py`** *(M)* — CLI plain-join routing + `--plan` parity tests.
- **`validators/wheelhouse/creator_engine_validator-0.2.0-py3-none-any.whl`** *(M)* — rebuilt 0.2.0 app
  wheel (source parity: `packaging_runtime.verify_wheel_matches_source` requires the committed wheel's
  `.py` bytes to equal source). The standard per-PR wheel-rebuild tax for any source change; `_version.py`
  is unchanged (its baked `BUILD_GIT_SHA` stays a valid HEAD-ancestor, so no re-bake is required).
- **`validators/wheelhouse/SHA256SUMS`** *(M)* — re-pinned the app-wheel line for the rebuilt wheel (the
  6 dependency-wheel lines are byte-unchanged).

Canonicalization:
`sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=10

AUTHORIZED_PATHS_SHA256=6b34e7614dda1125dbe3e8d1451ed43cac6031a6b76311a4711b8f877bda759e

```text
.ce/changelog/ce85-plain-join.md
.ce/pr-manifests/ce85-plain-join.md
docs/contracts/brownfield-adoption.md
docs/contracts/plain-join.md
validators/creator_engine_validator/onboard_apply.py
validators/creator_engine_validator/v3_cli.py
validators/tests/unit/test_onboard_apply.py
validators/tests/unit/test_v3_cli.py
validators/wheelhouse/SHA256SUMS
validators/wheelhouse/creator_engine_validator-0.2.0-py3-none-any.whl
```
