ROLE: implementer
SEAT: dev-1
PR: #877 canonical CE journey guides
BRANCH: ce-485-canonical-journey-doc-pair
CURRENT PR HEAD: 982f44dc7328f1d8b60606129e74ed096dfc5428

Read AGENTS.md and .claude/agents/implementer.md before acting. Work in the
existing isolated #877 branch/worktree only. Do not approve, merge, enqueue, or
comment on GitHub.

Task: repair the independent reviewer REQUEST_CHANGES findings for PR #877.

Reviewer verdict from dev-3 Galileo:
1. Required Scope fields are still not exactly `Goal`, `Done-when`,
   `Change-type`. `Ready` is presented as a field in:
   - `docs/guide/how-ce-builds-software.md:43`
   - `docs/guide/how-ce-builds-software.md:50`
   - mirrored in `docs/guide/how-ce-builds-software.html:1`
2. Same blocker appears in other journey docs:
   - `docs/guide/understanding-ce.md:48`
   - `docs/guide/understanding-ce.md:53`
   - `docs/guide/solo-ceo-onboarding.md:94`
   - `docs/guide/solo-ceo-onboarding.md:102`
   - `docs/guide/complete-walkthrough.md:69`

Expected repair:
- Make the canonical required Scope fields exactly `Goal`, `Done-when`,
  `Change-type`.
- Do not present `Ready` as a required Scope field. If readiness appears, frame
  it as an outcome/state/check, not a Scope field.
- Update generated/mirrored HTML where it is part of this PR.
- Keep scope to PR #877 journey guide files and required generated mirrors.

Bars:
- Run focused doc/content checks sufficient to prove the blocker text is gone.
- Run full local validator preflight before push.
- Push the repair to `ce-485-canonical-journey-doc-pair` only.

Stop line:
- READY #877 <new-head-sha> with changed paths, focused evidence, full preflight
  result, and pushed-head confirmation.
- BLOCKED with exact blocker and clean worktree status.

Standing preflight directive: run the FULL local validator preflight (`ce
validate-pr`, CI-parity) before every self-push or commit-for-harvest; do not
discover gates via CI.
