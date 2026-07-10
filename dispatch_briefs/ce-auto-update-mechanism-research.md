# RESEARCH HANDOFF — Should `ce` auto-update (on startup), and how — governed & safe?

**Requested by:** Operator (2026-06-30). **Role:** architect_research (READ-ONLY; decision-grade report, no code changes). **Decision owner:** Operator.

## The question
Today a pilot user (Arad) installs `0.3.0`; when `0.3.1` ships, how does he get it? The Operator's premise: **updates shouldn't be left to the user** — `ce` should ideally **check/apply updates automatically (on startup?)**. Assess what exists, then design the governed, safe auto-update path.

## Ground in CURRENT code (CE already has partial machinery — map it first)
- `validators/creator_engine_validator/update.py` and the `ce update` group (`ce_cli.py` ~line 237 parser, ~4546 handler) — what does `ce update` do TODAY? What does it update (the `ce` install itself? rented surfaces? toolchain?), and how (re-run signed install.sh? pull a release asset?).
- `validators/creator_engine_validator/surfaces/check_updates.py` — is there already an update-CHECK? What does it check against (GitHub releases? a manifest?).
- `validators/creator_engine_validator/hook_check.py` + `test_hook_check.py` — is there a hook that could run an update check on startup/launch?
- `validators/creator_engine_validator/surfaces/fleet_rollout.py` — the FLEET-side rollout path.
- `launch_runtime.py` (`ce launch`) — the startup seam where an auto-check could live (note it already does brain-bootstrap gating).
- The signed-install trust anchor: `install.sh` / `llms-install.md`, `PINNED_KEYS`, the install-sig guard (ce-ops#364 / #673, now blocking) — SSHSIG verify-before-execute.

## Questions the report must answer
1. **Current state:** exactly what `ce update` / check_updates / hook_check do now, and what's missing for "auto-update on startup."
2. **Should it auto-run on startup?** Trade-offs: UX (zero-touch updates) vs surprise/latency/reliability at launch vs reproducibility. Recommend a cadence + trigger (startup check, background, opt-out?).
3. **Safety model (critical):** auto-applying an update = auto-executing freshly-fetched code. Must reconcile with the existing **signed-install** trust anchor: signature verify-before-execute, version pinning, atomic/staged apply, **rollback on failure**, and surfacing the changelog. What's the failure-closed posture?
4. **The governance carve-out (do NOT miss this):** CE doctrine = "ONE governed mechanism to update every rented surface; **contained fleet seats NEVER self-update toolchain**" ([[ce-govern-rented-surface-updates]]). So design MUST distinguish:
   - **End-user installed CE (solo-tier, e.g. Arad):** auto-update is desirable — design it.
   - **Contained/fleet seats:** must NOT self-update; updates flow via the governed rollout (`fleet_rollout.py`). Keep these paths separate and explain the boundary.
5. **Tiering:** how does auto-update differ for solo-tier user vs full-fleet deployment? Map to `fleet_rollout.py`.
6. **Channels:** stable-release (Arad on 0.3.x) vs main-HEAD (contributor like Nitzan / auto-track-main) — does auto-update mean "latest release" for users and "track main" for contributors? Reconcile with the deploy/version-channel model.
7. If recommending a build: a concrete design (where the check lives, the verify→stage→apply→rollback flow, opt-out/config, telemetry) + a phased roadmap + which existing modules to extend vs build.

## Discipline
Be skeptical both ways (don't rubber-stamp "auto-update everything"; auto-executing fetched code is a real attack surface — weigh it). Ground capability claims in the CURRENT code and current vendor/security practice, not assumptions. Return a decision-grade report for Operator ratification; persist nothing yourself (controller persists).
