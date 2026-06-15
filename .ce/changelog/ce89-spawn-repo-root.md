---
slug: ce89-spawn-repo-root
date: 2026-06-15
kind: fixed
scope: v3 seat bridge (reviewer venue provisioning)
issue: ce-ops#89
---

**`cev3 review --spawn` now provisions out-of-repo reviewer venues out of the
box: pco-allocate gets a real `--repo-root`, and the derived lease id stays
schema-valid for long scope_ids.**

- **ce-ops#89 (a) — `cev3 review --spawn` aborted at `git worktree add` (exit
  128) for an out-of-repo venue.** `spawn_review_venue` built the
  `pco-allocate` argv WITHOUT `--repo-root` and ran it with `cwd` set to the
  out-of-repo venue zone. `pco-allocate` defaults `repo_root` to its process
  cwd (`cli.py:578`), so it tried to `git worktree add` from the venue zone —
  which is not a git repo — and exited 128, leaving the venue stillborn. The
  bridge now resolves a REAL repo context (`git -C <ledger-root> rev-parse
  --show-toplevel`, through the existing `runner` seam) and passes it as an
  explicit `--repo-root`. The active-work-ledger lives inside the controller's
  secondary worktree, so its git toplevel is exactly the non-root repo_root
  pco needs; PCO-031's root-checkout refusal stays enforced inside
  `pco-allocate`. When the ledger-root is not inside a git worktree the bridge
  fails closed BEFORE any pco side effect (`mark_spawn_failed` + `SpawnRefused`),
  never a half-venue.
- **ce-ops#89 (b) — the derived lease id overflowed the 64-char
  `worktree-lease` bound (PCO-020) for long scope_ids.** The review run_id is
  fed to `pco-allocate` AS the ledger lane id, and pco derives `lease_id` as
  `lease-<lane>-<14-digit stamp>`. The naive `rev-<scope_id>-<stamp>` run_id
  overflowed that bound once a scope_id exceeded ~22 chars, fail-closed
  refusing the venue. `materialize_review_dispatch` now mints the run_id via
  `_derive_review_run_id`, which clamps the id to the residual lane budget and
  hash-suffixes the clipped scope segment — so the lease id stays schema-valid
  for ANY scope_id length while distinct long scope_ids never collide into the
  same lane. Short scope_ids keep the readable, lossless form unchanged.

The full end-to-end acceptance — `cev3 review --spawn` with an out-of-repo
`--venue-root` launching a live venue — is exactly the behaviour Controller
dev-2 hand-worked-around for the PR #233 and #234 reviews; this fix makes it
work without the manual workaround.

The `validators/creator_engine_validator/**` edit requires the wheel pair to be
rebuilt: `creator_engine_validator-0.2.0-py3-none-any.whl` is rebuilt from
current source (`setuptools.build_meta`) and `validators/wheelhouse/SHA256SUMS`
re-pinned to the rebuilt digest. `_version.py` is left untouched (no version
bump — `verify_generated_version` stays clean).
