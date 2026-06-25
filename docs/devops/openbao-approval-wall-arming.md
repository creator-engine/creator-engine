# OpenBao Approval-Wall Arming Runbook

This value-free runbook records the OpenBao arming handoff for the approval
capability wall. Context: `/tmp/brief-openbao.md` and ce-ops#239/#446. The wall
daemon can source its verifier secret from the `openbao` SecretIdentityBackend,
but this lane must not mint the production wall signing secret, arm the live DGX
daemon, or flip the production armed flag.

## Verified VPS State

Connection parameters verified by the infra lane:

- `BAO_ADDR=https://ce-dev-1.tailf3cfef.ts.net:8200`
- Alternate URL: `https://100.72.252.20:8200`
- Client CA: `/usr/local/share/ca-certificates/ce-openbao-ca.crt`
- Service CA source: `/etc/openbao/tls/ca.crt`
- `CE_OPENBAO_KV_MOUNT=ce-kv`

Host status verified by the infra lane:

- OpenBao `v2.5.5`
- `openbao.service` is active and enabled under systemd
- Shamir initialized and unsealed
- 5 shares, threshold 3
- Integrated raft HA active
- Tailnet listener on `100.72.252.20:8200` and `100.72.252.20:8201`
- Audit file path exists at `/var/log/openbao/audit.log` with mode `0600` and
  owner `openbao:openbao`

Authenticated `/v1/sys/audit` and `ce-kv` verification were blocked because no
authorized `BAO_TOKEN` was available to this lane. Do not record those checks as
complete until a controller/operator runs the tokened day-2 steps below.

Current completed proof:

- Configured OpenBao backend with no token and env fallback present exited `1`.
- Failure reason was `configured_backend_without_secret`.
- The target secret file was not created.
- The env fallback was not used.

Live drift note: the VPS unit has stale `CAP_IPC_LOCK`/memlock drift from the
repository unit. Repair is recommended in a follow-up; this runbook lane does
not change the unit.

## SecretRef SSOT

The approval-capability wall has one canonical OpenBao SecretRef. Operators
must use this SecretRef for both verifier reads and controller/integrator
mint-on-approval issuance:

- Backend: `openbao`
- Mount: `ce-kv`
- Path: `forge/approval-capability/wall`
- Field: `signing_secret`
- Purpose: `approval-capability-wall`
- Owner-ref: `controller:integrator`

Earlier `forge/approval-wall/test` and `forge/approval-wall/prod` examples are
not the SecretRef for ce-ops#247. Do not use them for mint-on-approval or live
approval-wall arming.

The production signing secret must be created only by an authorized
controller/operator through the approved secret channel. This documentation lane
records the binding; it must not mint, reveal, or commit the live secret.

## Secure Token Retrieval

The controller/operator must decrypt `/home/ce/open_bao.json.gpg` or otherwise
hand off an authorized OpenBao token through the approved secret channel. Do not
put OpenBao tokens, wall signing secrets, unseal shares, or decrypted custody
material in this repository, logs, PRs, issues, shell history, or chat.

The exact authorized daemon token path inside the encrypted custody bundle is
unresolved for this lane. If the bundle does not contain the correct
least-privilege token, the controller/operator must mint one during the day-2
steps and hand it off through the approved secret channel.

## Day-2 Controller/Operator Steps

Use a controlled shell on the authorized host. Keep secret values in memory or
tmpfs only, and unset them at the end.

```bash
export BAO_ADDR='https://ce-dev-1.tailf3cfef.ts.net:8200'
export BAO_CACERT='/usr/local/share/ca-certificates/ce-openbao-ca.crt'
export CE_OPENBAO_KV_MOUNT='ce-kv'
export BAO_TOKEN='<authorized-operator-token-from-approved-channel>'
export CE_VALIDATOR_PYTHON="${CE_VALIDATOR_PYTHON:-python}"
```

1. Verify the authenticated audit endpoint.

```bash
curl --silent --show-error --fail \
  --cacert "$BAO_CACERT" \
  --header "X-Vault-Token: $BAO_TOKEN" \
  "$BAO_ADDR/v1/sys/audit"
```

2. Verify or create the `ce-kv` KV v2 mount.

```bash
bao secrets list -format=json | jq -e \
  '."ce-kv/".type == "kv" and ."ce-kv/".options.version == "2"' \
  || bao secrets enable -path="$CE_OPENBAO_KV_MOUNT" kv-v2
```

3. Verify or write the canonical approval-wall signing secret at
   `ce-kv/forge/approval-capability/wall`, field `signing_secret`. Use a tmpfs
   file or another approved in-memory handoff for the source value.

```bash
export CE_APPROVAL_WALL_SIGNING_SECRET_FILE="/run/user/$(id -u)/ce-approval-wall-signing-secret"
install -m 700 -d "$(dirname "$CE_APPROVAL_WALL_SIGNING_SECRET_FILE")"
# Operator writes the approved signing secret to the file with mode 0600.
jq -Rs '{data: {signing_secret: .}}' < "$CE_APPROVAL_WALL_SIGNING_SECRET_FILE" \
  | curl --silent --show-error --fail \
      --cacert "$BAO_CACERT" \
      --header "X-Vault-Token: $BAO_TOKEN" \
      --request POST \
      --data-binary @- \
      "$BAO_ADDR/v1/$CE_OPENBAO_KV_MOUNT/data/forge/approval-capability/wall"
```

4. Create a least-privilege read policy and short-lived daemon token for the
   canonical SecretRef only.

