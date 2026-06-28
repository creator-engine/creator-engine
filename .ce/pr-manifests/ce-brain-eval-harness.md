# PR path manifest - ce-brain-eval-harness - ce-ops#79 brain eval harness

Per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`, ce-ops#21 convention).
CI runs:

```bash
verify-path-manifest --base <PR base sha> --manifest-dir .ce/pr-manifests --head-ref ce-brain-eval-harness
```

and requires this PR's `base..HEAD` diff to equal exactly the authorized
path-set below. This carrier lists itself.

Base:
`83907bb7ff14b453c149caebca6bc4231adb8efd`.

- **Declared work class:** story

Scope:
ce-ops#79 adds a bounded, repeatable offline recall eval for the company-brain
surface. It introduces a fixed golden set, deterministic keyword and mock
semantic legs, and a structured report exposed through `ce brain eval`.

Per-file purpose:
- **`.ce/changelog/ce-brain-eval-harness.md`** *(A)* - changelog fragment.
- **`.ce/pr-manifests/ce-brain-eval-harness.md`** *(A)* - this closed path-set carrier.
- **`validators/creator_engine_validator/brain_eval.py`** *(A)* - offline eval harness.
- **`validators/creator_engine_validator/ce_cli.py`** *(M)* - brain-group-only CLI wiring for `ce brain eval`.
- **`validators/tests/unit/test_brain_eval.py`** *(A)* - harness and CLI unit coverage.

Canonicalization:
`sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=5

AUTHORIZED_PATHS_SHA256=436e6cb577fbbcbbf20bdb903b4bf42127e19f51ba8e7ea5a8b4cac202a474d2

```text
.ce/changelog/ce-brain-eval-harness.md
.ce/pr-manifests/ce-brain-eval-harness.md
validators/creator_engine_validator/brain_eval.py
validators/creator_engine_validator/ce_cli.py
validators/tests/unit/test_brain_eval.py
```
