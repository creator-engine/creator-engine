# Conveyor Harvest-to-Push Helper Design

## Scope

The conveyor mechanizes the repeatable contained-seat harvest path without
arming transport or reviewer actions. The full path is:

1. Detect a contained seat with a READY local branch.
2. Bundle the branch out of the contained runtime.
3. Land the bundle in a host worktree.
4. Rebase the branch onto current `origin/main`.
5. Clean generated validator artifacts.
6. Regenerate the changelog and per-PR carrier from final `base..HEAD`.
7. Re-add the legacy carrier line `- **Declared work class:** <tiny|story|feature|epic>`.
8. Run `validate-pr` with a known-good host venv and
   `PYTHONPATH=<worktree>/validators`.
9. Clean `validators/build` and `validators/*.egg-info` after validation.
10. Stop for controller/Operator-gated push, PR, and approval decisions.

## Safe Automation

These steps are local, deterministic, and safe to automate in an unattended
helper because they do not publish or approve code:

- Read contained-seat metadata and confirm the branch is READY.
- Create and import a `git bundle` into a host worktree.
- Ensure the local branch name equals the carrier stem from `branch_slug`.
- Fetch and rebase onto current `origin/main`, or verify the requested base is
  already an ancestor when running in verify-only mode.
- Remove `validators/build` and direct `validators/*.egg-info` artifacts before
  carrier regeneration.
- Regenerate `.ce/changelog/<branch-slug>.md` and
  `.ce/pr-manifests/<branch-slug>.md` with `carrier_gen.write_carriers`.
- Re-add the old-name declared work-class line for cross-gate compatibility.
- Run the injected `validate-pr` seam with a known-good venv and explicit
  `PYTHONPATH`.
- Remove generated validator artifacts again after validation and before any
  future staging step.
- Return structured ready/not-ready results with reasons.

## Autonomy-Arming Gates

The conveyor must not perform these steps unless a later Operator decision
explicitly arms them:

- Auto-push to a remote branch.
- Auto-open or auto-update a PR.
- Auto-approve, request approval, dismiss reviews, merge, or enqueue.
- Daemon-loop harvesting that continuously discovers and transports work.
- Docker or contained-runtime execution from the slice-1 helper.

Those actions cross the local-prep boundary into transport, source-host state,
or reviewer authority. They stay design-only in this slice.

## Slice Plan

XS: Local harvest prep core.

- Implement `creator_engine_validator.conveyor.prepare_harvest`.
- Accept worktree path, branch, base, carrier metadata, old-name work class, and
  injected git/validate runners.
- Clean generated validator artifacts, normalize branch naming, rebase or verify
  base, regenerate carriers, run validate, clean again, and return a structured
  result.
- Unit test all behavior with fake runners. No push, PR, docker, daemon, or
  autonomy arming.

S: Host bundle landing.

- Add bundle import and host worktree allocation around the XS prep core.
- Persist an operator-readable harvest report with source branch, imported HEAD,
  base, carrier paths, validation result, and residual reasons.
- Keep push and PR creation behind explicit controller invocation.

M: Operator-gated transport wrapper.

- Add an explicit arming envelope for push and PR creation.
- Require named Operator/controller intent, branch, base, target repo, and
  expected commit before transport.
- Keep auto-approve out of scope unless a separate Operator-approved Surface-B
  autonomy policy authorizes it.
- Emit side-effect ledger records for every armed source-host mutation.
