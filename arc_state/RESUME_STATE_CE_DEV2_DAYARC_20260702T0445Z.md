# RESUME STATE — CE-DEV-2 Orchestrator — 2026-07-02 ~04:45Z (DAY, autonomous)

> NEWEST — supersedes all prior 2026-07-02 resumes. Open MEMORY.md + NIGHTARC_MANDATE_CE_DEV2_20260701.md first.
> Arc authority = batch-ratified night grants (G-N1..G-N7; code≤M = 2-review quorum; docs XS/S single review).
> **Today: first external test user + contributor (Nitzan) onboarding — onboarding-path quality is pitch-critical.**
> Context window ~1M — do NOT self-throttle. main == live == 0.3.1. Merge daemon pid 648947 healthy (single instance; a 2nd pgrep hit = self-match footgun, not a dup). Token durable/restart-safe.

## ✅ MERGED THIS SESSION (all landed to main)
#719 libsodium(#339) · #724 prbody-parity(#370) · #721 pickup-filter(N2) · #723 self-push-canary(#337) · #718 conveyor-daemon-DISARMED(N1 core). (Earlier day: #713/#715/#716/#717.)

## ✅ OPERATOR RATIFIED 2026-07-02 (all controller recs approved as written) — [[ce-mainhead-install-option-a-ratified]]
1. **Main-HEAD install → Option A RATIFIED retroactively.** ADR-0003 = Accepted. **PR #725 APPROVED + ENQUEUED** (merging) → then verify merged. **ce-ops#366 CLOSED.** Unblocks L1.a clean-main-install + L1.b `ce update --track main`. Future-surface guard = ce-ops#389.
2. **Conveyor arming (G-N3) → HELD, design-pass first.** #718 merged DISARMED (5 adversarial rounds closed ALL code-level RCEs: validate_command/base/remote pinned, paths confined under daemon-pinned roots, TOCTOU closed). Arm ONLY after the redesign + independent review = **ce-ops#388** (payload-as-data-only + daemon-owned dirs + seat-authored-bundle CONTENT-trust). dev-4 drafting the #388 ADR now.
3. **#720 onboarding guide → publish WHEN fixes re-review GREEN** (don't publish before vocabulary/false-banner fixes land).

## 🔄 IN-FLIGHT
- **#725** (ratified ADR) — APPROVED, in merge queue → **verify it merges** next session.
- **#720 guide** (dev-1, branch ce-329-scrum-to-ce-guide, DRAFT) — dev-1 applying 2 fixes (restore canonical Frame→Shape→Build→Review→Ship vocab + cross-links; remove false "unlinked" banner). When pushed → re-review (docs) → then PUBLISH (Operator ratified publish-when-green) → un-draft + merge.
- **dev-3** (contained VPS): CE-native `ce init` (ce-ops#367, branch ce-367-ce-native-init) — Working. Replaces retired speckit. New `ce` group → needs gen_cli_reference --write + docs-reconciliation coupling. Harvest when done (harvest_intake).
- **dev-4** (contained DGX): #388 conveyor-redesign ADR (branch ce-388-conveyor-redesign-adr, docs-only) — Working. Harvest → DRAFT PR → Operator reviews the arm-safety model.
- Claims in .ce/claims/. PR-board watcher (Monitor bv4v0ibf4) armed persistent.

## ⏸️ AWAITING-OPERATOR (surface FIRST next session)
1. **#720 publication** — ratified "publish when green"; execute once dev-1 fixes land + re-review passes.
2. **#388 conveyor-redesign ADR** — bring the draft to Operator to ratify the arm-safety model (unblocks G-N3 arming).

## ⏭️ NEXT ACTIONS (fresh context)
1. Verify #725 merged; if queue stalled, check merge_group run (it's approved+clean).
2. Harvest dev-3 (#367 CE-native init) + dev-4 (#388 ADR) when they signal done (probe worktree; contained seats trap work — done-but-unpushed ≠ stalled). dev-3 via harvest_intake (git-bundle: docker exec cat, NOT docker cp on runsc); dev-4 same.
3. Re-review + gate #720 when dev-1 pushes fixes → then publish (Operator-ratified).
4. Re-feed seats after harvest — NO idle. Clean disjoint lanes: ce-ops#369 Fleet-IaC guard, #376 unscheduled-sweep, #368 test-coupling-gate (PROBE not-already-landed — test_coupling.py already on main). NOT conveyor code (that's #388 redesign territory).
5. **DEFERRED controller ops** (do at a quiet window, NOT while the seat is mid-task):
   - **dev-3 container RELAUNCH** to activate #723's launcher fix (self-push spine) — after #367 harvested + dev-3 idle. Canonical launch only; then verify self-push canary passes e2e.
   - **dev-4 image rebuild+relaunch** to bake in #719 system libsodium (arm64 base-digest override, ce-ops#377) — after #388 harvested + dev-4 idle. Relaunch as cedev4 via run-codex-runsc.sh + codex re-auth.

## TICKETS FILED THIS SESSION (all ce-ops, OPEN)
#383 conveyor argv option-smuggling hardening · #384 internal DevOps agent + runbook SSOT · #385 work-class vocab doc-drift (tiny|story|feature|epic → XS/S/M/L; also in role prompts) · #386 wheel-build test-isolation flake (xdist_group) · #387 PR-side awaiting-operator gate lacks _BLOCKING_LABELS · #388 conveyor security-redesign-before-arming · #389 ratification-gate pattern for trust surfaces.
Also: ce-ops#184 (VPS /tmp guard) CLOSED — fixed live via passwordless VPS sudo (tmpfiles.d 1d aging + 6h clean cadence; 11G→360K). ce-ops#367 REDIRECTED to CE-native init (speckit retired; PR #722 closed).

## KEY FACTS
- Auth: overwatch `set -a; source ~/.ce-keys/overwatch.env; set +a; export GH_TOKEN=$CE_OVERWATCH_PAT`. Approve as ce-dev-2: `GH_TOKEN=$(cat ~/.ce-keys/ce-dev-2.pat) gh pr review <n> --approve`. Merge queue required → `gh pr merge <n> --auto --merge`.
- Seat drive: dev-4 `sudo docker exec ce-dgx-codex bash -c "HERDR_SOCKET_PATH=/run/creator-engine/herdr/herdr.sock herdr <cmd> w1:p1"`; dev-3 same via `ssh dev1 'sudo docker exec ce-vps-codex ...'`; dev-1 tmux `ce-dev1-orchestrator:2.0` (C-u before send; avoid backticks in the herdr message — local shell substitution footgun).
- Pointer+SHA dispatch: tee brief into container /var/tmp, send short pointer + sha256 (never inline paste). Contained-seat preflight: PYTHONPATH=validators worktree source, NOT stale installed venv; rm validators/build+egg-info before wheel-gate runs.
- Work-class = **XS/S/M/L** (NOT tiny/story/feature/epic — retired #686).
- Orchestrator HAS passwordless VPS sudo. Public docs = ZERO ce-ops# refs (public_docs_confidentiality gate).
- **Whack-a-mole discipline proven this session:** #718 took 5 adversarial rounds; the deep "try-to-defeat" adversarial is the real gate (a shallow/stale APPROVE is not). At 2 strikes on a security surface → stop patching, fix the root / design-pass (→ #388).
