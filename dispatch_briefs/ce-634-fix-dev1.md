# BRIEF — dev-1 — Fix PR #634 (rebase off stale base)

Your FORGE-3 PR #634 (branch `ce-forge-workflow-catalog`) was built off a STALE local main, so its diff wrongly includes already-merged BRAIN-C files (`docs/guide/brain-ingest-refresh.md`, `scripts/brain-ingest-refresh.sh`, `ce-brain-ingest-refresh.md` changelog+manifest) AND a second carrier — this trips the multiple-carrier / diff-mismatch gate. Fix by rebasing onto CURRENT origin/main.

## Steps
1. `cd` to the ce-forge-workflow-catalog worktree.
2. `git fetch origin main` then `git rebase origin/main`. The already-merged BRAIN-C files should drop out of the diff (they're now in main). Resolve any trivial conflicts by taking main's version of the BRAIN-C files (you are NOT re-adding them).
3. Confirm `git diff --name-status $(git merge-base origin/main HEAD)..HEAD` shows ONLY your FORGE-3 files:
   - `docs/contracts/workflow-catalog.md`
   - `.ce/changelog/ce-forge-workflow-catalog.md`
   - `.ce/pr-manifests/ce-forge-workflow-catalog.md`
   (exactly ONE carrier, slug `ce-forge-workflow-catalog`). If any brain-ingest file or the `ce-brain-ingest-refresh` carrier still appears, `git rm` it from your branch (it belongs to the already-merged #631, not this PR).
4. Regenerate the carrier via carrier_gen (base = current merge-base) so AUTHORIZED_PATHS match exactly the 3 files; keep `- **Declared work class:** story` (or tiny).
5. FULL preflight GREEN: `rm -rf validators/*.egg-info validators/build; TMPDIR=/var/tmp PYTHONPATH=validators python -m creator_engine_validator.ce_cli validate-pr --head-ref ce-forge-workflow-catalog`
6. Force-push the rebased branch as ce-dev-1 (updates #634). Report the new head SHA + the final changed-paths list.

Do NOT approve/merge. Keep the workflow-catalog doc body free of internal identities/IPs/ce-ops#.
