# ce-egress-broker (ADR-0007 publish gateway — deterministic v0)

A **non-agent, deterministic** host-side broker that couriers a contained CE seat's *signed*
commit to the forge under fail-closed policy, attributed to the seat's **own** GitHub App. It
replaces the manual uncontained-controller courier and is the incremental path to the full
[ADR-0007](../../docs/decisions/ADR-0007-egress-gateway-publish-broker.md) egress gateway. See
the architecture map: [`docs/architecture/egress-broker.md`](../../docs/architecture/egress-broker.md).

> **Forge-egress TCB. Fail-closed: deny on any verification doubt.**

ce-ops#242 **SELF-PUSH** means the contained seat authors and signs locally, then asks the
host-side broker to publish its own branch. The seat-side request is value-free:
`ContainedSeatSelfPushRequest(seat_id, repo_path, branch)`. Raw sandbox `git push` remains
denied, and `gh` is not required or used inside the contained seat.

The host-side courier remains the transport deputy. It verifies the commit facts, obtains a
repo-scoped short-lived push/PR credential through the OpenBao / `forge.scoped_token` mint
authority, injects that credential only into trusted host child transports for git/PR work,
opens or updates the PR, revokes the credential, and writes a value-free audit record.

## Layout

```
tools/egress-broker/
  ce_egress_broker.py        # thin CLI (argparse → orchestrator.courier)
  apps.example.json          # per-App config template (dev-1/2/3/4)
  egress_broker/
    policy.py                # PURE fail-closed policy core (the TCB heart)
    commit_facts.py          # host-side %G?/author extraction (git spawn seam)
    installation.py          # installation_id discovery (GET /app/installations)
    minter.py                # generalized per-App installation-token mint + openssl signer
    config.py                # per-App + policy config schema + fail-closed loader
    audit.py                 # append-only, secret-free JSONL audit + rate counter
    orchestrator.py          # verify → mint → push → open/update PR → revoke → audit
```

The policy/verify core is unit-tested under `validators/tests/unit/test_egress_*.py` (CI-collected).

## Usage

Dry-run (the safe default — verifies + audits the plan, mints/pushes **nothing**):

```bash
python tools/egress-broker/ce_egress_broker.py \
  --seat dev-4 \
  --repo-path /home/cedev4/ce-workspaces/creator-engine \
  --branch ce-some-feature \
  --config ~/.ce-egress/broker.json
```

Apply (mint → push → open/update the attributed PR → revoke):

```bash
python tools/egress-broker/ce_egress_broker.py ... --apply
```

`--apply` is a live host boundary. This branch adds the contained-seat SELF-PUSH facade and
documentation, but does not perform a live push. The covered path remains deterministic and
fakeable: tests can inject git/gh/openssl/HTTPS seams and run with no network or real `gh`.

Exit codes: `0` allow, `2` fail-closed refusal, `3` config error. Add `--json` for machine output.

## Before a live `--apply`

1. **Host trust store** — the CE dev signing public keys must be in the broker host's gpg
   keyring / ssh `allowed_signers`. Without it every commit verifies `E`/`U` → denied (correctly).
   *This is the root of trust.*
2. **OpenBao / mint authority** — the App or scoped-token mint authority must live outside the
   sandbox. The contained seat never holds it.
3. **Repo-scoped short-lived token** — the live mint must produce only the least-privilege
   repo credential needed for push + PR (`contents:write` + `pull_requests:write`) with a short
   TTL and revocation after use.
4. **Trusted host child transports** — git and PR operations run outside the sandbox with
   credential env injection into those child processes only. The raw token must never appear in
   the contained seat env, argv, filesystem, logs, audit, returned result, or other durable
   record.
5. **Config** — copy `apps.example.json` to a host-local path; set the real App ids, the
   `authorized_logins` allow-list, and confirm `installation_id` (recorded for dev-2; `null` →
   discovered for dev-4) and the branch namespaces.

## Smoke expectations

The expected ce-ops#242 path is offline and fake-backed:

- deny paths never mint, push, or open a PR;
- dry-run verifies and audits but mints/pushes nothing;
- apply-path fakes run `verify → mint → push → open/update PR → revoke` in order;
- the credential is injected only into trusted host child transports, not the contained seat;
- audits are append-only and reject token/secret/PEM-shaped material.

## Safety invariants

- The contained seat supplies only `seat_id`, `repo_path`, and `branch`; it receives no forge
  credential and does not need `gh`.
- The App or scoped-token mint authority never enters the contained seat.
- The installation token lives only in trusted host child push/PR env + the in-memory
  `ScopedToken` (redacted repr) — never the argv, a log, the audit, disk, durable records, or
  sandbox; it is revoked in a `finally`.
- The push is **never** a force-push (fast-forward only; the frozen `forge.change_push`).
- The audit is structurally secret-free and append-only.
- Defensive only — never offensive (no history rewrite, no detection evasion, no exfiltration).
