# BRIEF — ce-410-s10 — final publish re-verification + per-phase audit (ce-ops#410 slice 10)

Role: implementer (dev-4, contained). Branch: `ce-410-s10-publish-reverify-audit` off freshly-fetched
origin/main, worktree under /var/tmp (NOT /workspace). venv has no activate → `.venv/bin/python -m pytest`.

## Design SSOT (embedded — you cannot read ce-ops)
CE410_ARMING_FIX_DESIGN item 5 + recommended-order item 4 ("Final publish re-verification and audit
bundle (S)"): immediately BEFORE push/PR in the armed conveyor path, record and verify:
1. Final tree sha / head sha RE-DERIVED from the daemon-owned checkout at publish time equals the
   tree the validation sandbox verified (no drift between validation completion and transport push).
2. Base ancestry: branch is `behind == 0` vs the base (or equivalent ancestry check).
3. Path-manifest fidelity re-check AFTER validation sandbox completion (diff paths still == carrier).
4. No repo-local credential helper/hook/config mutation affecting transport commands (e.g.
   core.hooksPath, credential.helper, url.*.insteadOf in the checkout's .git/config).
Plus: structured per-phase audit records proving which context each phase used (allocation/
validation/publish), emitted through the existing audit sink pattern.

## MANDATORY first step — semantic novelty check (main moved: slices 8a-8c + 9 landed)
Main ALREADY HAS: validation_tree_sha threading (conveyor_daemon.py:562-574, :979, :1001),
allocation audit (_audit_allocation :777), discovery audit, landed-tree check in land_bundle,
armed required-seam list incl. validation_ledger_binding (:386). Locate the publish call site
(push ~:585, pr create ~:612), enumerate which of the four re-checks above ALREADY exist on the
publish path, and implement ONLY the missing ones. Report in the changelog body which checks were
pre-existing vs added. If ALL four already exist end-to-end, signal BLOCKED with evidence instead
of inventing work.

## Constraints
- Files (closed set): validators/creator_engine_validator/conveyor_daemon.py ·
  validators/tests/unit/test_conveyor_daemon.py · .ce/changelog/ce-410-s10-publish-reverify-audit.md ·
  .ce/pr-manifests/ce-410-s10-publish-reverify-audit.md. If the design forces touching another file,
  STOP and signal BLOCKED with the reason — do not widen unilaterally.
- Fail-closed: any re-check failure must refuse publish for that item (audit + skip/error), never warn-and-push.
- Do NOT touch conveyor_daemon_runner.py (A1, just merged), deploy/, docs/, or any signed artifact.
- ⛔ If any gate fails on a signed artifact (SSHSIG/SHA256SUMS/content_sha256): STOP, report bytes —
  never sign; ce-root-v1 is controller-only.
- Bounded: target ≤ ~300 LOC. Class `story` (enum tiny|story|feature|epic).
- Tests: behavioral — a publish-time drift (mutated tree between validation and push) must be
  refused; behind>0 refused; manifest mismatch refused; config-mutation refused; audit records
  asserted per phase. Extend existing armed fixtures (ARMED_ROOTS pattern), do not weaken any.

## Preflight (standing ce-ops#303)
FULL `ce validate-pr` GREEN in ONE pass before commit-for-harvest. Brain-drift false-RED →
reconcile from canonical.

## Evidence + signal (contained seat: commit locally, controller harvests)
Commit with message `ce-ops#410 slice 10: final publish re-verification + per-phase audit`, then
`git rev-parse HEAD` and emit: `READY-FOR-HARVEST ce-410-s10-publish-reverify-audit <40-hex sha>`.
This slice is gate-adjacent → it will get independent non-author review before merge (Re-Arming
Evidence Bundle input).

## Stop line
No push (you have no push auth), no PR, no review, no signing. Controller harvests on signal.
