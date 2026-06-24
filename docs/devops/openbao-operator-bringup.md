# OpenBao Operator Bringup

This runbook is for ce-ops#113 items 2 and 3. These are Operator-performed
trust-root acts. Agents must not execute them against production and must not
inject real secret-zero material.

For a value-free single-node container pilot, use
`docs/devops/openbao/bringup-container-openbao.sh --plan`. That path is
dry-run-first and keeps live production init, unseal, and secret-zero custody as
Operator-controlled acts.

Prerequisites:

- Hetzner VPS is provisioned and reachable only on the tailnet.
- `docs/devops/openbao/provision-openbao.sh --apply` has been run by an
  Operator with root/sudo on the VPS.
- Internal TLS cert/key and client CA are staged at the paths configured in
  `/etc/openbao/openbao.hcl`.
- The `openbao` service is running and sealed.
- `docs/devops/openbao/bringup-container-openbao.sh --plan` has been reviewed,
  and any optional local `--apply` dogfood used only synthetic values in an
  external workdir.

## 1. Initialize With 3-of-5 Shamir

Operator action:

```bash
export BAO_ADDR='https://openbao.<tailnet>.ts.net:8200'
export BAO_CACERT='/etc/openbao/tls/ca.crt'
bao operator init -key-shares=5 -key-threshold=3 -format=json > openbao-init.json
```

Immediately split custody:

- Store each unseal share with a different approved custodian.
- Store the initial root token separately from shares and only for bringup.
- Do not place shares, root token, RoleIDs, SecretIDs, or wrapping tokens in
  this repository, shell history, issue comments, PRs, or chat transcripts.
- Record only value-free custody references in governance evidence.

## 2. Unseal

Three custodians provide shares through an Operator-controlled terminal:

```bash
bao operator unseal
bao operator unseal
bao operator unseal
bao status
```

Do not enable auto-unseal for this go-live. Auto-unseal remains a later,
separately ratified change.

## 2a. Activate Declarative Audit Device

OpenBao 2.5.x reads declarative audit devices only after a reload, not on the
first service start. After unseal, force the systemd reload path before any
secret-zero or AppRole work:

```bash
sudo systemctl reload openbao.service
bao audit list
```

`bao audit list` must show the configured file audit device before continuing.

## 3. Enable Per-Dev Policy And AppRole

Use the initial root token only for setup. Then revoke it.

```bash
export BAO_TOKEN='<initial-root-token>'
bao secrets enable -path=ce-kv kv-v2
bao auth enable approle

# Optional only when the Operator opens a ratified import window. Do not bind
# this policy to dev seats, CI, or agent containers.
bao policy write ce-operator-import docs/devops/openbao/ce-operator-import-policy.hcl.tmpl

export CE_DEV_ID='dev-1'
export CE_APPROLE_NAME="ce-${CE_DEV_ID}"
export CE_POLICY_NAME="ce-${CE_DEV_ID}-runtime"
docs/devops/openbao/render-dev-policy.sh > "/tmp/${CE_POLICY_NAME}.hcl"
bao policy write "$CE_POLICY_NAME" "/tmp/${CE_POLICY_NAME}.hcl"
rm -f "/tmp/${CE_POLICY_NAME}.hcl"

bao write "auth/approle/role/${CE_APPROLE_NAME}" \
  "token_policies=${CE_POLICY_NAME}" \
  token_ttl=10m \
  token_max_ttl=30m \
  secret_id_ttl=10m \
  secret_id_num_uses=1
```

Keep the broker policy artifact (`docs/devops/openbao/ce-broker-policy.hcl.tmpl`)
for the secret-zero broker bringup lane. Do not bind per-dev roles to the broker
policy.

Repeat policy rendering and role creation per approved dev identity (`dev-1`,
`dev-2`, and so on). Each AppRole gets exactly one per-dev runtime policy. Do
not bind multiple dev roles to one shared wildcard policy.

The initial runtime target paths are documented in
`docs/devops/openbao/openbao-secret-path-map.tsv`:

- Per-dev GitHub PATs:
  `ce-kv/data/devs/<dev>/runtime/github-pat`, field `token`.
- `CLAUDE_CODE_OAUTH_TOKEN`:
  `ce-kv/data/devs/<dev>/runtime/claude-code-oauth-token`, field `token`.
