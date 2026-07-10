# SEED BRIEF — ce-ops#371: Auto-update P0 (startup NOTICE) — SEAT: dev-1 (non-contained)

**Ticket:** ce-ops#371. **Branch:** `ce-371-autoupdate-p0-startup-notice` (off origin/main). **Role:** implementer. **Work class:** `story` (declare by floor; bump to feature if diff exceeds).

## Goal (self-contained — embed, do not rely on reading the private ticket)
Add a **lightweight, fail-open, non-blocking startup update NOTICE** to CE on the solo end-user (Stable channel) path. Operator-ratified default = **`notify`** (NOT auto-apply). This is P0 of the auto-update mechanism — design report lives at `.ce/briefs/ce-auto-update-mechanism-REPORT-20260630.md` (read it; the design is decision-grade and grounded in current code).

## Scope — EXACTLY these four, nothing more (P0 closes design gaps 2 + 6)
1. **Lightweight check path in `validators/creator_engine_validator/update.py`:** a spec-only update check that resolves the latest signed release's version/signature from `llms-install.md` **WITHOUT fetching wheels** (today `check_for_update()` downloads+verifies wheels — too heavy for startup). Reuse the existing trust-anchor/SSHSIG verify, but stop at version comparison. Must be **rate-limited + cached** and have a **fetcher timeout + fail-open** (any error/timeout → silent no-op; NEVER block or slow startup). Note: `update.py.default_fetcher` currently has no timeout — add one on this path.
2. **Non-blocking startup NOTICE:** when an interactive solo user on Stable starts `ce` and a newer signed release exists, print a one-line notice (e.g. `ce 0.3.1 available — run 'ce update'`). Shown at most once per cache window; interactive sessions only; never in non-interactive/JSON/piped output.
3. **Posture gate — statically OFF in governed/contained/fleet seats.** Reuse the existing posture predicate + the `toolchain_self_update` deny path in `hook_check.py`. Under containment/governed posture the startup checker must NOT run at all (egress-restricted + doctrinally forbidden; fleet updates flow controller→`fleet_rollout`, never self-check).
4. **Opt-out** surface so the checker can be disabled. (Full `auto_update: notify|apply|off` config + onboarding answer is **P1 — OUT OF SCOPE here**.)

## Hard out-of-scope (do NOT touch)
- Any auto-APPLY behavior. Any `ce update --auto` cron path. Any signed recall/min-version floor (those are P1/P2). Do not modify `fleet_rollout.py`'s rollout logic.

## Evidence / DoD
- Test proving the check is **time-boxed + fail-open** (simulate slow/erroring fetcher → startup proceeds, no notice, no raise).
- Test proving the checker is OFF under governed/contained posture and ON for interactive solo Stable.
- Test proving **no wheel download** on the check path.
- Opt-out honored. Per-PR `.ce/changelog/<slug>.md` + carrier (`carrier_gen.write_carriers(base=<merge-base>)`) + correct work-class line in PR body.

## Stop line
Run FULL `ce validate-pr` GREEN locally (CI-parity, one pass) BEFORE self-push. Then `git commit && echo <SHA>` and push the branch + open the PR as your own dev-1 identity. Report: branch, commit SHA, PR#, preflight result line. Do NOT approve/merge — controller holds the gate.
