ROLE: reviewer
SEAT: dev-3
PR: #876 CE journey next-step hints
CURRENT PR HEAD: e45088ecc6afbe2b1782c28ed438cfb77df808e3

Read AGENTS.md and .claude/agents/reviewer.md before acting. You are read-only.
Do not edit files. Do not mutate GitHub. Do not approve, comment, merge, or
enqueue.

Task: independently review PR #876 at exact head
`e45088ecc6afbe2b1782c28ed438cfb77df808e3`.

Context:
- dev-1 repaired #876 by rebasing onto current `origin/main`.
- GitHub checks are green on this head:
  - Validate governance artifacts: success
  - Advisory automerge decision: success
- ReviewDecision remains `CHANGES_REQUESTED`, so a fresh independent review is
  required before any gate action.

Review expectations:
- Verify live PR head still matches the exact head above. If not, BLOCKED.
- Inspect the diff and prior requested-change areas for regressions.
- Validate path manifest/work-class artifacts as appropriate for the PR.
- Run focused/local read-only checks where useful. Do not push.
- Return only one of: APPROVE, REQUEST_CHANGES, BLOCKED.

Stop line:
- APPROVE with evidence: head match, checks observed, key files reviewed, and
  focused/local check result if run.
- REQUEST_CHANGES with numbered findings and file:line evidence.
- BLOCKED with exact blocker.

Standing preflight directive: run the FULL local validator preflight (`ce
validate-pr`, CI-parity) before every self-push or commit-for-harvest; do not
discover gates via CI. For this read-only review, do not push.