```bash
cat > /run/user/$(id -u)/ce-approval-wall-read.hcl <<'POLICY'
path "ce-kv/data/forge/approval-capability/wall" {
  capabilities = ["read"]
}
POLICY

bao policy write ce-approval-wall-read \
  /run/user/$(id -u)/ce-approval-wall-read.hcl

bao token create \
  -policy=ce-approval-wall-read \
  -ttl=1h \
  -renewable=false \
  -format=json
```

Export only the returned token through the approved secret channel:

```bash
export BAO_TOKEN='<least-privilege-daemon-token-from-approved-channel>'
```

5. Run the queue-daemon proof with file target in tmpfs. Use `--once`,
   `--dry-run`, and a tmpfs wall state path so this proof does not arm the live
   daemon state.

```bash
export CE_APPROVAL_WALL_TMPFS="/run/user/$(id -u)/ce-approval-wall-test"
install -m 700 -d "$CE_APPROVAL_WALL_TMPFS"
rm -f "$CE_APPROVAL_WALL_TMPFS/secret" "$CE_APPROVAL_WALL_TMPFS/state.json"

BAO_ADDR="$BAO_ADDR" \
BAO_CACERT="$BAO_CACERT" \
CE_OPENBAO_KV_MOUNT="$CE_OPENBAO_KV_MOUNT" \
BAO_TOKEN="$BAO_TOKEN" \
PYTHONPATH=validators \
"$CE_VALIDATOR_PYTHON" -m creator_engine_validator.v3_cli queue-daemon \
  --repo '<OWNER/REPO>' \
  --once \
  --dry-run \
  --authorized-reviewer '<APPROVING_LOGIN>' \
  --approval-wall-secret-backend openbao \
  --approval-wall-secret-mount ce-kv \
  --approval-wall-secret-path forge/approval-capability/wall \
  --approval-wall-secret-field signing_secret \
  --approval-wall-secret-purpose approval-capability-wall \
  --approval-wall-secret-owner-ref controller:integrator \
  --approval-wall-secret-ref-policy-sha '<64_HEX_POLICY_SHA>' \
  --approval-wall-secret-target-ref "file:$CE_APPROVAL_WALL_TMPFS/secret" \
  --approval-wall-secret-repo '<OWNER/REPO>' \
  --approval-wall-secret-run-id approval-wall-openbao-test \
  --approval-wall-secret-seat-id controller \
  --approval-wall-secret-ttl-seconds 600 \
  --approval-wall-state "$CE_APPROVAL_WALL_TMPFS/state.json" \
  --approval-wall-policy-sha '<APPROVAL_POLICY_SHA>' \
  --json
```

6. Exercise mint-on-approval only through the trusted controller/integrator
   queue daemon. Do not set `CE_APPROVAL_CAPABILITY_SECRET` for automatic
   minting. On a controlled PR with a current-head approval from an authorized
   reviewer and no existing marker, run the queue daemon with the same OpenBao
   SecretRef, `--authorized-reviewer`, path manifest gate, settle state, and
   live reverify enabled. The first pass may defer as `approval_settle_pending`;
   the settled pass must mint only after current-head approval, reviewer
   authorization, path gate, and live reverify all succeed.

   A successful automatic mint writes the public
   `ce-approval-capability: v1.<payload-b64>.<signature>` marker into the PR
   body and returns `approval_capability_minted`. The daemon defers after
   minting; the armed verifier then verifies the marker from PR body metadata on
   the next pass before enqueue is eligible.

7. Verify a valid marker. Rerun the queue-daemon proof above against the PR body
   carrying the marker and confirm the marker verifies with the canonical
   OpenBao SecretRef.

8. Verify wrong-secret failure. Mint a marker with a different synthetic secret
   outside the daemon path, place it on the controlled PR body, rerun the
   queue-daemon proof, and confirm the failure reason is `signature_mismatch`.

9. Verify missing or unreachable secret failure. Run the queue-daemon proof with
   backend flags still configured but with no usable `BAO_TOKEN` or with an
   unreachable canonical path. Confirm exit `1`, no env fallback, and no target
   file creation.

10. Revoke proof tokens and remove only temporary local material. Do not delete
    the canonical OpenBao signing secret unless this is an explicitly authorized
    decommissioning action.

```bash
export BAO_TOKEN='<authorized-operator-token-from-approved-channel>'
bao token revoke '<daemon-token-or-accessor>'
bao policy delete ce-approval-wall-read
rm -f "$CE_APPROVAL_WALL_SIGNING_SECRET_FILE"
rm -rf "$CE_APPROVAL_WALL_TMPFS"
unset BAO_TOKEN BAO_ADDR BAO_CACERT CE_OPENBAO_KV_MOUNT CE_APPROVAL_WALL_SIGNING_SECRET_FILE
```

Do not flip the armed flag, update production daemon configuration, mint a
production wall secret, or leave proof tokens/secrets alive in this lane.

## Repo Validations

Run the docs and carrier checks for this change set:

```bash
export CE_VALIDATOR_PYTHON="${CE_VALIDATOR_PYTHON:-python}"

PYTHONPATH=validators "$CE_VALIDATOR_PYTHON" -m creator_engine_validator.ce_cli check \
  docs/devops/openbao-approval-wall-arming.md \
  .ce/changelog/ce-openbao-vps-standup.md \
  .ce/pr-manifests/ce-openbao-vps-standup.md

PYTHONPATH=validators "$CE_VALIDATOR_PYTHON" -m creator_engine_validator.cli scan-path-manifest \
  .ce/pr-manifests/ce-openbao-vps-standup.md
```
