# DISPATCH BRIEF — ce-ops#422: tenant-record schema + validator (dev-3)

- **Ticket:** ce-ops#422 (G1 of the client-tenant program, parent design ratified as ce-ops#421).
- **Branch:** `ce-422-tenant-record-schema` — branch off **freshly fetched** `origin/main`
  (git fetch origin main first; fetch failure = report BLOCKED, don't build stale).
- **Worktree:** create under `/var/tmp/wt-ce422` (NOT /workspace).
- **Role:** implementer. Task-scoped write authority only. No approval/merge/gate authority.
- **Declared work class:** story (ticket estimates S; keep the diff tight).

## Context (self-contained — do not fetch external tickets)
CE is generalizing from single-tenant (CE itself) to client-tenant deployments (first live
tenant exists). There is NO `tenant-record` kind in the repo today. The ratified design says a
tenant record must mirror the **Worker-Container Policy record discipline**: required fields,
`additionalProperties: false`, secrets as POINTERS only, schema + validator + well-formed
example + tests. Study these existing patterns and mirror them:
- `validators/creator_engine_validator/schemas/worker-container-policy.schema.yaml` (shape discipline)
- `schemas/install-answers.schema.yaml` — REUSE its `secret_ref` def shape verbatim for all
  credential pointer fields (it forbids raw secrets by construction) and mirror its
  `ratification_binding` def (~lines 601-625) for the governance ratification field.
- `examples/well-formed/worker-container-policies/*.yaml` (example placement pattern)

## Required record shape (from the ratified design §1.2 — freeze THIS, adjust names only where
existing repo conventions demand)
Top-level: `kind: tenant-record` (discriminator const), `tenant_id` (slug), `display_name`,
`status` (enum: active|onboarding|suspended|offboarded), `deployment_model` (enum: A|B|C),
`created_at` (date), plus these six required sections:
1. `identity.apps[]` — each: `app_name`, `role` (string tag), `custody_lane` (enum: own|shared),
   `app_id_ref`/`client_id_ref`/`private_key_ref` (secret POINTERS, openbao://… or
   policy-ref shape — reuse secret_ref def; NEVER raw values), optional `installation_id` (int).
2. `credential` — `openbao_mount` (dedicated mount name, required), `policy_ref`.
3. `confidentiality` — `denylist_ref` (path string), `cross_tenant_isolation` (const: enforced).
4. `issue_venue` — `kind` (enum: client-repo|ce-ops), `repo`.
5. `fleet_allocation` — `seats` (array, may be empty), `reviewer_identity`, `merging_bot`.
6. `governance` — `repo`, `protections` (enum incl. reference), `autonomy_tiers` (map of
   bool flags: docs_class_automerge, tier_a, tier_b), `ratified_by`, `ratification_ref`
   (64-hex, ratification_binding shape).
`additionalProperties: false` at every level. All fields above required unless marked optional.

## Deliverables (allowed paths — touch NOTHING else)
- `validators/creator_engine_validator/schemas/tenant-record.schema.yaml` (new)
- ONE new validator module wired the same way sibling record validators are (study how
  worker-container-policy records get validated and mirror the mechanism; keep it a pure
  fail-closed validate function + errors, no CLI group — do NOT add a new `ce` CLI group).
- `examples/well-formed/tenant-records/<fictional>.yaml` (new) — **CONFIDENTIALITY RULE: the
  committed example must be a FICTIONAL tenant (e.g. tenant_id `acme`), with plausible but fake
  App names, repo, reviewer login, and installation_id. Do NOT commit any real client/tenant
  identifier (no mythos, no real orgs/logins/ids).** The real tenant manifest is hand-authored
  out-of-repo by the controller against this schema.
- Unit tests (new test file next to sibling schema-validator tests): valid example passes;
  missing each required section fails; raw secret value (a PEM/token-looking string in a *_ref
  field) fails; unknown top-level/nested key fails (additionalProperties); bad enums fail;
  non-64-hex ratification_ref fails.
- `.ce/changelog/ce-422-tenant-record-schema.md` (REQUIRED changelog fragment)

## Standing preflight directive (ce-ops#303)
Run the FULL local validator preflight (`ce validate-pr`, CI-parity) GREEN in one pass before
commit-for-harvest; do not discover gates via CI. Venv has no activate — use
`.venv/bin/python -m pytest`.

## Evidence + stop line
- Commit on the branch, then echo `git rev-parse HEAD`.
- Signal exactly: `READY-FOR-HARVEST ce-422-tenant-record-schema <sha>`
- STOP after the signal. No push, no PR, no other tickets. Blocked >2 attempts on the same
  failure → report BLOCKED with failing output.
