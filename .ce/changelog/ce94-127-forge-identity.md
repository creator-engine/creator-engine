---
slug: ce94-127-forge-identity
date: 2026-06-19
kind: fixed
scope: installer forge identity
issues:
  - ce-ops#94
  - ce-ops#127
---

Fixed the bootstrap-token probe for fine-grained GitHub PATs and bound adoption
commit authorship to the install-configured token identity.

For ce-ops#94, classic PATs keep the `X-OAuth-Scopes` verification path, while
fine-grained PATs are identity-only at `GET /user`; greenfield write legs remain
the fail-closed capability check. Unknown token prefixes now refuse with
`bootstrap_token_unverifiable`, including plain-join.

For ce-ops#127, local adoption commits no longer bind author identity from
answers, ambient git config, or ambient `gh auth`. They use the authenticated
login returned by `GET /user` on the bootstrap token and refuse unresolved
identity before committing.
