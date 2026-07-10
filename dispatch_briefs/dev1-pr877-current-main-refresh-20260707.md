# dev-1 dispatch: PR #877 current-main refresh

Role: implementer, write-capable in the existing #877 worktree only.

Ticket/PR: #877 `docs: add canonical CE journey guides`
Branch: `ce-485-canonical-journey-doc-pair`
Current remote head to start from: `ee1647bc8e1064fec0721b0bb21c80a3093e0693`

Problem:
- The prior review blocker repair was pushed, but GitHub Validate is red on the
  harness promotion matrix gate.
- CI log root cause: `python -m creator_engine_validator verify-harness-promotion-matrix .`
  is not available on the branch.
- `origin/main` has advanced to `faf9307d3d178caba240a4da3bbd588d79ccf067`
  through #880/#875, so this branch must be refreshed against current main
  rather than repaired as a docs wording issue.

Allowed surfaces:
- The existing #877 worktree and branch only:
  `/home/ce-dev-1/worktrees/ce-485-canonical-journey-doc-pair`
- Conflict resolutions needed to rebase/merge #877 onto current `origin/main`.
- Generated guide HTML mirrors already in #877 if the rebase requires
  regeneration.
- Do not take unrelated PRDv2.1/html_prdv2 work.

Required work:
1. Fetch current `origin/main`.
2. Rebase or otherwise refresh `ce-485-canonical-journey-doc-pair` onto current
   `origin/main` at `faf9307d3d178caba240a4da3bbd588d79ccf067` or newer.
3. Preserve the #877 review fix: required Scope fields are exactly `Goal`,
   `Done-when`, `Change-type`; `Ready` may only appear as readiness state/check
   wording, not as a required Scope field.
4. Run focused scans for the prior review blocker.
5. Run `git diff --check`.
6. Run the FULL local validator preflight (`ce validate-pr`, CI-parity) before
   every self-push; do not discover gates via CI.
7. Push the refreshed #877 branch if and only if full preflight passes.

Expected evidence:
- Final pushed SHA.
- Exact `origin/main` SHA used as the refreshed base.
- Changed paths, if any beyond rebase metadata.
- Focused blocker scan result.
- Full preflight command and result.
- `git ls-remote` evidence that the remote branch matches the final SHA.

Stop line:
- `READY #877 <sha>` only after push and evidence are complete.
- `BLOCKED #877 <reason>` if conflicts, failing preflight, or auth prevent a
  safe push.

Hard stops:
- Do not approve, merge, enqueue, or comment on GitHub.
- Do not edit outside the allocated worktree or assigned scope.
