# Harvest

Check the seat output for the READY-FOR-HARVEST signal and the commit SHA before starting.
Check the brief's explicit `test-bearing` or `non-test-bearing` classification.
For test-bearing work, admit the seal only when it records exact test node ID(s),
the named base or prior head, the RED command and captured output against that
base/prior head, and the GREEN command and captured output after implementation.
If any field is absent, retain the seal as a named flagged/not-ready record and
refuse harvest before carrier generation or transport. A non-test-bearing
exemption must be explicit and carry a nonempty factual justification meeting
the dispatch brief's `no runtime surface` standard; do not infer it from a
missing seal.
This is structural detectability, not proof: the parser can flag missing or
malformed RED/GREEN structure, but cannot prove the RED output semantically
differs from GREEN. Identical pasted output defeats it. Controllers must weigh
that residual when deciding whether the record establishes the claimed repair.
Harvest the branch to a staging worktree under `.ce/wt-<slug>-harvest/`.
Collect changelogs from `.ce/changelog/<slug>.md`.
Regenerate the PR manifest via the `carrier_gen` API (`write_carriers(base="origin/main")`) - do not hand-list carrier filenames.
Commit the complete carrier set, push that final committed head, and open or update the delivery PR.
Do not run full local `ce validate-pr` as a standing pre-push, harvest, controller, or merge-gate prerequisite.
Record the pushed head SHA and required Validate run URL/status for that exact head (or required synthetic merge-group head). Local full-suite transcripts are not gate evidence; targeted author tests are optional iteration evidence only.
Enqueue for merge only after independent non-author review, green required CI checks, and ratification.
The controller holds the merge gate; the seat that authored the work never merges or self-approves.
