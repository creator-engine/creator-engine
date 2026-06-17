# PR path manifest — ce105-s1-deploy-classifier · Ring-1 deploy-classifier hardening (ce-ops#105 Scope-2 S1)

Per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`, the ce-ops#21 convention). CI runs:

    verify-path-manifest --base <PR base sha> --manifest-dir .ce/pr-manifests --head-ref ce105-s1-deploy-classifier

and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below (the carrier
lists itself); the repo-wide fidelity scan requires the declared count and SHA256 to match the fenced block.

Ratified:
SHA-pinned governed mandate `/tmp/ce-s1-mandate-20260617.md`, CE-DEV-3 §7 build seat (commit-local +
HOLD, push-denied). ONE branch, ONE PR — closed-manifest gate. Review routes to dev-2 / `ubuntuaws745-cmyk`.

Base:
`58990ff0ef3d649d25b6874340b3c1c6364702b3` (`main` = #246, P1 agent-executable GitHub DevOps layer —
S1 rebased onto it; the wheel is rebuilt from the unioned tree so it carries #246's forge ops + S1).

The changes (one branch, ce-ops#105 Scope-2 S1 — additive, low-blast-radius, mirrors #242):
- **Outward sub-verb coverage.** `_classify_git_subcommand` (`hook_check.py`) now classifies
  `git send-pack` as `deploy`, and the foreign-VCS bridges' only outward sub-verbs — `git p4 submit`
  and `git svn dcommit` — as `deploy`. Their read sub-verbs (`p4 sync` / `svn fetch` / any other) stay
  allowed; an absent/unparseable bridge sub-verb falls conservative (deploy). `send-pack`/`p4`/`svn`
  are added to `_GIT_BUILTINS` so they route to the new logic instead of the unknown path.
- **Abbreviation guard.** A directly-typed unknown subcommand that is a UNIQUE prefix of a restricted
  verb (`push`, `send-pack`, `branch-delete`) is classified as that verb's mechanic (e.g. `git pus`
  → deploy), removing the git-autocorrect dependency. An ambiguous prefix (>1 restricted verb) or a
  non-prefix unknown stays `None`/allow; an unknown reached via alias resolution stays `git_opaque`.
- **Observability exit code.** `ring1_tool_guard.DENY_EXIT_CODE` 126 → `121` (distinct from shell's
  "command found but not executable" 126), so a CE Ring-1 denial is observably distinct from a real
  exec failure. The shim interpolates the constant, so the emitted code follows; deny semantics are
  unchanged.

Tests (both directions):
`test_hook_check.py` adds DENY→deploy (`send-pack`, `p4 submit`, `svn dcommit`, unique-prefix `pus`,
alias-expands-to-`send-pack`, absent-subverb conservative) and ALLOW-regression (`p4 sync`,
`svn fetch`, `status`, `log`, non-prefix unknown). `test_runner_ring1_codex_push.py` updates the
denied-push exit-code assertion 126 → 121. `test_version_boundary` stays green (no version bump);
`test_packaging_contract` + `test_wheelhouse_built_surface` (40) pass against the rebuilt wheel.

Wheel pair (required by the `validators/creator_engine_validator/**` edit):
`creator_engine_validator-0.2.0-py3-none-any.whl` rebuilt from current source (`setuptools.build_meta`,
no egg-info/build leak) + `validators/wheelhouse/SHA256SUMS` updated (only the app-wheel line, digest
`1571e06f…`, self-verified via `sha256sum -c`). `_version.py` left untouched (no version bump).

Per-file purpose (the closed path-set — 8 paths; `(A)` add, `(M)` modify):
- **`.ce/changelog/ce105-s1-deploy-classifier.md`** *(A)* — changelog fragment.
- **`.ce/pr-manifests/ce105-s1-deploy-classifier.md`** *(A)* — this carrier (self-inclusive).
- **`validators/creator_engine_validator/hook_check.py`** *(M)* — send-pack/p4/svn classification + abbreviation guard + `_GIT_BUILTINS`.
- **`validators/creator_engine_validator/runner/ring1_tool_guard.py`** *(M)* — `DENY_EXIT_CODE` 126 → 121 (observability).
- **`validators/tests/integration/test_runner_ring1_codex_push.py`** *(M)* — denied-push exit-code assertion 126 → 121.
- **`validators/tests/unit/test_hook_check.py`** *(M)* — both-direction classifier coverage.
- **`validators/wheelhouse/SHA256SUMS`** *(M)* — rebuilt-wheel digest updated (only the app-wheel line).
- **`validators/wheelhouse/creator_engine_validator-0.2.0-py3-none-any.whl`** *(M)* — rebuilt from current source.

Canonicalization:
`sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=8

AUTHORIZED_PATHS_SHA256=0946419aa1d87751f0f5603faf15fa116e2972ae53f4409a4869bf8eee8bcbea

```text
.ce/changelog/ce105-s1-deploy-classifier.md
.ce/pr-manifests/ce105-s1-deploy-classifier.md
validators/creator_engine_validator/hook_check.py
validators/creator_engine_validator/runner/ring1_tool_guard.py
validators/tests/integration/test_runner_ring1_codex_push.py
validators/tests/unit/test_hook_check.py
validators/wheelhouse/SHA256SUMS
validators/wheelhouse/creator_engine_validator-0.2.0-py3-none-any.whl
```
