# PR path manifest — fix(gate-c): make pco-allocate --envelope-ref none refuse loudly

This file is the carrier for this PR's closed path manifest under
`docs/operations/PATH_MANIFEST_FIDELITY_PROTOCOL.md`. CI passes it to
`verify-path-manifest --base <PR base sha> --manifest .ce/pr-path-manifest.md`
and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set
below. The fidelity scan (`scan-path-manifest`) requires the declared count and
SHA256 to match the fenced block.

Scope: **Gate C — `pco-allocate --envelope-ref none` (and the equivalent empty
sentinel) must refuse loudly instead of silently allocating an unauthorized
claim.**

- `validators/creator_engine_validator/cli.py`: reject the `none`/empty
  envelope-ref sentinel at the allocate entrypoint.
- `validators/creator_engine_validator/hook_check.py`: the shared refusal path.
- `validators/tests/integration/test_pco_allocator_cli.py`: integration coverage
  for the loud refusal.
- `validators/tests/unit/test_hook_check.py`: unit coverage for the sentinel
  rejection.

**Version-boundary impact = ZERO.** No new `runner.*` module, no schema change,
no check registration, no `runner/__init__.py` export; `V3_RUNTIME` stays **28**
and `--list-checks` stays byte-identical.

- **base:** `97dbc28e8c72717759d572ec4b022e854331048a` (current `main`).
- **canonicalization:** `sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=5

AUTHORIZED_PATHS_SHA256=2b2021d411ca1b2d4a6e222ba6d9dca946b437b9b76b35ed345c70d6d458f49f

```text
.ce/pr-path-manifest.md
validators/creator_engine_validator/cli.py
validators/creator_engine_validator/hook_check.py
validators/tests/integration/test_pco_allocator_cli.py
validators/tests/unit/test_hook_check.py
```
