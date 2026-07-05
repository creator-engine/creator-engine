# PR path manifest - ce-brownfield-refusal-message

Design/task: U2 brownfield apply refusal-message split for credential resolution failures.

Base:
`2cfd39e5d010eee39dc0a9bfb7e01e7c309bcec1`

Declared work class: tiny

This is the closed path set for the refusal seam only. It intentionally does not
claim runner backend changes, installer schema changes, signed install-spec
changes, or edits to existing shared v3 CLI/installer test files.

Per-file purpose:

- **`.ce/changelog/ce-brownfield-refusal-message.md`** *(A)* - changelog fragment for the refusal-message fix.
- **`.ce/pr-manifests/ce-brownfield-refusal-message.md`** *(A)* - this PR's closed path-set carrier.
- **`validators/creator_engine_validator/v3_cli.py`** *(M)* - split the brownfield apply refusal text when dual escalation is requested but App credential resolution fails.
- **`validators/tests/unit/test_v3_brownfield_refusals.py`** *(A)* - focused tests for the vars-never-set and vars-set-but-credentials-unresolved refusal messages.

Canonicalization:
`sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=4

AUTHORIZED_PATHS_SHA256=5b117f5d4a5e9e199d4e4ab7030f5a8652600a89b8804c72322613f1041748c0

```text
.ce/changelog/ce-brownfield-refusal-message.md
.ce/pr-manifests/ce-brownfield-refusal-message.md
validators/creator_engine_validator/v3_cli.py
validators/tests/unit/test_v3_brownfield_refusals.py
```
