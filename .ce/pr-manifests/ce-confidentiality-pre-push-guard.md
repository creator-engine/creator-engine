# PR path manifest - ce-confidentiality-pre-push-guard

Per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`, ce-ops#21 convention).
CI runs:

```bash
verify-path-manifest --base <PR base sha> --manifest-dir .ce/pr-manifests --head-ref ce-confidentiality-pre-push-guard
```

and requires this PR's `base..HEAD` diff to equal exactly the authorized
path-set below. This carrier lists itself.

- **Declared work class:** story

Scope:
ce-ops#306 root-fix public-docs confidentiality leaks: single-source the rule
and catch `ce-ops#` / internal-host references in `docs/**` before push (in
`ce validate-pr`), not only at CI.

Base:
`c974ccd633a55bc99122967204c51709825195ee` (`origin/main`).

Per-file purpose (closed path-set - 7 paths):

- **`.ce/changelog/ce-confidentiality-pre-push-guard.md`** *(A)* - per-change changelog fragment.
- **`.ce/pr-manifests/ce-confidentiality-pre-push-guard.md`** *(A)* - this PR's closed path-set carrier.
- **`validators/creator_engine_validator/cli.py`** *(M)* - registers the `scan-public-docs-confidentiality` subcommand and dispatch.
- **`validators/creator_engine_validator/pr_preflight.py`** *(M)* - wires the confidentiality scan into `ce validate-pr` so leaks are caught pre-push.
- **`validators/creator_engine_validator/public_docs_confidentiality.py`** *(A)* - single source of truth for the confidentiality rule + standalone check `run()`.
- **`validators/tests/unit/test_public_docs_confidentiality.py`** *(M)* - CI guard test refactored into a thin caller of the shared module (no rule fork).
- **`validators/tests/unit/test_public_docs_confidentiality_cli.py`** *(A)* - covers the standalone check + CLI subcommand pass/fail behaviour.

Canonicalization:
`sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=7

AUTHORIZED_PATHS_SHA256=fcabeaeb76e8d80698caeb94c620d728765913cf19f8091104573992faa1d81e

```text
.ce/changelog/ce-confidentiality-pre-push-guard.md
.ce/pr-manifests/ce-confidentiality-pre-push-guard.md
validators/creator_engine_validator/cli.py
validators/creator_engine_validator/pr_preflight.py
validators/creator_engine_validator/public_docs_confidentiality.py
validators/tests/unit/test_public_docs_confidentiality.py
validators/tests/unit/test_public_docs_confidentiality_cli.py
```
