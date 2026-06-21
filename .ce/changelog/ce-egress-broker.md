---
slug: ce-egress-broker
date: 2026-06-20
kind: added
scope: adr-0007 egress gateway / publish broker (deterministic v0)
issue: ce-ops#128
---

Added the deterministic v0 of the ADR-0007 egress gateway / publish broker: a
non-agent, host-side broker (`tools/egress-broker/`) that couriers a contained
seat's *signed* commit to the forge under fail-closed policy, attributed to the
seat's own GitHub App. It replaces the manual uncontained-controller courier and
is the incremental path to the full gateway.

The broker verifies before transmitting (fail-closed — deny on any verification
doubt): a pure policy core admits only a fully-trusted good signature
(`git %G?` == `G`; `U`/`E`/`B`/`X`/`Y`/`R`/`N` all deny), a commit author on an
allow-list of authorized CE identities (exact email or GitHub no-reply login), a
target branch in an allowed namespace and never `main`/the base/a forbidden
branch, a per-window rate cap, and a pluggable ratification/CI precondition. Only
on allow + `--apply` does it mint the seat's least-privilege App installation
token (generalizing the existing mint-forge-token pattern, with
`installation_id` discovery via `GET /app/installations` when the config does not
record one — the dev-4 case), push the branch (never force; the frozen
`forge.change_push`), open/update the PR with a "authored by <seat>,
gateway-pushed" body, and revoke the token in a `finally`. Every path — allow or
deny — appends one immutable, secret-free JSONL audit record.

Strict TDD on the verify/policy core; the App PEM never enters the broker process
(only `openssl` reads it), the installation token never reaches the argv/log/
audit/disk, and the push is fast-forward-only. The full ADR-0007 gateway
(OpenBao JIT PEM custody, the signed-artifact handoff channel, OpenShell
supervisor placement, and the contained-controller endgame) is documented as
deferred in `docs/architecture/egress-broker.md`.
