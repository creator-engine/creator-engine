# Egress broker — deterministic v0 of the ADR-0007 publish gateway

> Status: **v0 (deterministic, non-agent) — built, locally green, not yet wired live.**
> Maps to [`ADR-0007`](../decisions/ADR-0007-egress-gateway-publish-broker.md).
> Code: [`tools/egress-broker/`](../../tools/egress-broker/). Forge-egress TCB — **fail-closed.**

## Why this exists

A contained seat authors + **signs** a commit on a local branch but **cannot raw-push** — it
holds no forge egress, by design (`ce-mandatory-containment-decision`,
`ce-governed-seat-cannot-push`). ce-ops#242 calls this **SELF-PUSH**: the seat requests
publication of its own branch by sending only value-free request facts
(`seat_id`, `repo_path`, `branch`) through `ContainedSeatSelfPushRequest`. Direct `git push`
from the sandbox remains denied, and the contained seat does not need `gh`.

ADR-0007 chose, as the endgame, a **non-agent deterministic gateway** as the sole holder of
forge egress — trustable with the push credential precisely *because it cannot be talked into
misusing it*, where an LLM agent cannot.

This v0 is the **incremental, build-now path** to that gateway: a deterministic host-side
broker that couriers a contained seat's signed commit to the forge under fail-closed policy,
attributed to the seat's **own** GitHub App. It replaces the manual courier with an auditable,
policy-gated, deterministic enforcer.

## What v0 does (the flow)

Given `{seat_id, repo_path, branch}` and a host-local config, the broker
([`orchestrator.courier`](../../tools/egress-broker/egress_broker/orchestrator.py)) runs:

1. **Read the seat's head-commit facts host-side.** The seat's branch is reachable via its
   bind-mount (dev-4: `/home/cedev4/ce-workspaces/creator-engine` ↔ container
   `/workspace/creator-engine`). [`commit_facts`](../../tools/egress-broker/egress_broker/commit_facts.py)
   resolves `refs/heads/<branch>` and extracts the value-free facts: head sha, `git`'s `%G?`
   signature verdict, the `%GS` signer, and the `%an`/`%ae` author.
2. **Verify (fail-closed) — the pure policy core.**
   [`policy.evaluate`](../../tools/egress-broker/egress_broker/policy.py) is the TCB heart: a
   pure, zero-I/O decision over the four ADR-0007 gates plus a rate/precondition guard:
   - **signature valid** — ONLY a fully-trusted good signature (`%G?` == `G`) passes. Every
     other code denies: `B` bad, `U` good-but-**unknown-validity** (key not in the host trust
     store), `X`/`Y`/`R` expired/revoked, `E` cannot-check, `N` none. *Good-but-untrusted is a
     verification doubt, and a doubt is a denial.*
   - **author authorized** — the commit author is on an allow-list of authorized CE identities
     (by exact email OR by the GitHub `<id>+<login>@users.noreply.github.com` login).
   - **branch never main** — the target is never `main`/`master`, the base branch, or any
     forbidden branch (absolute — overrides a matching namespace).
   - **allowed namespace** — the well-formed branch matches an allowed namespace prefix.
   - **rate/scope** — recent pushes for the seat are under the per-window cap.
   - **pluggable ratification/CI precondition** — each supplied precondition must be satisfied.
3. **Mint a repo-scoped push/PR credential host-side.** The live SELF-PUSH seam requires
   OpenBao or the scoped-token mint authority outside the sandbox. The generalized minter
   ([`minter`](../../tools/egress-broker/egress_broker/minter.py)) preserves the App-JWT seam
   and discovers the `installation_id` via `GET /app/installations`
   ([`installation`](../../tools/egress-broker/egress_broker/installation.py)) when config does
   not record one. The resulting capability is least-privilege (`contents:write` +
   `pull_requests:write`), repo-scoped, short-lived, and revocable.
4. **Inject only into trusted host child transports.** The credential is not handed to the
   contained seat and is not available to raw sandbox `git push`. It is injected only into
   host-side trusted push and PR child environments: the frozen `forge.change_push` push leg
   (constructed HTTPS remote, **never force**, fast-forward only) and the PR open/update leg.
   The PR body notes *"Authored by `<seat>`, gateway-pushed"*. Authorship travels with the
   **signed commit**; the broker is the transport, not the author. The credential is **revoked
   in a `finally`**.
5. **Audit (append-only).** Every path — allow OR deny — appends one immutable JSONL record
   ([`audit`](../../tools/egress-broker/egress_broker/audit.py)): seat, commit sha, author +
   signer, the verified checks + failing reasons, which App owner/installation couriered it, the
   push/PR result, and a timestamp. The audit is structurally **secret-free** (it refuses any
   token/secret/PEM-shaped material) and feeds the rate guard.

