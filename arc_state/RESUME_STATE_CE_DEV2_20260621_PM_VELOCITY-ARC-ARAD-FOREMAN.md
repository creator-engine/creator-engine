# RESUME STATE — CE-DEV-2 Controller · 2026-06-21 PM · VELOCITY-ARC + ARAD-CHAIN + FOREMAN-DIRECTIVE

**WRITTEN BY / WHERE:** CE-DEV-2 controller as `cedev2` on the **DGX `spark-b824`** (tailnet 100.100.105.50), tmux `ce-controller`, cwd `/home/cedev2/creator-engine`, Opus 4.8 effort-high. **SUPERSEDES** `RESUME_STATE_CE_DEV2_20260621_COMPANYBRAIN_WORKSIZING.md`. Read this + `MEMORY.md` first. **main = `4693465d`**. Transcript: `.ce/state/research/TRANSCRIPT_CE_DEV2_20260621_pm_velocity-arc-arad-foreman.jsonl` (sha `47290ed7…`, both hosts). Readable MD of the AM transcript also in that dir + reusable `transcript_to_md.py`.

**PEER-SEAT → HOST → REACH (verify a handle resolves locally before inferring state):**
- **dev-1** = VPS `ssh ce@100.72.252.20` → `sudo -n -u ce-dev-1 tmux ... -t ce-dev1-orchestrator`. Self-pushes as ce-dev-1.
- **dev-3** = VPS `sudo -n -u ce-dev-3 tmux ... -t dev3-onboard:1.0`. Self-pushes as ce-dev-3. cwd `~/creator-engine`.
- **dev-4** = CONTAINED DGX `ssh cedev4@localhost`; tmux `dev4stage1:0.0`; NEVER C-c. Container cwd `/workspace/creator-engine` ↔ host `/home/cedev4/ce-workspaces/creator-engine`. No egress → courier via git-bundle (bundle on dev-4 → shared /tmp → `git fetch <bundle>` on cedev2 → overwatch push). Brief courier = scp to `~/ce-workspaces/creator-engine/tmp/` (= container `/workspace/.../tmp/`).
- Brief dispatch = file → sha256 → courier → seed `Read <path> (sha256 <h>) and execute`. Long paste needs a **2nd Enter** on codex. **NEVER inline `$CE_OVERWATCH_PAT` in a seed.** gh ops: `source ~/.ce-keys/overwatch.env; export GH_TOKEN=$CE_OVERWATCH_PAT`.

## ⏸️ AWAITING-OPERATOR / STANDING OBLIGATIONS
- **🗓️ 22 Jun MIDDAY go/no-go (Arad)** — the only hard future obligation. Decide: hold Arad install 24 Jun (solo brownfield) vs move to **Sat 27 Jun + re-scope team-mode IN**, judged on measured velocity (commits+PRs vs the 4-PR-AM baseline) + parallelism. Quality-over-speed: move the date, never the bar. Tracked on **ce-ops#170** (gate cluster A + CONDITIONAL DECISION block).
- All session decisions ratified; nothing else blocking.

## RE-ARM ON RESUME (both die on /clear)
1. `bash ~/ce-fleet-watcher.sh` (run_in_background; heartbeat-and-exit every ~27min → re-arm each time it notifies).
2. **VERIFY THE FOREMAN-DIRECTIVE FIX EMPIRICALLY** — watch the next post-compaction *substantive* task on any seat: it MUST spawn worker sub-agents (fan-out), NOT edit source / run reviews inline. If a seat still works inline post-compaction, the `~/.codex/AGENTS.md` directive (sha `0610b86c`) isn't taking — escalate to repo-level or push #163 merge. (See [[ce-codex-foreman-directive-durable]].)

