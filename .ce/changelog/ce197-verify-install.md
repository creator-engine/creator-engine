# ce-ops#197 — verify installed CE release provenance

- Added `ce verify-install` for read-only post-install verification of a pinned
  CE bootstrap venv, including install-state pin checks, installed-file RECORD
  hash verification, online `SHA256SUMS` comparison, and offline local-only mode.
- Extracted the bootstrap artifact-manifest parser into a shared module so the
  verifier and `v3_installer` reuse one parser without crossing the v1/v3
  runtime boundary.
