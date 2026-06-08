# PR path manifest — feat(site): v5.1 cosmetic tidy (title/meta sync + headline demote)

This file is the carrier for this PR's closed path manifest under
`docs/operations/PATH_MANIFEST_FIDELITY_PROTOCOL.md`. CI passes it to
`verify-path-manifest --base <PR base sha> --manifest .ce/pr-path-manifest.md`
and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set
below. The fidelity scan (`scan-path-manifest`) requires the declared count and
SHA256 to match the fenced block.

Scope: **SITE — v5.1 cosmetic follow-up tidy on the live v5 redesign.** Three small
fixes to the shipped v5 `docs/index.html`, all cosmetic (no redesign, no new
version archive — an in-place v5.x patch):
1. **Title-meta sync** — the browser-tab `<title>` and `twitter:title` still read
   the pre-correction "…software factory you can trust"; sync both to the corrected
   H1 / `og:title` phrasing "turn your home computer into a software factory" so all
   three title surfaces agree.
2. **Headline de-duplication** — the "Why governance" section carried two co-equal
   `<h2>` headlines; demote the second ("Every consumer fear maps to a mechanism…")
   to a scoped `<h3>` sub-head so the section has one primary headline.
3. **Ledger reconcile** — sync the `site-archive/README.md` v5 row's quoted title to
   the real H1 and refresh its `docs/index.html` SHA256 to the patched bytes, with a
   v5.1 tidy note (no new archive row — in-place patch).

`docs/` is the only Pages-served path touched; **no code/schema/test/example change.**

- **base:** `af6ee9d2dd3b3b4c0849bea96a2b49b348b72930`.
- **canonicalization:** `sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=3

AUTHORIZED_PATHS_SHA256=b7871bd7b1d2e2b38dff3531b7d1541da18c26548511fa606ddee2cbbb79518f

```text
.ce/pr-path-manifest.md
docs/index.html
site-archive/README.md
```
