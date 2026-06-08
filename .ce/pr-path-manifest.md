# PR path manifest — docs(v3): Completion-Report vocabulary (3rd canon pass) + cockpit sketch + pilot-uiux reconcile

This file is the carrier for this PR's closed path manifest under
`docs/operations/PATH_MANIFEST_FIDELITY_PROTOCOL.md`. CI passes it to
`verify-path-manifest --base <PR base sha> --manifest .ce/pr-path-manifest.md`
and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set
below. The fidelity scan (`scan-path-manifest`) additionally requires the
declared count and SHA256 to match the fenced block.

Scope: **DOCS-ONLY**. (1) Add the 3rd user-facing vocabulary — the **◆ CE
Completion Report** fields (`Outcome` + plain value renderings · **Verdict** [was
`determination`] · `Next` · `Artifacts`/`Inspect`) over the conserved `outcome`
enum + grading signals — to the vocabulary canon (`docs/architecture/stage-vocabulary.md`).
(2) Reconcile the `docs/architecture/pilot-uiux-model.md` mockup to all three
locked vocabularies (stage / Scope-card / Completion-Report; incl. the Scope-card
line #163 didn't touch). (3) Commit the **cockpit sketch**
(`docs/architecture/cockpit.md`, post-pilot graduation). Index pointers in
`docs/architecture/README.md`.

**No mechanical enum, no Scope schema, no G-6 contract changed** — the
Completion-Report labels are a presentation skin; the `outcome` enum
(`runtime-evidence.schema.yaml:247`) and the grading signals are conserved verbatim.
No v1 change; no check / schema / runtime / roadmap change.

Standing requirements honored: docs-terminology canon (manual hygiene;
Operator/Controller; reconcile-note + pointer; redaction discipline on the cockpit
doc); v1↔v3 coexistence (ADDITIVE; **v1 deleted = ∅**); no implementation-name
residue. No check-surface change (stays **47**); `version_boundary` /
`v3_naming_hygiene` untouched (no v3 code); `check-examples` stays **78/0**
(docs-only). **Rebased onto G-7.0 (#164, `3cff507`)** per the concurrent-PR
discipline — content-disjoint from that slice; only the shared carrier was resolved.
Deferred follow-ons (named): the G-7 product-surface build (cites these docs); the
cockpit build; CEO mode; the Skill axis (all post-pilot).

- **base:** `3cff5072805d0a79da5054d749ba9e1e12c30fd4`.
- **canonicalization:** `sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=5

AUTHORIZED_PATHS_SHA256=0884e6a7a976a268ad961996577cad04d54aab6d281235ff836f653f7a280abf

```text
.ce/pr-path-manifest.md
docs/architecture/README.md
docs/architecture/cockpit.md
docs/architecture/pilot-uiux-model.md
docs/architecture/stage-vocabulary.md
```
