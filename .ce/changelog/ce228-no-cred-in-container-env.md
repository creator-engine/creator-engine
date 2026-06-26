---
slug: ce228-no-cred-in-container-env
date: 2026-06-26
kind: changed
scope: contained runsc launches
issue: ce-ops#228
work_class: story
---

Adds a deterministic contained-launch guard that refuses credential-bearing
environment carriers in Docker/runsc argv or OCI-style env specs. DGX and VPS
runsc launchers now validate their assembled container argv before dry-run
output or execution, and the VPS Claude/controller path no longer forwards
`CLAUDE_CODE_OAUTH_TOKEN` through Docker env. Credential delivery remains
broker/transport-deputy work; onecli transport-deputy handoff is follow-on
scope for this unit.
