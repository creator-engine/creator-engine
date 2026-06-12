# PR path manifest — ce-ops#21 per-PR path-manifest carrier files

This is the FIRST per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`), and the gate
that introduces the convention. CI runs:

```bash
verify-path-manifest --base <PR base sha> --manifest-dir .ce/pr-manifests --head-ref ce21-per-pr-carrier
```

and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below
(the carrier lists itself); the repo-wide fidelity scan requires the declared count and
SHA256 to match the fenced block.

Ratified gate:
Operator-RATIFIED ce-ops#21 gate spec (`designs/ce-21-per-pr-carrier-gate-spec-DRAFT-20260612.md`),
adopted with wheel-IN + roadmap-row-IN + branch name `ce21-per-pr-carrier` as proposed.
Migrate the single shared `.ce/pr-path-manifest.md` (which every gate PR rewrote — the
structural "batch-PR merge tax") to per-PR carrier files; the `verify-path-manifest` rule
becomes "exactly one ADDED carrier in the diff, slug == `branch_slug(head)`, diff == its
self-inclusive path-set", and merged carriers accumulate as a per-PR scope-audit ledger.

Base:
`570b20cfa7f908786a8f5c8fe129ca7a8b670b3b` (origin/main = #204, the v3.1-B.7 Cockpit fleet
cost meter; the §8 re-ground confirmed §2/§4 citations hold at this base — no unlisted drift).

Per-file purpose (the closed path-set — 13 paths, as ratified §4):
- **`.ce/pr-manifests/ce21-per-pr-carrier.md`** *(A)* — this carrier: the gate's own
  per-PR carrier (self-inclusive; the first ledger entry).
- **`.ce/pr-path-manifest.md`** *(D)* — the retired shared carrier, deleted (F5). Its content
  is durable in git history; the per-PR ledger starts here.
- **`.github/workflows/validate.yml`** *(M)* — the G-ii step → one unconditional per-PR
  invocation (`--manifest-dir`/`--head-ref`; the shell `if -f` is dropped).
- **`docs/operations/GITHUB_NATIVE_COORDINATION_PROTOCOL.md`** *(M)* — required-check row +
  §g carrier convention → per-PR carrier.
- **`docs/operations/PATH_MANIFEST_FIDELITY_PROTOCOL.md`** *(M)* — §h gate mode + per-PR
  convention, slug rule, the new error classes, and the no-other-files-in-dir rule.
- **`docs/v3-roadmap.md`** *(M)* — the ce-ops#21 gate-status row.
- **`validators/creator_engine_validator/checks/path_manifest_fidelity.py`** *(M)* —
  `branch_slug` + per-PR mode in `run_with_base` + the 4 new error classes.
- **`validators/creator_engine_validator/cli.py`** *(M)* — `--manifest-dir`/`--head-ref`
  flags + mutual-exclusion / head-ref-required guards.
- **`validators/creator_engine_validator/forge/change.py`** *(M)* — docstring +
  `_render_pr_body` text: the old shared path literal → the per-PR convention wording
  (text-only; refusal logic untouched).
- **`validators/tests/unit/test_open_change.py`** *(M)* — the `_MANIFEST` fixture → a
  per-PR-convention example path.
- **`validators/tests/unit/test_path_manifest_fidelity.py`** *(M)* — the slug id-shape
  corpus + the per-PR diff-gate tests.
- **`validators/wheelhouse/SHA256SUMS`** *(M)* — re-pinned for the rebuilt wheel (F6).
- **`validators/wheelhouse/creator_engine_validator-0.1.0-py3-none-any.whl`** *(M)* —
  rebuilt from this branch's source so the wheel<->source contract holds (F6).

Canonicalization:
`sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=13

AUTHORIZED_PATHS_SHA256=c523d2427bb641f034a19e5ba9fc452ad09bccb9cf8838c611164faf511da140

```text
.ce/pr-manifests/ce21-per-pr-carrier.md
.ce/pr-path-manifest.md
.github/workflows/validate.yml
docs/operations/GITHUB_NATIVE_COORDINATION_PROTOCOL.md
docs/operations/PATH_MANIFEST_FIDELITY_PROTOCOL.md
docs/v3-roadmap.md
validators/creator_engine_validator/checks/path_manifest_fidelity.py
validators/creator_engine_validator/cli.py
validators/creator_engine_validator/forge/change.py
validators/tests/unit/test_open_change.py
validators/tests/unit/test_path_manifest_fidelity.py
validators/wheelhouse/SHA256SUMS
validators/wheelhouse/creator_engine_validator-0.1.0-py3-none-any.whl
```
