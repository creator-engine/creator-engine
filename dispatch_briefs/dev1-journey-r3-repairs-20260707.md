ROLE: implementer
SEAT: dev-1
PRS: #876 and #877 journey program repairs

Read AGENTS.md and .claude/agents/implementer.md before acting. You are not
alone in the codebase; do not revert others' edits. Work in isolated worktrees
for the PR branches. Do not approve, merge, or enqueue.

Repair #876 at current branch `ce-486-next-step-hints`.
Blocking reviewer finding:
- `validators/creator_engine_validator/v3_cli.py` emits
  `journey_guidance.report_next()` unconditionally around the report command.
  For evidence outcome `pr_opened`, the command prints both a PR review next
  step and `Journey complete.`, contradicting `v3_report.render_next()`.

Expected fix:
- Make next-step hints conditional and consistent with `v3_report.render_next()`.
- Ensure JSON next fields remain correct.
- Add/adjust focused regression tests for the `pr_opened` case and the journey
  complete case.

Repair #877 at current branch `ce-485-canonical-journey-doc-pair`.
Blocking reviewer finding:
- `docs/guide/quickstart.md` and generated `quickstart.html` still say Budget
  is required.
- `docs/guide/complete-walkthrough.md` and generated
  `complete-walkthrough.html` have the same drift.

Expected fix:
- Required fields are exactly Goal, Done-when, and Change-type.
- Budget is opt-in wording only.
- Regenerate/update generated HTML mirrors and any affected doc index artifacts.

Bars:
- Keep #876 and #877 file scopes disjoint except shared generated docs only if
  required by the local generator.
- Run focused tests plus full `ce validate-pr` for each branch before push.
- Self-push only after validation. Stop with READY <pr> <head> and evidence, or
  BLOCKED with exact blocker.

Standing preflight directive: run the FULL local validator preflight (`ce
validate-pr`, CI-parity) before every self-push or commit-for-harvest; do not
discover gates via CI.
