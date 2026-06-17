# Onboard Apply Protocol

Status: E2 ratified implementation carrier for ce-ops#53.

`ce onboard --apply` is the side-effecting E2 executor for the verified
agent-native installer. Default `ce onboard`, `--inventory`, and `--plan` remain
read-only/dry-run surfaces.

## Gate

Apply refuses unless the install spec follows the real signed-spec path:

- `algo: ssh-ed25519`
- `key_id: ce-root-v1`
- namespace `ce-spec-v1`
- canonical bytes from `v3_installer.canonical_spec_bytes()`
- `content_sha256` matching those same canonical bytes

The sha256 content self-attestation remains valid only for inventory and dry-run
planning. It is not accepted for host, GitHub, App, workspace, or smoke
mutation.

## State

The apply state is rooted under the configured v3 local-state root:

```text
<state_root>/onboard/apply.lock
<state_root>/onboard/ledger.ndjson
```

The lock identity includes target repo, workspace root, and the signed spec
digest. The ledger is append-only NDJSON. Entries record leg id, non-secret
verification facts, result, rollback metadata, timestamp, invocation id, and
target repo. Secret values are never recorded; SecretRefs may be recorded.

## Legs

The ratified E2 leg order is stable:

1. `signed_spec_verify`
2. `answers_merge`
3. `host_dependencies`
4. `runtime_posture`
5. `cli_exposure`
6. `github_bootstrap_token_probe`
7. `github_repo_create`
8. `github_app_install`
9. `github_workflow_install`
10. `github_branch_protection`
11. `workspace_checkout`
12. `first_project_smoke`

Later legs run only after earlier required legs verify or are already satisfied.
Greenfield repo reuse requires E2 ledger provenance plus live verification.

### Adoption legs (ce-ops#85 E3 adoption-apply, mode-gated)

For a genuine non-CE existing repo, when the dual escalation is authorized
(`CE_FORGE_LIVE_FORGE=1` + `CE_FORGE_ADOPTION_WRITE=1`) and the repo is
`adoptable`/`adoptable_after_scrub`, `onboard --apply` drives seven adoption legs
appended to `LEG_IDS` (the join-PR flow); the greenfield FORGE legs (6–12 above)
return `skipped` (`brownfield_adoption_mode`), and the early local legs (1–5) run
in both modes:

13. `brownfield_inventory_drift_check`
14. `brownfield_secret_preflight` (the hard, affirmatively fail-closed scrub)
15. `brownfield_build_scaffold`
16. `brownfield_push_branch` (never force)
17. `brownfield_open_join_pr` (exactly one PR; idempotent claim)
18. `brownfield_verify_preserved_checks`
19. `brownfield_record_apply_evidence`

In every non-adoption run these seven return `skipped` (`not_brownfield_adoption`).
Reads (13/14/18 + the clone) ride the inherited Phase-1 READ token
(`administration:read`); the writes (16/17) ride a separate WRITE token
(`contents:write`+`workflows:write` Tier-2, `pull_requests:write` Tier-3) minted
for those two legs only and revoked immediately after — `administration:write` is
never minted. With the escalation absent, an existing non-CE repo keeps the
unchanged `brownfield_deferred` / `e2_brownfield_seam_unavailable` refuse. See
`docs/contracts/brownfield-adoption.md` for the full join-PR contract.

The live scrub in leg 14 runs only with runtime sha256-pinned scanner configuration:
`CE_FORGE_GITLEAKS_URL` + `CE_FORGE_GITLEAKS_SHA256` and
`CE_FORGE_TRUFFLEHOG_URL` + `CE_FORGE_TRUFFLEHOG_SHA256`. Missing, partial, or
invalid pins are not clean; they keep the leg fail-closed until the VPS Mode-A host
supplies the verified scanner pins.

With pins supplied, leg 14 scans the full mutation surface declared by the plan:
`[".", *scaffold_paths]`. The driver copies the existing checkout to a temporary
scan tree, overlays every scaffold artifact there, runs the scanners over that
materialized tree, and removes it before leg 15 can build/push/open the join PR.

The `github_bootstrap_token_probe` requirement is **right-sized to the operation**
(ce-ops#94): a **plain-join** (joining an already-CE repo) requires only a valid
identity distinct from the App bot — the PAT writes nothing (forge ops ride the
App's JIT token; protection is verify-only) — while a **greenfield** create
requires `contents/administration/actions/workflows:write` (+ org repo-create
when new-in-org). **Fine-grained PATs are accepted** (GitHub's recommended
default): they emit no `X-OAuth-Scopes` and expose no permission introspection,
so for greenfield their write-capability is enforced **fail-closed at the write
legs** (each refuses on a 403). An invalid token refuses as
`bootstrap_token_invalid`; an unrecognized/unverifiable token type as
`bootstrap_token_unverifiable`; a classic token missing greenfield scopes as
`bootstrap_token_scope_refused`.

## Summary Counters

The JSON action is `onboard_apply`. Top-level counters are derived from actual
leg outcomes: `applied`, `already_satisfied`, `verified_count`, `skipped`,
`refused`, `failed`, `rolled_back`, `manual_rollback_required`,
`greenfield_repos_created`, `repos_already_satisfied`, and
`brownfield_deferred`. The adoption-apply counters (ce-ops#85) are
`brownfield_adopted` (a join PR opened **or** idempotently claimed **and verified**
this run — the one counter rule), `brownfield_adoption_pr`
(`{repo,branch,base,pr_number,head_sha,plan_ref}` when opened, else `null`),
`brownfield_scrub_findings`, `brownfield_scrub_findings_waived`, and
`brownfield_scrub_findings_blocking`.

A planned action is not counted as applied — `brownfield_adopted` is never
incremented on a planned-but-unpushed branch or an unverified PR. A failed
verification makes the leg failed even when the mutation API returned success. Manual rollback is explicit
for package installs, App authorization, remote repo deletion, or any cleanup
that cannot be proven safe.

## Test Carrier

The E2 test carrier covers the ratified 18-case plan through focused unit and
integration tests with fake transports/runners. CI must not depend on live
GitHub, sudo, gVisor installation, or a real App authorization click.

Current per-gate baseline:

- `wheel_source_parity`: expected red for this E2 commit because the ratified
  night mandate rebuilds the source/wheel pair once at branch end under the E1
  manifest leg. This baseline is named in the local commit and must clear before
  the union branch merges.
