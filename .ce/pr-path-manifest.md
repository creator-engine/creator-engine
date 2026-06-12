# PR path manifest — v3.1-G2b review-venue run-id + venue-cwd fix-gate

CI passes this to `verify-path-manifest --base <PR base sha> --manifest .ce/pr-path-manifest.md`
and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; the
fidelity scan requires the declared count and SHA256 to match the fenced block.

Ratified gate:
Operator-RATIFIED fix-gate `esc-14-l7-venue-id-defect` (ce-ops#14, the v3.1 retirement run),
2026-06-12 in-session, with two binding amendments. Remediates two L7 live-drive HALTs in the
reviewer-venue leg of `v3_seat_bridge`:
- **run-id defect** (`esc-14-l7-venue-id-defect`): the review mint produced a run-id carrying the
  compact UTC stamp's uppercase `T`/`Z`, which `cev3 review --spawn` feeds to `pco-allocate` as the
  ledger lane id — fail-closed refused twice (lane pattern `^[a-z][a-z0-9-]{2,63}$`; derived lease
  id `lease-<lane>-<14-digit stamp>` overflowing the 64-char worktree-lease bound). Fix: lowercase
  the stamp and shorten the prefix (`run-review-` → `rev-`).
- **venue-cwd defect** (`esc-14-l7-venue-cwd-defect`, 2nd amendment): `spawn_review_venue`'s
  `ce lane launch` omitted `--worktree-path`; `lane_runtime` sets cwd only from it, so the relative
  `--mcp-config` failed under `--strict-mcp-config` and the venue claude died at birth while launch
  reported success. Fix: pass `--worktree-path <venue_root>/<run_id>`.

Both failures are now CI-visible forever via a schema-read id-shape test and a lane-launch argv
assertion. The wheel is rebuilt from this branch source and `SHA256SUMS` re-pinned so the
packaging contract (`test_packaging_contract.py::test_verify_wheel_matches_source_is_clean_on_repo`)
passes — CI hard-enforces wheel↔source parity.

Base:
`b4fba47b7cecb3531b4a1cc5642cd2cf7d29d6e9` (origin/main = #203, the v3.1-G2 keystone).

Per-file purpose (the closed path-set — 5 paths, as ratified):
- **`.ce/pr-path-manifest.md`** *(M)* — this carrier: authorized path-set count,
  hash, fenced block, base, and ratification note.
- **`validators/creator_engine_validator/v3_seat_bridge.py`** *(M)* — the review mint
  `rev-<scope_id>-<lowercased utcstamp>` (single mint site; `role: reviewer` is the discriminator)
  + `spawn_review_venue` now passes `--worktree-path` + updated docstring.
- **`validators/tests/unit/test_v3_seat_bridge.py`** *(M)* — adds the id-shape regression
  (run-id + derived lease id satisfy lane/lease patterns READ FROM the schemas) and asserts the
  lane-launch argv carries `--worktree-path <venue_root>/<run_id>`.
- **`validators/wheelhouse/creator_engine_validator-0.1.0-py3-none-any.whl`** *(M)*
  — rebuilt from this branch source so CI's wheel↔source contract holds.
- **`validators/wheelhouse/SHA256SUMS`** *(M)* — re-pinned for the rebuilt wheel.

Carrier sequencing (declared):
Open PR #204 also carries `.ce/pr-path-manifest.md`. Ratified order = this fix-gate merges
first; #204 rebases under the base-only refresh micro-auth.

Canonicalization:
`sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=5

AUTHORIZED_PATHS_SHA256=93114401afe64286b4dd2615e9a56c81ad4b8668e7dde29fd64c9475008179a5

```text
.ce/pr-path-manifest.md
validators/creator_engine_validator/v3_seat_bridge.py
validators/tests/unit/test_v3_seat_bridge.py
validators/wheelhouse/SHA256SUMS
validators/wheelhouse/creator_engine_validator-0.1.0-py3-none-any.whl
```
