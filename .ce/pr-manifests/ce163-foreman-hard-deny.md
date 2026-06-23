# PR path manifest — ce-ops#163 (foreman hard-deny REQ-3)

Per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`, ce-ops#21). CI runs:

```bash
verify-path-manifest --base <PR base sha> --manifest-dir .ce/pr-manifests --head-ref ce163-foreman-hard-deny
```

and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set
below (the carrier lists itself); the fidelity scan requires the declared count
and SHA256 to match the fenced block.

Ratified scope:
ce-ops#163 REQ-3 only: hard-deny foreman implementation-typed actions beyond
the action-type x irreversibility boundary unless the hook resolves a valid
worker-spawn implementer artifact for the current worktree. Worker-routed
implementation is allowed; coordination/read/status actions remain allowed;
restricted mechanics still deny before the foreman delegation check.

Explicitly excluded: born-a-foreman launcher injection (REQ-1), reviewer-author
gates, controller merge gates, and any new refusal feed outside the existing
`hook_check.py` refusal chain.

Per-file purpose:
- **`.ce/changelog/ce163-foreman-hard-deny.md`** *(A)* — changelog fragment.
- **`.ce/pr-manifests/ce163-foreman-hard-deny.md`** *(A)* — this carrier
  (self-inclusive).
- **`validators/creator_engine_validator/cli.py`** *(M)* — forwards existing
  worker environment metadata into hook context resolution.
- **`validators/creator_engine_validator/hook_check.py`** *(M)* — validates
  worker-spawn records and routes foreman hard denies through the existing
  refusal-chain seam.
- **`validators/creator_engine_validator/seat_class.py`** *(M)* — standardizes
  the ce-ops#163 REQ-3 denial reason.
- **`validators/tests/integration/test_hook_check_cli.py`** *(M)* — covers the
  CLI worker-routed allow path.
- **`validators/tests/unit/test_hook_check.py`** *(M)* — covers direct denial,
  refusal-chain recording, valid worker allow, and fail-closed worker context.
- **`validators/tests/unit/test_seat_class.py`** *(M)* — pins the REQ-3 reason
  identifier in the pure classifier.

Canonicalization:
`sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=8

AUTHORIZED_PATHS_SHA256=0f1b736aa2519b9070169e6b158ff357d6e33c111c825e06c6c1226cdd416bf3

```text
.ce/changelog/ce163-foreman-hard-deny.md
.ce/pr-manifests/ce163-foreman-hard-deny.md
validators/creator_engine_validator/cli.py
validators/creator_engine_validator/hook_check.py
validators/creator_engine_validator/seat_class.py
validators/tests/integration/test_hook_check_cli.py
validators/tests/unit/test_hook_check.py
validators/tests/unit/test_seat_class.py
```
