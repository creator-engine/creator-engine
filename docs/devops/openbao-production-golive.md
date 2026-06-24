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
- `openbao/bringup-container-openbao.sh` is the dry-run-first single-node
  container bring-up for dogfood and live validator tests. It defaults to
  `--plan`; `--apply` requires `OPENBAO_CONTAINER_CONFIRM=ephemeral`, binds only
  to `127.0.0.1`, writes generated init output only to an external workdir, and
  configures synthetic canaries rather than real secrets.
- `openbao/snapshot-openbao.sh` saves a raft snapshot, encrypts it with `age`,
  and copies only encrypted artifacts to an off-host `rclone:` or `scp:` target.
- `openbao/restore-drill-openbao.sh` restores an encrypted snapshot into an
  explicit throwaway OpenBao instance and writes a proof JSON after reading a
  canary from the restored state.
- `openbao/render-dev-policy.sh` renders one policy per dev identity so each
  AppRole is bound only to its own `ce-kv/devs/<dev-id>/runtime/*` paths.
- `openbao/ce-broker-policy.hcl.tmpl` defines the response-wrapped AppRole
  minting surface for the broker. It can read role IDs and create wrapped
  SecretIDs for concrete `ce-dev-*` roles, but it cannot write policies, unseal,
  or read broad KV content.
- `openbao/ce-operator-import-policy.hcl.tmpl` is a short-lived Operator-only
  import policy template for a ratified migration window. It is not a dev-seat,
  CI, or agent-container policy.
- `openbao/openbao-secret-path-map.tsv` is the value-free name-to-path map for
  per-dev GitHub PATs, `CLAUDE_CODE_OAUTH_TOKEN`, the shared GitHub App PEM,
  and the deferred `ce-root-v1` signing path.
- `openbao/emergency-revoke-openbao.sh` provides tested plan/execute commands
  for lease revocation, lease-prefix revocation, AppRole SecretID/token accessor
  revocation, and emergency seal, using the same per-dev role/policy naming.
- `openbao/secret-migration-inventory.tsv` is a value-free Operator template
  for source refs, target OpenBao refs, owners, rotation refs, rollback refs,
  and evidence refs. It is not a live import file and must remain a template
  with no real secret values.
- `openbao/verify-secret-migration-inventory.sh` validates the migration
  inventory shape, rejects duplicate `record_id` and `target_ref` rows, and
  rejects OpenBao token-shaped values (`hvs.`, `hvb.`, `bao.`), common API key
  shapes, password assignments, and PEM armoring before any migration window is
  approved.

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

## Single-Node Container Dogfood

Use the container script for dry-run validation and disposable live tests before
the Operator performs VPS bring-up. The default mode prints the plan and does
not start a container:

```bash
docs/devops/openbao/bringup-container-openbao.sh --plan
```

To create a local ephemeral OpenBao instance with synthetic paths only:

```bash
export OPENBAO_CONTAINER_CONFIRM=ephemeral
export OPENBAO_CONTAINER_WORKDIR="/tmp/ce-openbao-single-node"
export OPENBAO_DEV_IDS="dev-1,dev-2"
docs/devops/openbao/bringup-container-openbao.sh --apply
```

The script starts `openbao/openbao:2.5.5` by default, publishes only
`127.0.0.1:${OPENBAO_CONTAINER_PORT:-18200}`, initializes with a local
single-share Shamir profile, unseals the disposable instance, enables `ce-kv`
KV v2 and `approle`, writes the broker/import/per-dev policies, creates one
short-TTL AppRole per dev identity, and stores only a synthetic restore canary.
Generated init output is written under the external workdir with mode `0600`.
Do not move that file into the repo, logs, chat, issue comments, or CI.

Destroy the instance after the dogfood run:

```bash
docs/devops/openbao/bringup-container-openbao.sh --destroy
rm -rf /tmp/ce-openbao-single-node
```

The script can print the expected live-test environment without reading the
generated root token:

```bash
docs/devops/openbao/bringup-container-openbao.sh --print-live-test-env
```

## Live Validator Tests

The Python live tests use a local `bao` binary through `CE_OPENBAO_BIN`; they
start their own throwaway OpenBao processes and are skipped unless the variable
is set. After installing OpenBao locally or copying the binary out of the
container image, run:

```bash
cd validators
python -m pytest \
  tests/integration/test_openbao_p3_live.py \
  tests/integration/test_openbao_golive_restore_drill_live.py
```

The production config download smoke is intentionally separate because it
downloads and verifies OpenBao 2.5.5:

```bash
cd validators
CE_OPENBAO_GOLIVE_DOWNLOAD_SMOKE=1 python -m pytest \
  tests/integration/test_openbao_golive_production_config_live.py
```

Those live tests use synthetic canaries and generated throwaway init material.
They must not be pointed at production OpenBao or at real `~/.ce-keys` values.

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

