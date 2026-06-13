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
Arbitrary existing repos are refused as `brownfield_deferred`; E3 owns adoption.

## Summary Counters

The JSON action is `onboard_apply`. Top-level counters are derived from actual
leg outcomes: `applied`, `already_satisfied`, `verified_count`, `skipped`,
`refused`, `failed`, `rolled_back`, `manual_rollback_required`,
`greenfield_repos_created`, `repos_already_satisfied`, and
`brownfield_deferred`.

A planned action is not counted as applied. A failed verification makes the leg
failed even when the mutation API returned success. Manual rollback is explicit
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
