# PR path manifest — v3 G-2.1 (forge-native plan_approved + no-self-approval guardrail)

This file is the **carrier** for this PR's ratified closed manifest (the
convention defined in `docs/operations/PATH_MANIFEST_FIDELITY_PROTOCOL.md`).
CI (`.github/workflows/validate.yml`) passes it to
`verify-path-manifest --base <PR base sha> --manifest .ce/pr-path-manifest.md`,
which enforces that this PR's `base..HEAD` diff equals exactly the authorized
path-set below (the diff-gate runs *active*, not neutral). The fidelity scan
(`scan-path-manifest`) additionally requires the declared count and SHA256 to
match the fenced block.

This PR is the first **G-2 hardening** slice. It wires the G-2.0 ratification
gate to a **forge-native approval source-of-truth** and adds the
**no-self-approval guardrail**:

- NEW `forge/plan_approval.py` — `ApprovalQuery(repo, pr_number, run_id, policy_sha)`
  and `plan_approved(query, *, seat_identity, gh_runner=None) -> ApprovedPlan | None`,
  which resolves the approval from a plan-PR's reviews: bound to the run + policy
  (`ce-run-id`/`ce-policy-sha` body markers), commit-pinned (`review.commit_id` ==
  PR head), by an independent non-author non-seat reviewer, `APPROVED` state only.
  Pure behind the G-iii `GhRunner` seam (reuses `GhRunner`/`ForgeConfigError`
  imported from `github_repo_config`, which stays byte-unchanged); a transport
  failure raises `ForgeConfigError`, a clean "not ratified" returns `None`.
- MODIFY `orchestrator.py` — `run_plan` gains keyword-only `approval_resolver`
  (injected; production wires it to `forge.plan_approved`, so the orchestrator
  stays forge-free) and `seat_identity`; `_ratify_or_refuse` gains the
  `approved_by != seat_identity` guardrail. Backward-compatible: the existing
  explicit-`approved_plan` calls behave identically.

The resolver and the orchestrator are pure in-process Python: they register NO
validator check and NO `isolation_backend`, so `--list-checks` is **unchanged at
43** (source-tree count) and `available_backends()` stays
`('gvisor-proxy','local-noop')`. CI exercises the resolver with an injected fake
`GhRunner` (zero live network) and the lifecycle against the inert
`LocalNoopBackend` (zero live subprocess). No `ce_cli.py`/wheel change (stdlib +
the existing `gh` seam only). `mint_scoped_token` (G-2.2) and OpenShell (G-2.3)
remain deferred G-2 hardening.

- **base:** `77656e57a01f1d4c3f1febdd66eddea45ca4fe28`.
- **canonicalization:** `sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=7

AUTHORIZED_PATHS_SHA256=6fce3bb480648289d34ed662128d8e197e38f7bd123462b0658373241a65d8b5

```text
.ce/pr-path-manifest.md
docs/contracts/orchestrator.md
validators/creator_engine_validator/forge/__init__.py
validators/creator_engine_validator/forge/plan_approval.py
validators/creator_engine_validator/orchestrator.py
validators/tests/unit/test_orchestrator.py
validators/tests/unit/test_plan_approval.py
```
