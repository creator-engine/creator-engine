# PR path manifest - ce186-g6-seat-class-enforce

Per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`, ce-ops#21 convention).
CI runs:

```bash
verify-path-manifest --base <PR base sha> --manifest-dir .ce/pr-manifests --head-ref ce186-g6-seat-class-enforce
```

and requires this PR's `base..HEAD` diff to equal exactly the authorized
path-set below. This carrier lists itself.

Scope:
ce-ops#186 G6 seat-class enforce flip after the foreman WARN-only arm was
verified SAFE.

The changes:
- Flip governed `foreman_would_deny` / foreman-delegation decisions from
  advisory allow to hard deny while preserving governed manifest mismatch
  advisory behavior and ungoverned advisory behavior.
- Keep restricted mechanics and secret reads as earlier hard-deny checks that
  win before foreman delegation.
- Preserve in-class allows for launch-pinned worker implementation actions and
  foreman coordination actions.
- Update focused hook-check unit, CLI, and Claude hook-pack tests for the
  enforcement posture.

Per-file purpose (closed path-set - 7 paths):
- **`.ce/changelog/ce186-g6-seat-class-enforce.md`** *(A)* - changelog
  fragment.
- **`.ce/pr-manifests/ce186-g6-seat-class-enforce.md`** *(A)* - this carrier.
- **`validators/creator_engine_validator/hook_check.py`** *(M)* - governed
  foreman delegation enforcement flip and refusal-record provenance for file
  denials.
- **`validators/tests/integration/test_claude_hook_pack_pretooluse.py`** *(M)* -
  Claude hook-pack coverage for worker implementation allow and foreman
  coordination allow.
- **`validators/tests/integration/test_hook_check_cli.py`** *(M)* - CLI
  coverage for foreman deny, bootstrap fail-closed deny, and worker-pinned
  allows.
- **`validators/tests/unit/test_hook_check.py`** *(M)* - evaluator coverage for
  foreman deny, worker/coordination allow, manifest advisory, and hard-deny
  precedence.
- **`validators/tests/unit/test_hook_check_claude_format.py`** *(M)* - Claude
  format coverage for foreman hard deny.

Canonicalization:
`sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=7

AUTHORIZED_PATHS_SHA256=721c14ca79386f73b54d91756f97656a7a663333a4b39fe34d50a81157359186

```text
.ce/changelog/ce186-g6-seat-class-enforce.md
.ce/pr-manifests/ce186-g6-seat-class-enforce.md
validators/creator_engine_validator/hook_check.py
validators/tests/integration/test_claude_hook_pack_pretooluse.py
validators/tests/integration/test_hook_check_cli.py
validators/tests/unit/test_hook_check.py
validators/tests/unit/test_hook_check_claude_format.py
```
