# PR path manifest - ce196-queue-hygiene-completeness

Per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`, ce-ops#21 convention).
CI runs:

```bash
verify-path-manifest --base <PR base sha> --manifest-dir .ce/pr-manifests --head-ref ce196-queue-hygiene-completeness
```

and requires this PR's `base..HEAD` diff to equal exactly the authorized
path-set below. This carrier lists itself.

Base:
`dcb67181` (`origin/main` at branch handoff).

- **Declared work class:** story

Scope:
ce-ops#196 triage-planner queue-hygiene completeness (follow-up to ce-ops#194).
The slice extends `ce pickup triage` candidate exclusion so done-but-still-open
(merged/closed-as-done linked PR), held (AWAITING-OPERATOR / ⏸️ body or comment
marker), and meta/debug issues are not labeled as pickup-ready, failing closed
on ambiguous or incomplete linked-PR and comment lookups.

Per-file purpose:
- **`.ce/changelog/ce196-queue-hygiene-completeness.md`** *(A)* - changelog fragment.
- **`.ce/pr-manifests/ce196-queue-hygiene-completeness.md`** *(A)* - this closed path-set carrier.
- **`validators/creator_engine_validator/forge_triage.py`** *(M)* - done/held/meta candidate exclusion and linked-PR / comment hold-marker lookups through the injectable `gh` seam.
- **`validators/tests/unit/test_forge_triage.py`** *(M)* - offline regression tests for the new exclusion + fail-closed paths.

Canonicalization:
`sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=4

AUTHORIZED_PATHS_SHA256=5a332dad9ecaf79a1b0261d2aabbf2e42c82a7716b3a4b11f125c993eab6e878

```text
.ce/changelog/ce196-queue-hygiene-completeness.md
.ce/pr-manifests/ce196-queue-hygiene-completeness.md
validators/creator_engine_validator/forge_triage.py
validators/tests/unit/test_forge_triage.py
```
