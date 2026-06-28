---
slug: ce-automerge-decide-ci
date: 2026-06-28
kind: added
scope: automerge decision CI
issue: ce-ops#313
---

**advisory automerge decision CI.**

Adds an advisory GitHub Actions workflow that runs ce automerge-decide for pull_request and merge_group events.

- Records the dry-run JSON decision under .ce/state/automerge/decisions/ in the CI workspace.
- Uploads the decision JSON as a workflow artifact.
- Writes an AUTO/MANUAL-style GITHUB_STEP_SUMMARY with the raw decision and rationale.
- Keeps the workflow read-only: no merge, auto-merge enablement, marker minting, approvals, pushes, or PR/repo mutations.
