# Correction Brief: CE Orchestrator Agent Design Confidentiality Scrub

Target seat: dev-1
Role: implementer
Branch: ce-orchestrator-agent-design
Existing commit: 1387ee5f00621f7c2d054d5fb42a3781d1441c57

## Stop Line

The local branch is not allowed to push until the full source-module validate-pr
is GREEN in one pass.

## Problem

Full validation stopped on `public_docs_confidentiality`:

- `docs/design/ce-orchestrator-agent.md:55`
- `docs/design/ce-orchestrator-agent.md:636`

Both lines include an internal seat-login path marker:
`/home/ce-dev-1/creator-engine/.ce/state/research/RESUME_STATE_CE_DEV2_*`.

`docs/` is public product-lens. It must not include internal seat paths, private
repo references, or ce-ops issue markers.

## Allowed Scope

Only edit files already in the `ce-orchestrator-agent-design` branch diff:

- `.ce/changelog/ce-orchestrator-agent-design.md`
- `.ce/pr-manifests/ce-orchestrator-agent-design.md`
- `docs/design/ce-orchestrator-agent.md`
- `docs/design/ce-orchestrator-agent-epic.md`

Expected fix is likely limited to `docs/design/ce-orchestrator-agent.md` and
carrier regeneration if the manifest requires it.

## Required Work

1. Replace the two internal path references with public-safe generic wording.
2. Scan the two docs files for:
   - `/home/`
   - `.ce/state/research`
   - `RESUME_STATE`
   - `ce-ops#`
3. Regenerate carriers if path manifests or generated carriers are affected.
4. Commit the correction on the existing branch.
5. Run the full source-module preflight:

```bash
TMPDIR=/var/tmp PYTHONPATH=validators python3 -m creator_engine_validator.ce_cli validate-pr --declared-work-class story
```

## Report

If GREEN: report `READY-TO-PUSH` with branch, full SHA, validation command, and
changed paths. Do not push until controller confirms.

If RED: stop and report the exact failing check and output excerpt.
