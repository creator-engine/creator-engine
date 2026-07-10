# Correction Brief: ce-ops#344 Slice 3 Commit Recovery

Target seat: dev-4
Role: implementer
Branch: ce-344-slice3-skillify
Ticket: ce-ops#344 slice 3

## Stop Line

Do not rerun the hung verifier. Do not report READY until the commit SHA resolves
inside the container repository and the worktree status/diff are printed.

## Current Controller Finding

Your pane reported:

- branch: `ce-344-slice3-skillify`
- SHA: `ce395c9d250d72e317781acc4e45d720a787fe9e`
- changed paths:
  - `.ce/changelog/ce-344-slice3-skillify.md`
  - `.ce/pr-manifests/ce-344-slice3-skillify.md`
  - `.claude/skills/ce-dispatch/SKILL.md`
  - `.claude/skills/ce-harvest/SKILL.md`
  - `playbooks/controller/briefs/harvest.md`
  - `validators/tests/unit/test_skill_antidrift_guard.py`

Controller verification in the live container failed:

```bash
git -C /workspace/creator-engine cat-file -t ce395c9d250d72e317781acc4e45d720a787fe9e
# fatal: git cat-file: could not get object info
```

So the reported SHA is still not harvestable.

## Required Work

Locate the actual slice-3 worktree and commit the real work.

Run read-only discovery first:

```bash
git -C /workspace/creator-engine worktree list
git -C /workspace/creator-engine branch --list 'ce-344-slice3-skillify'
git -C /workspace/creator-engine stash list
find /workspace /home/cedev2 -maxdepth 5 -type f \( -path '*/.claude/skills/ce-harvest/SKILL.md' -o -path '*/playbooks/controller/briefs/harvest.md' \) 2>/dev/null
```

For the located worktree, run:

```bash
git -C <worktree> status -sb
git -C <worktree> diff --name-status
git -C <worktree> log --oneline -3
```

If changes are uncommitted, commit them on `ce-344-slice3-skillify`:

```bash
git -C <worktree> add -A
git -C <worktree> commit -m "feat(ce-ops#344): skill-ify dispatch and harvest playbooks"
```

Then verify the SHA resolves:

```bash
sha=$(git -C <worktree> rev-parse HEAD)
git -C /workspace/creator-engine cat-file -t "$sha"
base=$(git -C <worktree> merge-base origin/main HEAD)
git -C <worktree> status -sb
git -C <worktree> diff --name-status "$base"..HEAD
```

## Report

Report `READY-FOR-HARVEST` only with:

- worktree path
- branch
- full SHA
- `cat-file -t` result
- merge-base
- status
- changed paths

If the work is unrecoverable, report `UNRECOVERABLE` and list exactly which
expected files could not be found.
