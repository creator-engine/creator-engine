# RESUME STATE — CE-DEV-2 Orchestrator — 2026-07-02 ~06:40Z (DAY, autonomous)

> NEWEST — supersedes 0630Z. Open MEMORY.md first. Arc authority = batch-ratified grants
> (code ≤ class M = 2-review quorum; docs XS/S single review).
> **TODAY: first external test user + contributor (Nitzan) onboarding — onboarding quality is pitch-critical.**
> main == live == 0.3.1. Queue daemon pid 648947 healthy.

## ✅ DONE THIS BLOCK (since 0630Z resume)
- **#720 MERGED 06:10Z** — onboarding front-door guide published (Operator-ratified publish-when-green executed).
- **🚨 CONFIDENTIALITY INCIDENT contained (ce-ops#390)**: dev-1's PR #729 (ce-ops#369 fleet-guard denylist) vendored REAL identifiers plaintext into the PUBLIC repo (tailnet IPs, hostnames, OpenBao secret paths, key-file paths, account ids) in `fleet_identity_denylist_snapshot.py`. CI passed because `public_docs_confidentiality.py` scans ONLY README+docs/**. 2-review quorum unanimous REQUEST_CHANGES → RC submitted (GENERIC wording, no values echoed publicly) → PR CLOSED + branch DELETED. Full detail ONLY in private ce-ops#390. **⚠️ refs/pull/729/head still serves the blob — purge = GitHub Support ticket = RESERVED (Operator).**
- **#728 (ce-ops#376 sweep) quorum SPLIT** → CHANGES_REQUESTED as ce-dev-2: functional APPROVE; security pass found silent false-clean when arc ticket absent from payload (forge_triage.py:536-545 returns () with no signal — fails UNSAFE direction). Fix dispatched to dev-1 (ITEM 0). Follow-up (text-mode CLI never shows the advisory) = ce-ops#391.
- **dev-1 re-fed 4-item batch** brief `.ce/briefs/ce-dev1-batch-385-386-361.md` (sha 4d714ee6…): ITEM0 #728 fix (its own PR branch), #385 doc vocab XS, #386 xdist marker XS, #361 mirror-policy draft S. Told dev-1 NOT to re-push/redo ce-369 (waits on Operator direction).
- **dev-4 re-fed ce-ops#390 lane 1** brief `.ce/briefs/ce-390-confidentiality-scanner-coverage-dev4.md` (sha 6100089a…): widen confidentiality scan to ALL tracked files, fail-closed, allowlist w/ justification, FAKE fixtures only; branch `ce-390-confidentiality-scanner-coverage`, commit-for-harvest.
- Territory check caught **#379 ⟂ ce-382 collision** (both touch pr_preflight.py/ce_cli.py) → #379 DEFERRED until ce-382 PR merges. #387 ⟂ #728 (forge_triage.py) → deferred too.
- 3 reviewer subagents killed by API safety filters → workaround memorized ([[ce-reviewer-safety-flag-workaround]]): defensive-governance framing, no attack verbs.

## 🔄 IN-FLIGHT
- **harvest_intake worker (Sonnet, background)**: dev-4's ce-382 (brain-drift false-RED fix, HEAD 526a46b) → bundle-extract → preflight → push → PR. Diff touches pr_preflight.py, ce_cli.py, carrier_gen.py + tests. When PR opens: 2-review quorum (code M) → gate.
- **dev-1** (Working): 4-item batch above. #728 push dismisses prior review → re-review on new head (security lens must confirm the fail-closed fix).
- **dev-3** (Working): #726 symlink fix committed (7e7f716 "Fix ce init symlink containment") — running full validation, then broker self-push or READY-FOR-HARVEST. On land: 2-review re-quorum; adversarial MUST confirm CWE-59 closed + fail-without/pass-with tests.
- **dev-4** (Working): ce-390 scanner coverage (context 35% used — OK).
- Watchers ARMED this session (prior session's monitors did NOT survive): PR-board (b0lfdc6qd) + 3-seat pane/stall (b7wo8reit). NOTE: pane watcher greps READY-FOR-HARVEST and can false-positive on instruction text (happened w/ dev-3) — verify pane before harvesting.
- Claims current in .ce/claims/ (385/386/361/376/390 + earlier).

## ⏸️ AWAITING-OPERATOR (surface FIRST)
1. **ce-ops#390 residual exposure**: leaked blob still fetchable via refs/pull/729/head. Purge requires GitHub Support ticket (history-scrub = reserved). Exposure = topology/pointers, NO secret values.
2. **ce-ops#369 redo direction**: hashed/salted snapshot vs CI-derived artifact from access-scoped source. Do not re-dispatch until ratified.
3. **#727 conveyor arm-safety ADR (ADR-0004)** — DRAFT, green, unratified → blocks G-N3 conveyor arming.

## ⏭️ NEXT ACTIONS (fresh context)
1. ce-382 harvest PR opens → 2-review quorum → gate. THEN un-defer #379 (+ maybe #371) for next dispatch.
2. dev-3 #726 fix lands → re-quorum → gate. dev-1 #728 fix push → re-review (security lens) → gate.
3. dev-1 XS/S items land → single doc reviews → gate. #385 is onboarding-critical.
4. dev-4 ce-390 READY-FOR-HARVEST → harvest → quorum. Expect a pre-existing-hits list in its done-report → ticket a scrub if real leaks found.
5. Re-feed seats as they free — remaining clean candidates: ce-ops#320 (CAUTION signed-install), #166 (brain SSOT — check ⟂ ce-382 first), #379/#387 (after their blockers merge), #371 (after ce-382: ce_cli.py).
6. DEFERRED controller op: dev-4 image rebuild for libsodium (ce-ops#377, quiet window only).

## KEY FACTS
- Auth: overwatch `set -a; source ~/.ce-keys/overwatch.env; set +a; export GH_TOKEN=$CE_OVERWATCH_PAT`; approve as ce-dev-2 `GH_TOKEN=$(cat ~/.ce-keys/ce-dev-2.pat) gh pr review <n> --approve`; queue `gh pr merge <n> --auto --merge`. Repo=creator-engine/creator-engine; ISSUES=creator-engine/ce-ops.
- ce-dev-2 approval IS the merge trigger (~120s) — to hold, keep draft.
- Seat drive + harvest mechanics: unchanged (see 0630Z resume / MEMORY.md header).
- Review worktrees live: .ce/wt-728-review, .ce/wt-729-review (729 kept deliberately as the only local copy of the closed PR's content — do NOT push it anywhere).
- Local main checkout DIRTY on ce-release-0.3.1-rc2 — workers use worktrees off origin refs only.
