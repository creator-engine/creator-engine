# PR path manifest — creator-engine/ce-ops#433 · Confidentiality push guard

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce-433-confidentiality-surface-coverage` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

- **Declared work class:** story

Scope:
Add the bounded push-protection surface for the existing public-repo
confidentiality scanner. Scanner widening and denylist redo are already present
on the base branch; this carrier covers only the remaining hook-style push
guard.

Base:
`d6ec9c2454ee33bbe4acf100ef14b6059e60def3` (`origin/main`).

Per-file purpose (closed path-set - 5 paths):

- **`.ce/changelog/ce-433-confidentiality-surface-coverage.md`** *(A)* - per-change changelog fragment.
- **`.ce/pr-manifests/ce-433-confidentiality-surface-coverage.md`** *(A)* - this PR's closed path-set carrier.
- **`validators/creator_engine_validator/cli.py`** *(M)* - exposes the hook-style push guard CLI.
- **`validators/creator_engine_validator/public_docs_confidentiality.py`** *(M)* - adds tree scanning and pre-push/pre-receive update handling while reusing the existing rule source.
- **`validators/tests/unit/test_public_docs_confidentiality_cli.py`** *(M)* - covers clean and leaking pushed refs plus the CLI object path.

Canonicalization:
`sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=5

AUTHORIZED_PATHS_SHA256=4298312bdd695455be75a31c56d2a35529de223d570a85ca501edf470c608433

```text
.ce/changelog/ce-433-confidentiality-surface-coverage.md
.ce/pr-manifests/ce-433-confidentiality-surface-coverage.md
validators/creator_engine_validator/cli.py
validators/creator_engine_validator/public_docs_confidentiality.py
validators/tests/unit/test_public_docs_confidentiality_cli.py
```
