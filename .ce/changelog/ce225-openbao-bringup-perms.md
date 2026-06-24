---
slug: ce225-openbao-bringup-perms
date: 2026-06-24
kind: fixed
scope: devops / OpenBao container bring-up
issue: ce-ops#225
---

**Fix `bringup-container-openbao.sh --apply` failing to start the container with
`permission denied` on the bind-mounted config.** The script rendered the config +
workdir as root `0600`/`0700`; on the docker host a security-layer interaction denied
the container's read. The fix exposes only the value-free bind-mount inputs the
container needs — workdir + policy dir traversable, rendered config + policy files
readable, raft/log dirs writable — while init JSON and live-test env stay private
`0600`. Unblocks the ephemeral OpenBao rehearsal.
