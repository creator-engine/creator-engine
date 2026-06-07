# PR path manifest — site: port "Control-Room Violet" redesign into docs/index.html

This file is the carrier for this PR's closed path manifest under
`docs/operations/PATH_MANIFEST_FIDELITY_PROTOCOL.md`. CI passes it to
`verify-path-manifest --base <PR base sha> --manifest .ce/pr-path-manifest.md`
and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set
below. The fidelity scan (`scan-path-manifest`) additionally requires the declared
count and SHA256 to match the fenced block.

Scope: **SITE-ONLY** visual re-skin of the brand site to the Operator-ratified
"Control-Room Violet" cyberpunk-neon design — a single self-contained
`docs/index.html` (zero external dependencies: no fonts/images/scripts/network),
plus this manifest carrier. **No code/schema/test/example change**; the executable
surface is byte-identical. Copy and document structure are preserved; the change
is palette/layout/artwork only, with `.hermes`→`.ce` example copy corrected.

- **base:** `ec4eb3a34428770a00e688d452534fa6d54efccc`.
- **canonicalization:** `sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=2

AUTHORIZED_PATHS_SHA256=8e3c5e2898a8cc04bf8f9508693ae25c259052de79d90d2828610e9dc797d0d9

```text
.ce/pr-path-manifest.md
docs/index.html
```
