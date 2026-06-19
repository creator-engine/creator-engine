# PR path manifest - ce120-wave3-reviewer-triage-wiring

Per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`, ce-ops#21 convention). CI runs:

```bash
verify-path-manifest --base <PR base sha> --manifest-dir .ce/pr-manifests --head-ref ce120-wave3-reviewer-triage-wiring
```

and requires this PR's `base..HEAD` diff to equal exactly the authorized
path-set below. The carrier lists itself. The repo-wide `path_manifest_fidelity`
scan requires the declared count and SHA256 to match the fenced block.

Ratified gate:
CE Morning-Shift WAVE 3 downstream for ce-ops#120 reviewer triage. Commit-local
only; no push. Build the availability + eligibility triage wiring per the
ratified plan, preserving the plan-only/non-authority boundary.

Research sidecar:
The requested ce-ops#39 current merge-throughput prior-art note is written at
`.ce/state/research/DESIGN_ce39_merge_throughput_20260619T032314Z.md`.
Wave 3 addendum folded ce-ops#131 merger-agent analysis into that note and
forced it into this local commit despite `.ce/state/` normally being ignored.

Per-file purpose (closed path-set - 19 paths):
- **`.ce/changelog/ce120-wave3-reviewer-triage-wiring.md`** *(A)* - changelog fragment.
- **`.ce/pr-manifests/ce120-wave3-reviewer-triage-wiring.md`** *(A)* - this carrier.
- **`.ce/state/research/DESIGN_ce39_merge_throughput_20260619T032314Z.md`** *(A)* - ce-ops#39 current prior-art note plus ce-ops#131 merger-agent addendum.
- **`docs/operations/REVIEWER_TRIAGE.md`** *(M)* - documents the advisory `triage_results` routing view.
- **`examples/reviewer-triage/*.yaml`** *(M, 10 files)* - examples include schema-valid combined triage rows.
- **`schemas/reviewer-triage-decision.schema.yaml`** *(M)* - adds required `triage_results` contract.
- **`validators/creator_engine_validator/reviewer_triage.py`** *(M)* - emits combined per-candidate triage results.
- **`validators/tests/unit/test_reviewer_triage_plan.py`** *(M)* - TDD coverage for selected/selectable/ineligible/unavailable routing.
- **`validators/wheelhouse/SHA256SUMS`** *(M)* - app-wheel digest re-pinned after rebuilding the validator wheel.
- **`validators/wheelhouse/creator_engine_validator-0.2.0-py3-none-any.whl`** *(M)* - rebuilt app wheel from this branch source so `reviewer_triage.py` is packaged.

Canonicalization:
`sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=19

AUTHORIZED_PATHS_SHA256=89b2f225ddb383d946314f49d5eb5cce3adad9da4364299c1fdf6b3889756c4b

```text
.ce/changelog/ce120-wave3-reviewer-triage-wiring.md
.ce/pr-manifests/ce120-wave3-reviewer-triage-wiring.md
.ce/state/research/DESIGN_ce39_merge_throughput_20260619T032314Z.md
docs/operations/REVIEWER_TRIAGE.md
examples/reviewer-triage/eligible.yaml
examples/reviewer-triage/missing-access.yaml
examples/reviewer-triage/no-available-reviewer.yaml
examples/reviewer-triage/privileged-requires-source.yaml
examples/reviewer-triage/same-controller-tier1-reject.yaml
examples/reviewer-triage/same-host-tier2-valid.yaml
examples/reviewer-triage/same-human-reject.yaml
examples/reviewer-triage/tier4-release-valid.yaml
examples/reviewer-triage/uncontained-reject.yaml
examples/reviewer-triage/unresolved-identity-reject.yaml
schemas/reviewer-triage-decision.schema.yaml
validators/creator_engine_validator/reviewer_triage.py
validators/tests/unit/test_reviewer_triage_plan.py
validators/wheelhouse/SHA256SUMS
validators/wheelhouse/creator_engine_validator-0.2.0-py3-none-any.whl
```
