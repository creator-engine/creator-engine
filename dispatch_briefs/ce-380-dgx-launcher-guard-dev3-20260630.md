# SEED BRIEF — surfaces_manifest guard for DGX launcher image (ce-ops#380) — SEAT: dev-3

**Branch:** `ce-380-dgx-launcher-image-guard` off CURRENT origin/main (FIRST `git fetch origin` + worktree off origin/main — do not work stale). **Role:** implementer. **Work class:** declare by floor (XS/S). **No push auth** → commit + echo SHA; controller harvests.

## Problem (self-contained — do NOT rely on reading any private ticket)
The repo has a CI check that guards the VPS seat launcher's default image against the surface manifest, but the **DGX launcher has no equivalent guard**, so a future manifest version bump that forgets to update the DGX run-wrapper passes CI silently and can relaunch the DGX seat on a stale/broken image. (This actually happened: a stale-branch launcher defaulted to an old image missing ssh-keygen/PyNaCl.)

## The fix (symmetric extension of the existing guard)
1. Read `validators/creator_engine_validator/checks/surfaces_manifest.py` — find `_runsc_image_errors` (around lines 415–435) which currently validates the **VPS** launcher `CE_VPS_IMAGE` default in `deploy/vps-runsc/run-vps-runsc.sh` against the surface manifest's codex image/tag.
2. Extend it **symmetrically** to ALSO validate the **DGX** launcher's `CE_DGX_IMAGE` default in `deploy/dgx-runsc/run-codex-runsc.sh` against the manifest's expected DGX image tag (`creator-engine/codex-runsc:<version>-aarch64`). Reuse the SAME parsing/comparison helper; do not duplicate logic — generalize it over a small table of (script_path, env_var, expected_image) if that's cleaner. Match how the existing check extracts the default (it likely greps the `${CE_VPS_IMAGE:-...}` default) and how it derives the expected image from `surfaces/render.py` / the manifest.
3. Emit a clear, actionable error when they drift (name the script, the found default, the expected value) — mirror the existing VPS error message style.

## Tests
- Find the existing test for the VPS guard (likely in `validators/tests/unit/test_surfaces_manifest.py` or `test_surface_build_wiring.py`). Add a symmetric test fixture/case asserting: (a) DGX launcher default MATCHING the manifest passes; (b) a DGX launcher default that DIVERGES from the manifest fails with the new error. Keep the existing VPS coverage intact.
- This guard runs against the REAL repo files — make sure the check passes on current main (origin/main's `run-codex-runsc.sh` should already be at the correct version post-#687; if the check would FAIL on current main, that means the wrapper is genuinely out of sync → STOP and report rather than weakening the check).

## Carrier / changelog / preflight
Carrier `.ce/pr-manifests/ce-380-dgx-launcher-image-guard.md` (carrier_gen, stem==branch slug) + changelog `.ce/changelog/ce-380-*.md`; path-set == base..HEAD. Run FULL preflight GREEN in ONE pass (`TMPDIR=/var/tmp .venv/bin/python -m pytest -q <the surfaces_manifest test file>` + carrier/changelog gates). venv: `.venv/bin/python` (no activate).

## Stop line
Commit with `git commit && echo <SHA>`; report SHA + files + how you generalized the check + preflight result. If the guard reveals current main's DGX wrapper is genuinely out of sync with the manifest, STOP and report (don't weaken the check to make it pass). Do NOT push/approve/merge or scope-creep beyond this guard + test.
