# Harvest

Check the seat output for the READY-FOR-HARVEST signal and the commit SHA before starting.
Verify `ce validate-pr` (or `scripts/ce-preflight.sh`) is GREEN on the branch in one pass before touching the staging area.
Harvest the branch to a staging worktree under `.ce/wt-<slug>-harvest/`.
Collect changelogs from `.ce/changelog/<slug>.md`.
Regenerate the PR manifest via the `carrier_gen` API (`write_carriers(base="origin/main")`) - do not hand-list carrier filenames.
Enqueue for merge only after independent non-author review and green required CI checks pass.
The controller holds the merge gate; the seat that authored the work never merges or self-approves.
