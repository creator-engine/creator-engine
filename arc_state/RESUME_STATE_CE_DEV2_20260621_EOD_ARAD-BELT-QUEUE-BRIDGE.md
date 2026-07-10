# RESUME STATE — CE-DEV-2 Controller · 2026-06-21 EOD · ARAD #157 BUILT + MERGE-QUEUE + BELT + PROTECTION-BRIDGE

**WRITTEN BY / WHERE:** CE-DEV-2 controller as `cedev2` on the **DGX `spark-b824`** (tailnet `dgx-spark-1`/100.100.105.50, GPU GB10, aarch64), cwd `/home/cedev2/creator-engine`, Opus 4.8 effort-high. **SUPERSEDES** `RESUME_STATE_CE_DEV2_20260621_PM_VELOCITY-ARC-ARAD-FOREMAN.md`. Read this + `MEMORY.md` first. **main = `1b09d1b6`**. Session working-notes also in `tmp/21Jun2026.md`.

## ⚠️ CORRECTION vs the superseded resume (important)
The PM resume claimed **#157 shared-App minting was "built-uncouriered on dev-4."** That was WRONG — verified this session: #157 had ZERO shipped code. It was **designed + built fresh this session** (central hosted mint-broker, Option A) and is now **PR #300**. Also #292 (egress broker) does NOT close #157 (it's the dev-fleet courier, not an external-user minting service).

