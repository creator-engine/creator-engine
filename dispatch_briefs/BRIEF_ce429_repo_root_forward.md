# BRIEF — ce-429-repo-root-forward — forward --repo-root into decide_automerge (QUEUED UNIT 3)

Role: implementer (dev-1, self-push, foreman mode). UNIT 3 — start after your ce-49 skew-guard
unit's PR is opened. ⚠️ SAME-FILE SERIALIZATION: this unit also touches ce_cli.py — branch
`ce-429-repo-root-forward` off freshly-fetched origin/main AFTER your ce-49 branch is pushed, and
if ce-49 has not merged by the time you finish, expect a rebase at review time (note it in the PR
body if the diff context overlaps).

Mandate: read ce-ops#429 directly (gh read). Deliverable per ticket: the `decide_automerge` call
in validators/creator_engine_validator/ce_cli.py does not receive `--repo-root`; forward it.
Semantic novelty check first (verify the parameter is still missing on main); already-fixed →
BLOCKED already-resolved. Add/extend the behavioral test proving the forwarded root is used.

Files (closed set): validators/creator_engine_validator/ce_cli.py · its test module ·
changelog · carrier (stem == branch). Constraints: main-vintage ce invocation; ⛔ signed-artifact
stop-line; FULL validate-pr GREEN one pass; work class tiny. PR body: work-class line +
`Closes creator-engine/ce-ops#429`. Stop line: no review/approve/merge/enqueue.
