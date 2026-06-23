# PR path manifest - ce197-onboard-orchestrator - ce-ops#197 `ce onboard` orchestrator (PR-4 + PR-5)

Per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`, the ce-ops#21 convention).
CI runs:

    verify-path-manifest --base <PR base sha> --manifest-dir .ce/pr-manifests --head-ref ce197-onboard-orchestrator

and requires this PR's `base..HEAD` diff to equal exactly the authorized path
set below. This carrier lists itself.

Ratified:
Controller brief for ce-ops#197 PR-4 + PR-5 — build the central onboarding unit
for `ce onboard`, faithful to the revised 3-mode governed-install design
(`.ce/state/research/DESIGN_197_CE_ONBOARD.md` §A install modes, §B governed
rail, §1.1 six phases). PR-4 (doctor probes + `brain_init` library entry) is
combined with PR-5 (the orchestrator) per the design's "PR-4 may merge into
PR-5" allowance — PR-4's `brain_init` library function is a hard dependency of
PR-5's bootstrap leg.

The changes:
- NEW `ce_onboard.py` + `ce onboard` subparser: sequences the six phases
  (doctor → install → verify-install → fix-path → bootstrap → launch) as a thin
  composition over existing surfaces; injectable legs; idempotent + resumable +
  gracefully degrading; `--install-mode {agent,guided,hybrid,print,skip}` with
  §A.5 auto-selection (hybrid-when-agent-present, never print); `--emit-manifest`
  (the §A.1 machine-readable phase manifest carrying §B.2 consequence-class +
  reversibility); each `--json` phase record carries the §B.3 audit fields; the
  first launch drives exactly ONE `ce launch` + asserts a single live controller.
- `doctor_runtime` onboard phase-1 probes (`probe_low_tmpdir`, `probe_path_gap`),
  surfaced under `payload["onboard_probes"]` (advisory-only).
- `ce_cli.brain_init(state_root)` library entry (genesis ledger bootstrap),
  reused by the `ce brain init` handler and the orchestrator's bootstrap leg.
- `_versions.py` classifies `ce_onboard` as v1 (count 27 → 28).
- README documents `ce onboard`; docs-reconciliation + version-boundary guards
  updated to match the as-built inventory.

Per-file purpose (the closed path-set - 12 paths; `(A)` add, `(M)` modify):
- **`.ce/changelog/ce197-onboard-orchestrator.md`** *(A)* - changelog fragment.
- **`.ce/pr-manifests/ce197-onboard-orchestrator.md`** *(A)* - this carrier.
- **`README.md`** *(M)* - document `ce onboard` in the v1 command inventory.
- **`validators/creator_engine_validator/_versions.py`** *(M)* - classify `ce_onboard` as v1.
- **`validators/creator_engine_validator/ce_cli.py`** *(M)* - `onboard` parser + dispatch; extract `brain_init` library entry.
- **`validators/creator_engine_validator/ce_onboard.py`** *(A)* - the six-phase first-run orchestrator + `--emit-manifest`.
- **`validators/creator_engine_validator/doctor_runtime.py`** *(M)* - onboard phase-1 probes (low-TMPDIR + PATH-gap).
- **`validators/tests/unit/test_ce_onboard.py`** *(A)* - orchestrator TDD (happy/degradation/idempotent/refuse/single-controller/manifest).
- **`validators/tests/unit/test_ce_onboard_cli.py`** *(A)* - `ce onboard` CLI surface TDD.
- **`validators/tests/unit/test_doctor_onboard_probes.py`** *(A)* - PR-4 doctor probes + `brain_init` library TDD.
- **`validators/tests/unit/test_v1_docs_reconciliation.py`** *(M)* - expected inventory includes `onboard`.
- **`validators/tests/unit/test_version_boundary.py`** *(M)* - v1 runtime count reflects `ce_onboard`.

Canonicalization:
`sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=12

AUTHORIZED_PATHS_SHA256=bb814c4d4ce3f06a542ad04317cb012c983cf3415ff6fe0e52a06b643d3c24a3

```text
.ce/changelog/ce197-onboard-orchestrator.md
.ce/pr-manifests/ce197-onboard-orchestrator.md
README.md
validators/creator_engine_validator/_versions.py
validators/creator_engine_validator/ce_cli.py
validators/creator_engine_validator/ce_onboard.py
validators/creator_engine_validator/doctor_runtime.py
validators/tests/unit/test_ce_onboard.py
validators/tests/unit/test_ce_onboard_cli.py
validators/tests/unit/test_doctor_onboard_probes.py
validators/tests/unit/test_v1_docs_reconciliation.py
validators/tests/unit/test_version_boundary.py
```
