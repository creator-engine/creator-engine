# RESUME STATE — CE-DEV-2 Orchestrator — DAY-SHIFT ARC — 2026-06-30 ~06:30Z

> NEWEST. Supersedes 0500Z. Open this + MEMORY.md FIRST. Arc RATIFIED (G1–G7 + R-series). Two big new programs this block: **spec-kit FULL RETIREMENT** + **fleet-IaC deployment research**.

## ✅ MERGED THIS BLOCK (author≠approver, ce-dev-2 approves)
#672 L4 wikilink-graph · #673 L6 install-sig guard→blocking (controller-verified SHA + predecessor-merged).

## 🔻 SPEC-KIT FULL RETIREMENT — Operator-RATIFIED 2026-06-30 (the dominant program)
Research concluded CE's `ce`(cev3) Scope-lifecycle + governed orchestration SUBSUME & exceed spec-kit's SDD pipeline. Decisions LOCKED: don't-adopt runtime · #114→retire(not sync) · #368 native test-coupling gate filed · mode-axes canon reword ("agent invokes speckit"→"invokes CE cev3 loop") · FR-009 mechanical guard de-Hermesed ("governed envelope" not "Hermes"). Reports: `.ce/briefs/speckit-under-the-hood-REPORT-20260630.md`. **PLAN: `.ce/briefs/speckit-retirement-PLAN-20260630.md`.** Key fact: NO CI gate breaks on speckit removal (antidrift guard exempts speckit). User-facing cmd = `ce` (cev3 internal-only).
**MERGE ORDER (enforce at gate): Phase 0 → Phase 4 → Phase 1 → Phase 2 → Phase 3.** (Phase 4 before removals so repo never violates its own live constitution.)

### IN-FLIGHT (await notifications / gate)
- **Phase 0 = #674** (head 2cc6d5a4, branch ce-onboarding-mode-cell-banners): NEW `solo-dev-onboarding.md` (Nitzan cev3 hands-on) + CEO guide cev3→ce + retire-banners. validate-pr PASS. **Reviewer running (a5d98f6642de4d7e4).** THEN: Operator content-nod (pilot-facing) + approve as ce-dev-2 + merge FIRST. Review worktree `.ce/wt-onboarding-review`.
- **Phase 1** (dev-3 contained, branch ce-speckit-retire-skills): git rm 13 .claude/skills/speckit-*. Working → READY-FOR-HARVEST (harvest_intake; dev-3 no-egress → reports SHA, controller harvests).
- **Phase 2** (dev-1 non-contained, branch ce-speckit-retire-specify): git rm .specify/ EXCEPT memory/constitution.md. Working → self-pushes → board catches → gate.
- **Phase 4** (my implementer a2ecff3ab896d2eb0, branch ce-speckit-retire-principle-x): constitution Principle X amendment via spec/plan/tasks triple + MAJOR bump 1.1.0→2.0.0 + record Operator Source-approval. Working. **HOLD MERGE until Operator confirms the exact before/after Principle-X text** (constitution = show wording before it's law).
- **Phase 3** (queued, needs dev-4 healed + Phase 0 merged — collides on getting-started): full rewrite getting-started + agile-to-ce docs → cev3. Owner: dev-4 after self-heal.
- **#367** scaffold gap → CLOSE as superseded by retirement. **#114** → reframed retire (done, in ready queue). **#368** native test-coupling gate (ce-pickup/triage-ready).

## 🛰️ FLEET-IaC DEPLOYMENT (NEW research, product-aligned)
Deploy CE's Autonomous-Fleet to OTHER projects on fresh isolated cloud VM/project, tiered, no mixing. **REPORT: `.ce/briefs/fleet-deployment-iac-REPORT-20260630.md`** (brief: fleet-deployment-iac-research.md). Headline: **CE already has ~70%** (deploy/*/run-*-runsc.sh, cev3 onboard 12 legs, surfaces/render.py, ce launch, signed install). Net-new: fleet-manifest + cloud-VM wrapper (cloud-init+thin Terraform) + per-project secret/identity bootstrap (**LONG-POLE, blocked ce-ops#239/#240**) + `ce fleet` verb. **P0 (buildable now, decision-independent): fleet-manifest schema + CI guard rejecting CE-internal identifiers.** 3 OPERATOR DECISIONS PENDING: (a) shared-vs-own GitHub App (rec own), (b) per-fleet vs shared model account, (c) default tier (rec Solo+CEO os-native). Solo-tier shippable first; full Fleet waits on #239. Self-referential rented-surface-sync risk = ce-ops#114 lesson.

## ⏭️ NEXT ACTIONS (on resume)
1. **Catch #674 reviewer verdict** → fix any defect → Operator content-nod → approve+merge (Phase 0, today-critical for Nitzan).
2. **Harvest Phase 1 (dev-3) + gate Phase 2 (dev-1 PR)** when READY → enforce merge order (after Phase 0 + Phase 4).
3. **Phase 4 (constitution) lands** → SHOW Operator the Principle-X before/after text → on confirm, approve+merge BEFORE Phase 1/2.
4. **dev-4 self-heal done?** → dispatch Phase 3 (after Phase 0 merged).
5. **Fleet-IaC:** await Operator on the 3 decisions + whether to file the epic + start P0.
6. Hold R-series / irreversible for Operator.

## 🩺 INFRA / SEATS
- dev-4 (ce-dgx-codex): venv was path-broken (built /home/cedev2, repo at /workspace; no uv/ssh-keygen) → **self-healing now** (recreate venv). Pane alive+drivable. After green → Phase 3.
- dev-1 + dev-3 Working on Phase 2/1. Crons :00/:05/:30 alive. Board monitors b9aipnn3b/bh8s12igt + seat watchers alive. GitHub merge queue working.
- WORKER MODEL: Haiku=recon/triage, Sonnet=harvest/review/implement, Opus=hardest reasoning+controller. Always custom role + explicit model. Contained-seat dispatch = /var/tmp worktree, branch off origin/main, .venv/bin/python, deliver via docker-exec tee, pointer+sha via herdr (verify Working — Enter may need re-send).
