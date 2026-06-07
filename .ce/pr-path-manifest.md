# PR path manifest — docs(v3): stage-vocabulary canon (Frame → Shape → Build → Review → Ship) + dual-mapping docs

This file is the carrier for this PR's closed path manifest under
`docs/operations/PATH_MANIFEST_FIDELITY_PROTOCOL.md`. CI passes it to
`verify-path-manifest --base <PR base sha> --manifest .ce/pr-path-manifest.md`
and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set
below. The fidelity scan (`scan-path-manifest`) additionally requires the
declared count and SHA256 to match the fenced block.

Scope: **DOCS-ONLY** canon decision (GH #159). Record the user-facing, fractal
cognitive-phase vocabulary **Frame → Shape → Build → Review → Ship** layered over
the **conserved** mechanical state machine, and add the dual-mapping docs
(user-facing phase ↔ mechanical state ↔ BMAD phase) plus the fractal/altitude
framing. A NEW canon doc `docs/architecture/stage-vocabulary.md` (the authority +
the mapping table + the conserved-machine dig-in layer), a reconcile-note + pointer
into `docs/architecture/pilot-uiux-model.md` (the user-facing surface where the
vocabulary shows — line-11 prose + the illustrative TUI stage labels), and an index
pointer in `docs/architecture/README.md`.

**No mechanical enum is renamed or removed** — the spec-lifecycle, container-phase,
run-outcome, and mutation-class enums are conserved verbatim. No v1 change; no
check / schema / runtime / roadmap change.

Standing requirements honored: docs-terminology canon (docs-canon = manual hygiene;
Operator/Controller canon; reconcile-note + pointer, not a blanket-rename of the
reference doc); v1↔v3 coexistence (ADDITIVE; **v1 deleted = ∅** — no v1 module
touched); the new canon doc carries no implementation-name residue. No check-surface
change (stays **46**); `version_boundary` / `v3_naming_hygiene` untouched (no v3
code); `check-examples` stays **78/0** (docs-only → no example churn). Deferred
follow-ons (named): a docs-scoped CI stage-vocabulary terminology guard (separately
grounded); G-7 surfacing of the canon (status line · ◆ CE Completion Report · board);
the one-line G-6 prompt amendment to cite this canon doc.

- **base:** `ed536e0c24e1728bb86590b0442220296d3a0bcd`.
- **canonicalization:** `sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=4

AUTHORIZED_PATHS_SHA256=0ede0cb7593542f55317620a84b10c28eb3d06a5405fac0da6ded74a5d2598ce

```text
.ce/pr-path-manifest.md
docs/architecture/README.md
docs/architecture/pilot-uiux-model.md
docs/architecture/stage-vocabulary.md
```
