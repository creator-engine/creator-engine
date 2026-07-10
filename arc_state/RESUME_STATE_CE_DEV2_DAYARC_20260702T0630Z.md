# RESUME STATE — CE-DEV-2 Orchestrator — 2026-07-02 ~06:30Z (DAY, autonomous)

> NEWEST — supersedes all prior 2026-07-02 resumes. Open MEMORY.md + NIGHTARC_MANDATE_CE_DEV2_20260701.md first.
> Arc authority = batch-ratified night grants (G-N1..G-N7; code ≤ work-class M = 2-review quorum; docs XS/S single review).
> **TODAY: first external test user + contributor (Nitzan) onboarding — onboarding-path quality is pitch-critical.**
> main == live == 0.3.1. Merge daemon pid 648947 healthy (single instance; 2nd pgrep hit = self-match footgun). Token durable/restart-safe.

## ✅ DONE THIS BLOCK (since 0800Z resume)
- **#725 (main-HEAD ratified ADR) MERGED 05:35Z** — ratification lane fully closed; ce-ops#366 closed. L1.a/L1.b contributor lanes unblocked. Guard follow-up = ce-ops#389.
- **dev-3 CONTAINER RELAUNCHED** (deferred op DONE) — #723 launcher fix ACTIVE (egress broker socket parent-dir mount + dedup). Broker reachable, no stale-socket. GOTCHA recorded: override CE_VPS_IMAGE with LOCAL image digest (f0032ada…), default pin (42a402cd…) → pull-denied (no registry). [[ce-dev3-relaunched-selfpush-live]] Green canary pending a ce- branch (canary on main correctly REFUSED = broker enforcing).
- **ce-ops#368 CLOSED** (test-coupling gate already landed on main: checks/test_coupling.py + tests + #724).
- **#367 harvested → PR #726** (dev-3 CE-native `ce init`, class M). 2-review quorum SPLIT: functional APPROVE, **adversarial REQUEST_CHANGES = REAL blocker** (CWE-59 symlink write-escape in project_init.py — per-template paths not confined under resolved root; escapes on default mode via planted .ce symlink). Submitted REQUEST_CHANGES as ce-dev-2. **Fix dispatched back to dev-3** (branch ce-367-ce-native-init, brief .ce/briefs/ce-367-symlink-fix-dev3.md).
- **#388 harvested → PR #727 (DRAFT)** (dev-4 conveyor arm-safety ADR). ADR renumbered 0003→0004 at harvest (collision w/ merged main-HEAD ADR-0003). Preflight green. **⏸️ AWAITING-OPERATOR ratification of the arm-safety model** (unblocks G-N3 conveyor arming).
- Re-fed dev-1 (batch) + dev-4 (#382) — NO seat idle.

## 🔄 IN-FLIGHT (all 3 seats Working — verified d1w=1 d3w=1 d4w=1)
- **dev-1** (non-contained, self-push): BATCH of 3 file-disjoint items, brief .ce/briefs/ce-dev1-batch-720fix-369-376.md (sha 20b939d4…):
  1. **Finish PR #720** (branch ce-329-scrum-to-ce-guide) — delete false "Draft" banner line 3 + "Review Notes" section 243-247 (vocabulary fix already PASSED). Host checkout already shows commit b74293f "Remove draft notes" — VERIFY it pushed + re-review. PR stays DRAFT; controller publishes after green (Operator ratified publish-when-green).
  2. **ce-ops#369** Fleet-IaC guard denylist from identity-registry SSOT (branch ce-369-fleet-guard-ssot-denylist; checks/fleet_manifest_guard.py + tests).
  3. **ce-ops#376** commissioned-but-unscheduled sweep (branch ce-376-unscheduled-sweep; forge triage advise-mode, NOT conveyor files).
- **dev-3** (contained VPS, RELAUNCHED): **PR #726 symlink-containment fix** (branch ce-367-ce-native-init, stack on pushed head a43429735). Confine per-template paths under resolved root (plan_actions + write loop, close TOCTOU) + 2 symlink regression tests. Self-push via broker (ce- branch allowed) or controller harvests.
- **dev-4** (contained DGX): **ce-ops#382 brain-drift false-RED** (branch ce-382-brain-drift-local-reconcile; brief sha b466e82d…) — make local validate-pr brain-drift posture mirror CI (auto-reconcile instance-local .ce/state/brain, don't weaken real gate) + `ce brain sync` command + actionable message + tests. Controller harvests. **This is the exact bug that hit the first contributor today.**
- Claims in .ce/claims/. Watchers: PR-board (Monitor bv4v0ibf4, persistent) + 3-seat pane/stall (Monitor bnxtzm8mk, persistent).

## ⏸️ AWAITING-OPERATOR (surface FIRST)
1. **#727 conveyor arm-safety ADR (ADR-0004)** — DRAFT, preflight green. Ratify the arm-safety model (payload-as-data-only + daemon-owned dirs/remotes/refs/paths) → unblocks G-N3 conveyor arming. This is the design-pass you required before arming.
2. **#720 publication** — ratified publish-when-green; executes once dev-1's banner fix lands + re-review passes (first-contributor front door).

## ⏭️ NEXT ACTIONS (fresh context)
1. **dev-1 #720 fix** → verify pushed (host checkout has b74293f) → re-review (docs, single) → if green, un-draft + publish (Operator-ratified). Do NOT auto-merge publication silently — it's the ratified item but confirm green first.
2. **dev-3 #726 symlink fix** lands → 2-review re-quorum (functional + adversarial; the adversarial MUST confirm the symlink escape is closed + tests prove fail-without/pass-with) → gate.
3. **dev-4 #382** lands → 2-review quorum (code) → gate. High onboarding value.
4. **dev-1 #369/#376** land → 2-review quorum each → gate.
5. Re-feed seats after harvest — NO idle. Clean disjoint candidates NOT yet dispatched: ce-ops#320 (install narration polish — CAUTION: may touch signed install = RESERVED release op; scope carefully or skip), ce-ops#166 (Knowledge SSOT/brain), ce-ops#379 (G5 stale-base gap — touches forge workflow normalization, gate-sensitive). PROBE not-already-landed FIRST.
6. **DEFERRED controller op (still open):** dev-4 image REBUILD+relaunch to bake in #719 system libsodium (arm64 base-digest override, ce-ops#377; relaunch canon = cedev4/run-codex-runsc.sh + codex re-auth). dev-4 is functional without it (harvests via controller; libsodium only gates Ed25519 self-push). Do at a genuinely quiet window when dev-4 is idle — it's an optimization, NOT blocking. [[ce-dev4-rebuild-and-launch-canon]]

## KEY FACTS
- Auth: overwatch `set -a; source ~/.ce-keys/overwatch.env; set +a; export GH_TOKEN=$CE_OVERWATCH_PAT`. Approve as ce-dev-2: `GH_TOKEN=$(cat ~/.ce-keys/ce-dev-2.pat) gh pr review <n> --approve`. Merge queue required → `gh pr merge <n> --auto --merge`. Repo slug = **creator-engine/creator-engine** (NOT chmod735/…). ISSUES = creator-engine/ce-ops.
- Seat drive: dev-4 `sudo docker exec ce-dgx-codex bash -c "HERDR_SOCKET_PATH=/run/creator-engine/herdr/herdr.sock herdr <cmd> w1:p1"`; dev-3 same via `ssh dev1 'sudo docker exec ce-vps-codex ...'`; dev-1 tmux `ce-dev1-orchestrator:2.0` (C-u before send). Contained brief transfer = docker exec -i … tee /var/tmp/<f> (runsc-safe stdin), then herdr agent send pointer+SHA + pane send-keys Enter.
- Harvest contained seat = git bundle create in worktree → docker exec cat → host (NO docker cp on runsc). Rebase onto fresh origin/main; carrier stem == branch slug; regen via carrier_gen write_carriers(base=<merge-base>).
- Work-class = **XS/S/M/L** (tiny/story/feature/epic RETIRED #686).
- Local main checkout is DIRTY on ce-release-0.3.1-rc2 (build-image.sh + test_install_bootstrap.py etc.) — workers must use worktrees off origin refs, never the main checkout (caused #719 false review).
- Pre-existing flake noted at #727 harvest: test_install_bootstrap.py::test_install_sh_uv_hash_mismatch_fails_closed_before_execution (x86_64 vs aarch64 uv-archive URL) — present at base+head identically, zero-new-failures under baseline-diff. Consider a ticket if it recurs.
- **Adversarial-review discipline PROVEN AGAIN this block:** #726 functional-APPROVE would have shipped a CWE-59 write-escape; the deep adversarial pass caught it. 2-review quorum on code is doing its job — never gate on the functional APPROVE alone.
