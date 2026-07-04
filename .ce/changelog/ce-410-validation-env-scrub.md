# ce-410 Validation Env Scrub

- Added a typed validation sandbox seam with explicit env allowlists, cwd, timeout, command, result audit trail, and credential-shaped env-key refusal.
- Routed conveyor validation through the sandbox while preserving the slice-6 validate command and `PYTHONPATH`/`TMPDIR`/`PATH` scrubbed environment.
