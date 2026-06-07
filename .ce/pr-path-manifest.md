# PR path manifest — creator-engine.dev GitHub Pages launch

This file is the carrier for this PR's closed path manifest under
`docs/operations/PATH_MANIFEST_FIDELITY_PROTOCOL.md`. CI passes it to
`verify-path-manifest --base <PR base sha> --manifest .ce/pr-path-manifest.md`
and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set
below.

Scope: GitHub Pages launch preparation for `creator-engine.dev`: update the
self-contained landing page, add the Pages custom-domain CNAME file, and carry
this manifest. This PR does not mutate GitHub repository settings or Cloudflare
DNS.

- **base:** `ab482eeab8bc6c060e605277e2d5f85c3e3d1aa4`.
- **canonicalization:** `sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=3

AUTHORIZED_PATHS_SHA256=667c86e6bf619eff8f3695673a0ec0208a548a4b2eda0d556cf3c7cd74c8db71

```text
.ce/pr-path-manifest.md
docs/CNAME
docs/index.html
```
