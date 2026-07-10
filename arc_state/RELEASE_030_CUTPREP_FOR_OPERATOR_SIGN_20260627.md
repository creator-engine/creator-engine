# 0.3.0 RELEASE — CUT-PREP & ONE-GESTURE OPERATOR SIGN

> Pre-drafted 2026-06-27 ~17:13Z for the night-shift Wave 1 (PRIMARY). Goal: the controller stages EVERYTHING to the signing seam autonomously; the Operator's part collapses to ONE review + ONE `ssh-keygen -Y sign` gesture (ce-root-v1, Operator-held). Companion to RESUME_STATE_CE_DEV2_NIGHTARC_20260627T1713Z.md.

## WHY 0.3.0 NOW
The Arad onboarding proved the published 0.2.0 wheel is broken for real users (schemas not packaged #331, tmux pane-parse #332, brownfield-apply #328). All fixed in main. 0.3.0 is what turns onboarding from "works only if dev-2 hand-holds + hand-patches" into "just works" — and lets Arad/Nitzan/next-user install cleanly. This is the night's headline.

## PREREQUISITES (verify ALL before staging)
- [ ] **#591 merged** (schemas packaging — ce-ops#331). At checkpoint: queued to merge. CONFIRM merged.
- [ ] Confirm in fresh **origin/main**: #590 (tmux #332) ✅merged · #586 (release anchor — SIGNING_KEY_ID should resolve to ce-root-v1, not ce-dev1-root-v1) · #587 (brownfield forge-identity #328) · #583 (install |sh→|bash).
- [ ] Re-verify the install-blocker fixes actually work from a CLEAN wheel built off main: build wheel → install in fresh venv → from a NON-repo CWD run `ce brain init` (must succeed — this is the exact #331 repro) AND confirm `ce launch` pane-identity parse handles tmux 3.4. (Do NOT trust the source tree; test the wheel.)
- [ ] Controller checkout is STALE (ce11-test-tier-split) — stage from a fresh origin/main worktree, not the polluted local HEAD.

## STAGE 1 — controller drives autonomously (⚙️, no Operator needed)
Run in an isolated worktree off fresh origin/main (worker or controller-fork):
1. **Version bump** 0.2.0 → 0.3.0 in `validators/pyproject.toml` (+ any `_versions.py`/version SSOT — grep `0.2.0`). One PR, governed (carrier + changelog fragment + work-class).
2. **Changelog**: `cev3 release-changelog` (Phase A machinery, #576) — assemble the 0.3.0 notes from `.ce/changelog/*` fragments. Lead with the user-facing install fixes (#331/#332/#328/#583).
3. **Baseline tag / wheelhouse / build env** (the Operator-named cut-prep): refresh the vendored wheelhouse for the offline install, set the release baseline tag, confirm the build env (python 3.14, `build` backend present).
4. **Stage the signed-release mirror**: run the Phase-A staging (`release_publish.py` / `cev3 release` stage path) with `--sign-mode placeholder`. This produces the publishable Pages mirror with a `<RESIGN-REQUIRED-ce-root-v1>` signature placeholder AND emits the EXACT `ssh-keygen -Y sign ...` command the Operator runs. Capture that command + the staged artifact path.
5. **Full gate green** on the bump PR + the staged artifact; merge the bump.
6. Surface to Operator: a single message = "staged 0.3.0 at <path>; review diff/changelog; run THIS command: <exact ssh-keygen -Y sign cmd>." 

## STAGE 2 — THE ONE OPERATOR GESTURE (🔒 R-reserved)
1. Review the staged mirror + changelog (one look).
2. Run the single emitted command with the Operator-held key:
   `ssh-keygen -Y sign -f <ce-root-v1 private key> -n file <staged-artifact>` (exact form emitted by Stage 1 step 4).
3. Hand the signature back (or drop it at the staged location). Controller finalizes publish (replace placeholder → publish Pages/release).

That's it — review + one sign command. Everything else is staged.

## VERIFY POST-PUBLISH
- [ ] Install the published 0.3.0 via the one-liner on a clean box (or fresh venv) → `ce onboard` / `ce brain init` from a non-repo CWD succeeds, signature verifies against ce-root-v1.
- [ ] Re-test Arad's path: a clean 0.3.0 install on her machine REPLACES the band-aids (remove the CWD `schemas/` + restore `tmux_adapter.py.bak`).

## ROLLBACK
Release staging is placeholder-gated and non-destructive until the Operator signs + publish runs. If the signed artifact fails verify, do not publish; re-stage. The 0.2.0 wheel stays the published default until 0.3.0 publish completes.

## NOTES
- Signing/publish is Phase B = R-reserved (ce-root-v1 stays the Operator's one gesture) — do NOT attempt to self-sign. Only `--sign-mode placeholder` is supported by code; root signing is Operator-gated by design.
- If SIGNING_KEY_ID in release_publish.py still reads `ce-dev1-root-v1` in main, #586 did NOT land correctly — STOP and fix the anchor before staging (the recipe must reference ce-root-v1 as the trust root).
