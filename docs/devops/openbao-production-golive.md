# OpenBao Production Go-Live Artifacts

This runbook covers the deployable artifacts for ce-ops#113 item 1, item 4,
item 5, and item 6. Items 2 and 3 are Operator trust-root acts and are covered
in [openbao-operator-bringup.md](openbao-operator-bringup.md).

Host decision is locked: Hetzner VPS, logically segregated from work seats,
reachable only on the tailnet. Do not expose OpenBao on a public listener.

## Artifacts

- `openbao/openbao.hcl.tmpl` configures integrated raft storage, a tailnet-only
  TLS listener, and a file audit device. OpenBao's audit device write failure is
  treated as a serving failure, so the sink path must remain writable by the
  `openbao` service user.
- `openbao/openbao.service` runs as the dedicated `openbao` user with a hardened
  systemd sandbox and write access limited to `/var/lib/openbao`,
  `/var/log/openbao`, and `/run/openbao`.
- `openbao/provision-openbao.sh` is idempotent. `--plan` prints the rendered
  config without mutation. `--apply` requires root/sudo on the VPS to create the
  system user, write `/etc/openbao/openbao.hcl`, install the unit, and enable the
  service.
- `openbao/snapshot-openbao.sh` saves a raft snapshot, encrypts it with `age`,
  and copies only encrypted artifacts to an off-host `rclone:` or `scp:` target.
- `openbao/restore-drill-openbao.sh` restores an encrypted snapshot into an
  explicit throwaway OpenBao instance and writes a proof JSON after reading a
  canary from the restored state.
- `openbao/emergency-revoke-openbao.sh` provides tested plan/execute commands
  for lease revocation, lease-prefix revocation, AppRole SecretID/token accessor
  revocation, and emergency seal.

## Host Provisioning

Set host-specific values before planning:

```bash
export OPENBAO_TAILNET_HOSTNAME='openbao.<tailnet>.ts.net'
export OPENBAO_TAILNET_BIND_ADDR='100.x.y.z'
export OPENBAO_TLS_CERT_FILE='/etc/openbao/tls/openbao.crt'
export OPENBAO_TLS_KEY_FILE='/etc/openbao/tls/openbao.key'
export OPENBAO_TLS_CLIENT_CA_FILE='/etc/openbao/tls/ca.crt'
docs/devops/openbao/provision-openbao.sh --plan
```

Apply on the VPS only after the Operator has installed OpenBao and staged the
tailnet TLS material:

```bash
sudo -E docs/devops/openbao/provision-openbao.sh --apply
sudo systemctl start openbao.service
```

The apply step needs root/sudo for system user, directory ownership, `/etc`, and
systemd writes. This repository does not perform that VPS step.

The provision script intentionally does not run `operator init`, `operator
unseal`, or any secret-zero injection.

## Encrypted Snapshot

Configure a public `age` recipient and a real off-host destination:

```bash
export BAO_ADDR='https://openbao.<tailnet>.ts.net:8200'
export BAO_CACERT='/etc/openbao/tls/ca.crt'
export OPENBAO_AGE_RECIPIENT='age1...'
export OPENBAO_SNAPSHOT_REMOTE_URI='rclone:ce-openbao-snapshots/prod'
sudo -E docs/devops/openbao/snapshot-openbao.sh
```

For local restore drills only, `OPENBAO_SNAPSHOT_REMOTE_URI=file:/tmp/...` may be
used with `OPENBAO_SNAPSHOT_ALLOW_LOCAL=1`. Production snapshots must leave the
host.

## Restore Drill Gate

The hard go-live gate is a successful restore into a throwaway OpenBao instance.
Never point the drill at production:

```bash
export OPENBAO_RESTORE_DRILL_CONFIRM=throwaway
export OPENBAO_RESTORE_DRILL_ADDR='http://127.0.0.1:18200'
export OPENBAO_ENCRYPTED_SNAPSHOT='/path/to/ce-openbao-raft-YYYYMMDDTHHMMSSZ.snap.age'
export OPENBAO_AGE_IDENTITY='/path/to/local-drill-age-identity.txt'
export OPENBAO_RESTORE_TOKEN='<target-throwaway-restore-token>'
export OPENBAO_VERIFY_TOKEN='<restored-snapshot-canary-read-token>'
export OPENBAO_RESTORE_CANARY_PATH='ce-kv/data/devs/dev-1/runtime/restore-canary'
export OPENBAO_RESTORE_CANARY_FIELD='ok'
export RESTORE_DRILL_PROOF='restore-drill-proof.json'
docs/devops/openbao/restore-drill-openbao.sh
```

The throwaway instance must be initialized and unsealed for the drill, with a
token authorized to restore the snapshot. Verification uses a separate token
from the restored snapshot state. If the restored snapshot seals the throwaway
instance, set `OPENBAO_RESTORE_DRILL_UNSEAL_KEY_FILE` to a local drill-only file
containing the restored-state unseal key. These are drill-only credentials and
must not be production custody material.

## Emergency Revocation

Every emergency action is bound to a per-dev identity:

```bash
export CE_DEV_ID='dev-1'
docs/devops/openbao/emergency-revoke-openbao.sh --plan lease
docs/devops/openbao/emergency-revoke-openbao.sh --plan approle
docs/devops/openbao/emergency-revoke-openbao.sh --plan seal
```

Execute only during an incident or a scheduled drill:

```bash
export CE_DEV_ID='dev-1'
export OPENBAO_LEASE_ID='ce-kv/creds/example/abc123'
docs/devops/openbao/emergency-revoke-openbao.sh --execute lease

export OPENBAO_APPROLE_ROLE='ce-dev-1'
export OPENBAO_SECRET_ID_ACCESSOR='accessor...'
export OPENBAO_TOKEN_ACCESSOR='token-accessor...'
docs/devops/openbao/emergency-revoke-openbao.sh --execute approle

export OPENBAO_EMERGENCY_REASON='host compromise suspected'
docs/devops/openbao/emergency-revoke-openbao.sh --execute seal
```

## Audit Fail-Closed

The HCL enables a file audit device at `${OPENBAO_AUDIT_LOG}`. The go-live test
must prove that OpenBao stops serving requests when that sink cannot accept
writes. The validator integration suite contains the local fail-closed smoke
against an ephemeral OpenBao process; production cutover must repeat the same
class of probe against the VPS after Operator bringup and before migration.

## Held Operator Actions

The following actions are not performed by these artifacts:

- Operator init with Shamir shares.
- Operator unseal and share custody.
- Initial root token use and revocation.
- AppRole creation with live policy grants.
- Response-wrapped secret-zero token minting and injection.
- Live secret migration.
