# PR path manifest — site v6.1: copy button on the install one-liner

CI passes this to `verify-path-manifest --base <PR base sha> --manifest .ce/pr-path-manifest.md`
and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; the
fidelity scan requires the declared count + SHA256 to match the fenced block.

Operator-directed convention fix (2026-06-10): the install one-liner gets a `Copy` button to its
right, per the convention on every referenced site. **Site/archive only — zero validator code, no
installer artifact changes, no check-registry or `V3_RUNTIME` change.**

Per-file purpose:
- **`docs/index.html`** *(M)* — wrap the one-liner in a flex `.ib-row`, add the `.ib-copy` ghost
  button (violet, lime "Copied" confirm) + its CSS + the page's first/only inline script
  (clipboard-only, no network, no tracking). Nothing else touched.
- **`site-archive/index-v6-buildfromhome.html`** *(A)* — verbatim snapshot of the outgoing v6 index
  (sha256 `29d4e614…4329` = the ledger's v6 row).
- **`site-archive/README.md`** *(M)* — demote v6 to snapshot; promote v6.1 as current.
- **`.ce/pr-path-manifest.md`** *(this carrier)*.

- **base:** `60cc607`.
- **canonicalization:** `sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=4

AUTHORIZED_PATHS_SHA256=7bdf3db559d862aff23ce75071c4da6dd0eba3c711a3e532658bd3e37a78afba

```text
.ce/pr-path-manifest.md
docs/index.html
site-archive/README.md
site-archive/index-v6-buildfromhome.html
```
