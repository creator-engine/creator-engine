# PR path manifest - site v7 "The Choice" (Operator-approved v7.8)

CI passes this to `verify-path-manifest --base <PR base sha> --manifest .ce/pr-path-manifest.md`
and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; the
fidelity scan requires the declared count and SHA256 to match the fenced block.

Ratification: interactive Operator session 2026-06-11 — v7 concept ratified-with-changes,
then 8 directed revision rounds to v7.8 "draft approved, let's move to a governed live PR";
full round-by-round trail = ce-ops#10 comments of 2026-06-11. Approved draft source:
`~/Documents/ce-website-v7-draft-index.html` (CE-DEV-1).

Base: `1fb22f654527088fe4ce4a1348a30fa33d0f3fb9` (origin/main, post-#199).

Per-file purpose (7 paths):
- **`docs/index.html`** *(M)* - the v7 "The Choice" site (approved v7.8), adapted for live:
  hero art src -> `assets/the-choice-agent.webp`, favicon -> tracked `assets/ce-favicon-v2.svg`,
  header comment promoted draft->live. Content otherwise byte-identical to the approved draft, plus the 5 cockpit-serve theme-contract alias tokens required by test_v3_cockpit_serve.SITE_HEX (same values, zero visual change).
- **`docs/assets/the-choice-agent.webp`** *(A)* - Operator-provided hero art, webp q86
  (55KB; source PNG 1.6MB stays outside the repo).
- **`docs/assets/ce-logo-v2-weldarm.svg`** *(A)* - the new CE mark v2 "weld arm", tracked +
  versioned (512px presentational).
- **`docs/assets/ce-favicon-v2.svg`** *(A)* - the favicon artifact (same mark on a night tile);
  referenced by the page instead of an inline data URI.
- **`site-archive/index-v6-1-copy-button.html`** *(A)* - byte-exact snapshot of the outgoing
  v6.1 live page (sha256 `1a3f2645...` verified against the ledger row).
- **`site-archive/README.md`** *(M)* - ledger: v6.1 row pinned to its snapshot + live commit
  `6118a1c` (#194); v7 row added as current-live with the new content SHA256.
- **`.ce/pr-path-manifest.md`** *(M)* - this carrier.

Canonicalization:
`sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=7

AUTHORIZED_PATHS_SHA256=4d7eb9a60ce8040dad3628fb493f4cd8c1908ab2d05e3ac6de381c06361dbddb

```text
.ce/pr-path-manifest.md
docs/assets/ce-favicon-v2.svg
docs/assets/ce-logo-v2-weldarm.svg
docs/assets/the-choice-agent.webp
docs/index.html
site-archive/README.md
site-archive/index-v6-1-copy-button.html
```
