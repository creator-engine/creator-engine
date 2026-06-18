---
slug: ce94-finegrained-pat
date: 2026-06-18
kind: fixed
scope: onboard --apply live-forge bootstrap probe
issue: ce-ops#94
base: 8d2a83be700d9337aeaaa7b704e6306da79744c8
---

Accepts valid fine-grained GitHub PATs in the live bootstrap probe without
weakening the classic-PAT scope path.

- Keeps classic PAT validation on `X-OAuth-Scopes` and the existing
  `REQUIRED_BOOTSTRAP_SCOPES` table.
- Adds fine-grained PAT permission probes that use GitHub's fine-grained
  `X-Accepted-GitHub-Permissions` model and invalid-body write endpoints, so
  permission checks can pass authorization while refusing any successful
  mutation.
- Requires greenfield fine-grained PATs to prove the same CE permission names:
  `administration:write`, `contents:write`, `actions:write`,
  `workflows:write`, plus `org:repo_create` when the existing CE path requires
  it.
- Preserves plain-join identity-only behavior because plain-join writes nothing
  with the bootstrap PAT.
- Adds regression coverage for accepted fine-grained PATs and missing
  fine-grained permissions.
