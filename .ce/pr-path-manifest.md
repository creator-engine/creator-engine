# PR path manifest — site: v4 vocabulary-consistency tidy + archive v3

This file is the carrier for this PR's closed path manifest under
`docs/operations/PATH_MANIFEST_FIDELITY_PROTOCOL.md`. CI passes it to
`verify-path-manifest --base <PR base sha> --manifest .ce/pr-path-manifest.md`
and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set
below. The fidelity scan (`scan-path-manifest`) requires the declared count and
SHA256 to match the fenced block.

Scope: **SITE-ONLY, copy-level**. A light vocabulary-consistency tidy of the live
`docs/index.html` (v3→v4) to the CE canon (`docs/architecture/stage-vocabulary.md`
+ `docs/architecture/pilot-uiux-model.md`): stage phases Frame→Shape→Build→Review→Ship,
Scope-card labels (Goal/Done-when/Budget/Change-type/Ready), Completion-Report labels
(Outcome/Verdict/Next), "mutation class"→"change type" (user-facing skin; `mutation_class`
conserved), and correcting the stale "Visible Controller seat" to the v3 product framing.
NOT a redesign. PLUS the standing website-archive: snapshot the outgoing v3 into
`site-archive/index-v3-fomo.html` and update the `site-archive/README.md` ledger.
`site-archive/` is NOT served by GitHub Pages. **No code/schema/test/example change.**

- **base:** `280e92735043702019ba29c46d8e50a6a3526af6`.
- **canonicalization:** `sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=4

AUTHORIZED_PATHS_SHA256=751821497cb1d574f17f3f6d241541585c0beb492b940ab59462f0241d8dc2e0

```text
.ce/pr-path-manifest.md
docs/index.html
site-archive/README.md
site-archive/index-v3-fomo.html
```
