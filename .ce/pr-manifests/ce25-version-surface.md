# PR path manifest — ce25-version-surface · ce-ops#25 `ce --version` surface

Per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`, the ce-ops#21 convention). CI runs:

```bash
verify-path-manifest --base <PR base sha> --manifest-dir .ce/pr-manifests --head-ref ce25-version-surface
```

and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below
(the carrier lists itself); the repo-wide fidelity scan requires the declared count and
SHA256 to match the fenced block.

Ratified gate:
Operator-RATIFIED rev-2 gate spec `ce-25-version-surface-gate-spec-DRAFT-20260612.md`
(sha256 `244810b1e655f34a840ef6babd002b0a44b44bdcfb411a1cb4c905a014f3a87a`) on ce-ops#25.
Pinned @ `0e379d91`; re-ground to `b057f9ec` authorized + drift-checked, then ADOPT-RUN rebased to
`d25a45d4` (only mechanical drift: line-number shifts + version-boundary counters 52/35→53/36 from
intervening #210, which this gate does not touch — `_version.py`/`version.py` stay `shared`, so
v1/v3 counters are UNCHANGED).

Base:
`d25a45d47b0bd4d9b85be17eb6948a893f8a7dd8` (`main` = #213, F6 Phase-0 two-tier change-block
re-stamp). PRE-AUTHORIZED Fork-A ADOPT-RUN: this gate was authored concurrently with F6 Phase-0 on
base `b057f9ec` (#212); F6 landed first as #213, so this second-lander paid the declared adopt-run —
rebased onto `d25a45d4`, the ONLY conflict the shared wheelhouse pair (both gates rebuilt it),
resolved by REBUILDING the app wheel from rebased source + re-pinning `SHA256SUMS`. F6's forge/merge
paths are disjoint from this gate's; no other conflict.

The change (rev-2 Design):
One honest derived CE version identity `<semver>+<short-sha>` (`0.1.0+d25a45d4` at this base),
visible from `ce`/`cev3 --version`, `ce doctor`, the Cockpit (JSON `source.ce_version` + L3
header), and the governed session frame. The token is derived (live `git rev-parse --short=8 HEAD`
→ baked `BUILD_GIT_SHA` fallback → fail-closed), cached once per process per repo root; the L2
Cockpit fold never runs git. A generated `_version.py` (semver + the merge-parent build SHA,
`BUILD_GIT_SHA = d25a45d4…`) is committed before the wheel build so the wheel==source byte-parity
contract holds; the app wheel + `SHA256SUMS` are rebuilt in this PR (mandatory wheelhouse rule).

Per-file purpose (the closed path-set — 16 paths):
- **`.ce/pr-manifests/ce25-version-surface.md`** *(A)* — this carrier (self-inclusive).
- **`validators/creator_engine_validator/version.py`** *(M)* — the shared version API: `SEMVER`,
  `ce_version()`, the live-git/baked resolver (`functools.cache`), `add_version_flag()`, and the
  `--write-build-file` generator. `__version__` kept a literal (packaging AST guard).
- **`validators/creator_engine_validator/_version.py`** *(A)* — GENERATED build-identity constants
  (`SEMVER`, `BUILD_GIT_SHA` = the merge-parent HEAD); committed before the wheel build.
- **`validators/creator_engine_validator/__init__.py`** *(M)* — export `ce_version` beside
  `__version__`.
- **`validators/creator_engine_validator/ce_cli.py`** *(M)* — top-level `ce --version` (lazy action).
- **`validators/creator_engine_validator/v3_cli.py`** *(M)* — top-level `cev3 --version` (exits before
  the default `session`); cockpit resolves the token once and passes it into demo + live loaders;
  session passes the token into the banner + JSON.
- **`validators/creator_engine_validator/doctor_runtime.py`** *(M)* — `ce_version` in the JSON payload
  + `version=<token>` on the first human line.
- **`validators/creator_engine_validator/runner/cockpit_readmodel.py`** *(M)* — additive
  `source.ce_version` threaded through `fold_snapshot` + `snapshot_from_roots` (no `SNAPSHOT_VERSION`
  bump; the fold stays pure).
- **`validators/creator_engine_validator/v3_cockpit.py`** *(M)* — L3 header title from
  `snapshot["source"]["ce_version"]`, `APP_TITLE` prefix/fallback.
- **`validators/creator_engine_validator/v3_session.py`** *(M)* — `version` param on
  `render_banner`/`render_session` (pure render).
- **`validators/creator_engine_validator/packaging_runtime.py`** *(M)* — `verify_generated_version()`
  (semver parity + baked-SHA 40-hex + ancestor-of-HEAD) folded into the aggregate contract.
- **`validators/tests/unit/test_version_surface.py`** *(A)* — the version API + generator + all
  surface proofs (one token everywhere; L3 header textual-guarded).
- **`validators/tests/unit/test_packaging_contract.py`** *(M)* — generated-version parity tests
  (clean-on-repo + synthetic semver/SHA/missing-file drift + no-op without source tree).
- **`validators/tests/unit/test_wheelhouse_built_surface.py`** *(M)* — assert the wheel ships the
  `cev3` console script and bundles `_version.py`/`version.py` byte-identical to source.
- **`validators/wheelhouse/creator_engine_validator-0.1.0-py3-none-any.whl`** *(M)* — app wheel rebuilt
  from this branch's source (the byte-parity guard checks every bundled `.py` against source).
- **`validators/wheelhouse/SHA256SUMS`** *(M)* — re-pinned for the rebuilt wheel (line 2).

Canonicalization:
`sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=16

AUTHORIZED_PATHS_SHA256=2ce3701809ef376680630bc15c12fbdf3e63576bc42b4abb5169fa0d3d1e3482

```text
.ce/pr-manifests/ce25-version-surface.md
validators/creator_engine_validator/__init__.py
validators/creator_engine_validator/_version.py
validators/creator_engine_validator/ce_cli.py
validators/creator_engine_validator/doctor_runtime.py
validators/creator_engine_validator/packaging_runtime.py
validators/creator_engine_validator/runner/cockpit_readmodel.py
validators/creator_engine_validator/v3_cli.py
validators/creator_engine_validator/v3_cockpit.py
validators/creator_engine_validator/v3_session.py
validators/creator_engine_validator/version.py
validators/tests/unit/test_packaging_contract.py
validators/tests/unit/test_version_surface.py
validators/tests/unit/test_wheelhouse_built_surface.py
validators/wheelhouse/SHA256SUMS
validators/wheelhouse/creator_engine_validator-0.1.0-py3-none-any.whl
```
