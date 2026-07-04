---
slug: ce-410-validation-env-scrub
date: 2026-07-04
kind: story
scope: validation subprocess env-scrub sandbox seam (slice 7 rework)
issue: ce-ops#410
---

**Add validation sandbox env-scrub subprocess seam.**

- Added a typed validation-subprocess seam (`ValidationSandboxSpec` / `run_validation_sandbox`) that constructs its execution context via `ValidationSandboxContext.from_sandbox(...)` and revalidates the env allowlist against a widened credential-shaped-key filter before every invocation.
- Routed `conveyor.py`'s `_default_validate_runner` through the sandbox seam while preserving the slice-6 validate command and scrubbed `PYTHONPATH`/`TMPDIR`/`PATH` environment (regression-pinned in `test_conveyor.py`).
- Extended (not replaced) the slice-4 `forge/authority_contexts.py` module: widened `_FORBIDDEN_CREDENTIAL_KEYS`/added token-pattern matching, added `require_no_credential_env`/`is_credential_env_key` helpers; `TransportCredentialContext`, `LocalGitContext`, and `ValidationSandboxContext.from_sandbox` are unchanged.