- Creator Engine shared GitHub App PEM:
  `ce-kv/data/forge/github-apps/creator-engine-shared/private-key`, field `pem`,
  broker/Operator-only.
- `ce-root-v1`:
  deferred `ce-transit/governance/signing/ce-root-v1` signing path, not a dev
  runtime KV import and not available to dev AppRoles.

## 4. Broker-Minted Short-TTL Secret-Zero

After the per-dev AppRoles exist, steady-state dev seat bootstrap is brokered
through the `SecretIdentityBackend` adapter. The broker, not the dev seat,
requests a response-wrapped SecretID for the concrete role (`ce-dev-1`,
`ce-dev-2`, and so on), using a short wrapping TTL and `secret_id_num_uses=1`.
The broker delivers only an in-memory RoleID/wrapping-token payload through the
approved one-use seat channel and records only value-free accessors/refs.

Operator reference command for a manual break-glass mint, not agent automation:

```bash
bao read -field=role_id auth/approle/role/ce-dev-1/role-id
bao write -wrap-ttl=10m -f auth/approle/role/ce-dev-1/secret-id
```

Hand off only through the approved secret-zero channel. Do not store RoleIDs,
SecretIDs, wrapping tokens, PEMs, or resulting OpenBao tokens on disk. The seat
unwraps once, logs in through AppRole, and uses the resulting short-lived token
through `SecretIdentityBackend` for its own
`ce-kv/data/devs/<dev>/runtime/*` paths.

For `CLAUDE_CODE_OAUTH_TOKEN`, the cutover target is broker-mediated
just-in-time delivery from
`secret-ref:ce-kv/devs/<dev>/runtime/claude-code-oauth-token`. The launcher
cutover removes direct `CLAUDE_CODE_OAUTH_TOKEN` env forwarding from
`deploy/dgx-controller-runsc/run-controller-runsc.sh` and
`deploy/vps-runsc/run-vps-runsc.sh`; the governed run receives only a SecretRef
and value-free grant metadata until the broker injects the value into the
approved in-memory/tmpfs delivery target. This is the Transport-deputy precursor
for `ce-ops/designs/DESIGN_THREE_DEPUTY_GOVERNANCE_20260624.md`.

## 5. Revoke Initial Root Token

After policy, AppRole, audit, and restore drill gates pass:

```bash
bao token revoke -self
unset BAO_TOKEN
```

Confirm the root token is unusable and that day-2 operations use named
least-privilege Operator tokens or response-wrapped AppRole flows.

## 6. Go-Live Checks Before Migration

Operator records value-free evidence for:

- `bao status` shows initialized and unsealed.
- `sudo systemctl reload openbao.service` has been run after unseal, and
  `bao audit list` includes the configured file audit device.
- Audit fail-closed probe blocks serving when the sink is unavailable.
- Encrypted off-host snapshot completes.
- Restore drill into a throwaway instance passes and writes proof JSON.
- Emergency revocation plan has been rehearsed by lease, AppRole accessor, and
  emergency seal.
- The migration inventory validates with
  `docs/devops/openbao/verify-secret-migration-inventory.sh`; duplicate
  `record_id` and `target_ref` rows are rejected, and the repository copy
  remains a template only.
- `docs/devops/openbao/openbao-secret-path-map.tsv` has been copied to
  Operator custody for the live window and expanded by name only; no values are
  copied back into this repository.
- The inventory contains only source refs, target refs, owner refs, rotation
  refs, rollback refs, evidence refs, statuses, and notes. It contains no
  OpenBao token-shaped values (`hvs.`, `hvb.`, `bao.`), PEM blocks, passwords,
  API keys, or other secret values.
- The migration importer policy/token for the first window is time-limited,
  scoped only to listed target refs, denies broad list/readback outside those
  refs, and has a recorded revocation step.
- Initial root-token revocation is complete or the remaining root-token custody
  exception has explicit Operator quorum approval; migration approval does not
  grant agents or CI access to root/admin credentials.

Only after those checks pass may the Operator separately ratify live secret
migration. Migration is performed by the Operator from controlled custody only,
outside this repository and outside agent/container lanes: do not place secret
values in this repository, shell history, issue comments, PRs, chat transcripts,
persistent temp files, container layers, or CI logs. Rollback or production
restore remains an Operator break-glass act that requires value-free evidence
for the active audit sink, encrypted snapshot id, restore-drill proof, revoked
accessors/leases, and quorum ratification.
