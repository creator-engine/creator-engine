# PR path manifest — ce-ops#45 (journey-cockpit elevation; full + Slice 1)

Per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`, ce-ops#21). CI runs:

```bash
verify-path-manifest --base <PR base sha> --manifest-dir .ce/pr-manifests --head-ref ce45-journey-cockpit-elevation
```

and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set
below (the carrier lists itself); the fidelity scan requires the declared count and
SHA256 to match the fenced block.

Ratified scope:
**`/home/cedev2/ce-briefs/ce45-journey-cockpit-elevation.md`** (SHA256
`5bc70c04e0a012d6334448d7b6eb8191959b0bc01eb247e28bbcd54474038aa9`), ce-ops#45 —
the journey-cockpit **elevation**, superseding the PR #230 "ratified minimum". This
carrier covers **Slice 1 only** (read-only elevation): the solo-founder journey
becomes the DEFAULT face, the expert ops board is demoted to a Dev face, a
persisted CEO ↔ Dev persona switch is added, the full visual development-arc /
roadmap is built, and the decision-inbox becomes a first-class surface. Slice 2
(the interactive governance write-seam) is a SEPARATE, governance-reviewed PR and
is **not** in this set.

L2/L3 hard law honored: all new computation is additive pure data on
`snapshot["journey"]["arc"]` (`stage_descriptions` / `lanes` / `position` /
`journey_lane_count`) in `runner/cockpit_readmodel.py`; `v3_cockpit.py` is
view-only (the L3 source guard stays green — no loader, no file I/O). The persona
is a UI preference (not governance state, not in the snapshot): a new textual-free
`runner/cockpit_prefs.py` (pure normalize/fold + a tolerant I/O edge) read by the
composition root (`v3_cli._cmd_cockpit`) and injected into the view with an
`on_persona_change` callback. Read-only surface — no approve/resolve/sync/dispatch/
merge/push/write path. No new schema or check.

Base:
fresh `origin/main` (this branch `ce45-journey-cockpit-elevation` off `main`).

Per-file purpose (the closed path-set — 12 authored paths):
- **`.ce/changelog/ce45-journey-cockpit-elevation.md`** *(A)* — changelog fragment.
- **`.ce/pr-manifests/ce45-journey-cockpit-elevation.md`** *(A)* — this carrier (self-inclusive).
- **`docs/architecture/cockpit.md`** *(M)* — journey-as-default-face + roadmap + persona-persistence architecture.
- **`docs/v3.5-roadmap.md`** *(M)* — WS-6: re-sequence #45 from DEFER (Slice 1 in progress).
- **`validators/creator_engine_validator/runner/cockpit_prefs.py`** *(A)* — the persona preference (pure core + tolerant I/O edge); textual-free.
- **`validators/creator_engine_validator/runner/cockpit_readmodel.py`** *(M)* — L2: enrich `_fold_journey` with the full arc/roadmap (`stage_descriptions`, `lanes`, `position`, `journey_lane_count`).
- **`validators/creator_engine_validator/v3_cli.py`** *(M)* — `_cmd_cockpit`: load/persist the persona via `cockpit_prefs`, inject into `run_app`.
- **`validators/creator_engine_validator/v3_cockpit.py`** *(M)* — L3: `JourneyScreen` (default face) + `BoardScreen` (Dev face) + persona mode switch + first-class decision-inbox; binds snapshot only.
- **`validators/tests/unit/test_cockpit_journey.py`** *(M)* — L2 journey/roadmap tests (arc lanes, descriptions, position).
- **`validators/tests/unit/test_cockpit_prefs.py`** *(A)* — persona preference tests.
- **`validators/tests/unit/test_v3_cockpit.py`** *(M)* — L3 source-guard + board smoke + CLI persona-wiring test.
- **`validators/tests/unit/test_v3_cockpit_journey.py`** *(M)* — L3 journey-face tests (default face, mode switch, persistence callback, roadmap render, first-class inbox).

WHEELHOUSE FOLLOW-UP (controller / release step — **amend this manifest +2 → 14 at that time**):
editing `cockpit_readmodel.py` / `v3_cli.py` / `v3_cockpit.py` and adding
`runner/cockpit_prefs.py` (all shipped in the app wheel) drifts the packaging
contract (`verify_wheel_matches_source`), exactly as the #230 lane manifest noted.
The app wheel must be rebuilt and `validators/wheelhouse/SHA256SUMS` re-pinned,
adding these two paths to the authorized set:
- `validators/wheelhouse/creator_engine_validator-0.2.0-py3-none-any.whl` *(M)*
- `validators/wheelhouse/SHA256SUMS` *(M)*

This is **deliberately left to the controller/release step**: a governed worker
seat cannot correctly bake the merge-parent SHA into `_version.py` (`BUILD_GIT_SHA`)
before the commit is pushed/merged, and ADR-0006 (accepted) keeps derived artifacts
out of the author trust path. The 2 packaging-contract tests are the only expected
red on this branch; every source/logic test is green.

Canonicalization:
`sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=12

AUTHORIZED_PATHS_SHA256=ef7846e13878c8bb6858caba5a1e6b832997657331a0d7c77e7a7768a8de3d3c

```text
.ce/changelog/ce45-journey-cockpit-elevation.md
.ce/pr-manifests/ce45-journey-cockpit-elevation.md
docs/architecture/cockpit.md
docs/v3.5-roadmap.md
validators/creator_engine_validator/runner/cockpit_prefs.py
validators/creator_engine_validator/runner/cockpit_readmodel.py
validators/creator_engine_validator/v3_cli.py
validators/creator_engine_validator/v3_cockpit.py
validators/tests/unit/test_cockpit_journey.py
validators/tests/unit/test_cockpit_prefs.py
validators/tests/unit/test_v3_cockpit.py
validators/tests/unit/test_v3_cockpit_journey.py
```
