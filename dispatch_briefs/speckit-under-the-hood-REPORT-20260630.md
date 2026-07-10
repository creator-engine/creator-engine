# Research Report — Should CE wire spec-kit's SDD pipeline "under the hood" into its proven orchestration build path?

**Role:** architect_research (Opus, read-only) · **Date:** 2026-06-30 · **External sources current as of 2026-06-30 (spec-kit 0.12.0 released 2026-06-29)**
**Status:** decision-grade; awaiting Operator ratification. Brief: `.ce/briefs/speckit-under-the-hood-research.md`.

## Recommendation (up front)
**Do NOT wire spec-kit's runtime pipeline (specify→clarify→plan→tasks→implement→analyze) under the hood.** Three parts:
1. **Pipeline: don't-adopt (HIGH confidence).** CE's `cev3` outer loop (Frame→Shape→Build→Review→Ship + Scope card) + orchestration inner loop (dispatch→implementer-in-worktree→harvest→independent review→merge-gate) already subsumes SDD and adds governance speckit lacks (Budget/appetite cap, mutation_class, ratify, author≠approver, attestation, external grading).
2. **Templates: keep status quo (HIGH).** Speckit stays at the human-authored artifact layer for feature/epic specs (constitution Principle X). Already the case.
3. **The one real gap — test-first coupling — build CE-native, NOT from speckit (MEDIUM-HIGH).** Speckit wouldn't even close it: its `tasks-template.md:11` makes tests OPTIONAL (CE's fork preserved that). A `validate-pr` check would.

## Redundancy / additivity map
| spec-kit stage | CE already covers it | Net-new if wired |
|---|---|---|
| specify | cev3 Scope: Goal(intent)+Done-when(acceptance) (v3_cli.py:126-130,767-773); Principle I Spec-First; spec-template vendored | ~None — Done-when is the executable acceptance contract |
| clarify | cev3 shape detect-and-offer (v3_shaping.py); Budget human-only | Low — Shape forces ambiguity resolution pre-bet |
| plan (Constitution Check) | plan-template.md ALREADY forked with CE's 12-principle Constitution Check; ratify is the gate | ~None — re-importing upstream would REGRESS the fork |
| tasks ([P] markers, test tasks) | tasks-template.md ALREADY forked (sidecar metadata, attestation tasks); parallelism via territory-map+batch-dispatch | Partial+mismatched — static tasks.md is file-level; CE parallelizes across file-disjoint tickets/worktrees |
| implement | implementer role in isolated worktree, scoped PAT, no merge authority | None — CE's is stronger (isolation+credential+author≠approver) |
| analyze | validate-pr (baseline-diff regression gate, work-class, path-manifest, changelog, docs-reconcile) + independent review + merge-gate | None — CE's is the "grader OUTSIDE the agent" (the moat); speckit analyze is in-agent self-check (weaker) |

**Value flowed CE→speckit-template, not the reverse.** Every stage is already covered, most more strongly.

## Decisive points
- **Moat dilution (HIGH):** speckit analyze/clarify are IN-agent self-checks — the opposite of CE's "grader outside the agent" thesis. Wiring them moves judgment back inside the agent.
- **Rented-surface sync burden (HIGH, evidenced):** spec-kit went 0.8.7 (2026-05-07) → 0.12.0 (2026-06-29) = ~25 releases in ~7 weeks, ≥4 breaking checkpoints (incl. v0.10.0 removing `--no-git`/`--ai`). Upstream is ALSO growing its OWN orchestration layer (workflow step catalog, fan-out/fan-in, converge, governance extensions) — i.e. drifting toward COMPETING with CE's native orchestration. Deepening the dependency binds CE to a fast-moving target colonizing its own differentiator. This is the ce-ops#114 drift, already in flight.
- **Doctrine conflict (MEDIUM):** speckit spec/tasks templates carry MVP-first framing (spec-template.md:16 "viable MVP"; tasks-template.md:218 "MVP First") — directly contradicts CE's no-MVP-quality-from-day-1 doctrine. The #114 template sync MUST strip this, not import it.
- **Real drift modes are coordination, not spec-absence:** "done≠committed-SHA," "verify-not-already-landed," territory collisions, re-brief discipline — caught at harvest + merge-gate, NOT preventable by an SDD front-half. Out-of-scope builds already bounded by Done-when grading + one-worktree implementer scope.
- **TDD gap is real but un-purchasable from speckit:** validate-pr's baseline-diff gate is regression-proof, NOT test-first; speckit leaves tests optional. CE's actual test-first rigor is playbook discipline, not a machine gate.

## The only thing worth building: a CE-native test-coupling gate
New `pr_preflight.py` check beside `_run_baseline_diff_tests`: if a code-class (mutation_class) diff adds ZERO test deltas → gate finding, tunable by class (docs/tiny exempt; feature/epic strict). ~Zero added LLM cost, no artifacts, no rented surface.

**Optional A/B pilot (only if Operator wants the empirical kill-shot):** one feature-class ticket run twice from same Scope — Arm A current orchestration vs Arm B +speckit-pipeline. Metrics: drift (mid-stream re-briefs + out-of-Done-when findings), rework (post-merge fix commits), quality (REQUEST_CHANGES count + new-line test coverage), throughput (wall-clock + tokens), sync cost. Decision rule: Arm B must beat Arm-A-plus-the-native-test-gate net of cost. Predicted: Arm B's win is mostly "a written spec existed," which Arm A already has via Done-when.

## Implication for the mode-axes canon
Reword "agent invokes the speckit pipeline under the hood" → **"invokes CE's cev3 SDD outer-loop + governed orchestration."** What our Fleet cells actually run under the hood is CE's own Frame→Shape→Build→Review→Ship — the better realization of the same SDD intent. Keep speckit at the Principle-X artifact-compatibility layer only.

## Recommended follow-ups
1. Reword the mode-axes canon (governance-doc edit).
2. Proceed with **ce-ops#114 as a TEMPLATE-layer sync only** — re-base forked spec/plan/tasks templates onto 0.12.0, PRESERVE CE governance forks, STRIP MVP-first framing — NOT runtime adoption.
3. Spec a **CE-native test-coupling gate** in validate-pr (the one real gap) as a small TDD-strengthening ticket.
4. Optional: run the A/B pilot only if an empirical record is wanted before closing the question.

## Honest method limitations
- No shell → did not run `sha256sum` on the brief (read directly) or `gh` to sample real merged PRs; grounded the drift question in `specs/_traceability_matrix.md` + the codified anti-pattern corpus instead. Controller could confirm against 10-15 recent PRs' harvest notes.
- The brief named `harvest_intake`/`ops_triage` as worker roles; `.claude/agents/` has four files (implementer/reviewer/verification/architect_research) — harvest is a controller playbook. (Note: these DO exist as session-provided subagent types; the discrepancy is only in `.claude/agents/` files and is immaterial to the recommendation.)

## Sources
github/spec-kit releases + CHANGELOG (0.8.7 2026-05-07 → 0.12.0 2026-06-29); arXiv 2602.00180 (SDD code-to-contract); arXiv 2601.03878 (SANER 2026 empirical SDD+LLM); BCMS SDD 2026 guide. Key internal paths: v3_cli.py:124-175/765-773, pr_preflight.py:282-322, .specify/templates/*, .specify/memory/constitution.md (Principles I,IV-VIII,X), specs/_traceability_matrix.md.
