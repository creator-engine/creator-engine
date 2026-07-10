# dev-3 dispatch: read-only review PR #878 current head

Role: reviewer, read-only isolated worktree.

Ticket/PR: #878 `feat: seed shaping from PRD context`
Branch: `ce-487-shape-from-prd`
Author: `ce-dev-1`
Required head: `846af99a0c9f5320da9bc96d808846213e62b1c0`

Context:
- GitHub Validate governance artifacts and Advisory automerge decision are
  successful on the required head.
- GitHub reviewDecision still says `CHANGES_REQUESTED`.
- A previous independent review reportedly found the PRD-safety blocker closed,
  but this dispatch needs a fresh local verdict on the exact current head.

Allowed surfaces:
- Read-only review only.
- Create/use an isolated review worktree if needed.
- Do not mutate GitHub.

Required review:
1. Read `AGENTS.md` and `.claude/agents/reviewer.md`.
2. Fetch PR #878 and verify the live head exactly matches
   `846af99a0c9f5320da9bc96d808846213e62b1c0`; stop `BLOCKED` on mismatch.
3. Review the actual diff and path manifest/work-class carriers.
4. Check that prior PRD shaping/safety requested-change areas are resolved and
   that no new blocker is introduced.
5. Run read-only checks appropriate for reviewer evidence, at minimum
   `git diff --check` and path-manifest verification.

Expected evidence:
- Exact head SHA and check-run status.
- Path manifest path count/hash or mismatch.
- Focused files/lines for any blocker.
- Brief statement of local checks run.

Stop line:
- `APPROVE #878 <sha>` if no blocking issues remain.
- `REQUEST_CHANGES #878 <sha>` with file:line blockers if changes are needed.
- `BLOCKED #878 <reason>` if the live head mismatches or review cannot finish.

Hard stops:
- Do not approve, merge, enqueue, or comment on GitHub.
- Do not edit files.
