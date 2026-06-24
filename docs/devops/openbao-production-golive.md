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
- `openbao/render-dev-policy.sh` renders one policy per dev identity so each
  AppRole is bound only to its own `ce-kv/devs/<dev-id>/runtime/*` paths.
- `openbao/emergency-revoke-openbao.sh` provides tested plan/execute commands
  for lease revocation, lease-prefix revocation, AppRole SecretID/token accessor
  revocation, and emergency seal, using the same per-dev role/policy naming.
- `openbao/secret-migration-inventory.tsv` is a value-free Operator template
  for source refs, target OpenBao refs, owners, rotation refs, rollback refs,
  and evidence refs. It contains no real secret values.
- `openbao/verify-secret-migration-inventory.sh` validates the migration
  inventory shape and rejects common token, key, password, and PEM patterns
  before any migration window is approved.

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
```

The apply step needs root/sudo for system user, directory ownership, `/etc`, and
systemd writes. It also starts `openbao.service` and issues a reload so the
OpenBao 2.5.x declarative audit-device path is exercised; after Operator unseal,
repeat `sudo systemctl reload openbao.service` and confirm `bao audit list`
shows the file audit device before creating AppRoles or minting secret-zero.
This repository does not perform that VPS step.

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

## Secret Migration Gate

Live migration is allowed only after Operator bringup, audit activation,
fail-closed probing, encrypted snapshot, restore drill, and emergency revocation
rehearsal all have value-free evidence. Agents and containers must not receive
OpenBao root/admin tokens, unseal shares, RoleIDs, SecretIDs, wrapping tokens,
PEMs, model-provider keys, bootstrap tokens, reviewer tokens, signing keys, or
runtime secret values.

Migration is one approved window per secret family. The Operator records only
refs and evidence handles in the inventory:

```bash
docs/devops/openbao/verify-secret-migration-inventory.sh \
  docs/devops/openbao/secret-migration-inventory.tsv
```

For a real window, use an Operator-controlled copy of the same TSV shape outside
the repo. The live inventory may name source custody handles and target OpenBao
logical paths, but it must not contain literal secret material and must not be
committed back to this repository. Each row must have:

- `source_ref`: where the Operator can retrieve the current value, expressed as
  a handle such as `source-ref:legacy-host/dev-1/runtime-token`.
- `target_ref`: the intended OpenBao logical ref, such as
  `openbao-ref:ce-kv/forge/github-apps/primary/private-key`.
- `owner_ref`, `rotation_ref`, `rollback_ref`, and `evidence_ref`: value-free
  governance handles.
- `status`: one of `planned`, `imported`, `verified`, `cutover`,
  `rolled-back`, or `decommissioned`.

Before import:

1. Freeze new broker secret materialization for the target family.
2. Take and copy an encrypted off-host snapshot.
3. Run a restore drill from the current snapshot into a throwaway instance.
4. Validate the value-free inventory with
   `verify-secret-migration-inventory.sh`.
5. Confirm the migration importer token is time-limited, scoped only to the
   listed target paths, and revoked after the window.

The verifier is a preflight guard, not a sanitizer. If it fails, discard the
working copy or move it back to Operator custody; do not edit secret-bearing
material in an agent container to make the file pass.

During import, secret values may be materialized only in an Operator-controlled
terminal or tmpfs on the trusted host. Do not write values to git, issue
comments, shell history, persistent temp files, container layers, CI logs, or
chat. Use OpenBao commands with Operator-provided stdin or tmpfs files and
record only target refs, metadata refs, accessors, policy names, and audit refs.

After import:

1. Verify metadata for every target ref with `bao kv metadata get` or the
   equivalent OpenBao API call.
2. Verify a broker-mediated materialization path using a canary or already
   authorized low-risk row before migrating higher-risk material.
3. Cut over consumers by ref, not by copying values back out of OpenBao.
4. Revoke the migration importer token, revoke any one-use wrappers, and record
   value-free audit/accessor refs.
5. Take a post-import encrypted snapshot and run a restore drill before
   decommissioning the source.

## Rollback And Restore

Rollback is chosen by failure class:

- Inventory or preflight failure: abort the window. No OpenBao state mutation is
  allowed.
- Import failure before cutover: freeze broker issuance for the affected target
  refs, revoke importer and wrapper credentials, delete or quarantine only the
  newly imported target refs, and keep consumers on the legacy source handles.
- Cutover failure with OpenBao healthy: move consumers back to the previous
  value-free source refs, revoke OpenBao tokens and dynamic leases issued during
  the window, and keep imported refs disabled until rotation or reimport.
- OpenBao state corruption: freeze all broker issuance, preserve audit logs,
  seal OpenBao if compromise is suspected, and restore production only from the
  last encrypted snapshot that passed a throwaway restore drill and Operator
  quorum approval.
- Source compromise discovered during migration: stop migration for that family,
  rotate at the upstream provider first, import only the rotated value through
  Operator custody, then decommission the compromised source handle.

Restore to production is a break-glass Operator act. Never restore a snapshot
over production from this repository or from an agent/container lane. Evidence
for rollback or restore must remain value-free: snapshot id, encrypted artifact
digest, restore drill proof id, target refs, revoked accessors, lease ids, and
Operator ratification refs.

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

The HCL declares a file audit device at `${OPENBAO_AUDIT_LOG}` using OpenBao
2.5.x's required `options = { ... }` map syntax. OpenBao 2.5.x does not activate
that declarative audit device on first boot; it activates after reload. The
go-live sequence therefore starts the service, reloads it, and after unseal
reloads it again before `bao audit list` evidence is accepted. The go-live test
must also prove that OpenBao stops serving requests when the sink cannot accept
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
- Live secret value migration. This runbook defines gates, inventory shape, and
  rollback/restore handling only; the actual value import is Operator-executed
  during a ratified window.
