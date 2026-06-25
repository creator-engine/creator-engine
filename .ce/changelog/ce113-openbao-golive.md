---
slug: ce113-openbao-golive
date: 2026-06-19
kind: added
scope: openbao production go-live
issue: ce-ops#113
---

Added production go-live artifacts for the ratified VPS/tailnet OpenBao
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

Track B update: added the no-real-secrets migration gate, value-free migration
inventory template, inventory verifier, rollback/restore workflow, and Operator
bringup checklist additions. The workflow documents secret refs and governance
evidence only; live secret value import remains an Operator-ratified action
outside the repo and outside agent/container custody.

Track B hardening: the migration inventory verifier now rejects duplicate
`record_id` and `target_ref` rows plus OpenBao token-shaped values, PEM
armoring, password assignments, and common API key patterns. The go-live and
Operator bringup docs now state that the repository inventory is a template
only, live import remains Operator-only outside repo/container custody, and
rollback/restore requires audit, encrypted snapshot, restore-drill, and
value-free revocation evidence.

Track B completion: added the canonical dry-run-first single-node container
bring-up script, broker/import policy templates, a name-only OpenBao path map
for per-dev PATs, Claude OAuth, GitHub App config/key families, reviewer app
names, and deferred `ce-root-v1`, plus unit and live-test prerequisite coverage.
The runbooks now name `docs/devops/openbao/bringup-container-openbao.sh` as the
container dogfood path and document opt-in live validator prerequisites through
`CE_OPENBAO_BIN` and `CE_OPENBAO_GOLIVE_DOWNLOAD_SMOKE`.
