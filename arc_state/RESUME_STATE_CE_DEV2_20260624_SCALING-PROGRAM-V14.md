# RESUME STATE — CE-DEV-2 · 2026-06-24 NIGHT · 🏗️ SCALING PROGRAM → PRE-DAWN RELEASE · V14

**WHERE:** CE-DEV-2 controller, `cedev2` on DGX `spark-b824` (GB10 aarch64), cwd `/home/cedev2/creator-engine`, Opus 4.8 high. **SUPERSEDES V13** (V13 still holds the full Phase-0 program text + DoD + onboarding spec — read it too). READ FIRST: this + MEMORY.md + [[ce-release-to-traction-doctrine]] + [[ce-parallelize-everything-scale-the-gate]] + [[controller-drive-work-through-own-fork-workers]]. Discipline: **verify-don't-trust**, **build properly**, **drive work through workers (incl. MY OWN forks), never inline**. Operator ASLEEP — drive the night-shift autonomously; surface at wake-up.

## 🎯 MISSION (unchanged)
Scale CE dev capability massively (this 12h); the scaled machine lands install+onboard (Arad, she/her — see V13 ONBOARDING SPEC) at **pre-dawn**. Controller = FOREMAN: stock the queue, hold the gate, drive through workers. Phase 0 (gate runs itself) → Phase 1 (saturate default-6) → Phase 2 (6→8) → Phase 3 (pre-dawn DoD).

