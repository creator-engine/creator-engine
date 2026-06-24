# PR path manifest - ce214-pr-open-carrier-scaffold

Per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`, ce-ops#21 convention).
CI runs:

```bash
verify-path-manifest --base <PR base sha> --manifest-dir .ce/pr-manifests --head-ref ce214-pr-open-carrier-scaffold
```

and requires this PR's `base..HEAD` diff to equal exactly the authorized
path-set below. This carrier lists itself.

Base:
`origin/main` at branch handoff.

- **Declared work class:** story

Scope:
ce-ops#214. Inject the required PR governance scaffold in the forge PR-open
helper by default, including a valid declared work-class line and clear
`.ce/pr-manifests/<branch-slug>.md` plus `.ce/changelog/<branch-slug>.md`
carrier guidance. No deploy run scripts, OpenBao files, `install.sh`, or
validator version registries are changed.

Per-file purpose:
- **`.ce/changelog/ce214-pr-open-carrier-scaffold.md`** *(A)* - changelog fragment.
- **`.ce/pr-manifests/ce214-pr-open-carrier-scaffold.md`** *(A)* - this closed path-set carrier.
- **`validators/creator_engine_validator/forge/change.py`** *(M)* - add the PR body governance scaffold and work-class validation.
- **`validators/tests/unit/test_open_change.py`** *(M)* - cover the emitted scaffold and explicit work-class override.

Canonicalization:
`sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=4

AUTHORIZED_PATHS_SHA256=e1f1731e9bce7a71dfa6c11bd96145c1e6081e7e6e63ff22b3b5a51b332acfac

```text
.ce/changelog/ce214-pr-open-carrier-scaffold.md
.ce/pr-manifests/ce214-pr-open-carrier-scaffold.md
validators/creator_engine_validator/forge/change.py
validators/tests/unit/test_open_change.py
```
