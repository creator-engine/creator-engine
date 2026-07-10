# BRIEF — ce-ops#454 slice 1: merge-triggered dependency-unlock executor (SHADOW-first)
# Dispatched 2026-07-05 night (ratified night-arc lane N-D). Controller: CE-DEV-2.

Branch: ce-454-dependency-unlock-executor. Work class: feature.
Worktree: your own, off FRESH origin/main (post-#838; verify docs/contracts/dependency-unlock.md
is present at your base — it merged via #828). If ce_cli.py at your base lacks #837's
preflight changes, `git fetch` again — #837 is merging as this is written; branch AFTER it
lands to avoid a ce_cli.py seam conflict.

## Controller decisions (locked)
- Shape: validator module + `ce` CLI subcommand (the ce_ops_triage_queue.py pattern), NOT a
  standalone .github/scripts script. Workflow YAML = thin glue.
- CLOSED-WITHOUT-MERGE RULE (verbatim from ce-ops#454, review-banked): "closed-without-merge
  is NOT completion; the blocker stays blocking unless a completed successor is declared or
  the dependency is explicitly removed." Implement as: PR blocker resolved ⇔ merged==true;
  issue blocker resolved ⇔ state==closed AND state_reason=="completed". Everything else
  (closed unmerged, not_planned, unknown) = still blocking, fail-closed.
- SHADOW mode = workflow log + JSON audit artifact ONLY (no marker comments on issues).
- Stretch piece-4 (work_claims lifecycle states) is NOT in this unit. Do not touch work_claims.py.

## Build
1. NEW validators/creator_engine_validator/dependency_unlock.py — pure logic, injectable
   GhRunner (reuse the GhRunner/label-delta idioms from ce_ops_triage_queue.py; reuse
   forge_triage.readiness_blockers/_BLOCKING_LABEL_PREFIXES/_DEPENDENCY_FIELDS for parsing —
   do NOT reimplement blocker parsing).
2. NEW .github/workflows/ce-dependency-unlock.yml — trigger: pull_request types:[closed],
   gated merged==true && base.ref=='main', plus workflow_dispatch (optional apply bool,
   default false). Auth: existing CE_CROSS_REPO_TOKEN secret; continue-on-error: true at job
   level; fail-open (warn + exit 0) if token absent — mirror ce-ops-autoclose.yml. Do NOT
   edit ce-ops-autoclose.yml. concurrency group ce-dependency-unlock-${{ github.event.pull_request.number }},
   cancel-in-progress: false. Upload audit artifact ce-dependency-unlock-audit-${{ github.run_id }}-${{ github.run_attempt }}
   (if-no-files-found: warn) on EVERY run.
3. Behavior per run: identify merged item (owner/name#number, merge SHA, timestamp) →
   search ce-ops open issues whose blocker surfaces name it → for each candidate RE-READ
   labels+body immediately before deciding → recompute readiness fresh → if ALL declared
   blockers resolved (rule above) AND no non-dependency hold label present → proposed
   mutation = remove ONLY the dependency-hold label. SHADOW default: zero write calls, log
   + artifact the proposal (candidate id, blocker refs, label, dedup key, evidence hash).
   LIVE (dormant): _remove_issue_label-style call with re-check-before-mutate; label-already-
   absent = success no-op.
4. Switches (repo VARS, not inputs): CE_DEP_UNLOCK_RUN_MODE ('live' enables; anything else
   = shadow) + CE_DEP_UNLOCK_KILL_SWITCH (truthy FORCES shadow regardless). Ship with
   neither set — PR body must state "ships SHADOW-only; no repo variable set to enable live
   mode". Variable provisioning is a later ops action, never in this PR.
5. Dedup key per contract: dependency_unlock + repository + blocked_item + blocker_ref +
   normalized_event_kind + evidence_hash + window; window="instant" only this slice.
6. Fail-closed set (contract obligations, all must have code paths): unparseable ref;
   ref resolving to ≠1 item; any blocker open/unknown/inaccessible/missing/ambiguous;
   disagreeing declarations → union, all must complete; labels/body not re-readable → stay
   blocked; non-dependency hold label → stay blocked; mutation target changed after evidence
   → stale, re-evaluate; missing tooling/creds → refusal evidence, never best-effort. If the
   cross-repo blocker-reference SEARCH itself is degraded/incomplete → whole scan
   inconclusive, refuse (not silently partial). The search helper is new surface — test it.
7. Tests (NEW validators/tests/unit/test_dependency_unlock.py, fake GhRunner, zero network):
   (a) same event twice → one proposal; (b) fail-closed on unparseable/ambiguous/multi-
   resolving refs; (c) non-dependency hold blocks despite resolved deps; (d) shadow mode
   makes ZERO write-verb calls (assert on fake runner call log); (e) kill-switch truthy
   forces shadow even with RUN_MODE=live; (f) closed-without-merge: PR closed unmerged stays
   blocking; issue closed not_planned stays blocking; issue closed completed resolves.

## File allowlist
NEW dependency_unlock.py + test_dependency_unlock.py + ce-dependency-unlock.yml; minimal
ce_cli.py subcommand registration (+ .ce/reference/cli.generated.md regen if the repo
regenerates it for new subcommands — check how #837 did it); .ce/changelog/ce-454-dependency-
unlock-executor.md + carrier via write_carriers (rm -rf build/ *.egg-info first). Do NOT
touch: docs/contracts/dependency-unlock.md, ce-ops-autoclose.yml, work_claims.py,
checks/surfaces_manifest.py, launch_runtime.py, cli.py, v3_cli.py, tools/egress-broker/**.

## Bar
FULL `ce validate-pr --declared-work-class feature` GREEN one pass before finishing. Commit
everything on the branch; report head SHA + validate-pr summary + any contract ambiguity you
hit (surface it, don't reinterpret). Do NOT push (controller harvests), do NOT approve/merge.
