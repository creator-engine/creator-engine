# Controller Migration Completeness

Use this checklist when moving an active controller from host-A to host-B. Do
not dispatch workers or take autonomous controller action from host-B until each
required item is complete and its evidence is recorded.

## Agent Role Definitions Travel

- [ ] Confirm the host-A controller state snapshot includes every required `.claude/agents/*.md` role definition as controller state, independent of the repo checkout.
  Acceptance evidence: verified by `jq -r '.files[].path' <snapshot>/manifest.json | grep '^\.claude/agents/.*\.md$'`.

- [ ] Restore the role definition files onto host-B before any worker dispatch.
  Acceptance evidence: verified by `find .claude/agents -maxdepth 1 -type f -name '*.md' -print | sort`.

- [ ] Prove host-B can resolve a governed worker role from the restored files.
  Acceptance evidence: verified by a dry worker-spawn preflight resolving `implementer`, `reviewer`, and `verification` without missing-role errors.

## Memory Sync

- [ ] Copy the controller memory directory and its index from host-A to host-B.
  Acceptance evidence: verified by `find <host-B-memory-root> -maxdepth 2 -type f -print | sort` showing the expected memory files and index.

- [ ] Rewrite the memory index host-topology header for host-B before the first autonomous act.
  Acceptance evidence: verified by `sed -n '1,40p' <host-B-memory-index>` showing host-B as the active controller host.

- [ ] Preserve the multi-controller artifact rule: peers may append artifacts, but must not rewrite the executor's live index.
  Acceptance evidence: verified by the restored index history or audit note showing only host-B rewrote the live index header during migration.

## Credentials Matrix

- [ ] Confirm no secrets travel inside the controller snapshot bundle.
  Acceptance evidence: verified by `jq -r '.denied_paths[]?' <snapshot>/manifest.json` plus inspection that no auth env files, private keys, passphrases, or token files are present in the snapshot tree.

- [ ] Provision host-B auth environment values outside the bundle.
  Acceptance evidence: verified by `env | grep -E '^(CE_|GH_|OPENAI_|ANTHROPIC_)'` in the controller service environment with secret values redacted in the evidence record.

- [ ] Provision per-identity tokens on host-B outside the bundle.
  Acceptance evidence: verified by a token inventory table listing each controller, worker, and review identity as present on host-B without recording token values.

- [ ] Provision the signing key and passphrase on host-B outside the bundle.
  Acceptance evidence: verified by a signing dry run or key fingerprint check that succeeds on host-B without exposing private key material.

- [ ] Provision inter-host SSH keys on host-B outside the bundle.
  Acceptance evidence: verified by `ssh -o BatchMode=yes <expected-peer> true` or an equivalent connectivity check from host-B.

- [ ] Regenerate host-local harness authentication and npm/pip toolchain state on host-B.
  Acceptance evidence: verified by the harness login/status command and `npm --version && python -m pip --version` succeeding on host-B.

## Session Infra Recreate-List

- [ ] Enumerate every host-A cron, watcher, monitor, timer, and long-running session-owned helper used by the controller.
  Acceptance evidence: verified by `systemctl list-timers`, `systemctl list-units`, `crontab -l`, and the session process list captured before host-A shutdown.

- [ ] Recreate required controller infrastructure on host-B under systemd or infrastructure-as-code ownership.
  Acceptance evidence: verified by `systemctl list-units '<controller-prefix>*'` and the deployment declaration showing the recreated units.

- [ ] Confirm no acting controller infrastructure depends on an interactive host-B session.
  Acceptance evidence: verified by terminating the bootstrap session and observing the controller units remain active under `systemctl is-active`.

## Gate Topology As Declared State

- [ ] Declare which host owns the singleton merge-gate service after migration.
  Acceptance evidence: verified by the deployment declaration naming host-B as the merge-gate owner.

- [ ] Declare and apply the merge-gate service drop-ins, including host-network placement when required.
  Acceptance evidence: verified by `systemctl cat <merge-gate-service>` showing the expected drop-ins on host-B.

- [ ] Declare and apply the host firewall rule allowing the gate container subnet to reach the local secrets backend.
  Acceptance evidence: verified by `ufw status numbered` showing `172.17.0.0/16` allowed to port `8200/tcp` on host-B, or the equivalent firewall declaration for the active platform.

- [ ] Disable the old host's merge-gate unit as singleton proof.
  Acceptance evidence: verified by `systemctl is-enabled <merge-gate-service>` and `systemctl is-active <merge-gate-service>` reporting disabled/inactive on host-A.

- [ ] Confirm only host-B can act as the merge-gate after migration.
  Acceptance evidence: verified by the gate health check succeeding on host-B and failing closed or reporting inactive on host-A.
