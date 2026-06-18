# PR path manifest - ce94-finegrained-pat - fine-grained PAT bootstrap probe

Root closed-manifest carrier for ce-ops#94. CI/path review should compare this
branch's `base..HEAD` diff to the authorized path set below. This carrier lists
itself.

Ratified:
Controller relay for ce-ops#94 on 2026-06-18: fix `onboard --apply`
live-forge bootstrap probing so valid fine-grained PATs are accepted via actual
fine-grained permission validation while classic PAT validation remains intact.
Commit locally only; do not push.

Base:
`8d2a83be700d9337aeaaa7b704e6306da79744c8` (`origin/main` at branch creation).

The changes:
- The live probe classifies `github_pat_` tokens as fine-grained and validates
  permission-specific GitHub responses instead of deriving empty classic scopes.
- Greenfield bootstrap gating now requires fine-grained `permissions` to satisfy
  the unchanged bootstrap requirement table; missing permissions fail closed.
- Plain-join stays identity-only because the bootstrap PAT performs no writes.
- Tests cover fine-grained accepted, missing-permission refused, unknown-token
  fail-closed, and classic-PAT continuity.

Per-file purpose (the closed path-set - 6 paths; `(A)` add, `(M)` modify):
- **`.ce/changelog/ce94-finegrained-pat.md`** *(A)* - changelog fragment.
- **`.ce/pr-path-manifest.md`** *(A)* - this root closed-manifest carrier.
- **`validators/creator_engine_validator/onboard_apply.py`** *(M)* -
  gate fine-grained bootstrap permissions before greenfield write legs.
- **`validators/creator_engine_validator/onboard_apply_live.py`** *(M)* -
  live fine-grained permission probes and response-header parsing.
- **`validators/tests/unit/test_onboard_apply.py`** *(M)* -
  end-to-end bootstrap leg coverage for fine-grained permission acceptance and
  refusal.
- **`validators/tests/unit/test_onboard_apply_live.py`** *(M)* -
  live-driver probe coverage for fine-grained permission reporting.

Canonicalization:
`sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=6

AUTHORIZED_PATHS_SHA256=1056091650bc02c50e276ac4be7fc5c16a9988bea2d5c1bf17ad8fa7eeee2cb4

```text
.ce/changelog/ce94-finegrained-pat.md
.ce/pr-path-manifest.md
validators/creator_engine_validator/onboard_apply.py
validators/creator_engine_validator/onboard_apply_live.py
validators/tests/unit/test_onboard_apply.py
validators/tests/unit/test_onboard_apply_live.py
```
