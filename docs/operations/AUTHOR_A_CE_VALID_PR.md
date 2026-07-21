# Author A CE-Valid PR

Use this playbook before handing a branch to a controller for commit, push, or review.

> **Standing validation directive.** Do not run full local `ce validate-pr` as
> a standing pre-push, harvest, controller, or merge-gate prerequisite. Push the
> committed current head; wait for required Validate checks; require independent
> review and ratification. Gate evidence is the pushed current-head SHA plus the
> required Validate run URL/status for that exact head (or required synthetic
> merge-group head). Local full-suite transcripts are not accepted as gate
> evidence. Targeted author tests remain optional iteration evidence and cannot
> substitute for required CI. `ce validate-pr` remains an optional diagnostic.

1. Before every diff, re-derive and record the comparison base. Do this before
   creating the branch and again before each commit-for-harvest or PR-ready
   diff; a previously observed `origin/main` is not evidence for a later diff.

   ```sh
   git fetch --prune origin
   BASE_SHA="$(git rev-parse origin/main)"
   printf 'derived base: %s\n' "$BASE_SHA"
   git switch -c <branch-slug> origin/main
   ```

   The handoff report names this derived base SHA.

2. Make the scoped change and keep the tree focused on the ticket. Stage only
   the named, authorized paths: never use `git add -A`. Before committing,
   record and verify the exact staged set with `git diff --cached --name-only`.

3. Add the PR carriers for the same branch slug:

   - `.ce/changelog/<branch-slug>.md`
   - `.ce/pr-manifests/<branch-slug>.md`

   Derive the slug programmatically by invoking `branch_slug(head_ref)` (or the
   existing `write_carriers` recipe); never predict a carrier slug by hand.
   For the programmatic carrier-writing path, follow the Manifest-fidelity
   recipe in `docs/contracts/authoring-a-governed-pr.md`.
   Before commit and before PR, report the supplied head ref, the derived slug,
   and the matching carrier filenames. The PR manifest must list the closed
   `origin/main..HEAD` path set, include itself, and include exactly one current
   PR-body work-class line:

   ```md
   - **Declared work class:** <XS|S|M|L>
   ```

   Use only `XS`, `S`, `M`, or `L`. These are CE ceremony tiers, not Agile work
   item types. Before PR, compute and report the diff's floor and the declared
   class. Legacy inputs normalize as `tiny` → `XS`, `story` → `S`, `feature` →
   `M`, and `epic` → `L`; a declared class above the computed floor clears the
   floor, while one below it does not.

   When an edited document is the evidence reference of an active brain
   assertion, identify that pinned document in the carrier result and append its
   same-carrier correction through `ce brain correct`. Pass the predecessor
   `--statement` explicitly, report the predecessor and successor ids, preserved
   statement, and asserted shipped hash, and never edit `claim.sha256` in place.

4. Optionally run focused checks or the local diagnostic while iterating:

   ```sh
   PYTHONPATH=validators python -m creator_engine_validator.ce_cli validate-pr
   ```

   The local command is diagnostic only. Its transcript is not gate evidence
   and does not substitute for required CI on the pushed head.

   For uncommitted worker handoff checks, add `--allow-dirty` only to inspect deterministic gates before the foreman commit. The authoritative carrier and diff gates validate committed `base..HEAD` state.

5. A result is ready for handoff only after a commit exists: report the
   committed `HEAD` and a clean worktree. A clean worktree alone never
   substitutes for a committed head. After push, record the required Validate
   run URL/status bound to that exact head.

6. Hand off the branch evidence to the foreman/controller. Do not self-merge.
