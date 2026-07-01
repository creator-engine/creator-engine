# PR path manifest - ce-triage-autolabel - ce-ops triage advisory autolabels

Per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`, ce-ops#21 convention).
CI runs:

    verify-path-manifest --base <PR base sha> --manifest-dir .ce/pr-manifests --head-ref ce-triage-autolabel

and requires this PR's `base..HEAD` diff to equal exactly the authorized path
set below. This carrier lists itself.

- **Declared work class:** story

The changes:
- Add apply-gated advisory classification label synchronization for ce-ops issue triage.
- Manage only deterministic `wc:` and `triage:` labels, preserving all other labels.
- Report dry-run label deltas, create missing managed labels in apply mode, and isolate per-issue label failures.
- Add focused unit coverage for delta planning, dry-run non-mutation, idempotent no-op behavior, and failure isolation.

Per-file purpose:
- **`.ce/changelog/ce-triage-autolabel.md`** *(A)* - changelog fragment for advisory triage autolabeling.
- **`.ce/pr-manifests/ce-triage-autolabel.md`** *(A)* - this carrier.
- **`validators/creator_engine_validator/ce_ops_triage_queue.py`** *(M)* - plan/report/apply managed advisory classification labels.
- **`validators/tests/unit/test_ce_ops_triage_queue.py`** *(M)* - focused coverage for the new label behavior.

Canonicalization:
`sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=4

AUTHORIZED_PATHS_SHA256=c20c07688eac1821a448b96e270cc8f76b0e2f3882b268ca6e2814d5e12fec44

```text
.ce/changelog/ce-triage-autolabel.md
.ce/pr-manifests/ce-triage-autolabel.md
validators/creator_engine_validator/ce_ops_triage_queue.py
validators/tests/unit/test_ce_ops_triage_queue.py
```
