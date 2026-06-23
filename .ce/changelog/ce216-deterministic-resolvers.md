# ce-ops#216 deterministic resolver library

- Added a v3 forge deterministic resolver module for the Integrator MVP's known
  mechanical conflict families: `_versions.py` registry union, version-boundary
  expected counts, non-overlapping CE changelog/manifest additions, and
  conservative append-only registries.
- Resolver results are structured as applicable/resolved/unresolved outcomes
  with changed paths, reason, evidence, and optional resolved content.
- Unknown, malformed, colliding, or semantically unclear conflicts now escalate
  as unresolved instead of selecting a side.
