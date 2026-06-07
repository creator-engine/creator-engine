# PR path manifest — site: ship v3 (FOMO + augmentation) and archive prior versions

This file is the carrier for this PR's closed path manifest under
`docs/operations/PATH_MANIFEST_FIDELITY_PROTOCOL.md`. CI passes it to
`verify-path-manifest --base <PR base sha> --manifest .ce/pr-path-manifest.md`
and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set
below. The fidelity scan (`scan-path-manifest`) additionally requires the declared
count and SHA256 to match the fenced block.

Scope: **SITE-ONLY**. Replace the live `docs/index.html` with the Operator-approved
**v3** brand-site (FOMO + visual-augmentation pass on the Control-Room Violet
system — single self-contained file, zero external dependencies), AND establish a
tracked website-version archive: snapshot the outgoing **v2** (Control-Room Violet)
and backfill the original **v1** (cyan launch) into `site-archive/`, with a version
ledger `site-archive/README.md`, plus this manifest carrier. `site-archive/` is NOT
served by GitHub Pages (Pages serves `docs/` only). **No code/schema/test/example
change**; the executable surface is byte-identical.

- **base:** `1ed368b183df8a8f2477b40342da0191cbf0a238`.
- **canonicalization:** `sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=5

AUTHORIZED_PATHS_SHA256=48779609fbf02d935bcb183cea6fc6af0954b419dfb305e016f52060557a02b9

```text
.ce/pr-path-manifest.md
docs/index.html
site-archive/README.md
site-archive/index-v1-launch-cyan.html
site-archive/index-v2-control-room-violet.html
```
