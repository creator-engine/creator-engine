---
slug: ce228-transport-deputy-policy
date: 2026-06-24
kind: added
scope: transport deputy policy
issue: ce-ops#228
work_class: story
---

Adds an offline, pure forge policy seam for credential-injection transport
deputy decisions. The default reviewer profile allows GitHub PR review
submission and read paths while failing closed on destructive writes, opaque
GraphQL mutations, unknown git smart-HTTP writes, missing role/seat context,
and any request metadata that carries credential material.
