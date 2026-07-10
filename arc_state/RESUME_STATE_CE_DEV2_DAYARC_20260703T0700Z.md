# RESUME STATE — CE-DEV-2 Orchestrator — 2026-07-03 ~07:00Z (pre-Arad-session checkpoint)
> Open MEMORY.md first. ARC: DAYARC_MANDATE_CE_DEV2_20260703.md — RATIFIED (R-A..R-D + G1-G5,
> Operator in-session 2026-07-03). Arad session 07:30Z. SESSION RUNBOOK (follow it):
> .ce/state/research/ARAD_D1B_SESSION_RUNBOOK_20260703.md · answers file ARAD_D1B_ce-install.answers.yaml

## ⏸️ AWAITING-OPERATOR (surface FIRST)
1. "B1" confirm (apply runs controller-side, PEM never leaves us; B2 fallback = plan-only at
   window, apply later after ce-ops#419). Proposed + explained; not yet confirmed.
2. PEM scp → ~/.ce-keys/ (original download or regenerated; mythos App fastest — recorded
   installation_id may skip the click; shared App = product-correct). BLOCKS apply either way.
3. GitHub support case #4529858: reply-2 sent by Operator; they monitor; purge watcher armed
   (bg task fires when refs/pull/729/head dies → prune local ref).

## ARAD FACTS (verified)
aradsky@100.74.214.78 (aradsky-vostro-3400, tailnet, online) · Ubuntu 24.04.4 x86_64 · key auth
WORKS · admin on chmod735-dor/mythos (w/ ce-overwatch admin, ce-dev-2 push) · clone at
~/ce-mythos/mythos · 0.2.0 leftovers benign (symlink shims, reusable venv) · subscription auth ·
PAT = identity-only (no scopes!) · prior App click hit aradSmith PERSONAL (must be chmod735-dor
ORG) · NO sudo will fire (solo-pilot→os-native) · canary GREEN (evidence /var/tmp/ce-canary-d1a-20260703/)

## IN-FLIGHT (check task notifications / TaskList before re-dispatching — subagents auto-resume)
- dev-4 #407 s1 HARVEST worker (branch ce-407-pin-migration-s1 @ bc2d2240b) → PR → then
  reviewer worker → approve as ce-dev-2 (= merge). Ledger lane = dev-4's.
- pilot-docs implementer (worktree .ce/wt-pilot-docs-fix, branch ce-pilot-docs-daytoday):
  ce→cev3 fixes in solo guides + index.html + collaborator section + PACKAGE rebuild
  (tmp/arad-welcome-package: README order, constitution manual-path rewrite, internal docs
  moved out, new day-to-day-with-ce.md). Harvest+review+merge BEFORE handoff step of session.
- dev-3 building #412 Tier A (flip-live on merge = R-B) · dev-1 building #294 bundle (demo
  on own PR = R-D). Tier B #413 waits for Tier A merge, dev-4 after N2 slices.
- Watchers: seat-signals (alive) · PR-board 3m (Monitor) · #729 purge (bg Bash).

## TODAY'S LEDGER SO FAR
Tickets filed: #412 #413 (tiers) #414 (installer docs) #415 (brownfield bug) #416 (rc2 drift —
do NOT publish from rc2 branch until reconciled) #417 (runbook gaps) #418 (pilot docs/cev3 +
constitution gap) #419 (mint-broker no server) #420 (App-PEM custody). Claims recorded for 3
dispatched lanes. Held: #383 until N2 s2 migrates integrator_belt pins.

## HARD-WON (this session)
- Mint-broker = logic only, NO server (#419); ghu_ device-flow for pilots unwired. Do NOT
  attempt rush-deploy.
- App PEMs were /dev/shm-only, dead (#420). ce-forge fleet App key IS durable (~/.ce-keys).
- resolve_live_config PEM branch ignores app.kind → controller-side apply w/ mythos App
  creds works regardless of answers kind:shared.
- mythos-overwatch PAT can't list org installations (403) — verify installations via App JWT.
- Live install chain internally consistent 0.3.1 (canary EXECUTED it); local rc2 checkout
  stale — distrust any "live is 0.3.0" doc-read claims (#416).
- Audit: solo-ceo/solo-dev guides shipped cev3-only verbs as `ce` (site+package); constitution
  ratification had NO working path — manual-commit path is the interim (in docs PR).
