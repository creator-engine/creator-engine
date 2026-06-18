# PR path manifest - ce94-finegrained-pat - fine-grained PAT bootstrap probe

Per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`, the ce-ops#21 convention).
CI/path review should compare this branch's `base..HEAD` diff to the authorized
path set below. This carrier lists itself.

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
- The validator app wheel is rebuilt from the current branch source and
  `validators/wheelhouse/SHA256SUMS` is refreshed; the signed Pages mirror under
  `docs/downloads/0.2.0/` is intentionally untouched.

Per-file purpose (the closed path-set - 8 paths; `(A)` add, `(M)` modify):
- **`.ce/changelog/ce94-finegrained-pat.md`** *(A)* - changelog fragment.
- **`.ce/pr-manifests/ce94-finegrained-pat.md`** *(A)* - this per-PR
  closed-manifest carrier.
- **`validators/creator_engine_validator/onboard_apply.py`** *(M)* -
  gate fine-grained bootstrap permissions before greenfield write legs.
- **`validators/creator_engine_validator/onboard_apply_live.py`** *(M)* -
  live fine-grained permission probes and response-header parsing.
- **`validators/tests/unit/test_onboard_apply.py`** *(M)* -
  end-to-end bootstrap leg coverage for fine-grained permission acceptance and
  refusal.
- **`validators/tests/unit/test_onboard_apply_live.py`** *(M)* -
  live-driver probe coverage for fine-grained permission reporting.
- **`validators/wheelhouse/SHA256SUMS`** *(M)* - refreshed dev wheelhouse
  digest manifest for the rebuilt validator app wheel.
- **`validators/wheelhouse/creator_engine_validator-0.2.0-py3-none-any.whl`**
  *(M)* - rebuilt validator app wheel matching this branch's source.

Canonicalization:
`sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=8

AUTHORIZED_PATHS_SHA256=3835c7f4a7aeb5fb6cb44ed797a26a3086892dce05275d3ecc9b0cff453a24e6

```text
.ce/changelog/ce94-finegrained-pat.md
.ce/pr-manifests/ce94-finegrained-pat.md
validators/creator_engine_validator/onboard_apply.py
validators/creator_engine_validator/onboard_apply_live.py
validators/tests/unit/test_onboard_apply.py
validators/tests/unit/test_onboard_apply_live.py
validators/wheelhouse/SHA256SUMS
validators/wheelhouse/creator_engine_validator-0.2.0-py3-none-any.whl
```
