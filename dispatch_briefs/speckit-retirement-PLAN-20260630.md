# Spec-Kit Full Retirement — Execution Plan (CE-DEV-2)
**Operator-ratified FULL RETIREMENT (2026-06-30).** Pilot: Nitzan Solo+Dev TODAY; NVIDIA pitch 01-Jul (don't break live install/docs/demo). Full architect plan: agent a992557a8980282f8 log. Report basis: `.ce/briefs/speckit-under-the-hood-REPORT-20260630.md`.

## KEY FACTS
- **No CI gate breaks on speckit removal** — `skill_antidrift_guard.py:23` explicitly exempts speckit skills; `test_v1_docs_reconciliation`, `test_site_index_docs_nav` (file-existence only), full pytest — none reference speckit. Verified.
- **User-facing command = `ce`** (v3_cli.py:18-24; `cev3` is internal console-script only, users never type it). Docs are user-facing truth → BOTH onboarding guides must use `ce`. The in-flight solo-ceo-onboarding.md uses `cev3` → FIX to `ce`.
- **KEEP:** `specs/00X-*` + `_traceability_matrix.md` (historical), `.specify/memory/constitution.md` (until Principle X amended).

## PHASES
- **Phase 0 — TODAY-CRITICAL (docs, additive, SAFE-NOW).** On #674 branch (ce-onboarding-mode-cell-banners): (a) NEW `docs/guide/solo-dev-onboarding.md` = cev3 hands-on path (Nitzan); (b) fix solo-ceo-onboarding.md speckit refs (line ~28 Shape row, ~247) → `ce` cev3 framing; (c) change banners on getting-started-step-by-step.md + agile-to-ce-sdlc.md from "type /speckit" → "speckit retiring; see solo-dev-onboarding.md" (banner only, NOT full rewrite); (d) index.html link + carriers. Owner: onboarding implementer (a26e1368). Work-class story.
- **Phase 1 — Skill removal (tiny, SAFE-NOW, merge AFTER Phase 0).** Delete all 13 `.claude/skills/speckit-*`. Owner: dev-3 (contained seat). No CI change.
- **Phase 2 — `.specify/` removal (tiny, SAFE-NOW, merge after Phase 1).** Delete `.specify/` EXCEPT `.specify/memory/constitution.md`. Owner: dev-1 (contained seat).
- **Phase 3 — Full guide rewrites (story, SAFE-NOW, AFTER Phase 0 merges — collides w/ Phase 0 on getting-started).** Rewrite getting-started-step-by-step.md + agile-to-ce-sdlc.md to cev3; minor contributing-to-ce.md. Owner: a seat post-Phase-0.
- **Phase 4 — Constitution Principle X amendment (RATIFICATION-GATED).** spec/plan/tasks triple + Operator(Source) approval + MAJOR version bump; optionally move constitution → docs/governance/CONSTITUTION.md; annotate architecture docs (integration-map, SAD, agentic-sdlc-operating-model §d, agent-interaction-model). NOT bundled with mechanical PRs. HOLD for Operator.
- **Phase 5 — Housekeeping.** Close ce-ops#114 (retired, not synced) + #367 (superseded). File follow-up: "CE-native build-decomposition artifacts (`ce spec/plan/tasks new`)" — fills the one cev3 GAP (visible hands-on spec/plan/tasks docs that speckit-specify/plan/tasks provided); medium-pri, NOT a pilot blocker.

## MERGE ORDER (controller-gated): Phase 0 → 1 → 2 → 3. Phase 4 parallel but Operator-gated.
## dev-4 BLOCKED: in-container py3.14 venv broken (cf ce-ops#339 libsodium) → cannot run preflight → no build dispatch until env fixed (L5 seat-health / canonical relaunch).
