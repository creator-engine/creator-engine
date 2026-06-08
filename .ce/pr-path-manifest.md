# PR path manifest — docs(v3): Scope-card vocabulary (2nd canon pass) + shaping-UX design + user guide

This file is the carrier for this PR's closed path manifest under
`docs/operations/PATH_MANIFEST_FIDELITY_PROTOCOL.md`. CI passes it to
`verify-path-manifest --base <PR base sha> --manifest .ce/pr-path-manifest.md`
and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set
below. The fidelity scan (`scan-path-manifest`) additionally requires the
declared count and SHA256 to match the fenced block.

Scope: **DOCS-ONLY**. (1) Extend the vocabulary canon with the 2nd user-facing
vocabulary — the **Scope-card field labels** (`Goal · Done-when · Budget ·
Change-type · Ready`) over the conserved `schemas/scope.schema.yaml` fields;
`docs/architecture/stage-vocabulary.md` is extended **in place** (H1 retitled to
"CE v3 — Vocabulary (canon)"; filename kept because G-6's `scope.md` /
`scope.schema.yaml` / `coordination.py` cite it by path — a rename would break
them). (2) Commit the **shaping-UX + chat→Scope trigger dial** design in-repo
(`docs/architecture/shaping-ux.md`) as the G-7 build-input. (3) Add a user-facing
**guide** (`docs/guide/understanding-ce.md`). Index pointers in
`docs/architecture/README.md`.

**No mechanical enum, no Scope schema, no G-6 contract changed** — the Scope-card
labels are a presentation skin; the schema field-names (`intent` /
`acceptance_criteria` / `appetite` / `mutation_class`) and the
`definition_of_ready` predicate are conserved verbatim. No v1 change; no check /
schema / runtime / roadmap change.

Standing requirements honored: docs-terminology canon (docs = manual hygiene;
Operator/Controller canon; reconcile-note + pointer, not blanket-rename; redaction
discipline on the curated design doc — design substance + dated citations in,
instance/provenance out); v1↔v3 coexistence (ADDITIVE; **v1 deleted = ∅**); the new
docs carry no implementation-name residue. No check-surface change (stays **47**);
`version_boundary` / `v3_naming_hygiene` untouched (no v3 code); `check-examples`
stays **78/0** (docs-only). Deferred follow-ons (named): the G-7 product-surface
build (which cites these docs); the cockpit sketch; the ◆ Completion-Report field
vocabulary; a docs-scoped CI terminology guard.

- **base:** `dee9c9b9abc9f851d96545eafdb8e8466f67271c`.
- **canonicalization:** `sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=5

AUTHORIZED_PATHS_SHA256=a4cbabe6c1132f0fe07f3158d6261fdccf65fa2ca93a39bd585dec4c0af85744

```text
.ce/pr-path-manifest.md
docs/architecture/README.md
docs/architecture/shaping-ux.md
docs/architecture/stage-vocabulary.md
docs/guide/understanding-ce.md
```
