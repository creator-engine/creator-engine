# PR path manifest — L4-brain · Add wikilink graph recall and launch hydration support

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce-brain-l4-recall` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=8

AUTHORIZED_PATHS_SHA256=731ba063afc9a522d5871678fcff5574556e90a65830b8f2a0b5d2906eee7142

```text
.ce/changelog/ce-brain-l4-recall.md
.ce/pr-manifests/ce-brain-l4-recall.md
validators/creator_engine_validator/brain_eval.py
validators/creator_engine_validator/brain_recall_surface.py
validators/creator_engine_validator/brain_sqlite_vec.py
validators/tests/unit/test_brain_eval.py
validators/tests/unit/test_brain_recall_surface.py
validators/tests/unit/test_brain_sqlite_vec.py
```
