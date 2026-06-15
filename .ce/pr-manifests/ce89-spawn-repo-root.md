# PR path manifest — ce89-spawn-repo-root · `cev3 review --spawn` repo-root + lease-id length fix

Per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`, the ce-ops#21 convention). CI runs:

    verify-path-manifest --base <PR base sha> --manifest-dir .ce/pr-manifests --head-ref ce89-spawn-repo-root

and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below (the carrier
lists itself); the repo-wide fidelity scan requires the declared count and SHA256 to match the fenced block.

Ratified:
SHA-pinned governed mandate `/tmp/dev3-mandate-ce89.md` (sha256 `abcb38fb…`), CE-DEV-3 seat `dev3-milestone`
(push-denied). ONE branch, ONE PR — closed-manifest gate.

Base:
`fa8916ae35ac77b38860399b45e4f3807224aed1` (`main` = #234, post schema-path/codex/gh-identity batch).

The changes (one branch, two coupled fixes for ce-ops#89):
- **ce-ops#89 (a) — out-of-repo `--repo-root`.** `spawn_review_venue`
  (`v3_seat_bridge.py`) built the `pco-allocate` argv WITHOUT `--repo-root` and ran it with `cwd` =
  the out-of-repo venue zone. `pco-allocate` defaults `repo_root` to its process cwd (`cli.py:578`),
  so `git worktree add` ran against the non-git venue zone and exited 128 — the venue never
  provisioned. The bridge now resolves a REAL repo context via `_resolve_repo_root`
  (`git -C <ledger-root> rev-parse --show-toplevel`, through the existing `runner` seam) and passes it
  as an explicit `--repo-root`. The active-work-ledger lives inside the controller's secondary
  worktree, so its git toplevel is the non-root repo_root pco needs; PCO-031's root-checkout refusal
  stays enforced inside `pco-allocate`. An unresolvable ledger-root fails closed BEFORE any pco side
  effect (`mark_spawn_failed` + `SpawnRefused`) — never a half-venue.
- **ce-ops#89 (b) — lease-id length (PCO-020).** The review run_id is fed to `pco-allocate` AS the
  ledger lane id, and pco derives `lease_id = lease-<lane>-<14-digit stamp>`. The naive
  `rev-<scope_id>-<stamp>` overflowed the 64-char `worktree-lease` bound once a scope_id exceeded
  ~22 chars. `materialize_review_dispatch` now mints the run_id via `_derive_review_run_id`, which
  clamps to the residual lane budget and hash-suffixes the clipped scope segment — schema-valid for
  ANY scope_id length, collision-free across distinct long scope_ids, lossless for short ones.

Acceptance note:
The full end-to-end (`cev3 review --spawn` with an out-of-repo `--venue-root` launching a live venue)
is the acceptance — exactly the behaviour Controller dev-2 hand-worked-around for the PR #233 and #234
reviews. Unit coverage added: pco-allocate now emits a resolved `--repo-root`; unresolvable repo-root
fails closed pre-pco; and the run_id→lease_id derivation stays ≤64 + unique for a long scope_id.

Wheel pair (required by the `validators/creator_engine_validator/**` edit):
`creator_engine_validator-0.2.0-py3-none-any.whl` rebuilt from current source (`setuptools.build_meta`)
+ `validators/wheelhouse/SHA256SUMS` updated (only the app-wheel line). `_version.py` left untouched
(no version bump — `verify_generated_version` stays clean).

Per-file purpose (the closed path-set — 6 paths; `(A)` add, `(M)` modify):
- **`.ce/changelog/ce89-spawn-repo-root.md`** *(A)* — changelog fragment covering both fixes (carrier).
- **`.ce/pr-manifests/ce89-spawn-repo-root.md`** *(A)* — this carrier (self-inclusive).
- **`validators/creator_engine_validator/v3_seat_bridge.py`** *(M)* — `_resolve_repo_root` + explicit `--repo-root`; `_derive_review_run_id` lease-id clamp.
- **`validators/tests/unit/test_v3_seat_bridge.py`** *(M)* — repo-root argv + fail-closed tests; long-scope lease-bound + collision-free tests.
- **`validators/wheelhouse/SHA256SUMS`** *(M)* — rebuilt-wheel digest updated (only the app-wheel line).
- **`validators/wheelhouse/creator_engine_validator-0.2.0-py3-none-any.whl`** *(M)* — rebuilt from current source.

Canonicalization:
`sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=6

AUTHORIZED_PATHS_SHA256=62de60177175962a78b36e2c0691bdf8a9fcdb86844386062fd761ef03980bce

```text
.ce/changelog/ce89-spawn-repo-root.md
.ce/pr-manifests/ce89-spawn-repo-root.md
validators/creator_engine_validator/v3_seat_bridge.py
validators/tests/unit/test_v3_seat_bridge.py
validators/wheelhouse/SHA256SUMS
validators/wheelhouse/creator_engine_validator-0.2.0-py3-none-any.whl
```
