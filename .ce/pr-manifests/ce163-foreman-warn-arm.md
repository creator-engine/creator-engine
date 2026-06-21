# PR path manifest — ce-ops#163 G6 foreman WARN-only live-arm

Per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`, ce-ops#21). CI runs:

```bash
verify-path-manifest --base <PR base sha> --manifest-dir .ce/pr-manifests --head-ref ce163-foreman-warn-arm
```

and requires this PR's `base..HEAD` diff to equal exactly the authorized
path-set below (the carrier lists itself); the fidelity scan requires the
declared count and SHA256 to match the fenced block.

Ratified scope:
ce-ops#163 G6 WARN-only foreman seat_class live-arm.

Scope: arm `hook_check.py` for WARN/observe mode only. Do not hard-deny foreman
implementation work, do not implement worker spawning, and do not flip
enforcement. Reuse the existing pure `seat_class.py` helpers and the
launch-pinned brain-bootstrap env pair for seat-class resolution; keep
runtime-policy schema churn minimal by resolving `ce.seat_class_policy` and
`ce.seat_class_policy_ref` from the hook event.

Per-file purpose:
- **`.ce/changelog/ce163-foreman-warn-arm.md`** *(A)* — changelog fragment.
- **`.ce/pr-manifests/ce163-foreman-warn-arm.md`** *(A)* — this carrier
  (self-inclusive).
- **`docs/contracts/seat-class-policy.md`** *(M)* — documents WARN-only hook
  observation and preserved hard-deny precedence.
- **`validators/creator_engine_validator/_version.py`** *(M)* — generated build
  identity refreshed from the current base so author-side packaging checks stay
  green without adding first-party wheel churn.
- **`validators/creator_engine_validator/cli.py`** *(M)* — verifies the
  launch-pinned brain-bootstrap digest and injects its `seat_class` into
  `hook-check`, failing invalid bootstrap evidence closed to foreman.
- **`validators/creator_engine_validator/hook_check.py`** *(M)* — resolves
  seat class/policy in `HookContext` and emits WARN-only foreman advisory
  decisions after existing hard-deny checks.
- **`validators/tests/integration/test_hook_check_cli.py`** *(M)* — CLI coverage
  for `ce.seat_class_policy_ref` and launch-pinned brain-bootstrap seat-class
  paths.
- **`validators/tests/unit/test_hook_check.py`** *(M)* — evaluator coverage for
  foreman warning, worker/coordination no-warning, refusal-chain absence, and
  `git push` hard-deny precedence.

Canonicalization:
`sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=8

AUTHORIZED_PATHS_SHA256=4214a2212b83dd4243d7d904431c92f2293868d52d930138b840cf27e4c4bb37

```text
.ce/changelog/ce163-foreman-warn-arm.md
.ce/pr-manifests/ce163-foreman-warn-arm.md
docs/contracts/seat-class-policy.md
validators/creator_engine_validator/_version.py
validators/creator_engine_validator/cli.py
validators/creator_engine_validator/hook_check.py
validators/tests/integration/test_hook_check_cli.py
validators/tests/unit/test_hook_check.py
```
