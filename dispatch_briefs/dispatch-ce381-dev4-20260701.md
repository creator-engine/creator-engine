# DISPATCH — ce-ops#381: fix L2 automerge-decide path-set (two-dot → three-dot) — dev-4

LANE: the L2 `automerge-decide` workflow misclassifies PRs because it computes changed paths with a **two-dot** diff against a STALE base. A pure-docs PR (#704) classified as `deploy` (→ never auto-merges) because the two-dot diff swept in `.github/**` files inherited from a moving main. Fix so the path set = ONLY the PR's own changes.

WORKTREE under /var/tmp off CURRENT origin/main. Branch **ce-381-automerge-decide-pathset**. validate-pr via `TMPDIR=/var/tmp PYTHONPATH=$PWD/validators /workspace/creator-engine/.venv/bin/python -m creator_engine_validator.ce_cli validate-pr`. STOP before push. **Do NOT change any arming/policy — ONLY the path-set computation.**

## Root cause (verified by controller)
`.github/workflows/automerge-decide.yml`, "Resolve changed paths" step (~line 100): `git diff --name-only --find-renames "${base_sha}..${head_sha}"` with `base_sha=${PR_BASE_SHA}` (github.event.pull_request.base.sha = a stale snapshot). Two-dot includes commits in head not in the stale base → inherited main files.

## Fix (pick the robust one)
**Preferred:** use the GitHub API file list — `gh pr view "${PR_NUMBER}" --json files --jq '.files[].path'` — which returns EXACTLY the PR's changed files (no base-staleness). Fall back to the git diff only if the API is unavailable.
**Alternative (if staying with git):** switch to **three-dot** `git diff --name-only --find-renames "${base_sha}...${head_sha}"` (merge-base), which excludes inherited commits. Also ensure base_sha is fetched.
Keep the merge_group branch of the logic working (it uses GITHUB_SHA^..GITHUB_SHA — leave it, or align).

## Also (secondary, from #381)
The decide workflow read work-class `S` (the default) for #704 whose body declared `tiny` — verify the PR-body work-class regex extraction actually matches the `- **Declared work class:** <XS|S|M|L or tiny/...>` line; fix if the regex misses valid forms. (Non-blocking if out of scope — note it.)

## Evidence
- Add/extend a test: a docs PR whose branch is based on a main containing unrelated `.github/**` commits must resolve a path set of ONLY the doc files → mutation_class `docs` (not deploy). Use the existing automerge-decide workflow-shape test module if present, or a unit test on the path-resolution helper if the logic is extractable.
- `ce validate-pr` GREEN. Carrier+changelog (head_ref=ce-381-automerge-decide-pathset, kind=fix, scope=ci, issue=ce-ops#381) + `- **Declared work class:** story` in carrier (OLD names for gate compat). rm validators/build before git add. Branch name == carrier stem.
- Verify vs origin/main, NOT rc2. Do NOT touch docs/install.sh or docs/downloads.
Report: branch, SHA, validate-pr PASS line, the fix approach chosen.
