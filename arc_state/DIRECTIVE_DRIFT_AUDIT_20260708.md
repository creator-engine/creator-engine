# DIRECTIVE DRIFT AUDIT — 2026-07-08 (controller-annotated)

> Produced by a read-only architect_research worker; ANNOTATED AND PARTIALLY CORRECTED by
> the controller before persistence. ⚠️ The worker read parts of the LOCAL ROOT CHECKOUT
> (stale ce-release-0.3.1-rc2 branch) as if it were main. Every ⚠️-marked claim below was
> re-verified against origin/main (e5d3710c) by the controller on 2026-07-08. Corroborating
> independent sources: RELEASE_ENGINEERING_GAP_ANALYSIS_20260708.md (API-level #467
> post-mortem) and the T5 welcome-pack fork (.hermes onboard behavior on main 0.3.4).

## 1. ce-ops#467 post-mortem (docs currency / drift gate) — CORRECTED
- ⚠️ CORRECTED: `checks/version_drift.py` + its test DO exist on origin/main (worker's
  "absent from main" verdict was an rc2 artifact). The version-string gate SHIPPED:
  main README carries 0.3.4 correctly.
- CONFIRMED on main: README still contains the "As of June…" narrative status block —
  the gate polices VERSION STRINGS, not narrative content currency. Confirmed:
  release.yml contains ZERO README/website sync steps. So #467's "release-triggered
  README + website sync" and content-currency parts NEVER shipped.
- CONFIRMED via API (release-engineering fork): the autoclose bot closed #467 on a PR
  explicitly titled "slice 1" — closure on cross-reference credit, not on acceptance.
- NET VERDICT: #467 = closed-but-partial. Version-drift slice real; sync/content
  currency unshipped. The dev-4 P0 unit (ce-readme-overhaul) extends the gate to
  README version coverage; content-currency + release-triggered sync remain open scope
  (fold into ce-ops#509 release-acceptance program or reopen/re-file #467 residual).

## 2. Spec-kit retirement completeness — CONFIRMED ON MAIN
The 3 retirement PRs removed skills (24 files) + .specify tree (37 files) + amended the
constitution. NOT covered, VERIFIED still on origin/main: 12 live-crutch doc files that
present /speckit-* verbs as the current workflow:
docs/architecture/{agentic-sdlc-operating-model (16 refs), SAD, integration-map,
agent-interaction-model, parallel-agent-development-model}; docs/product/{REQUIREMENTS,
PRD, ROADMAP}; docs/delivery/{DEFINITION_OF_READY, ASSIGNMENT_ENVELOPE_TEMPLATE};
docs/governance/{MUTATION_CLASS_MODEL, AUTHORITY_AND_RATIFICATION_MODEL}.
(docs/guide legacy-labeled mentions + specs/006 retirement spec = acceptable.)
Severity: medium — contributor-facing comprehension; docs layer was in NO retirement
PR's path manifest (tight-manifest discipline made docs systematically out-of-scope).

## 3. .hermes kill-list scope (feeds ce-ops#507 / dev-1 unit)
From the worker's tree sweep (rc2-based counts; magnitudes indicative, re-enumerate from
main in the retirement unit): ~196 files / ~993 references. 7 LIVE RUNTIME deps (onboard
behavior independently confirmed on main 0.3.4 by the T5 fork):
1. init_runtime.py KERNEL_STATE_DIRS — ce init creates 14 .hermes/* dirs
2. environment_guard.py RED-G-4 — ce doctor fails unless .hermes git-ignored
3. ce_onboard.py STATE_PATH_GUIDANCE — user-facing .hermes instructions
4. pco_allocator.py — controller-id at .hermes/controller-id
5. cli.py — --ledger-root auto-resolves to .hermes/active-work-ledger
6. role_boundary_attribution.py — handoffs from .hermes/handoffs/
7. hermes_launch_spec.py — whole module
NOTE: v3_naming_hygiene.py documents the rename as "post-pilot, ratifiable" — the
deferral WAS designed, but #149's closure never stated that scope boundary, which is how
it read as "retired" in controller/Operator working memory. Operator has now directed:
cut NOW while zero active users (2026-07-08).

## 4. Closed-vs-real sweep — PARTIAL (repo-local only)
Confirmed drift: #467 (partial, above) · #149 (partial: launch paths only) · #140
(real at close-time; no prevention mechanism → re-rotted).
Latent reliability gap: ce-ops-autoclose bot is continue-on-error+fail-open — on token
rotation it silently stops closing (infrastructure, not drift).
REMAINING WORK: API sweep of last-21-day closed retire/migrate/automate/gate/sync
tickets vs main artifacts — needs overwatch PAT; queue as a follow-up recon unit.

## 5. Root cause + structural fix (CONVERGES with RELEASE_ENGINEERING_GAP_ANALYSIS)
Engine of the drift class: the autoclose bot is EVIDENCE-FREE — "a PR referencing
ce-ops#N merged" ⇒ closed, regardless of partial scope or which PR actually ships the
artifact. Compounders: rebase-limbo PRs blur when work "really" landed; tight path
manifests systematically exclude docs from feature scope; no post-close audit exists.
FIX (both workers independently converged; recommend Operator ratification):
closing a directive-class ticket requires an `Acceptance-Evidence:` field in the
closing PR body naming a test path or validator check that FAILS if the feature is
absent from main; autoclose bot greps for it (warn-first rollout, then enforce), plus
fix the bot's fail-open token behavior. This extends CE's merge-time evidence doctrine
to the tracker — same principle, fourth object (artifact/journey/ticket/release per
ce-ops#509).