`--apply` is opt-in: without it the broker is a **dry-run** that verifies + audits the plan but
mints/pushes nothing (the safe default).

## Where the trust sits (the TCB split)

The broker's trusted computing base is small and **wholly deterministic** — no LLM on the path:

- **Cryptographic verification → `git`.** Signature validity is `git`'s `%G?` verdict against
  the host's own trust store (gpg keyring / ssh `allowed_signers`). The broker passes that
  verdict through; the host trust config is the root of trust the controller must provision.
- **Policy → `egress_broker.policy`.** A pure, exhaustively-tested function. Deny on any doubt.
- **Secret custody → OpenBao + frozen forge seams.** The host seam holds the trust store and
  mint authority. The raw token lives only in trusted host child push/PR env injection and the
  in-memory `ScopedToken` (redacted repr) — never the contained seat env, argv, filesystem,
  logs, audit, returned result, or other durable record.

This is the **network-egress twin** of the OpenBao secret broker (ce-ops#135): the secret broker
stops agents *holding* secrets; this gateway stops agents *reaching* the forge.

## Smoke path and live boundary

Expected smoke coverage for ce-ops#242 is offline and fake-backed:

- deny paths never mint, push, or open a PR;
- dry-run verifies and audits but mints/pushes nothing;
- apply-path fakes run `verify → mint → push → open/update PR → revoke` in order;
- the trusted child transport receives the credential only through env injection;
- audit records stay value-free and reject token/secret/PEM-shaped material.

This branch does **not** claim a live push was performed. A live `--apply` remains a host-side
operator boundary requiring the real trust store, OpenBao/scoped-token wiring, forge App grant,
network egress, and a ratified invocation outside the contained sandbox.

## What the controller must wire to run it live

This v0 is code-complete and locally green, but **not yet wired**. To run a live `--apply`:

1. **Host trust store** — the CE dev signing public keys must be in the broker host's gpg
   keyring / ssh `allowed_signers`, or every commit verifies as `E`/`U` and is (correctly)
   denied. *This is the root of trust; nothing else matters until it is set.*
2. **OpenBao / scoped-token mint authority** — the App or token mint authority must be held
   outside the sandbox and issue only repo-scoped, short-lived push/PR credentials.
3. **Host git/PR child env injection** — the raw token must be injected only into trusted
   host-side git/PR children. It must not be present in the contained seat env, argv,
   filesystem, logs, audit, returned result, or durable record.
4. **Installation ids** — fill `installation_id` for seats whose env records one (dev-2); leave
   `null` for discovery (dev-4).
5. **Config** — copy [`apps.example.json`](../../tools/egress-broker/apps.example.json) to a
   host-local path, set the real App ids and the `authorized_logins` allow-list, and confirm the
   `allowed_branch_namespaces` / `forbidden_branches` for your repo.
6. **(Optional) precondition hook** — wire a real ratification/CI precondition (e.g. CI-green +
   a ratification record) into the pluggable hook as the gateway matures.

## Deferred to the full ADR-0007 gateway (NOT in v0)

| Concern | v0 (this) | Full gateway (deferred) |
| --- | --- | --- |
| Credential custody | OpenBao/scoped-token injection for trusted host push/PR children | richer OpenBao lease metadata and gateway-local revocation evidence |
| Signed-artifact handoff | host reads the seat's bind-mounted branch directly | a **controlled handoff channel** (branch + SHA / commit object signalled to the gateway) |
| Runtime placement | a host-side CLI run by the (still-uncontained) controller | the **OpenShell supervisor/gateway** layer; the controller itself contained (ce-ops#128) |
| Merge | out of scope (push + PR only) | the **same shape**, actuated only on ratification + peer review + green CI |
| Ratification/CI gate | a pluggable hook (default: none) | a wired, mandatory precondition bound to the ratification record |
| Rate/scope | per-window push cap from the local audit | gateway-level quotas + richer scope policy |
| Pagination/multi-account discovery | one page of `/app/installations` | full pagination + multi-account disambiguation |

Until those land, the **uncontained dev-2 courier remains the honest stopgap** (ADR-0007
trade-off), and this broker is the deterministic component that replaces the *manual* step of it.

## Defensive posture

Defensive only — it couriers our own governed seat's signed, reviewed work through our own forge
under policy. It **never** force-pushes, rewrites history, evades detection, or exfiltrates a
credential. On any verification doubt it denies, audits, and exits non-zero.
