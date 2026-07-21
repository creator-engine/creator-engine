# Harvest

Check the seat output for the READY-FOR-HARVEST signal and the commit SHA before starting.
Harvest the branch to a staging worktree under `.ce/wt-<slug>-harvest/`.
Collect changelogs from `.ce/changelog/<slug>.md`.
Regenerate the PR manifest via the `carrier_gen` API (`write_carriers(base="origin/main")`) - do not hand-list carrier filenames.
Commit the complete carrier set, push that final committed head, and open or update the delivery PR.
Do not run full local `ce validate-pr` as a standing pre-push, harvest, controller, or merge-gate prerequisite.
Record the pushed head SHA and required Validate run URL/status for that exact head (or required synthetic merge-group head). Local full-suite transcripts are not gate evidence; targeted author tests are optional iteration evidence only.
Enqueue for merge only after independent non-author review, green required CI checks, and ratification.
The controller holds the merge gate; the seat that authored the work never merges or self-approves.