Migration is one approved window per secret family. The repository inventory is
a template only; it proves the value-free TSV shape and must not be edited into
the live import plan. The Operator records only refs and evidence handles in the
inventory:

```bash
docs/devops/openbao/verify-secret-migration-inventory.sh \
  docs/devops/openbao/secret-migration-inventory.tsv
```

For a real window, use an Operator-controlled copy of the same TSV shape outside
the repo and outside agent/container custody. The live inventory may name source
custody handles and target OpenBao logical paths, but it must not contain
literal secret material and must not be committed back to this repository. Each
row must have:

- `source_ref`: where the Operator can retrieve the current value, expressed as
  a handle such as `source-ref:legacy-host/dev-1/runtime-token`.
- `target_ref`: the intended OpenBao logical ref, such as
  `openbao-ref:ce-kv/forge/github-apps/primary/private-key`; no two rows may
  use the same target ref.
- `record_id`: a stable value-free row id; no two rows may use the same id.
- `owner_ref`, `rotation_ref`, `rollback_ref`, and `evidence_ref`: value-free
  governance handles.
- `status`: one of `planned`, `imported`, `verified`, `cutover`,
  `rolled-back`, or `decommissioned`.

### Legacy `~/.ce-keys` and env-forwarding map

The committed inventory is template-only. It enumerates the legacy names CE
currently expects from `~/.ce-keys` or host env-forwarding without storing or
implying any live value. A real migration window expands any `N` family row in
an Operator-controlled copy outside the repository.

| Legacy name or family | Target OpenBao ref | Policy | Owner | Rollback ref |
| --- | --- | --- | --- | --- |
| `ce-dev-1.pat` | `openbao-ref:ce-kv/devs/dev-1/runtime/github-pat` | `ce-dev-1-runtime-read` | `owner-ref:dev-1` | `rollback-ref:legacy-host/.ce-keys/ce-dev-1.pat` |
| `ce-dev-2.pat` | `openbao-ref:ce-kv/devs/dev-2/runtime/github-pat` | `ce-dev-2-runtime-read` | `owner-ref:dev-2` | `rollback-ref:legacy-host/.ce-keys/ce-dev-2.pat` |
| `ce-dev-3.pat` | `openbao-ref:ce-kv/devs/dev-3/runtime/github-pat` | `ce-dev-3-runtime-read` | `owner-ref:dev-3` | `rollback-ref:legacy-host/.ce-keys/ce-dev-3.pat` |
| `ce-dev-4.pat` | `openbao-ref:ce-kv/devs/dev-4/runtime/github-pat` | `ce-dev-4-runtime-read` | `owner-ref:dev-4` | `rollback-ref:legacy-host/.ce-keys/ce-dev-4.pat` |
| `CLAUDE_CODE_OAUTH_TOKEN` | `openbao-ref:ce-kv/devs/controller/runtime/claude-code-oauth-token` | `ce-controller-runtime-read` | `owner-ref:controller-runtime` | `rollback-ref:legacy-host/env-forwarding/CLAUDE_CODE_OAUTH_TOKEN` |
| `ce-forge-app.pem` for the creator-engine shared App | `openbao-ref:ce-kv/forge/github-apps/creator-engine-shared/private-key` | `ce-forge-app-jwt-sign` | `owner-ref:forge-platform` | `rollback-ref:legacy-host/.ce-keys/ce-forge-app.pem` |
| `ce-forge-app.json` | `openbao-ref:ce-kv/forge/github-apps/creator-engine-shared/config` | `ce-forge-app-config-read` | `owner-ref:forge-platform` | `rollback-ref:legacy-host/.ce-keys/ce-forge-app.json` |
| `ce-forge-devN.json` | `openbao-ref:ce-kv/forge/github-apps/devs/config` | `ce-forge-app-config-read` | `owner-ref:forge-platform` | `rollback-ref:legacy-host/.ce-keys/ce-forge-devN.json` |
| `agent-reviewer-app.json` | `openbao-ref:ce-kv/forge/github-apps/reviewer/config` | `ce-reviewer-app-config-read` | `owner-ref:forge-reviewers` | `rollback-ref:legacy-host/.ce-keys/agent-reviewer-app.json` |
| `agent-reviewer-app.pem` | `openbao-ref:ce-kv/forge/github-apps/reviewer/private-key` | `ce-reviewer-app-jwt-sign` | `owner-ref:forge-reviewers` | `rollback-ref:legacy-host/.ce-keys/agent-reviewer-app.pem` |
| `ce-root-v1` | `openbao-ref:ce-transit/governance/signing/ce-root-v1` | `ce-root-v1-signing-request` | `owner-ref:operator-trust-root` | `rollback-ref:legacy-offline/.ce-keys/ce-root-v1` |

