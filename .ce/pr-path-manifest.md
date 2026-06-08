# PR path manifest — site: v5 NVIDIA-ready redesign + archive v4

This file is the carrier for this PR's closed path manifest under
`docs/operations/PATH_MANIFEST_FIDELITY_PROTOCOL.md`. CI passes it to
`verify-path-manifest --base <PR base sha> --manifest .ce/pr-path-manifest.md`
and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set
below. The fidelity scan (`scan-path-manifest`) requires the declared count and
SHA256 to match the fenced block.

Scope: **SITE-ONLY, redesign.** Replace the live `docs/index.html` (v4
"Control-Room Violet" vocab-tidy) with the Operator-chosen **corrected Claude v5
"NVIDIA-ready" redesign** (durable source verbatim from
`.hermes/research/creator-engine-site-launch-20260607T053148Z/claude-v5-redesign-winner/index.html`,
SHA256 `f39afa2f…`). A sanctioned visual-identity evolution: adds a lime/`--spark`
accent alongside Control-Room Violet, a consumer "software factory" reframe, a
two-altitude descent, the Creator Console hero, and a "Built for security with
NVIDIA OpenShell" alignment band. Vocabulary stays on the canon
(Frame→Shape→Build→Review→Ship, Goal/Done-when/Budget/Change-type/Ready,
Outcome/Verdict/Next); honesty discipline preserved (OpenShell/RTX = forward
story, explicitly labeled "not shipped"; today Linux/macOS pre-release). PLUS the
standing website-archive: snapshot the outgoing v4 into
`site-archive/index-v4-vocab-canon.html` and update the `site-archive/README.md`
ledger (`site-archive/` is NOT served by GitHub Pages). **No code/schema/test/example change.**

- **base:** `e0cfbef6d2172a2edf963ba078873e0cb76eeb37`.
- **canonicalization:** `sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=4

AUTHORIZED_PATHS_SHA256=a296917ab22b7e7b586d5dca54c5adc5434596c7decee2f1a82e23c07da14485

```text
.ce/pr-path-manifest.md
docs/index.html
site-archive/README.md
site-archive/index-v4-vocab-canon.html
```
