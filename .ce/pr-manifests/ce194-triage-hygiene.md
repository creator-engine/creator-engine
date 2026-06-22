# PR path manifest - ce194-triage-hygiene

Per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`, ce-ops#21 convention).
CI runs:

```bash
verify-path-manifest --base <PR base sha> --manifest-dir .ce/pr-manifests --head-ref ce194-triage-hygiene
```

and requires this PR's `base..HEAD` diff to equal exactly the authorized
path-set below. This carrier lists itself.

Base:
`67d5612` (`origin/main` at branch handoff).

- **Declared work class:** story

Scope:
ce-ops#194 triage-planner hygiene. The slice tightens `ce pickup triage`
candidate selection so non-leaf, closed/done, held/checkpoint, already-covered
by open PR, or lookup-ambiguous issues are not labeled as pickup-ready.

Per-file purpose:
- **`.ce/changelog/ce194-triage-hygiene.md`** *(A)* - changelog fragment.
- **`.ce/pr-manifests/ce194-triage-hygiene.md`** *(A)* - this closed path-set carrier.
- **`validators/creator_engine_validator/forge_triage.py`** *(M)* - candidate exclusion hygiene and open-PR lookup through the injectable `gh` seam.
- **`validators/tests/unit/test_forge_triage.py`** *(M)* - offline regression tests for the new exclusion paths.

Canonicalization:
`sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=4

AUTHORIZED_PATHS_SHA256=e714b756162a9f7f68b70c8b2557db8db89942ba5128dba5a3b8eee747a70048

```text
.ce/changelog/ce194-triage-hygiene.md
.ce/pr-manifests/ce194-triage-hygiene.md
validators/creator_engine_validator/forge_triage.py
validators/tests/unit/test_forge_triage.py
```
