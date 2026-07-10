ROLE: implementer
SEAT: dev-4
PR: #864 reviewer-authority envelope minting
BRANCH: ce-426-g11-reviewer-authority-minting
CURRENT PR HEAD: d74a18b71b963c90e8d6e2e78c8e9364ffe17a81

Read AGENTS.md and .claude/agents/implementer.md before acting. Work in an
isolated worktree for PR #864 only. Do not approve, merge, enqueue, or comment
on GitHub. Do not edit the dirty main checkout.

Task: repair the current CI-red Validate failure on PR #864 only.

Previous stop line:
- Worker `019f3bb0-1770-7d33-99a0-234eb8f4cd0e` BLOCKED because the minimal
  correct fix requires `validators/creator_engine_validator/cli.py`, which was
  outside the prior allowed surfaces.

Live failure:
- Validate run: 28851552190
- Job: 85567870624
- Failing command:
  `PYTHONPATH=validators python -m creator_engine_validator verify-harness-promotion-matrix .`
- Failure:
  `creator_engine_validator: error: argument subcommand: invalid choice:
  'verify-harness-promotion-matrix'`

Evidence from blocked worker:
- `python -m creator_engine_validator` imports
  `validators/creator_engine_validator/__main__.py -> cli.main`.
- The parser rejects `verify-harness-promotion-matrix` before `ce_cli.py` is
  involved.

Allowed surfaces:
- Existing PR #864 surfaces from the current PR diff.
- Additionally allow the minimal necessary CLI parser file:
  `validators/creator_engine_validator/cli.py`.
- If tests/docs/generated references are tightly coupled to this CLI exposure,
  update only the smallest necessary coupled files and list them explicitly in
  the stop line.

Required evidence:
- Show the focused command:
  `PYTHONPATH=validators python -m creator_engine_validator verify-harness-promotion-matrix .`
  is accepted and passes or reaches the intended validator behavior.
- Run focused tests for the touched CLI/gate area.
- Run full local validator preflight before push or commit-for-harvest.

Stop line:
- READY #864 <commit-sha> with pushed head or harvestable commit evidence,
  changed paths, focused command results, and full preflight result.
- BLOCKED with exact blocker, current worktree status, and no scope expansion.

Standing preflight directive: run the FULL local validator preflight (`ce
validate-pr`, CI-parity) before every self-push or commit-for-harvest; do not
discover gates via CI.
