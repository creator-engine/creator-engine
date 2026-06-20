---
slug: ce113-openbao-golive
date: 2026-06-19
kind: added
scope: openbao production go-live
issue: ce-ops#113
---

Added production go-live artifacts for the ratified Hetzner/tailnet OpenBao
deployment: hardened raft/TLS/audit config, systemd/provisioning scripts,
encrypted off-host snapshot and restore-drill tooling, emergency revocation
automation, Operator bringup runbooks, and validator tests including an opt-in
throwaway raft restore drill.

Review fix: replaced the shared wildcard broker policy with a per-dev policy
template and renderer, so each AppRole is bound to only its own
`ce-kv/devs/<dev-id>/runtime/*` paths.

Review fix: removed OpenBao 2.5.5-incompatible mlock settings from the
production HCL render and systemd unit, and added an opt-in live smoke that
downloads, verifies, and starts OpenBao 2.5.5 against the rendered production
config.

Follow-on fix: changed the audit stanza to OpenBao 2.5.x's required
`options = { ... }` map syntax, made provision/apply and Operator bringup
reload the service so declarative audit devices activate, and extended the
2.5.5 smoke to prove `bao audit list` shows the file audit device after reload.
