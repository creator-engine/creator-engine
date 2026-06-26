# Author A CE-Valid PR

Use this playbook before handing a branch to a controller for commit, push, or review.

1. Start from current main.

   ```sh
   git fetch origin
   git switch -c <branch-slug> origin/main
   ```

2. Make the scoped change and keep the tree focused on the ticket.

3. Add the PR carriers for the same branch slug:

   - `.ce/changelog/<branch-slug>.md`
   - `.ce/pr-manifests/<branch-slug>.md`

   The PR manifest must list the closed `origin/main..HEAD` path set, include itself, and include exactly one PR-body line:

   ```md
   - **Declared work class:** <tiny|story|feature|epic>
   ```

4. Run the local preflight before push:

   ```sh
   PYTHONPATH=validators python -m creator_engine_validator.ce_cli validate-pr
   ```

   For uncommitted worker handoff checks, add `--allow-dirty` only to inspect deterministic gates before the foreman commit. The authoritative carrier and diff gates validate committed `base..HEAD` state.

5. Fix every failed per-check line until the final summary is `PASS: PR preflight`.

6. Hand off the branch evidence to the foreman/controller. Do not self-merge.
