# PR path manifest - ce219-codex-pretooluse-hook

Per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`, ce-ops#21 convention).
CI runs:

```bash
verify-path-manifest --base <PR base sha> --manifest-dir .ce/pr-manifests --head-ref ce219-codex-pretooluse-hook
```

and requires this PR's `base..HEAD` diff to equal exactly the authorized
path-set below. This carrier lists itself.

Base:
`385e246` (`origin/main` at branch handoff).

- **Declared work class:** feature

Scope:
ce-ops#219 hardening follow-up for the Codex PreToolUse adapter. Invocation
failures in the shared `hook-check` subprocess must fail closed with a generic
deny reason only; child stdout, child stderr, and runner exception text are live
hook surfaces and must remain secret-safe.

Per-file purpose:
- **`.ce/changelog/ce219-codex-pretooluse-hook.md`** *(A)* - changelog fragment.
- **`.ce/pr-manifests/ce219-codex-pretooluse-hook.md`** *(A)* - this closed path-set carrier.
- **`validators/creator_engine_validator/codex_pretooluse.py`** *(M)* - redact `hook-check` invocation failure details from fail-closed Codex deny reasons.
- **`validators/tests/unit/test_codex_pretooluse.py`** *(M)* - regression coverage for synthetic secret bytes in failed child output and runner exceptions.

Canonicalization:
`sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=4

AUTHORIZED_PATHS_SHA256=9da5f651eff1acf6da31b9187681fe34d7b4d6d498d8d108802e56af77a65540

```text
.ce/changelog/ce219-codex-pretooluse-hook.md
.ce/pr-manifests/ce219-codex-pretooluse-hook.md
validators/creator_engine_validator/codex_pretooluse.py
validators/tests/unit/test_codex_pretooluse.py
```
