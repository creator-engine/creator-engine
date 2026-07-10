# Seed Brief: N4c(2) — Press-merge evidence-bundle ARCHITECT PASS (DESIGN-ONLY)

- Role: architect (read + analyze + write ONE report file). Night-arc mandate lane N4, second design item.
- DESIGN-ONLY tonight: no code, no workflows, no commits, no push. The build phase happens later
  under a separate dispatch after Operator ratification of your design.

## Ticket content (embedded — the tracker is not reachable from your seat)
Title: "Evidence-verified press-merge UX — single ratification surface (Wave 1.4)"
Goal: aggregate gate evidence (diff + test results + review notes + computer-use video where
relevant) into a SINGLE ratification surface so the human act collapses to: "review the bundle,
press merge."
Scope: an evidence-bundle assembler pulling diff, CI results, reviewer notes, and (where relevant)
computer-use capture into one structured artifact; presented per-PR as a ratification artifact
(comment, artifact file, or dedicated surface — that choice is YOURS to design and justify).
DoD for the full ticket: design complete + a working bundle for ≥1 real PR; if build exceeds one
PR, halt + amend. Tonight you deliver the DESIGN half only.

## Read (in-repo evidence base — use a fresh /var/tmp read worktree at origin/main like your
## previous task; record the SHA you read)
- The merge-gate surfaces the bundle must cover: validators/creator_engine_validator/forge/
  (automerge_policy.py, automerge_actuator.py, integrator_belt.py — audit-record shapes),
  work_sizing.py, checks/path_manifest_fidelity.py, checks/work_sizing_floor.py
- .github/workflows/automerge-decide.yml + automerge-actuate.yml (decision JSON + audit JSONL —
  natural bundle inputs)
- The `ce` CLI structure (ce_cli.py) for where a `ce pr evidence` style command would live
- docs/adr/ADR-0004 for the safety idiom (bundle must be read-only aggregation; it must never
  become an execution or authority surface)
- Existing PR ceremony artifacts: .ce/pr-manifests/, .ce/changelog/ (bundle inputs)

## Produce: /var/tmp/PRESS_MERGE_EVIDENCE_BUNDLE_DESIGN_dev4_20260702.md
1. Inventory of every evidence source that already exists per-PR (with file:line or artifact name):
   decision JSON, actuation audit, validate-pr output, review verdicts, carrier, changelog,
   work-class declaration, head/approval state.
2. Bundle schema proposal: one structured artifact (name the format) with a stable field set;
   every field maps to a named source; include provenance (SHAs, run IDs, timestamps) so the
   bundle is verifiable, not narrative.
3. Presentation surface decision: PR comment vs artifact file vs dedicated `ce` command — pick a
   default and justify; state how staleness is handled (bundle minted for a head SHA, invalid on
   push, consistent with the approval-must-match-current-head doctrine).
4. Assembler placement: where the code lives, what triggers it (decide-workflow completion is the
   likely seam), read-only permissions it needs, and explicitly what it must NEVER do (no merge,
   no approve, no state mutation beyond publishing the bundle).
5. Build plan for the one-PR demo (the ticket's DoD): smallest end-to-end slice, estimated size
   (target XS/S), file list it would touch — so the follow-up build dispatch is ready-made.
6. Ratification asks: numbered decisions with your recommendation as the default.

## Evidence + stop line
- Done-report (single line, then stop):
  `READY-FOR-HARVEST report=/var/tmp/PRESS_MERGE_EVIDENCE_BUNDLE_DESIGN_dev4_20260702.md sha256=<sha256sum> read-sha=<main SHA read>`
- NO commits, NO branch, NO push, NO PR, NO edits outside /var/tmp. Stop after the done-report.
