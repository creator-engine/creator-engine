# ce-ops#197 — verify installed CE release provenance

- Added `ce verify-install` for read-only post-install verification of a pinned
  CE bootstrap venv, including install-state pin checks, installed-file
  verification, online `SHA256SUMS` comparison, and offline local-only mode.
- Anchored installed-file verification in the TRUSTED published wheel (fetched
  and verified against the signed `SHA256SUMS` chain) rather than the venv's own
  mutable `RECORD`, so a tampered file paired with a tampered `RECORD` is still
  refused online. `--offline` is an explicit reduced-assurance check that only
  attests "matches local install-state", never "matches the published release"
  (`venv.assurance` / `venv.anchor` report which anchor was used).
- Validated `RECORD` path containment against the venv root, so legitimate
  venv-owned console scripts (e.g. `../../../bin/ce`) are accepted and only a
  true escape outside the venv root is flagged.
- Extracted the bootstrap artifact-manifest parser into a shared module so the
  verifier and `v3_installer` reuse one parser without crossing the v1/v3
  runtime boundary.
