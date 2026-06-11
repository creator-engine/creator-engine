# PR path manifest - v3.1-G2 forge-leg join (the pitch-arc keystone)

CI passes this to `verify-path-manifest --base <PR base sha> --manifest .ce/pr-path-manifest.md`
and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; the
fidelity scan requires the declared count and SHA256 to match the fenced block.

Ratified gate:
Operator-RATIFIED v3.1-G2 spec (sha256 `a91663b1...`), ce-ops#13 W1 keystone,
2026-06-11 in-session. ONE gate runs Scope->ratify->drive->seat->PR-open->
independent-review->merge through the v3 product surface (a pure v3->v3 composition
beyond the named `ce_cli --json` v1 fix). The retirement RUN itself is ce-ops#14,
a separately-ratified operation.

Base:
`a5af150392ab2e23eeaece6eee5f000d413a87f0` (origin/main = #202, trust root).

Per-file purpose (the closed path-set - 17 paths, as ratified):
- **`.ce/pr-path-manifest.md`** *(M)* - this carrier: authorized path-set count,
  hash, fenced block, base, and ratification note.
- **`docs/v3-roadmap.md`** *(M)* - the v3.1-G2 row (LANDING).
- **`schemas/dispatch-record.schema.yaml`** *(M)* - additive `change` (G2a) +
  `role`/`review_of` (G2b) fields; every existing G1 record stays valid.
- **`validators/creator_engine_validator/_versions.py`** *(M)* - V3_RUNTIME 33->35
  (`forge.change_push` + `v3_forge_join`); V1/registry/allowlist/V3_SCHEMAS unchanged.
- **`validators/creator_engine_validator/ce_cli.py`** *(M)* - the ONLY v1 edit:
  `ce lane launch --json` (the reviewer-venue consumption seam).
- **`validators/creator_engine_validator/forge/change_push.py`** *(A)* - the
  missing branch-push primitive (plan-by-default; CONSTRUCTED HTTPS remote; never force).
- **`validators/creator_engine_validator/v3_cli.py`** *(M)* - `cev3 pr` + collect
  change-block derivation (G2a) · `cev3 review` (G2b) · `cev3 merge` + show/status (G2c).
- **`validators/creator_engine_validator/v3_forge_join.py`** *(A)* - the forge-leg
  composition root (load_app_config · openssl_signer · open_change_for_run ·
  merge_for_run); imports NO v1 module.
- **`validators/creator_engine_validator/v3_seat_bridge.py`** *(M)* - the
  reviewer-venue leg (compose_reviewer_envelope · materialize_review_dispatch ·
  spawn_review_venue); still imports NO v1 module.
- **`validators/tests/unit/test_ce_lane_cli.py`** *(M)* - `--json` record +
  byte-unchanged human path.
- **`validators/tests/unit/test_change_push.py`** *(A)* - push hygiene + never-force.
- **`validators/tests/unit/test_v3_cli.py`** *(M)* - pr/review/merge + collect
  derivation + read-model + the end-to-end faked drive.
- **`validators/tests/unit/test_v3_forge_join.py`** *(A)* - AST no-v1 · app-config ·
  openssl signer · mint->push->open->stamp->revoke · merge_for_run.
- **`validators/tests/unit/test_v3_seat_bridge.py`** *(M)* - reviewer-venue leg
  (schema-valid envelope · role/review_of · fail-closed spawn).
- **`validators/tests/unit/test_version_boundary.py`** *(M)* - count 33->35
  (co-moved with `_versions.py`).
- **`validators/wheelhouse/creator_engine_validator-0.1.0-py3-none-any.whl`** *(M)*
  - rebuilt from the combined branch source.
- **`validators/wheelhouse/SHA256SUMS`** *(M)* - re-pinned for the rebuilt wheel.

Canonicalization:
`sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=17

AUTHORIZED_PATHS_SHA256=5ce5adb81595a067c1716ffeb4864d6087f31b86d402b777afdca60b6ad879e7

```text
.ce/pr-path-manifest.md
docs/v3-roadmap.md
schemas/dispatch-record.schema.yaml
validators/creator_engine_validator/_versions.py
validators/creator_engine_validator/ce_cli.py
validators/creator_engine_validator/forge/change_push.py
validators/creator_engine_validator/v3_cli.py
validators/creator_engine_validator/v3_forge_join.py
validators/creator_engine_validator/v3_seat_bridge.py
validators/tests/unit/test_ce_lane_cli.py
validators/tests/unit/test_change_push.py
validators/tests/unit/test_v3_cli.py
validators/tests/unit/test_v3_forge_join.py
validators/tests/unit/test_v3_seat_bridge.py
validators/tests/unit/test_version_boundary.py
validators/wheelhouse/SHA256SUMS
validators/wheelhouse/creator_engine_validator-0.1.0-py3-none-any.whl
```
