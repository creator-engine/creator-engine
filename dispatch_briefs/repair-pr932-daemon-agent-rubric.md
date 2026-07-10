# Implementer brief — repair PR #932 daemon-vs-agent rubric

## Assignment

- Ticket/work: ce-506 daemon-vs-agent routing rubric design, review repair
- PR: #932 at exact starting head `34531faef356c85b4a0cc197d5593df56d22d976`
- Branch: `ce-506-daemon-vs-agent-rubric-design-s1`
- Base: `origin/main@727f01a40a94f5ddcc43c52da4d0c2d31ce4718c`
- Role: `.claude/agents/implementer.md`
- Allocated worktree: `/home/ce-dev-2/creator-engine/.ce/wt-ce-506-daemon-vs-agent-rubric-design-s1-harvest`
- No network, push, PR review, approval, merge, Operator release, or authority action.

## Exclusive write territory

- `docs/design/daemon-vs-agent-rubric.md`
- `.ce/changelog/ce-506-daemon-vs-agent-rubric-design-s1.md`
- `.ce/pr-manifests/ce-506-daemon-vs-agent-rubric-design-s1.md`

Read-only surrounding policy, schemas, and runtime code are allowed.  Do not edit
any other path.  Preserve work class `story` and the design-preview hold.

## Required repair

Resolve both blocking review findings:

1. AutoReview must not load its governing reviewer policy from candidate HEAD or
   route a model verdict as ratification/approval.  Specify that reviewer policy
   is loaded from a trusted ratified control-plane/base ref and bound by digest;
   candidate policy edits are reviewed input only.  AutoReview emits advisory
   `COMMENT` or blocking `REQUEST_CHANGES` evidence and never `APPROVE`; an
   independent authorized human/controller decision remains separate.
2. Correct the hydration contract to match repository semantics.  The structural
   SSOT write is authoritative.  Recall is an advisory, derived, rebuildable,
   non-canonical projection and may fail independently; runtime must preserve
   deterministic SSOT/core fallback.  Include pointer metadata, live-source
   verification, SSOT precedence, and confidentiality/privacy gating.  Do not
   require SSOT and recall writes in one commit or claim recall is mandatory for
   correctness.

Keep proposals clearly distinct from ratified/current behavior.  Update the
changelog only as needed for truthfulness; regenerate the carrier via the
repository API only if necessary.

## Validation and disk admission

Run read-only focused documentation/governance checks available without a full
suite and `git diff --check`.  Root disk is admission-closed for another parity
copy while ce-516 owns `/var/tmp/ce-preflight-basetemp-ce516`.  Do not begin full
`ce validate-pr` until the controller explicitly sends `PREFLIGHT-ADMISSION-OPEN`;
report `READY-FOR-PREFLIGHT` after focused green and wait.  Once admitted, use one
uniquely named fixed basetemp and clean only that basetemp after the process exits.

Standing preflight directive: run the FULL local validator preflight (`ce validate-pr`,
CI-parity) before every self-push or commit-for-harvest.  Do not discover gates via CI.

## Deliverable and stop line

After admitted full preflight is green, commit the repair with the original
dev-3 author identity and your own implementer committer identity, then report
the exact commit, changed paths, focused/full validation evidence, and residual
risk.  Do not push.  Stop on scope expansion, red validation, base/head drift,
or any requirement for credentials, approval, or Operator authority.

