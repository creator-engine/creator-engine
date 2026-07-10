# Materializer App-Key Custody Runbook

## Purpose And Scope

This runbook governs the lifecycle of the GitHub App private key that the armed
materializer uses to mint short-lived installation tokens for direct pushes to
`main`. It applies the credential-delivery and lease-topology decisions in
`docs/decisions/ADR-0015-materializer-arming-credential-lease.md`.

## Credential Lifecycle

Storage is OpenBao KV v2 at the path declared by the daemon environment file
through `CE_MATERIALIZER_KEY_VAULT_PATH`. The environment file holds the vault
address and mount/path reference, never the key value. `MaterializerConfig`
carries `private_key_env` only as an environment-variable name that resolves to
the vault-path reference.

The daemon performs a per-call fetch at signing time. It does not write the key
to a file, log it, expose it to workers, or retain it between calls. On
rotation, `ce-operator` replaces the key in OpenBao; the daemon reads the new
value on its next signing call and requires no restart. On revocation,
`ce-operator` revokes the App installation token and the OpenBao secret version;
the daemon enters HELD on the next signing attempt and pages.

Only `ce-operator` may use break-glass through the approved secret channel in
`docs/devops/openbao-operator-bringup.md`. No agent or worker role may access a
raw PEM.

## Authority Matrix

| Role | Authority |
| --- | --- |
| `ce-operator` | Store, rotate, revoke, and perform break-glass recovery. |
| `ce-materializer-architect` | Design and review lease and credential changes. |
| `ce-release-signer` | Provide the required release-signing authority artifact; this role has no private-key custody. |
| Materializer daemon role | Read the vault-path reference from its environment and request a per-call fetch only. |

Worker roles, including `ce-implementer` and `ce-reviewer`, never hold, touch,
or reference the App private key or its vault-path value. The key never appears
in pull requests, transcripts, prompts, or changelog fragments.

## Non-Authorities

Workers never sign. The daemon never holds the key across calls. No tracked
file contains a seat identity, host name, or key value. `private_key_env`
carries an environment-variable name only, never a resolved value.

## Failure And Recovery

A vault read error becomes a signer error and HELD state for the affected
intent, with a 30-minute closeout window before hard failure. Follow
`docs/design/ce-491-optiona-merge-intent.md` for that lifecycle. To recover,
`ce-operator` resolves vault access and clears HELD through the materializer's
documented recovery path.

For a `DaemonLeaseStale` or `DaemonLeaseHeld` conflict, follow the canonical
procedure in `playbooks/controller/runbooks/conveyor-daemon-stuck-lease.md`.
A broken ledger hash chain is an Operator-only recovery. The local lease is
authoritative only for the current single-host deployment; revisit the topology
before any second host or materializer instance gains brain-append capability.

## ADR-0015 Decision References

Source: `docs/decisions/ADR-0015-materializer-arming-credential-lease.md`

> Decision: use OpenBao-backed short-TTL issuance for the dedicated materializer
> App credential. The App private key must never be written to worker disk or
> placed in worker-visible logs, prompts, argv, repository files, comments, or
> evidence artifacts. The delivery mechanism is per-call fetch via the
> vault_signer pattern already shipped for the egress broker ([vault-signer-impl]):
> per-call OpenBao KV v2 read at the per-app private-key path → /dev/fd pipe to
> openssl signing subprocess → JWT; the PEM is zeroed from memory after signing
> and never written to disk or passed through any worker-visible env var or argv.
> The materializer App private-key path follows the per-app family established in
> the OpenBao secret-path map ([openbao-path-map]):
> `ce-kv/forge/github-apps/<app-name>/private-key`; the concrete materializer-app
> path is specified in the arming runbook (slice (c)), not in this ADR.

> Decision: for the current single-host, strict singleton merge-gate daemon
> topology, use MaterializerLease wrapping daemon_lease.acquire("brain-append",
> ...) in `validators/creator_engine_validator/brain_intent_materializer.py`
> ([materializer-impl]) as the active exclusion mechanism for the `brain-append`
> component. This local file lease is authoritative for the current single-host
> topology. The revisit trigger is any second host or instance gaining
> brain-append capability.
