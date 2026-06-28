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
- **`.ce/reference/schemas.generated.md`** *(M)* - regenerated schema reference including the new press-merge-bundle schema (schema_reference_autogen_sync guard).
- **`docs/operations/PRESS_MERGE_BUNDLE.md`** *(A)* - design note and prose contract for the proposed press-merge bundle.
- **`validators/creator_engine_validator/_versions.py`** *(M)* - add baselined shared->v1 allowlist entry for press_merge_bundle->fanin_runtime (version_boundary guard).
- **`validators/creator_engine_validator/press_merge_bundle.py`** *(A)* - CLI-agnostic aggregator and Markdown renderer.
- **`validators/creator_engine_validator/public_docs_confidentiality.py`** *(M)* - add PRESS_MERGE_BUNDLE.md to KNOWN_OPERATIONS_EXCEPTIONS ratchet (public_docs_confidentiality guard).
- **`validators/creator_engine_validator/schemas/press-merge-bundle.schema.yaml`** *(A)* - proposed schema, exposed through the repo-root `schemas/` symlink.
- **`validators/tests/unit/test_press_merge_bundle.py`** *(A)* - focused unit tests for the aggregator and renderer entrypoints.
- **`validators/tests/unit/test_version_boundary.py`** *(M)* - update allowlist size assertion from 4 to 5 and update the exact-set test to include the new W3 edge.

Canonicalization:
`sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=10

AUTHORIZED_PATHS_SHA256=67f9b75f20ffb63a5256f25ae67344c08220c3999ff017d221aecce630b20d6a

```text
.ce/changelog/w3-evidence-bundle-press-merge.md
.ce/pr-manifests/w3-evidence-bundle-press-merge.md
.ce/reference/schemas.generated.md
docs/operations/PRESS_MERGE_BUNDLE.md
validators/creator_engine_validator/_versions.py
validators/creator_engine_validator/press_merge_bundle.py
validators/creator_engine_validator/public_docs_confidentiality.py
validators/creator_engine_validator/schemas/press-merge-bundle.schema.yaml
validators/tests/unit/test_press_merge_bundle.py
validators/tests/unit/test_version_boundary.py
```
