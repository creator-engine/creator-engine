# Rebase repair brief: PR #864 reviewer-authority envelope minting

Role: implementer. Write-capable only in one isolated worktree.
Seat: dev-1.
Original author seat: dev-4. This is a repair lane, not a review.

Repository: `creator-engine/creator-engine`
Pull request: #864
Branch: `ce-426-g11-reviewer-authority-minting`
Exact starting head: `9bbff9037f07a4831b8cdb4e298abfac7652ecc0`
Current `origin/main`: `faf9307d3d178caba240a4da3bbd588d79ccf067`

Problem:
- GitHub reports PR #864 as `mergeable: CONFLICTING` / `mergeStateStatus:
  DIRTY`.
- The branch is at the harvested dev-4 fix head, but it must be rebased onto
  current main and have its manifest/carriers refreshed before review.
- The prior full preflight in dev-4 was blocked by broad/environment gates
  after focused #864 evidence passed; do not treat that as permission to skip
  branch hygiene or focused validation.

Allowed path surfaces:
- `.ce/brain/assertions.yaml`
- `.ce/changelog/ce-426-g11-reviewer-authority-minting.md`
- `.ce/pr-manifests/ce-426-g11-reviewer-authority-minting.md`
- `.ce/reference/cli.generated.md`
- `docs/operations/GOVERNED_LANE_LAUNCH_PROTOCOL.md`
- `docs/operations/REVIEWER_VENUE_AUTHORITY.md`
- `validators/creator_engine_validator/ce_cli.py`
- `validators/creator_engine_validator/checks/reviewer_authority_envelope.py`
- `validators/creator_engine_validator/cli.py`
- `validators/creator_engine_validator/forge/cred_injection_proxy.py`
- `validators/creator_engine_validator/hook_check.py`
- `validators/creator_engine_validator/lane_runtime.py`
- `validators/creator_engine_validator/schemas/reviewer-authority-envelope.schema.yaml`
- `validators/tests/unit/test_cli.py`
- `validators/tests/unit/test_cred_injection_proxy.py`
- `validators/tests/unit/test_egress_self_review_broker.py`
- `validators/tests/unit/test_hook_check.py`
- `validators/tests/unit/test_hook_check_cli_reviewer_authority_ref.py`
- `validators/tests/unit/test_hook_check_reviewer_authority.py`
- `validators/tests/unit/test_lane_runtime_reviewer_venue.py`
- `validators/tests/unit/test_reviewer_authority_envelope.py`

Task:
1. Read `AGENTS.md` and `.claude/agents/implementer.md`.
2. Use/create exactly one isolated worktree for
   `ce-426-g11-reviewer-authority-minting`; do not edit the main checkout.
3. Fetch `origin/main` and `origin/ce-426-g11-reviewer-authority-minting`.
4. Verify the branch starts at
   `9bbff9037f07a4831b8cdb4e298abfac7652ecc0`; if not, stop
   `BLOCKED #864 HEAD_CHANGED <actual-sha>`.
5. Rebase onto current `origin/main` (`faf9307d...` or newer if main advances
   during fetch).
6. Resolve conflicts conservatively:
   - Preserve current main for unrelated surfaces.
   - Preserve only #864 reviewer-authority envelope changes.
   - Do not carry unrelated already-merged work into the PR diff.
7. Regenerate the PR manifest/carrier with repo-native tooling after rebase.
8. Validate:
   - `git diff --check`
   - path manifest fidelity for `base..HEAD`
   - focused reviewer-authority tests touched by this PR
   - brain drift/hash verification if `.ce/brain/assertions.yaml` changes
   - full local validator preflight (`ce validate-pr`, CI-parity) before push
9. Push only if the branch is clean, manifest is correct, and validation is
   acceptable. Use an explicit lease against
   `9bbff9037f07a4831b8cdb4e298abfac7652ecc0`.

Stop line:
- `READY #864 <new-sha>` with changed paths and validation evidence, or
- `READY-BUNDLE #864 <new-sha> <bundle-path>` if you cannot push, or
- `BLOCKED #864 <reason>`.

Constraints:
- Do not approve, comment, request changes, merge, enqueue, or mutate PR
  metadata.
- Do not edit outside the allocated worktree or outside the allowed path
  surfaces.
- Ignore all PRDv2.1/html_prdv2 work in this repo.
- Full local validator preflight (`ce validate-pr`, CI-parity) is required
  before every self-push or commit-for-harvest; do not discover gates via CI.
