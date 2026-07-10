# RUNBOOK — dev-4 Retirement & Clean-Install (Fleet-Retirement M1, first canary)

**Author:** CE-DEV-2 controller (cedev2 @ DGX), 2026-06-22. **Status: DRAFT — awaiting Operator GO.**
**Program:** [[ce-fleet-retirement-clean-install-program]]. dev-4 = first seat (Operator pick). Goal: replace dev-4's patchwork (stale dev-wheel `ce` + source-checkout-bypass via `PYTHONPATH=validators python -m`) with a GENUINE clean install of `ce` from the signed publish pipeline, brain-bootstrapped, where the seat RUNS from installed `ce`. Validate end-to-end, then proceed to next seat.

## TARGET STATE (recon 2026-06-22)
- dev-4 = `cedev4` on THIS DGX; `ssh cedev4@localhost -i ~/.ssh/id_ed25519`; codex gpt-5.5 controller, tmux `dev4stage1` %0; HELD/idle.
- Current `ce`: `~/.local/bin/ce` → `~/.local/share/creator-engine/bootstrap/venv/bin/ce` = **`0.2.0+ac513c4f` (DEV wheel, local +sha, Jun 18)** — NOT a clean published release.
- Works in source checkout `~/ce-workspaces/creator-engine`, branch `ce157-mint-broker`.
- Identity to preserve: git `ce-dev-4` <294754021+ce-dev-4@users.noreply.github.com>; `~/.codex` (auth.json, config.toml, AGENTS.md); `~/.ssh`; any `~/.ce-keys`; GH tokens.

## PRECONDITIONS (front-loaded; ALL must clear before any destructive step)
- **P1 — Fleet HELD ✅** dev-1/3/4 idle, no pickup. (Done 2026-06-22.)
- **P2 — Drain ce157 ⚠️ CONFIRMED REQUIRED.** `origin/main...ce157-mint-broker` = **17 files, +2297 lines UNMERGED** (new `tools/mint-broker/` pkg: binding/config/service; `forge/user_install_discovery.py`; `onboard_apply_live` changes; full test suite; rebuilt wheel). #300 merged an earlier "#157 S1-S6"; #330 (#157) was CLOSED unmerged. **Action: push `ce157-mint-broker` to origin (preserve remotely) + open/restore a PR BEFORE touching dev-4's checkout.** Disposition (merge vs park) decided separately — but the bits must be safe off the local-only branch first. Do NOT wipe until pushed.
- **P3 — Published signed release exists ⚠️ VERIFY/LIKELY-BLOCKER.** `install.sh` pulls a signed artifact manifest from `creator-engine.dev/downloads/` (package_version). dev-4's current install is a dev wheel, not a published release. #80 (signed publish pipeline) only just merged → a clean signed release may not be staged on the site yet. **Action: confirm a current signed release is live+reachable at creator-engine.dev/downloads/, OR cut+publish one via the #80 pipeline FIRST.** This may gate the whole canary.
- **P4 — Identity/credential backup.** Snapshot `~/.codex` (auth.json/config.toml/AGENTS.md), `~/.ssh`, `~/.ce-keys`, `git config`, GH token config to a safe location (on cedev2 or `~/cedev4-identity-backup-<ts>`). Verify restorable.
- **P5 — Capture dev-4 working/resume state.** Save its current codex session note + branch state; record its AGENTS.md (foreman/proactive-pickup directives) for re-seed.
- **P6 — Rollback artifacts retained.** RENAME (don't delete) the old install (`~/.local/share/creator-engine/bootstrap`) + old `ce`/`cev3` symlinks + the source checkout, so we can restore if acceptance fails.

## EXECUTION (after GO; ⚠️ ownership flagged)
- **S1.** Final ce157 drain per P2 (push + PR). Verify origin has the branch.
- **S2.** Backup identity/creds per P4. Confirm.
- **S3.** Quiesce dev-4 codex controller for reinstall. ⚠️ **Per [[ce-seat-relaunch-canonical-launch-only]], stopping/restarting a contained codex seat = root/Operator via canonical `ce launch`, NOT cedev2 ssh send-keys.** So S3+S7 are Operator/root actions.
- **S4.** Remove patchwork TOOLCHAIN: rename old dev-wheel install + clear the `PYTHONPATH=validators python -m` invocation pattern (rollback-safe rename).
- **S5.** Clean-install via signed `install.sh` (verify signed spec → venv → wheels → `~/.local/bin/ce`). Confirm `ce --version` = released version (NO `+localsha`).
- **S6.** Working clone: ensure a clean `creator-engine` checkout on main for dev-4 to develop in (working-tree ≠ toolchain).
- **S7.** `ce brain init` the workspace repo-root → brain ledger present (#206; verify the M1 prereq we just built).
- **S8.** Restart codex controller via canonical `ce launch` (Operator/root); re-seed AGENTS.md updated to invoke **installed `ce`** (not `python -m`), keep foreman/proactive-pickup directives.
- **S9.** Release dev-4 from HOLD.

## ACCEPTANCE GATE (promote dev-4 + proceed to next seat only when ALL pass)
- **A1.** `ce --version` = clean released wheel (no `+localsha` dev suffix).
- **A2.** dev-4 governs via installed `ce` (verify AGENTS.md/config invoke `ce`, not source `python -m`).
- **A3.** dev-4 completes ONE real e2e cycle from the clean install: **pickup → claim → allocate → launch a governed lane → do work → open a PR**, ZERO source-toolchain / hand-bootstrap intervention. ← the dogfood proof.
- **A4.** Only after A1-A3: remove rollback artifacts (P6).

## ROLLBACK
If acceptance fails: restore renamed old install + symlinks + checkout (P6), re-seed dev-4 to prior state (P5), release HOLD. dev-4 returns to patchwork operation; file what broke; do not proceed to next seat.

## OPEN OPERATOR DECISIONS (flag, not guess)
- **Q1 — Ownership of S3/S5/S7/S8** (destructive reinstall + canonical relaunch). Seat-relaunch rule → root/Operator. Confirm you drive these (I prep P2/P4/P5/P6 + verify acceptance), or authorize me a specific mechanism.
- **Q2 — Dogfood depth:** does dev-4 govern its own work with the INSTALLED (released) `ce`, moving forward via `ce update` like a real user (full dogfood loop)? (Recommended — it's the whole point.)
- **Q3 — Release prerequisite (P3):** if no signed release is published yet, cut+publish one via #80 FIRST (adds a step before the canary). Confirm.
- **Q4 — ce157 disposition:** after pushing it safe (P2), merge it or park it? (Separate from the retirement.)