## PEER-SEAT → HOST → REACH (verified 2026-06-21; verify a handle before inferring state)
- **THIS host = DGX** (controller permanent on DGX). dev-2 laptop (100.106.203.52) = separate peer, NOT this session.
- **dev-1** = codex as user **ce-dev-1** on VPS → **`ssh dev1`** (alias, direct, id_ed25519) [backup: `ssh ce-dev-1`=ce@VPS then `sudo -n -u ce-dev-1 tmux`]. tmux `ce-dev1-orchestrator` %0. Self-pushes as ce-dev-1.
- **dev-3** = codex as user **ce-dev-3** on VPS → **`ssh dev3`** (alias) [backup: `sudo -n -u ce-dev-3 tmux`]. tmux `dev3-onboard:1.0` %2. Self-pushes as ce-dev-3.
- **dev-4** = CONTAINED codex on the DGX → `ssh cedev4@localhost -i ~/.ssh/id_ed25519`; tmux `dev4stage1:0.0` %0; codex/ce on LOGIN PATH (`bash -lc`); checkout `~/ce-workspaces/creator-engine`. **NEVER C-c** (kills container; use /compact). **dev-4 git push FIXED today** (gh + ce-dev-4 PAT, `push:true` both repos).
- WAKE send-keys recipe: `tmux send-keys -t <pane> C-u; … -l "$(cat seedfile)"; … Enter` + **sleep 1 + SECOND Enter** (first often doesn't submit). Confirm via `capture-pane -p | tail -18` showing `• Working`.
- gh ops as overwatch: `set -a; source ~/.ce-keys/overwatch.env; set +a; export GH_TOKEN=$CE_OVERWATCH_PAT` (identity ce-overwatch, admin). NEVER inline the token in a seed.

## ⏰ RE-ARM ON RESUME (these die on /clear)
1. **Cron `95824002` (SESSION-ONLY) — Team-upgrade checkpoint, fires 22 Jun 16:57 UTC.** If resuming BEFORE then, RE-CREATE it: CronCreate `57 16 22 6 *`, recurring:false. On fire: probe `gh api repos/chmod735-dor/mythos/rulesets` (mythos-overwatch.pat); if upgraded → apply CE protection floor on mythos (RulesetPolicy) for the gate; if 403 → PushNotification Operator it's due.
2. Belt deploy is pending #302 merge (not yet armed).

## ⏸️ AWAITING-OPERATOR / STANDING OBLIGATIONS
- **🗓️ Mon 22 Jun ~17:00 UTC — Operator does the GitHub Team upgrade on `chmod735-dor`** (web-UI billing, org-owner; I CANNOT do it). Gates the protection floor on mythos. Cron above verifies/applies. STILL 403 as of EOD 21 Jun.
- **🗓️ 22 Jun go/no-go (Arad date + team-mode)** — on ce-ops#170 (default: solo brownfield 24 Jun; re-scope team-mode IN + slip to Sat 27 Jun if velocity supports prod-quality).
- F6 (merge-queue, no-key) = **RATIFIED today** (done) → merge-queue enablement unblocked (gated, after #301 merges).

## CALENDAR (verified weekdays)
Sun 21 Jun (today) · **Mon 22 Jun 17:00 UTC = Team upgrade** · **Tue 23 Jun = reviewer-floor go/no-go gate (against real chmod735-dor/mythos)** · Wed 24 Jun = Arad run · Sat 27 Jun = fallback. (Operator said "Thu 23rd" — 23rd is a TUESDAY.)

## PROTECTION STATE — SURGICAL BRIDGE LIVE (main)
`enforce_admins=TRUE` (restored), `dismiss_stale_reviews=FALSE`, `require_last_push_approval=FALSE`, required check `Validate governance artifacts` strict=true, code_owner + 1 review. ⟹ merges flow WITHOUT the rebase→re-review tax AND without admin-bypass. **Re-tighten the 2 FALSE settings once the native merge queue is enabled** (approval survives `merge_group`). Set via overwatch.

## IN-FLIGHT (all 3 seats WOKEN + working as of EOD; verify handles)
- **dev-1** — reviewing **#300 (ce157 G1)** + **#301 (merge-queue)**; then address own **#294**.
- **dev-3** — opened **#303** (ce23 baseline attestation) + reviewing **#302 (belt)**; on deck: re-review **#299** (head c8cec044).
- **dev-4** — idle; did #299 rebase (couldn't push → I worked around). Now push-capable. Available for #157 fast-follows (S7–S10) or ce23 Slices.

## OPEN PRs (main = 1b09d1b6; bridge = tax-free; still serialize on wheelhouse until queue enabled)
- **#300** ce157 mint-broker S1–S6 (closes #157 P0) — REVIEW_REQUIRED (dev-1 G1 on binding.py/ceiling). **THE Arad blocker.** After merge: S7 CLI poll, S8 OpenBao custody, S9 TLS deploy, S10 one-shot admin floor-mint, + the signed 0.2.0 REPUBLISH.
- **#301** ce39 merge-queue — REVIEW_REQUIRED. merge_group CI trigger + opt-in RulesetPolicy + runbook `docs/operations/MERGE_QUEUE_ENABLEMENT_RUNBOOK.md`. F6=no-key (ratified). After merge → gated enablement (drain train → flip ruleset → re-tighten bridge → empirical approval-survival test).
- **#302** ce55 belt S1–S3 — REVIEW_REQUIRED (dev-3). `ce pickup poll`→claim→`ce lane launch` (gated `--enable-launch`). After merge: DEPLOY per-seat systemd timer (dev1/dev3 via `ssh`, dev-4 local) → seats auto-pickup → no more manual wakes.
- **#299** ce-fwheel1 (ADR-0010 wheel-gate relax) — head `c8cec044`, MERGEABLE, CHANGES_REQUESTED → needs dev-3 re-review. KEYSTONE (eases wheel conflicts).
- **#303** ce23 baseline attestation (dev-3, ce-ops#23) — needs review.
- **#294** trust-anchor (dev-1, ce-ops#158) — CHANGES_REQUESTED (author dev-1).

## MERGED THIS SESSION: #297 (foreman seat_class, ce-ops#163) · #296 (work-sizing, ce-ops#168). [Earlier today: #281/#292/#293/#295/#298.]

## TICKETS / FORGE RECORDS FILED THIS SESSION
#171 (installer detect no-protection plan → warn/degrade) · #172 (Windows/WSL2 host support) · #173 (idempotent re-install) · #174 (path-manifest stale-base SHA after rebase→force-push) · #175 (dev-4 push-credential — **(b) gh DONE**, (a) App-mint helper pending). F6 ratified on #39; merge-queue research on #39; belt design on #55; SSOT field-evidence on #166.

## ARAD CHAIN — critical path to 24/27 Jun
#157 BUILT (#300) → review+merge #300 → S7–S10 fast-follows + **0.2.0 republish** (runbook in plan/tmp; sign with ce-root-v1) → **Team upgrade Mon** → apply mythos protection floor → **Tue 23 rehearsal against real mythos** (cold install → shared-App apply → real PR + reviewer-floor enforced) → **Wed 24 Arad** (or Sat 27). Remove-vs-overwrite SETTLED: prior run left ZERO forge artifacts → local-only cleanup on Arad host; leave repo as-is.

## KEY RATIFIED DECISIONS THIS SESSION
- #157 topology = **central hosted mint-broker** (Option A) — device-flow OAuth + `GET /user/installations` binding check (pasted installation_id is spoofable); v0 ceiling read+contents+PR, **NO administration:write**; two-token split (separate one-shot admin mint for the floor); interim openssl sign → OpenBao fast-follow; team = single shared-App org install (defer #90/#120).
- Rebase-hell permanent fix = **GitHub-native merge queue** (#301); F6 = no key (post-merge tree-equivalence audit is the gate).
- Idle-fleet permanent fix = **forge pickup belt** (#302); poll Notifications API → `ce lane launch` per item; idempotent claim (#38) + independent-reviewer fence.
- Rehearsal runs against the **real chmod735-dor/mythos** (doubles as a true Arad dry-run).
- ce-dev-4 = full forge participant (collaborator both repos; push fixed).

## DEPLOY-LESSON memos written this session
[[ce-delegate-merge-conflict-triage]] (conflict triage/rebase = worker, not controller inline). Topology corrections to [[ce-dev4-dgx-spark-access]] + MEMORY.md header. ⚠️ MEMORY.md is **~42KB (over the ~24KB budget)** — needs a dedicated trim pass (index entries too long); not done this session.
