# ADDENDUM 2 — ce-446-base-resolve-robust — BLOCKED resolved: your `ce` binary is a stale wheel

Your CE-BRAIN-LEDGER-INVALID block is a FALSE-RED from tooling vintage, not a real ledger defect.

Controller evidence (2026-07-05 ~05:1xZ, on a clean checkout of current origin/main):
`PYTHONPATH=validators python3 -m creator_engine_validator.ce_cli brain verify --state-root .ce`
→ `ce brain verify: OK (134 record(s))`, rc=0 — the SAME tracked ledger you saw fail.

Root cause: your host-installed `ce` (signed 0.3.1 wheelset) predates the supersession records the
brain pin-migration appended to the ledger after 0.3.1 shipped; its older verifier rejects
`brain_assertion_supersede_target` records that current main considers valid. This is the same
stale-wheel class as your earlier S3b verb-routing block.

## Instruction
For THIS unit, run every `ce` command via main-vintage code from your worktree instead of the
installed binary:
`PYTHONPATH=validators python3 -m creator_engine_validator.ce_cli <subcommand> ...`
(applies to `brain correct`, `brain verify`, AND the final `validate-pr`).

Then complete per Addendum 1: supersession-append the corrected assertion(s) for your edited
validate.yml via `brain correct`, `brain verify` green, full `validate-pr` green one pass, carrier
regen to include .ce/brain/assertions.yaml, self-push and open the PR per the original brief.

All other constraints unchanged. Your rebased commit ffc1823f is fine to build on.
