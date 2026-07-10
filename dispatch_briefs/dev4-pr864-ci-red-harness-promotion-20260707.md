ROLE: implementer
SEAT: dev-4
PR: #864 reviewer-authority envelope minting
BRANCH: ce-426-g11-reviewer-authority-minting
CURRENT PR HEAD: d74a18b71b963c90e8d6e2e78c8e9364ffe17a81

Read AGENTS.md and .claude/agents/implementer.md before acting. You are not
alone in the codebase; do not revert others' edits. Work in an isolated
worktree for PR #864 only. Do not approve, merge, enqueue, or comment on
GitHub.

Task: repair the current CI-red Validate failure on PR #864 only.

Live failure:
- Validate run: 28851552190
- Job: 85567870624
- Failing step: Creator Engine validator - harness promotion matrix gate
- Command in CI:
  `PYTHONPATH=validators python -m creator_engine_validator verify-harness-promotion-matrix .`
- Failure:
  `creator_engine_validator: error: argument subcommand: invalid choice:
  'verify-harness-promotion-matrix'`

Interpretation to verify, not assume:
- The PR currently modifies reviewer-authority and harness-promotion related
  validator surfaces, but the branch's CLI subcommand registry does not expose
  `verify-harness-promotion-matrix`.
- Repair the missing/incorrect CLI exposure or coupling so the CI command is
  valid and exercises the intended gate.

Allowed surfaces:
- Existing PR #864 surfaces only:
  `.ce/brain/assertions.yaml`,
  `.ce/changelog/ce-426-g11-reviewer-authority-minting.md`,
  `.ce/pr-manifests/ce-426-g11-reviewer-authority-minting.md`,
  `.ce/reference/cli.generated.md`,
  `docs/operations/GOVERNED_LANE_LAUNCH_PROTOCOL.md`,
  `docs/operations/REVIEWER_VENUE_AUTHORITY.md`,
  `validators/creator_engine_validator/ce_cli.py`,
  `validators/creator_engine_validator/checks/reviewer_authority_envelope.py`,
  `validators/creator_engine_validator/forge/cred_injection_proxy.py`,
  `validators/creator_engine_validator/hook_check.py`,
  `validators/creator_engine_validator/lane_runtime.py`,
  `validators/creator_engine_validator/schemas/reviewer-authority-envelope.schema.yaml`,
  `validators/tests/unit/test_cred_injection_proxy.py`,
  `validators/tests/unit/test_egress_self_review_broker.py`,
  `validators/tests/unit/test_hook_check.py`,
  `validators/tests/unit/test_hook_check_cli_reviewer_authority_ref.py`,
  `validators/tests/unit/test_hook_check_reviewer_authority.py`,
  `validators/tests/unit/test_lane_runtime_reviewer_venue.py`,
  `validators/tests/unit/test_reviewer_authority_envelope.py`.
- If the minimal correct fix requires a tightly coupled test/docs/generated
  update outside this list, stop as BLOCKED and name the path and reason.

Required evidence:
- Show the focused command that proves
  `python -m creator_engine_validator verify-harness-promotion-matrix .` is
  accepted and passes or reaches the intended validator behavior.
- Run focused tests for the touched CLI/gate area.
- Run full local validator preflight before push or commit-for-harvest.

Stop line:
- READY #864 <commit-sha> with pushed head or harvestable commit evidence,
  changed paths, focused command results, and full preflight result.
- BLOCKED with the exact blocker, current worktree status, and no scope
  expansion.

Standing preflight directive: run the FULL local validator preflight (`ce
validate-pr`, CI-parity) before every self-push or commit-for-harvest; do not
discover gates via CI.
