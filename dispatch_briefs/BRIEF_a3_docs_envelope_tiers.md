# BRIEF — A3: extend automerge AUTO-tier coverage to the FULL ratified docs-class envelope
Role: implementer (foreman-batch OK). Claim: ce-a3-docs-envelope-tiers. Branch: `ce-a3-docs-envelope-automerge` (worktree under /var/tmp, branch off origin/main; your origin/main is stale — that is fine, controller reconciles at harvest).

## Goal (one sentence)
Make the IMPLEMENTED auto-merge tier coverage equal the RATIFIED docs-class envelope — docs/**, *.md, .ce/changelog/**, .ce/pr-manifests/** — so a pure docs-class PR (e.g. an ADR) with APPROVED review + green required checks gets decision AUTO end-to-end, instead of falling to manual because only the narrower carrier/changelog and brain-supersede path-set tiers fire today.

## Authority context (embedded — you cannot read ce-ops)
Ratification record (ce-ops#356, Operator 2026-06-29, Option A, ARMED since): "Surface A armed via repo Variables CE_AUTOMERGE_RUN_MODE=ceo + CE_AUTOMERGE_ENABLING_REF. Blast radius: docs-class only (docs/**, *.md, changelogs, manifests); code/validator/schema PRs unaffected." This task IMPLEMENTS the already-ratified envelope. It does NOT need new ratification. Anything beyond that envelope (code-class etc.) is OUT OF SCOPE — hard stop.
Live gap evidence: PR #771 (docs/adr/ADR-0014 + changelog + carrier, pure docs-class) required a manual ce-dev-2 approval+merge because no armed tier's path-set predicate matched. Your fix must make exactly that case AUTO. Existing tiers to preserve: carrier/changelog tier (landed with the L2 arming work) and brain-supersede tier (your own PR #757, merged).

## Design seed
YOUR OWN proposal: /var/tmp/AUTOMERGE_TIER_EXPANSION_PROPOSAL_dev4_20260702.md (current-state map with file:line refs is accurate as of ~2 days ago — re-verify against your checkout). Relevant surfaces from it: forge/automerge_policy.py (AUTO/GESTURE constants, materialization, decision predicates ~:286-440), forge/mutation_classifier.py (AUTO_CLASSES = {"none","docs"}), forge/automerge_mutation_policy.yaml (docs path envelope :16-23 — likely already correct; the gap is which TIER/path-set predicates produce AUTO), forge/automerge_actuator.py (independent re-verify :66-124), and the daemon-side path-set tier predicates (where the carrier/changelog + brain-supersede path sets are enforced — locate them, likely forge/integrator_belt.py or adjacent).

## Requirements
1. NOVELTY CHECK FIRST: probe your checkout's main for an existing docs-envelope tier (grep the tier/path-set predicate definitions). If already implemented, STOP and signal BLOCKED with evidence instead of duplicating.
2. Extend the tier path-set coverage to the full ratified envelope. Extend-don't-weaken: every OTHER AUTO precondition stays intact (armed run mode, enabling ref, kill switch, APPROVED review on current head, green required checks, distinct author/approver, work-class ceiling tiny|XS / story|S, size band, mutation class not gesture).
3. Regression test reproducing the #771 case: path set {docs/adr/ADR-00xx-*.md, .ce/changelog/<slug>.md, .ce/pr-manifests/<slug>.md} + all other predicates satisfied → expect AUTO. Plus negative tests: same set + one code file → NOT AUTO; envelope file with work class M/L → NOT AUTO.
4. Keep the decide/actuate workflow contract unchanged unless strictly required; if a workflow file must change, flag it prominently in your done-report.
5. Changelog fragment .ce/changelog/ce-a3-docs-envelope-automerge.md + path-manifest carrier via the carrier_gen API (never hand-list). Work-class: S expected; use M if diff exceeds ~400 lines.

## Stop lines (hard)
Do NOT touch: conveyor_daemon.py, daemon_lease.py (in-flight PR #778), validation_sandbox_*.py (in-flight PR #777), v3_cli.py, ce_cli.py, ce_onboard.py (just-merged #776 — CLI churn forbidden; if a CLI knob is needed, note it as a follow-up in the done-report), portability_plane.py (in-flight #774), docs/install.sh or anything under docs/downloads/ (release-signed). No repo-Variable changes, no run-mode changes, no new tiers beyond the ratified docs envelope.

## Preflight + signal (standing, ce-ops#303)
Run the FULL local validator preflight (`ce validate-pr`, CI-parity) GREEN in ONE pass before commit-for-harvest; do not discover gates via CI (use `.venv/bin/python -m pytest` for iteration; the full suite gates the finish). Then commit and emit exactly:
`READY-FOR-HARVEST ce-a3-docs-envelope-automerge <full-40-hex-commit-sha>`
(no placeholder, bare prefix form, real sha from `git rev-parse HEAD`). If blocked: `BLOCKED ce-a3-docs-envelope-tiers <one-line reason>`.
