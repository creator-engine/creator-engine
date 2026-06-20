# PR path manifest — ce-ops#45 (journey-cockpit elevation; Slice 1 + Slice 2)

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
branch carries TWO ratified slices, each a SEPARATE commit with its own review:

- **Slice 1 (read-only elevation)** — the solo-founder journey becomes the DEFAULT
  face; the expert ops board is demoted to a Dev face; a persisted CEO ↔ Dev persona
  switch is added; the full visual development-arc / roadmap is built; the
  decision-inbox becomes a first-class surface. Visual checkpoint **approved by the
  Operator**.
- **Slice 2 (the interactive write-seam)** — the decision-inbox can RESOLVE a
  decision, but ONLY by actuating the existing canonical escalation-resolve gate
  (`v3_cli.resolve_escalation`) with a form-echo confirmation
  ([[ce-authority-attaches-to-form]]). The cockpit becomes another *rendering* of the
  gate — it writes no governance state itself and bypasses nothing. Gets a governance
  review distinct from the Slice 1 visual one.

Hard laws honored across both: L1/L2/L3 separation (Slice 1's new data is additive
pure L2 on `snapshot["journey"]["arc"]`; Slice 2's write goes through the canonical
gate, never the view); `cev3 cockpit --json` parity (Slice 1 datums all carried;
Slice 2 adds NO new datum — `need_id` == the `escalation_id` the read-model already
carries); plain-language guard (`plain_copy_findings == 0`, incl. the form-echo).
The persona + resolve seams are both injected by the composition root, so
`v3_cockpit.py` does no file I/O and the L3 source guard stays green.

Base:
fresh `origin/main` (this branch `ce45-journey-cockpit-elevation` off `main`).

Per-file purpose (the closed path-set — 15 authored paths):
- **`.ce/changelog/ce45-journey-cockpit-elevation.md`** *(A)* — Slice 1 changelog fragment.
- **`.ce/changelog/ce45-journey-cockpit-elevation-slice2.md`** *(A)* — Slice 2 changelog fragment.
- **`.ce/pr-manifests/ce45-journey-cockpit-elevation.md`** *(A)* — this carrier (self-inclusive).
- **`docs/architecture/cockpit.md`** *(M)* — journey-as-default-face + roadmap + persona persistence (Slice 1) + the interactive resolve seam (Slice 2).
- **`docs/v3.5-roadmap.md`** *(M)* — WS-6: re-sequence #45 from DEFER.
- **`validators/creator_engine_validator/runner/cockpit_prefs.py`** *(A)* — the persona preference (pure core + tolerant I/O edge); textual-free.
- **`validators/creator_engine_validator/runner/cockpit_readmodel.py`** *(M)* — L2: full arc/roadmap (`stage_descriptions`, `lanes`, `position`, `journey_lane_count`).
- **`validators/creator_engine_validator/v3_cli.py`** *(M)* — `_cmd_cockpit` persona load/persist + the LIVE-mode `on_resolve` wiring; the reusable `resolve_escalation` gate seam (delegated from `_cmd_escalation_resolve`).
- **`validators/creator_engine_validator/v3_cockpit.py`** *(M)* — L3: `JourneyScreen`/`BoardScreen` + persona switch + first-class inbox (Slice 1); `ResolveConfirmScreen` form-echo + injected resolve actuation (Slice 2). Binds snapshot only; writes nothing.
- **`validators/tests/unit/test_cockpit_journey.py`** *(M)* — L2 journey/roadmap tests.
- **`validators/tests/unit/test_cockpit_prefs.py`** *(A)* — persona preference tests.
- **`validators/tests/unit/test_v3_cli.py`** *(M)* — the `resolve_escalation` seam + CLI-delegation tests.
- **`validators/tests/unit/test_v3_cockpit.py`** *(M)* — L3 source/journey guards + board smoke + CLI persona-wiring test.
- **`validators/tests/unit/test_v3_cockpit_journey.py`** *(M)* — L3 journey-face tests (default face, mode switch, persistence, roadmap, inbox).
- **`validators/tests/unit/test_v3_cockpit_resolve.py`** *(A)* — Slice 2 tests: form-echo, canonical-gate actuation, cancel, demo read-only, view-never-writes guard, CLI seam wiring.

WHEELHOUSE FOLLOW-UP (controller / release step — **amend this manifest +2 → 17 at that time**):
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

AUTHORIZED_PATHS_COUNT=15

AUTHORIZED_PATHS_SHA256=9a56f5ccf339ffbfe62222cde552688f4d7f46859f7424afc97977c3756e2cd4

```text
.ce/changelog/ce45-journey-cockpit-elevation-slice2.md
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
validators/tests/unit/test_v3_cli.py
validators/tests/unit/test_v3_cockpit.py
validators/tests/unit/test_v3_cockpit_journey.py
validators/tests/unit/test_v3_cockpit_resolve.py
```
