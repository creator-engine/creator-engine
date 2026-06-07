# PR path manifest — docs: coexistence amendments (design §5)

This file is the carrier for this PR's closed path manifest under
`docs/operations/PATH_MANIFEST_FIDELITY_PROTOCOL.md`. CI passes it to
`verify-path-manifest --base <PR base sha> --manifest .ce/pr-path-manifest.md`
and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set
below. The fidelity scan (`scan-path-manifest`) additionally requires the
declared count and SHA256 to match the fenced block.

Scope: **DOCS-ONLY** reconciliation of the design docs to the already-ratified-
and-shipped **version coexistence** decision (the ratified design §5; G-3.9 / PR
#152). Reframes deletion/teardown framing → coexistence/retention across three
docs and finalizes the G-3.9 roadmap row PR/SHA (`#152` / `a02aca8`):
`docs/v3-roadmap.md` (G-3.9 row + the two "D0–D6 deletion plan" references + the
G-7 "retires D2"/"replacement" framing → "v1 retained, distinct v3 entry"),
`docs/architecture/v3-spec.md` (§6 "Deletion plan" → "Version coexistence plan",
v1-surface inventory retained + the "Bottom line" sentence), and
`docs/architecture/pilot-roadmap.md` (§G-3.9 + §7.0/§7.3 + the ordering
sentences). **No code/schema/test/example change** — module inventories and the
runtime-lifecycle `teardown` term are preserved; the executable surface is
byte-identical (`--list-checks` STAYS **44**, `check-examples` STAYS **77/0**).

- **base:** `a02aca84a8e3fa99bb046cf0b5d5c043170cd10b`.
- **canonicalization:** `sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=4

AUTHORIZED_PATHS_SHA256=2ea86b9535899204cbb4593391a32bfe84b2d14ab165e40bc87dea2a22ae282a

```text
.ce/pr-path-manifest.md
docs/architecture/pilot-roadmap.md
docs/architecture/v3-spec.md
docs/v3-roadmap.md
```
