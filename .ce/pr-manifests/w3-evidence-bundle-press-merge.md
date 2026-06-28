# PR path manifest - w3-evidence-bundle-press-merge

Per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`, ce-ops#21 convention).
This is the closed path set for W3 evidence-bundle press-merge.

- **Declared work class:** feature

Schema decision:
Add proposed `schemas/press-merge-bundle.schema.yaml` rather than reusing or
extending `evidence-fan-in-packet`. Rationale: press-merge is PR-keyed and needs
first-class diff, test/CI, review, and computer-use sections; forcing those into
the generic fan-in packet `evidence[]` shape would obscure the ratification
surface W1/W2 need. The new schema mirrors fan-in invariants (`has_authority:
false`, `source_ratification`, ref+sha evidence, deterministic `content_hash`)
and is proposed, not frozen.

Per-file purpose:
- **`.ce/changelog/w3-evidence-bundle-press-merge.md`** *(A)* - changelog fragment.
- **`.ce/pr-manifests/w3-evidence-bundle-press-merge.md`** *(A)* - this closed path-set carrier.
- **`docs/operations/PRESS_MERGE_BUNDLE.md`** *(A)* - design note and prose contract for the proposed press-merge bundle.
- **`validators/creator_engine_validator/press_merge_bundle.py`** *(A)* - CLI-agnostic aggregator and Markdown renderer.
- **`validators/creator_engine_validator/schemas/press-merge-bundle.schema.yaml`** *(A)* - proposed schema, exposed through the repo-root `schemas/` symlink.
- **`validators/tests/unit/test_press_merge_bundle.py`** *(A)* - focused unit tests for the aggregator and renderer entrypoints.

Canonicalization:
`sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=6

AUTHORIZED_PATHS_SHA256=f63e71f725cbb0c1cd8e93ef197d42c7414c2be6f29299873e2cc8855884073b

```text
.ce/changelog/w3-evidence-bundle-press-merge.md
.ce/pr-manifests/w3-evidence-bundle-press-merge.md
docs/operations/PRESS_MERGE_BUNDLE.md
validators/creator_engine_validator/press_merge_bundle.py
validators/creator_engine_validator/schemas/press-merge-bundle.schema.yaml
validators/tests/unit/test_press_merge_bundle.py
```