## 🚨 CRITICAL PATH — FINISH THE GATE BOOTSTRAP (do this FIRST)
The autonomous merge gate (Integrator daemon) is LIVE but had **3 live-only discovery bugs** (all found by the grader-outside-the-agent — live dry-run, NOT CI, because unit tests inject candidates and never build the live `gh` call):
1. ✅ `$query` GraphQL var collided with gh's reserved field → fixed (#428, merged).
2. ✅ `_DAEMON_SEARCH_QUERY` brace-unbalanced → fixed (#428, merged).
3. 🔨 **`latestReviews` is EMPTY for non-requested reviewers** → daemon skipped every approved PR `approval_not_current_head`, never merged anything. Fix = `latestOpinionatedReviews`. **PR #431** (approved by ce-dev-4, native auto-merge LATCHED, CI pending). **Live-verified by a fork: #430 went skip→enqueue.**

**🎉 EXIT-GATE PROOF ALREADY FIRED:** the live Integrator daemon AUTONOMOUSLY enqueued #431 (`eligible_enqueued`, `gh_pr_merge_auto=true`, zero `gh pr merge` from me) — Phase-0 exit gate PROVEN. (It could gate #431 even pre-fix because review-pickup requested ce-dev-4 as reviewer → `latestReviews` populated for *requested* reviewers; the #431 fix makes it work for *non-requested* approvals too, e.g. #430. The two daemons are cooperating.)
**STEP 1 (on #431 merge):** RESTART daemons → `/home/cedev2/.ce/bin/launch-gate-daemons.sh` (idempotent; pre-flight asserts the fixed source). This loads the FIXED integrator_belt from new main. THEN tail `~/.ce/logs/integrator-daemon.log` — it should ENQUEUE #430 (and the others once green). **That enqueue = the long-chased Phase-0 EXIT-GATE PROOF (one PR brief→merge, zero `gh pr merge` from me).** Currently the daemons run the OLD buggy code (pid still from the pre-fix launch) — they MUST be restarted after #431 merges or the gate stays broken.
- Poll #431: `gh pr view 431 --repo creator-engine/creator-engine --json state` (overwatch token). #431 latched native auto-merge (NOT via the daemon — chicken-egg: the daemon can't merge the fix to its own bug).

## 🔧 IN-FLIGHT PRs (all APPROVED + MERGEABLE; gate will auto-merge once it works)
- **#431** Integrator latestOpinionatedReviews fix — latched, CI pending → merge → **RESTART DAEMONS**.
- **#430** cred-injection PR-1 (ce-dev-1, transport_deputy_policy fail-closed gate) — approved (ce-dev-2), carrier-clean, CI green. Will auto-merge once the gate works. **Touches `_versions.py`** (overlaps #429 → Integrator will path-overlap DEFER one; both merge, sequenced).
- **#429** dispatch_worktree PR-1 (ce-dev-3) — approved + carrier, but **CI RED** (was version-boundary; dev-3 built the fix `ad2b8f1` IN ITS CONTAINER `ce-vps-codex` but it is NOT PUSHED). **ACTION:** push it from dev-3 host (`ssh dev3 'cd /home/ce-dev-3/creator-engine && git push origin ce-dispatch-worktree'`) → then carrier-REGEN (the path-set now includes `_versions.py` + a `v3_cli.py` change dev-3 also made — REVIEW that v3_cli change) → push → CI greens → gate merges. Worktree for carrier: `/home/cedev2/ce-wt/dispatch-pr1`.

## 📦 PENDING INTEGRATION (drive through workers/forks, NOT inline)
- **auto-carrier** branch `ce-auto-carrier` (`22921c4`, ce-dev-4, PUSHED, the `ce carrier` tool) — needs carrier + PR-open (author ce-dev-4 from its host). NO PR yet. Then gate merges. (Once merged, USE `ce carrier` instead of hand-rolling carriers.)
- Carrier mechanic (until `ce carrier` lands): worktree → write `.ce/changelog/<slug>.md` → commit → `python3 /tmp/gen-manifest.py <slug> <issue> <title>` → commit manifest → `.venv/bin/python -m creator_engine_validator verify-path-manifest --base origin/main --manifest-dir .ce/pr-manifests --head-ref <slug>` (PASS) → push. PR body needs `- **Declared work class:** <story|feature>`. **NO `--require-carrier` flag (stale memory; this validator build lacks it).**

## 🤖 dev-1 SELF-PICK (Operator approved Option A) — ✅ LIVE, one refinement pending
- **DONE + PROVEN:** nudge-bridge LIVE on dev-1. Cron `1-59/5 * * * * bash ~/pickup-nudge.sh # CE-PICKUP-NUDGE`. Script `~/pickup-nudge.sh` (93 lines): poll `ce pickup poll --identity ce-dev-1 --keys-dir ~/.ce-keys --repo creator-engine/creator-engine --json` → 15-min rate-limit (`~/.pickup-nudge.last`) → robust idle-detect (two captures 6s apart identical + no busy-indicator in bottom 4 lines) → inject ONE nudge via relay. **dev-1 self-picked from cold idle, zero dev-2 hand-tasking ✅.** 401 FIXED: extracted gh's durable fine-grained PAT to `~/.ce-keys/ce-dev-1.pat` (chmod600), belt-canary cron also swapped to `--keys-dir`. (If persistent 401s recur: `ssh dev1 'gh auth token > ~/.ce-keys/ce-dev-1.pat'`.)
- ⚠️ **PENDING REFINEMENT (Operator — apply on resume):** the LIVE nudge is GENERIC ("own PRs → review-requested → unclaimed tickets") — the "unclaimed tickets" fallback risks free-roam onto stale non-arc backlog. SWAP the `NUDGE` text in `~/pickup-nudge.sh` for an ARC-AWARE version: (1) continue its own arc lane = **#228 cred-injection follow-ups** (PR-1 #430 shipped; PR-2/3 of its cut remain); (2) review-requested arc PRs; (3) next **arc-scoped** ticket ONLY — explicitly "do NOT pick unrelated backlog; if no arc work, stop and wait." (Tonight's risk is LOW: dev-1's own #228 PRs dominate the priority, so it stays arc-aligned until those run out.)
- 🆕 **STOCK A MACHINE-DISCOVERABLE ARC QUEUE** (fleet-wide): a label/milestone for the scaling arc so `ce pickup poll` is arc-scoped → every self-picking dev stays on-mission. Controller curates the arc; devs self-pick from it. [[ce-seats-foremen-self-managed-fanout]]
- dev-1 currently still effectively hand-tasked (gap not yet closed). [[controller-owns-dev1-intake RETIRED but reality lags]]

## 🧠 KEY LESSON THIS SESSION (Operator-driven, persisted as memory)
[[controller-drive-work-through-own-fork-workers]] — when I hold the context (esp. needs live-verify only my box can do), fan out through MY OWN `fork`/subagent, NOT a blind remote seat. The 3 Integrator bugs slipped because seats can't live-test. "Don't inline" ≠ "remote-seat it". Also: **every build brief's done-criteria must include `ce check`** (offline governance gate — catches version-boundary/crosswalk/etc. without burning a CI run).

## ✅ LANDED THIS SESSION (main `559c4198`; +#431 imminent)
#426 Integrator merge daemon, #427 review-pickup daemon, #428 discovery fixes (query+brace) — all merged. Daemons flipped LIVE (verified fail-closed: code+tests+live dry-run gating real PRs). Release DoD RATIFIED + recorded on ce-ops#191. 10 stale ce-ops tickets closed (audit); 4 kept open w/ one-item gaps (#43 cockpit-sentinel, #95 `ce seats ls`, #158 .odt-plaintext-warn, #142 CUE Ring-2+dogfood). #148 closed.

## 🎛️ CONTROLLER QUEUE (resumed-me, in order)
1. **Poll #431 → on merge RESTART DAEMONS (`launch-gate-daemons.sh`) → confirm gate enqueues #430 in the log** = EXIT-GATE PROOF. Surface it.
2. Push dev-3's `ad2b8f1` to #429 + carrier-regen (review the v3_cli.py change) → CI greens → gate merges #429.
3. Carrier+PR the `ce-auto-carrier` branch → gate merges.
4. Verify worker `a71b1bb1` (dev-1 nudge) result; apply the ARC-AWARE nudge text; stock the arc queue (label/milestone).
5. Keep all seats on ARC lanes: dev-1 #228 follow-ups, dev-3/dev-4 next scaling items (dispatch_worktree PR-2 = container mount + live smoke; observability; Search-API headroom for Phase 2). dev-3/4 free after their current work.
6. **Phase 1:** once the exit gate is proven + worktree-isolation usable, saturate default-6 via foreman fan-out (decomposable objectives), assess, THEN 6→8 (never >8). Operator ratifies step-ups (he's asleep — PREPARE + assess, do NOT bump concurrency unattended).
7. **Phase 3 pre-dawn:** drive the release DoD (V13: N1 install git/curl remediation + soft-fail + re-source; N2 docs ce→cev3 + curl/git prereq + homepage link; N3 first-value author→commit→push→PR→merge on `chmod735-dor/mythos`; N4 auth+App; N5 fail-safe; N6 clean-room rehearsal = ship/slip gate). Ship IFF green.

## 🛠️ OPS ESSENTIALS
- **Daemons:** `~/.ce/bin/launch-gate-daemons.sh` (restart both, from source; logs `~/.ce/logs/{integrator,review}-daemon.log`). NOHUP — survive session, NOT reboot (systemd-ize = hardening TODO). Run daemons FROM SOURCE: `PYTHONPATH=validators .venv/bin/python -m creator_engine_validator.v3_cli <cmd>` (installed `cev3` is STALE, #198). Integrator token = overwatch.
- **Tokens:** `~/.ce-keys/`: ce-dev-2.pat (login ce-dev-2, my reviewer id), ce-dev-4.pat (ce-dev-4), mythos-overwatch.pat (ce-overwatch, **admin+push on chmod735-dor/mythos** — D4 de-risked), overwatch.env (`CE_OVERWATCH_PAT`=merge mechanics). Repo `creator-engine/creator-engine`; ISSUES `creator-engine/ce-ops`.
- **Seats:** dev-4 `ce-dgx-codex` (local `sudo docker exec -i`; host push `ssh cedev4@localhost -i ~/.ssh/id_ed25519 'cd ~/ce-workspaces/creator-engine && git push'`). dev-3 `ce-vps-codex` via `ssh dev3` (host `/home/ce-dev-3/creator-engine`). dev-1 = controller, tmux `ce-dev1-orchestrator:2.0` via `ssh dev1` (send-keys; C-u×6→`-l`→Enter).
- **Dispatch (seats):** `cat brief | sudo docker exec -i <ctr> bash -lc '...'` (verify brief delivered: `wc -l`; abort if empty). ⚠️ **DON'T wrap ssh dispatch in `timeout` — codex outlives it; POLL the container for the commit instead.** For MY-context work, use a `fork` not a seat.
- **Review routing:** dev-authored PR → I review ce-dev-2. My-fork-authored → open as ce-dev-2, approve via ce-dev-4 (distinct non-author) OR route to dev-1. Contained seats can't submit reviews.
- **Carrier:** see PENDING INTEGRATION above. **Path-overlap:** Integrator DEFERS PRs with intersecting path-sets (e.g. `_versions.py` in #429+#430) — sequences them, both merge.
- **Background tasks/pollers/forks DIE on /clear** — resumed-me re-establishes any needed pollers (poll #431, etc.).
