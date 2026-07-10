# BUILD MANDATE — Integrator MVP (autonomous merge-mechanics, Phase 1)

**Drafted by CE-DEV-2 controller, 2026-06-23. Status: TEED UP** (Operator approved sequencing + go-ahead 2026-06-23; per-unit escalations noted). **Design basis:** `DESIGN_INTEGRATOR_merge_mechanics_20260623.md` + ce-ops#216. **Grounding:** the 2026-06-23 Wave-1 rebase work (#366/#367/#368) is the live spec — the conflicts the controller resolved by hand (`_versions.py` frozenset, `test_version_boundary` count, `install.sh` keep-both, path-manifest carriers) are exactly what the MVP automates.

## SCOPE (Phase 1 / MVP — deterministic-only, no LLM resolver yet)
On a merge-queue eviction (`DIRTY/BEHIND/CONFLICTING`) of an APPROVED+green PR: detect it, rebase, apply **deterministic mechanical resolvers** for the common cases, re-green, re-enqueue with a race guard. Escalate anything not mechanically resolvable to the controller (technical escalation for MVP; plain-language product-framing is Phase 2). Reuses the belt/spine; no new always-on daemon.

## PREREQUISITE (hard dependency)
- **Bot-fix: `ce-forge-dev-2[bot]` dismiss-on-push** (investigation in flight 2026-06-23). The Integrator's rebases MUST preserve a standing approval — otherwise every repair re-triggers full re-review and the MVP cannot land a PR hands-free. **Integrator build does not start until the bot is diff-aware (rebase preserves approval).**

## WORK UNITS (bounded, strict-TDD; ~200-400 ln each)
- **I-0 · Grounding/design pass** (controller + Operator-gated): pin the eviction-detection trigger (polling the forge for APPROVED+`DIRTY/BEHIND/CONFLICTING` via the existing `pickup.py` Search-API pattern = ratified default; merge_group-failure webhook = future) and the deterministic-resolver registry shape. **Escalation:** trigger-surface + the mechanical-vs-product conflict taxonomy are architecture calls → surface before building.
- **I-1 · Eviction detection / repairable-PR intake**: extend the belt poll to surface APPROVED PRs that went non-mergeable as `repairable` work items (reuse `pickup.py` poll/claim + `work_claims` lease + dedup ledger; reviewer-fence still applies). Read-only detection; emits a claimable repair item.
- **I-2 · Deterministic mechanical resolver library** (the heart): codify the resolvers proven by hand today — `_versions.py` frozenset union, `test_version_boundary` count recompute-from-frozenset, changelog fragments, `.ce/pr-manifests/*` carriers (recompute against new base), lockfiles, isolated/non-overlapping hunks. Each resolver = pure function + property tests; explicit "not-resolvable → escalate" return. **This is the unit that pays back today's manual toil.**
- **I-3 · Repair executor + race guard**: adopt branch (from REMOTE head — local refs go stale), rebase onto main, apply I-2 resolvers, re-green (run the gate suite), `--force-with-lease` push, re-enqueue. Race guard = settle (~90s) + re-fetch live head + requeue-not-push-if-moved (ClawSweeper pattern). **Write-authority stays with the deterministic executor; no LLM in MVP** (LLM read-only resolver = Phase 2). Governed: runs on the spine, evidence-logged.
- **I-4 · Escalation seam (MVP)**: when I-2 returns not-resolvable, emit a contact-on-need notify event (via `notify_feed`, reuse the #364 webhook sink) to the controller. MVP = technical escalation; **Phase 2 = plain-language product-decision framing** (the differentiator).

## SEQUENCING (the program order)
1. **NOW (in flight):** finish onboarding wave (PR-4+5 / PR-6 / A2-scope2) + close Wave-1 (#368) + **bot-fix** (prerequisite).
2. **NEXT: Integrator MVP** — I-0 (design pass, Operator-gated) → I-1/I-2/I-3/I-4 (I-2 and I-1 parallelizable; I-3 depends on both; I-4 additive). Each unit independently reviewed, merge-gated; conflict-disjoint dispatch (manifest-intersection — lesson from Wave 1).
3. **THEN: belt-arming** — one-seat live canary of `pickup poll --claim --enable-launch` → fleet flip (+ dev-4 cron + belt roots/brain-init). Sequenced AFTER the Integrator so pickup→PR→merge is hands-free **end-to-end** (arming before the Integrator would flood the manual merge leg — see belt-assessment 2026-06-23).

## ESCALATION LINES
- I-0 trigger-surface + conflict-taxonomy = architecture → Operator bless.
- Any governance-posture change (bot dismiss behavior; what the Integrator may auto-land vs must escalate) → Operator bless.
- Phase 2 (LLM read-only resolver; plain-language product escalation) + Phase 3 (control-plane + ephemeral-execution; per-module `_versions` registration) are OUT of MVP scope.

## DoD (MVP)
A merge-queue-evicted, APPROVED+green PR with a *mechanical* conflict is rebased, resolved, re-greened, and re-enqueued **with zero controller action**, approval preserved (bot-fix landed), evidence-logged on the spine; a non-mechanical conflict escalates cleanly. Proven on a real eviction (the next `_versions.py` collision is the natural test case).
