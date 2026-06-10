# PR path manifest — v3.5-E/site-v6: build-from-home locked homepage package

CI passes this to `verify-path-manifest --base <PR base sha> --manifest .ce/pr-path-manifest.md`
and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; the
fidelity scan requires the declared count + SHA256 to match the fenced block.

Implements the operator-locked creator-engine.dev v6 top surface: minimal Build-from-home hero,
Quick-Start install block, real Textual cockpit SVG demo asset, text-only OpenShell security badge,
bridge line, and the same-change-set website versioning snapshot. **Site/archive only — zero
validator code, no installer artifact changes, no check-registry or `V3_RUNTIME` change.**

Per-file purpose:
- **`docs/index.html`** *(M)* — replace the top surface with the locked hero, Quick-Start, real cockpit embed, OpenShell badge, and bridge line; downstream sections keep their existing content.
- **`docs/assets/cockpit-demo-v6.svg`** *(A)* — real SVG screenshot generated from `CE_DEMO=1 ce cockpit` via the Textual `CockpitApp.save_screenshot` path.
- **`site-archive/index-v5-1-install-oneliner.html`** *(A)* — verbatim snapshot of the outgoing v5.1 index.
- **`site-archive/README.md`** *(M)* — demote v5.1 to snapshot and promote v6 as current.
- **`.ce/pr-path-manifest.md`** *(this carrier)*.

- **base:** `bbd21c4`.
- **canonicalization:** `sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=5

AUTHORIZED_PATHS_SHA256=e8df3ad7a03ede211fe21125c82a229cb7b8158b1993772626e2fe9ea0ee2da6

```text
.ce/pr-path-manifest.md
docs/assets/cockpit-demo-v6.svg
docs/index.html
site-archive/README.md
site-archive/index-v5-1-install-oneliner.html
```
