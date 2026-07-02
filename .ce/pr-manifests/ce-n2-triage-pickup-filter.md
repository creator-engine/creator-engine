# PR path manifest - ce-n2-triage-pickup-filter

Per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`, ce-ops#21 convention).
CI runs:

```bash
verify-path-manifest --base <PR base sha> --manifest-dir .ce/pr-manifests --head-ref ce-n2-triage-pickup-filter --require-carrier
```

and requires this PR's `base..HEAD` diff to equal exactly the authorized
path-set below. This carrier lists itself.

- **Declared work class:** feature

Scope:
Adds an advisory N2 pickup filter to the existing ce-ops triage queue JSON
payload. The filter emits machine-readable ready-to-dispatch candidates from
existing triage classification/readiness data while excluding blocked,
assigned, and in-progress issues.

Non-authority posture:
The pickup filter is advisory only. It reuses the existing non-authority
statement and does not ratify, approve, review, merge, authorize dispatch,
label-mutate, open PRs, or block CI.

Per-file purpose:
- **`.ce/changelog/ce-n2-triage-pickup-filter.md`** *(A)* - changelog fragment.
- **`.ce/pr-manifests/ce-n2-triage-pickup-filter.md`** *(A)* - this closed path-set carrier.
- **`validators/creator_engine_validator/ce_ops_triage_queue.py`** *(M)* - pure pickup-candidate projection and advisory scan payload wiring.
- **`validators/tests/unit/test_ce_ops_triage_queue.py`** *(M)* - pickup-filter coverage for inclusion, exclusion, ordering, dry-run/no-mutation, and empty output.

Canonicalization:
`sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=4

AUTHORIZED_PATHS_SHA256=cdd8580354f2b3b030d37fac58e0d5d0ba6fced3ef9639ee569f87cc887091e1

```text
.ce/changelog/ce-n2-triage-pickup-filter.md
.ce/pr-manifests/ce-n2-triage-pickup-filter.md
validators/creator_engine_validator/ce_ops_triage_queue.py
validators/tests/unit/test_ce_ops_triage_queue.py
```