## IN-FLIGHT (verify each handle before acting)
- **dev-1** — idle (61% ctx, compacted). Last act: 2nd review of #299 → **CHANGES_REQUESTED again** (the determinism/gate fixes still insufficient).
- **dev-3** — idle (87% ctx, compacted). **Committed #23 Slice 1** = `c24e6ab` "feat: add brownfield baseline attestation spine" on branch `ce23-s1-baseline-attestation` (LOCAL on dev-3, NOT pushed) → COURIER + review.
- **dev-4** — on branch `ce-fwheel1-author-gate` (27% ctx). Installed the foreman directive. Available for next build (Arad #23 Slice 2/3, or #299 wheel-rebase).

## OPEN PRs (main=4693465d) — ALL wheel-CONFLICTING (the #298-merge cascade)
- **#299** F-wheel-1 (ADR-0010 author-gate relax + wheel_bake.py + ADR-0010 doc) — **CHANGES_REQUESTED (2nd, dev-1)**, CONFLICTING. dev-1's findings: byte-reproducibility of wheel_bake.py + over-broad gate demotion + NOTICE. **THE KEYSTONE**: merging #299 relaxes the wheel gate → #297/#296 drop wheel churn → cascade clears. Next: dev-4 fixes #299 round-2 → courier → re-review → merge.
- **#297** foreman seat_class spine (ce-ops#163) — **APPROVED**, CONFLICTING. Just needs wheel resolved (post-#299) → merge. = the PERMANENT foreman fix.
- **#296** work-sizing spine (ce-ops#168) — **APPROVED**, CONFLICTING. Same — wheel resolve → merge.
- **#294** W6 trust-anchor (ce-ops#158) — CHANGES_REQUESTED, CONFLICTING (author dev-1).
- **#23 Slice 1** (dev-3 local `c24e6ab`) — not yet a PR; courier+push+open→review.

## MERGED TODAY (5): #281 OpenBao · #292 egress(ADR-0007) · #293 scanner-pins · #295 ADR-0009 tenet · #298 brain assertion-ledger.

## ARC #169 (MORNING, theme = deterministic-substrate / CE-dev-pace unblockers) — ce-ops#169
G-A brain #298 ✅MERGED · G-B foreman #297 APPROVED(wheel) · G-C work-sizing #296 APPROVED(wheel) · G-D egress #292 ✅MERGED · G-E F-wheel-1 #299 (in fix) · G-F F-wheel-2 push-to-main bake (queued, needs #299) · G-G ADR-0006 reloc (queued) · G-H clear wheel PRs (= the cascade).

## NIGHT ARC #170 (PRE-DRAW — finalize+batch-ratify BEFORE driving) + ARAD GATE CLUSTER A
- Candidate N-gates: N-1 work-sizing F2 · N-2 foreman live-arming (needs #297 merged) · N-3/4 wheel Phase-B (ADR-0006 Gate2/3) · N-5 company-brain Phase-2 recall (unblocked by #298) · N-6 morning carryover.
- **Arad cluster A** (Operator-ratified 2026-06-21, start-now + 22-Jun go/no-go): A-1 #157 shared-App minting (built-uncouriered on dev-4, stacked on merged #292; needs RELEASE to published signed wheelhouse + the F-wheel-1 deterministic-wheel fix) · A-2 #22 design ✅closed-by-worker · A-3 #14 = **NON-blocker** (retirement run already complete) · A-4 #23 build (Slice1 done, Slices 2 G-A + 3 G-B-wiring remain; ~one session) · A-5 clean-room rehearsal (the real go/no-go) · A-6 Arad-side cleanup.
- **CONDITIONAL team-mode/date decision** lives on #170 (default: team-mode DESCOPED + 24 Jun solo; re-scope IN + 27 Jun if velocity supports prod-quality).

## ARAD CHAIN DETAIL (ce-ops#23 + checklist `/tmp/arad-preflight-checklist.md`)
- Prior run (2026-06-20, GH `aradSmith`, repo `chmod735-dor/mythos`) fail-closed CLEAN (zero forge writes) on missing shared-App minting #157. #159 scanner wall already fixed.
- **Both #23 binding OQs RATIFIED** (anchor `~/ce-briefs/ratification-23-brownfield-oqs-2026-06-21.txt` sha `d8d01f1a`): OQ1 scrub-waiver=human-binding-yes; OQ2 attestation=value-free+digest v0.
- #23 brief `/tmp/brownfield-23-brief.md` (3 thin slices, G-B already built). Slice 2 (G-A) + Slice 3 (G-B wiring) both touch `v3_installer.py` → run same wave (avoid collision with Slice 1 until it merges).
- **Remove-vs-overwrite (answered):** clean the stale `~/.local/share/creator-engine/.../install.lock` + revoke Arad's self-registered App+PEM+PAT (her side); installer idempotent for the rest. No `ce uninstall` exists = product gap.
- ⚠️ SLEEPER: install.sh fetches the PUBLISHED signed wheelhouse → #157 must be RELEASED not just merged (#80 release gap).

## NEXT MOVES ON RESUME (priority)
1. Re-arm watcher + START foreman-directive empirical verification.
2. **Drive the wheel cascade:** dev-4 fixes #299 round-2 → courier → dev-1 re-review → merge #299 → then rebase #297/#296 (drop wheel churn) → merge both (foreman + work-sizing = the durable fixes land).
3. Courier dev-3's #23 Slice 1 (`c24e6ab`) → PR → review → merge; dispatch #23 Slices 2+3.
4. Stage #157 (rebase onto merged main, courier) — release HELD for rehearsal + go/no-go.
5. Prep 22 Jun go/no-go data (velocity delta).

## ANCHORS THIS SESSION
ADR-0010 wheel ratified sha `87727ac8` (ce-ops#164) · #23 OQs sha `d8d01f1a` · foreman-directive sha `0610b86c` (~/.codex/AGENTS.md on all 3 seats) · arc issues #169 (morning) #170 (night predraw).
## MEMORIES WRITTEN THIS SESSION: ce-no-egress-seat-self-contained-briefs · ce-two-shift-arc-operating-model · ce-codex-foreman-directive-durable · ce-agent-paced-estimation (3rd reinforcement).
