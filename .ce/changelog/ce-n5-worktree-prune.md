# ce-n5-worktree-prune

- Added `ce worker worktree-prune` as a dry-run-by-default stale worktree scanner.
- Added fail-safe pruning for clean, merged or content-empty old worktrees, plus empty orphan directories with broken `.git` pointers.
- Added apply-mode audit records under `.ce/state/worktree-prune.jsonl`.
