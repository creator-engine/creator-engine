---
slug: ce-gitignore-tmp-instance-zone
date: 2026-07-20
kind: changed
scope: repository hygiene
issue: ce-ops#635
---

**Ignore the repo-root `tmp/` instance zone so operator drop material cannot be staged.**

- `tmp/` at the repository root was untracked but NOT ignored, so `git add -A`
  would stage anything left there. It is routinely used to hand operator
  transcripts and scratch material to the controller, and on 2026-07-20 it was
  briefly used to hand over a live GitHub credential during a PAT rotation.
- Adds an anchored `/tmp/` line to the existing "Instance-local
  governed-execution working zones" block, matching the convention already used
  for `/ce-worktrees/` and `/ce-review-venues/`.
- Anchored to the repository root deliberately: an unanchored `tmp/` would also
  ignore nested `tmp/` directories anywhere in the tree, which is broader than
  intended.
- Verified before landing: `git ls-files` returns zero tracked paths matching
  `^tmp/` or `/tmp/`, so this rule cannot orphan tracked content.
- No credential was committed. The staged file was shredded and a tree-wide
  residue scan found no real token values.