`ce-root-v1` is listed so the migration map is complete, not because this
runbook authorizes importing a governance signing root. ADR-0005 and ADR-0012
hold signing-root co-tenancy behind separate Operator ratification. Until that
ratification exists, rollback is the current offline Operator custody path.

### Cutover from host files to brokered identity

Cutover is by consumer and by ref. No consumer copies values back out of
OpenBao, and no seat receives OpenBao root/admin tokens, RoleIDs, SecretIDs,
wrapping-token values, App PEM contents, PAT values, Claude OAuth contents, or
the `ce-root-v1` private key.

1. Import the approved live inventory copy through Operator custody only.
2. Verify every `target_ref` with metadata reads and audit evidence.
3. Create or confirm per-seat AppRoles and policies named in the map. The
   existing per-dev runtime policy template covers `ce-kv/data/devs/<dev-id>/runtime/*`.
4. Issue response-wrapped secret-zero through the OpenBao secret-zero broker.
   Seats redeem through `SecretIdentityBackend` and hold only an in-memory
   `OpenBaoAppRoleSession`.
5. Change consumers from `~/.ce-keys/<name>` and host env-forwarding to
   `SecretRef` or broker request handles:
   `ce-dev-N.pat` reads become per-dev runtime reads, GitHub App PEM use becomes
   broker-side JWT signing, `CLAUDE_CODE_OAUTH_TOKEN` is delivered by env name
   from the broker boundary, and `ce-root-v1` remains a signing request handle
   unless separately ratified.
6. Freeze legacy env-forwarding and host-file mounts for the migrated family.
   Keep rollback refs available until a post-cutover encrypted snapshot and
   restore drill pass.
7. Revoke migration importer credentials, one-use wrappers, and any temporary
   accessors, then record only value-free audit refs.

The W5 run-script token-leak fix is explicitly deferred from this migration
map. This docs-only cutover does not change or authorize changes to
`deploy/*/run-*.sh`; deploy run scripts remain out of scope for this lane.

Before import:

1. Freeze new broker secret materialization for the target family.
2. Confirm audit is active with `bao audit list` and audit fail-closed evidence
   has been recorded for the production sink.
3. Take and copy an encrypted off-host snapshot.
4. Run a restore drill from the current snapshot into a throwaway instance.
5. Validate the value-free inventory with
   `verify-secret-migration-inventory.sh`.
6. Confirm the migration importer token is time-limited, scoped only to the
   listed target paths, and revoked after the window.

The canonical value-free name-to-path map for the first dogfood window is:

| Secret name | Destination ref | Policy boundary |
| --- | --- | --- |
| Per-dev GitHub PAT | `openbao-ref:ce-kv/devs/dev-N/runtime/github-pat` | `ce-dev-N-runtime`, read by the matching dev AppRole only |
| `CLAUDE_CODE_OAUTH_TOKEN` | `openbao-ref:ce-kv/devs/dev-N/runtime/claude-code-oauth-token` | `ce-dev-N-runtime`, served JIT by broker or Transport-deputy precursor |
| Creator Engine shared GitHub App PEM | `openbao-ref:ce-kv/forge/github-apps/creator-engine-shared/private-key` | broker/Operator-only; materialize to tmpfs or signing helper, never to seats |
| `ce-root-v1` signing key | `openbao-ref:ce-transit/governance/signing/ce-root-v1` | deferred Operator-only transit signing path; not imported into the dev runtime KV instance |

The same map is encoded in
`docs/devops/openbao/openbao-secret-path-map.tsv` for review and runbook use.

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

## Launcher Cutover For The W5 Token Leak

The W5 leak closes when launchers stop forwarding `CLAUDE_CODE_OAUTH_TOKEN` into
the sandbox and request the OpenBao ref just-in-time through the broker. This is
the Transport-deputy precursor called out by the three-deputy governance design
(`ce-ops/designs/DESIGN_THREE_DEPUTY_GOVERNANCE_20260624.md`). That design file
is external to this repo snapshot; this runbook preserves the requested path as
the governance reference.

The launcher implementation change is intentionally not made in this slice, but
the required cutover is:

```diff
- docker run ... --env CLAUDE_CODE_OAUTH_TOKEN ...
+ docker run ... --env CE_SECRET_REF_CLAUDE_CODE_OAUTH_TOKEN=secret-ref:ce-kv/devs/${CE_DEV_ID}/runtime/claude-code-oauth-token ...
+ # broker resolves the ref through SecretIdentityBackend and injects the value
+ # only into the approved in-memory/tmpfs delivery target for the governed run
```

Apply that shape to the controller and VPS launcher surfaces, including
`deploy/dgx-controller-runsc/run-controller-runsc.sh` and
`deploy/vps-runsc/run-vps-runsc.sh`, during the launcher cutover PR. The
OpenBao policy boundary above means the sandbox receives a ref and broker grant
metadata, not the standing host environment value.

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
