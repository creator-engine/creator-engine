# dev-1 brief: fix PR #877 generated HTML mirrors

Role: dev-1 foreman / implementer worker lane.

Scope:
- PR: `creator-engine/creator-engine#877`
- Branch: `ce-485-canonical-journey-doc-pair`
- Expected current head: `7d18df824f47d0a11f6f4f3a12830ba02b5b6b77`

Blocking review findings to fix:
- `docs/guide/quickstart.html` is stale versus `docs/guide/quickstart.md`.
- `docs/guide/complete-walkthrough.html` is stale versus `docs/guide/complete-walkthrough.md`.
- `docs/guide/solo-dev-onboarding.html` is stale versus `docs/guide/solo-dev-onboarding.md`.

Rules:
- You are not alone in the codebase. Do not revert or alter unrelated edits.
- Work only on PR #877 branch/worktree and only on generated HTML/doc mirror consistency plus any required carrier updates.
- Verify the branch head is still `7d18df824f47d0a11f6f4f3a12830ba02b5b6b77` before editing. If not, report `HEAD_CHANGED`.
- Regenerate or update generated HTML using the repo's established docs generation path. Do not hand-edit broad unrelated HTML.
- Run focused docs/nav tests and full source `ce validate-pr` if feasible.
- Push to the existing PR branch after green.
- Do not approve, merge, enqueue, sign, or change protected settings.

Stop line:
- `READY ce-485-canonical-journey-doc-pair <sha>`
- Include validation evidence and whether #876 should remain draft or be marked ready by the controller.
