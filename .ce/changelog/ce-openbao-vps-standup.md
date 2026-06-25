---
slug: ce-openbao-vps-standup
date: 2026-06-25
kind: added
scope: devops / OpenBao approval wall arming
issue: ce-ops#239, ce-ops#446
---

Added a value-free controller/operator runbook for completing OpenBao-backed
approval-wall arming after VPS standup.

- Records verified OpenBao connection parameters and host status without secret
  values.
- Documents the TEST SecretRef at `ce-kv/forge/approval-wall/test`,
  `signing_secret`.
- States that authenticated `/v1/sys/audit` and `ce-kv` checks remain blocked
  until an authorized token is supplied.
- Captures the completed fail-closed proof for a configured backend with no
  token and env fallback present.
- Provides day-2 controller/operator steps for audit/KV verification, TEST
  secret write, least-privilege test token mint, queue-daemon proof, marker
  mint proof, negative checks, and cleanup.
- Notes live systemd unit `CAP_IPC_LOCK`/memlock drift as follow-up work, not a
  change in this lane.
