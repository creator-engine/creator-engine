# Controller Identity Protocol

## Purpose

This protocol defines the PCO Slice 2.5A controller-key record substrate for `PCO-025`.

A controller-key record binds a `controller_id` to public-key metadata so later gates can verify worktree-lease signatures (`PCO-024`). This gate is substrate-only. It does not generate keys, hold private keys, verify lease signatures, allocate worktrees, launch panes, implement worker containers, or expand autonomy.

## Canonical record location

Source ratified OSD-2 as:

`tenants/<tenant>/controllers/<controller-id>.key.yaml`

Example fixtures may live under `examples/**` for validator coverage, but production/controller records use the tenant controller path above unless a later Source-ratified overlay supersedes it.

## Record shape

A controller-key record has this shape:

```yaml
kind: controller-key-record
record_type: controller_key
schema_version: "1"
tenant_id: dogfood
controller_id: hermes-primary
key_algorithm: ed25519
public_key:
  encoding: base64url-no-padding
  value: AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA
issued_at: 2026-05-22T00:00:00Z
issued_by: source-controlled:tenants/dogfood/identity.yaml
key_custody_mode: per_host
status: active
```

Required fields:

- `kind: controller-key-record`
- `record_type: controller_key`
- `schema_version: "1"`
- `tenant_id`, matching `^[a-z][a-z0-9-]{2,63}$`
- `controller_id`, matching `^[a-z][a-z0-9-]{2,63}$`
- `key_algorithm: ed25519`
- `public_key.encoding: base64url-no-padding`
- `public_key.value`, unpadded base64url that decodes to exactly 32 bytes
- `issued_at`
- `issued_by`, currently `source-controlled:<repo-relative-path>`
- `key_custody_mode: per_host`
- `status`, one of `active` or `revoked`

If `status: revoked`, the record must include `revoked_at`.

## Source-ratified OSD carry-forward

- OSD-1: v1 controller-key custody is `per_host`. Other custody modes are deferred. The per-container ephemeral controller-key candidate is future-only until Controller containerization.
- OSD-2: controller-key records live under `tenants/<tenant>/controllers/<controller-id>.key.yaml`.
- OSD-3: later lease signatures use Ed25519 over `creator-engine/worktree-lease-signature/v1` canonical UTF-8 JSON bytes with `algorithm`, `canonicalization`, `key_ref`, and unpadded base64url `value` fields. This protocol does not implement that verification.
- OSD-4: allocator pane spawn remains separate until Slice 3. This protocol does not implement allocation.

## Secret and private-key boundary

Controller-key records carry public-key metadata only.

They must not contain:

- private keys;
- secret values;
- host `GH_TOKEN` or any other credential value;
- credential broker payloads;
- worker-container authority material.

The `controller_key_schema` validator rejects common private/secret-looking fields such as `private_key`, `secret_value`, `token`, `credential`, `pem_private_key`, and `host_gh_token` with `PCO-025`.

Controller-key private keys must not enter worker containers. Worker containers do not receive Controller authority.

## Validator

The registered validator check is `controller_key_schema` and cites `PCO-025`.

Discovery rules:

- scan `.yml` and `.yaml` files;
- skip `schemas/` and `templates/` directories;
- skip atomic temp files whose basename contains `.tmp.`;
- treat only YAML mappings with `kind: controller-key-record` as candidates;
- zero controller-key records is a passing state.

Focused CLI:

```bash
creator-engine-validator scan-controller-keys <path>
```

## Non-goals

This protocol does not authorize:

- controller-key private-key generation, storage, rotation, or inspection;
- `PCO-024` lease signature verification;
- `schema_version: "2"` worktree leases;
- `pco-allocate` or `pco-release` runtime implementation;
- Docker/Podman build/run/pull/version probing;
- worker image, credential broker, egress, mount-grant, or container runtime implementation;
- Hermes runtime/profile/plugin/MCP/model-provider mutation;
- external tracker mutation;
- autonomy expansion beyond Source-ratified envelopes.
