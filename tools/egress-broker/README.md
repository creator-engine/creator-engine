# ce-egress-broker (ADR-0007 publish gateway — deterministic v0)

A **non-agent, deterministic** host-side broker that couriers a contained CE seat's *signed*
commit to the forge under fail-closed policy, attributed to the seat's **own** GitHub App. It
replaces the manual uncontained-controller courier and is the incremental path to the full
[ADR-0007](../../docs/decisions/ADR-0007-egress-gateway-publish-broker.md) egress gateway. See
the architecture map: [`docs/architecture/egress-broker.md`](../../docs/architecture/egress-broker.md).

> **Forge-egress TCB. Fail-closed: deny on any verification doubt.**

ce-ops#242 **SELF-PUSH** means the contained seat authors and signs locally, then asks the
host-side broker to publish its own branch. The live seat-side protocol is value-free:
`{"seat_id":"dev-4","branch":"ce242-..."}` over a per-seat Unix socket. A legacy
`repo_path` field may be present for compatibility, but the daemon ignores it and uses the
trusted host repo path supplied to the daemon. Raw sandbox `git push` remains denied, and
`gh` is not required or used inside the contained seat.

The host-side courier remains the transport deputy. It verifies the commit facts, obtains a
repo-scoped short-lived push/PR credential through the OpenBao / `forge.scoped_token` mint
authority, injects that credential only into trusted host child transports for git/PR work,
opens or updates the PR, revokes the credential, and writes a value-free audit record.

## Layout

```
tools/egress-broker/
  ce_egress_broker.py        # thin CLI (argparse → orchestrator.courier)
  ce_egress_self_review_broker.py # host Unix-socket PR review broker
  apps.example.json          # per-App config template (dev-1/2/3/4)
  egress_broker/
    policy.py                # PURE fail-closed policy core (the TCB heart)
    commit_facts.py          # host-side %G?/author extraction (git spawn seam)
    installation.py          # installation_id discovery (GET /app/installations)
    minter.py                # generalized per-App installation-token mint + openssl signer
    config.py                # per-App + policy config schema + fail-closed loader
    audit.py                 # append-only, secret-free JSONL audit + rate counter
    orchestrator.py          # verify → mint → push → open/update PR → revoke → audit
    host_broker.py           # contained SELF-PUSH request handler + Unix-socket daemon seam
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

Run the contained SELF-PUSH host daemon for one seat:

```bash
install -d -m 0700 /run/user/$UID/creator-engine/egress-broker
python tools/egress-broker/ce_egress_self_push_broker.py \
  --seat dev-4 \
  --socket /run/user/$UID/creator-engine/egress-broker/dev-4.sock \
  --expected-peer-uid "$CONTAINED_SEAT_UID" \
  --expected-peer-gid "$CONTAINED_SEAT_GID" \
  --host-repo-path /home/cedev4/ce-workspaces/creator-engine \
  --config ~/.ce-egress/broker.json
```

The socket should be owned by the seat UID/GID and mode `0600` or `0660`
(depending on whether a seat group is used). The daemon binds one broker seat id to one socket
and always calls `contained_seat_self_push(..., apply=True)` with the configured host repo path.
It requires explicit `--expected-peer-uid` and `--expected-peer-gid` values and rejects
unexpected Unix-socket peers through `SO_PEERCRED` before request parsing; those peercred
decisions remain secret-free audit records. It rejects request fields such as `command`,
`remote`, `refspec`, `token`, `pem_path`, and `config_path`; a request `apply` field is
ignored. The seat cannot select a command, target remote, credential, host config, or
dry-run/apply mode.

That one-socket-per-seat binding is load-bearing for JIT credentials too: the active credential
registry is process-local, so cross-process single-active behavior assumes exactly one live
broker process owns the seat socket. Deployments must not start a second broker against the
same seat/socket path; the bind-time existing-socket refusal and systemd single socket unit are
part of the safety boundary.

Host seam spec:

- Transport: host-owned AF_UNIX stream socket, one JSON line per connection.
- Request: `{"seat_id":"dev-4","branch":"ce-ops-242-smoke"}`. Compatibility
  `repo_path` may be present but is ignored in favor of `--host-repo-path`.
- Response: one secret-free JSON line with status and value facts only.
- Live behavior: the daemon calls `contained_seat_self_push(..., apply=True)`;
  there is no seat-controlled apply flag.
- Ownership boundary: one daemon process binds one broker seat id to one socket.

Live apply smoke template from a contained seat:

```bash
# Host: start the daemon with the real host trust/config/mint seams.
python tools/egress-broker/ce_egress_self_push_broker.py \
  --seat dev-4 \
  --socket /run/user/$UID/creator-engine/egress-broker/dev-4.sock \
  --expected-peer-uid "$CONTAINED_SEAT_UID" \
  --expected-peer-gid "$CONTAINED_SEAT_GID" \
  --host-repo-path /home/cedev4/ce-workspaces/creator-engine \
  --config ~/.ce-egress/broker.json

# Contained seat: send only values over CE_EGRESS_BROKER_SOCKET.
python3 - <<'PY'
import json
import os
import socket

req = {"seat_id": os.environ["CE_SEAT_ID"], "branch": "ce-ops-242-smoke"}
with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as sock:
    sock.connect(os.environ["CE_EGRESS_BROKER_SOCKET"])
    sock.sendall((json.dumps(req, separators=(",", ":")) + "\n").encode())
    print(sock.recv(65536).decode(), end="")
PY
```

Contained-seat canary script:

```bash
python3 tools/egress-broker/ce_self_push_canary.py \
  --branch "$(git rev-parse --abbrev-ref HEAD)" \
  --require-noop
```

The canary uses `CE_SEAT_ID` and `CE_EGRESS_BROKER_SOCKET` by default. It sends the same
value-only request as the template above, requires an applied broker response, and fails loudly
on stale socket mounts (`ECONNREFUSED`), broker refusals, or non-no-op responses when
`--require-noop` is set. VPS contained seats should mount the broker socket directory, not the
socket inode, so a daemon restart does not strand the container on a stale Unix socket.

The zero-credential contained environment cannot run
`tools/egress-broker/ce_egress_broker.py --apply` directly. A direct `--apply`
smoke is host-only and requires the host config, trust store, App PEM, mint
authority, and trusted child transports:

```bash
python tools/egress-broker/ce_egress_broker.py \
  --seat dev-4 \
  --repo-path /home/cedev4/ce-workspaces/creator-engine \
  --branch ce-ops-242-smoke \
  --config ~/.ce-egress/broker.json \
  --apply
```

## JIT Seat Credential Socket Verb (ce-ops#228)

The host broker accepts value-only JSON socket requests for short-lived seat credentials:

```json
{"verb":"mint-seat-credential","seat_id":"dev-3","credential_class":"forge-scoped"}
```

and explicit revocation:

```json
{"verb":"revoke-seat-credential","seat_id":"dev-3","credential_class":"forge-scoped"}
```

Credential classes are fail-closed and per-seat allowlisted with
`allowed_credential_classes`. v1 classes are `model-api` and `forge-scoped`. The response
delivers the credential value only on the broker Unix stream; the broker does not create a
container env, argv, Docker `-e`, Docker exec env, or persisted container-config delivery
path. Every mint/refusal/revoke appends a secret-free audit line, and the broker keeps only
one active credential per seat/class in the live broker process, with active TTL sweep,
lazy expiry on subsequent requests, and explicit revoke support. For `forge-scoped`, the
GitHub installation token lifetime remains about one hour at the API unless upstream revocation
succeeds; the 300s TTL is the broker's bookkeeping and active-revocation deadline.
The daemon refuses to start unless expected peer UID/GID values are supplied, and a peercred
mismatch is rejected before a credential mint/revoke request can return any credential value.

## Contained-seat self-review broker (ce-ops#243)

This repository does not currently contain a separate `ce_egress_self_push_broker.py`; the
self-review daemon mirrors the closest existing host-side egress-broker pattern:
`ce_egress_broker.py` plus the `egress_broker` config/minter seams. It runs outside the sandbox,
listens on a Unix socket, accepts one bounded JSON request per connection, and submits only
`COMMENT` or `REQUEST_CHANGES` PR reviews through `gh api`.

Host daemon command:

```bash
python tools/egress-broker/ce_egress_self_review_broker.py \
  --serve \
  --socket "${XDG_RUNTIME_DIR:-/tmp}/ce-egress-self-review.sock" \
  --config ~/.ce-egress/broker.json \
  --verbose
```

The contained-seat request is value-only:

```json
{"seat_id":"seat-reviewer-1","pr_number":123,"head_sha":"<40-hex-head>","event":"COMMENT","body":"Review note."}
```

The host broker refuses `APPROVE` before config lookup, installation discovery, token minting,
or any source-host call. For allowed `COMMENT` / `REQUEST_CHANGES`, it resolves the seat App,
mints a short-lived repo-scoped token with `metadata:read` + `pull_requests:write`, and injects
the token only into the trusted host child `gh api` environment. The token is never placed in
argv, stdin, socket responses, durable request metadata, or logs.

Opt-in live COMMENT smoke against a running daemon:

```bash
python tools/egress-broker/ce_egress_self_review_broker.py \
  --send-comment \
  --socket "${XDG_RUNTIME_DIR:-/tmp}/ce-egress-self-review.sock" \
  --seat seat-reviewer-1 \
  --pr-number 123 \
  --head-sha "<40-hex-head>" \
  --body "ce-ops#243 live smoke: brokered COMMENT review."
```

The smoke command is intentionally non-default and requires an existing throwaway PR head SHA.

The host broker also enforces the **author≠reviewer** invariant: before minting any credential or
making any source-host call, it resolves the PR author host-side (`gh api repos/{repo}/pulls/{pr}`)
and refuses if the requesting seat is the PR's own author — for any event, fail-closed if the
author cannot be resolved. This mirrors the existing `forge/plan_approval.py` /
`forge/review_pickup.py` non-author guard.

## Contained-seat forge read broker (ce-ops#475)

The forge read lane adds host-side read-only verbs for contained seats that cannot carry `gh`,
`curl`, or forge credentials in the sandbox:

```bash
python tools/egress-broker/ce_egress_forge_read_broker.py \
  --config ~/.ce-egress/broker.json \
  --seat dev-4 \
  get-issue creator-engine/creator-engine 475
```

Supported verbs are:

```text
get-issue <repo> <number>
get-pr <repo> <number>
list-comments <repo> <number>
```

Each request carries only values: seat id, verb, repo, and issue/PR number. The host broker
resolves the configured seat App, enforces the broker policy's per-seat rate window against
`forge_read` audit records, mints a short-lived installation token with read-only permissions
(`metadata:read`, `issues:read`, `pull_requests:read`), injects that token only into the trusted
host child `gh api` environment, revokes it, and returns JSON containing the response body plus
metadata. The contained seat never receives the credential and cannot request HTTP methods,
payloads, permissions, or write-shaped operations through these verbs.

Every read attempt appends a secret-free `forge_read` audit line, including refusals. The record
includes `seat_id`, `repo`, `resource`, `verb`, decision, and timestamp fields.

Deferred seams:

- `kind:own` solo parity is intentionally not routed in this slice; the request shape is
  mode-neutral so a later slice can add that lane without changing the contained-seat read verbs.
- Governed `web-fetch` is out of scope for this slice and must use a separate policy and audit
  surface.

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
6. **Host path binding** — start the self-push daemon with the trusted host repo path. Do not
   trust a repo path supplied by the contained seat; compatibility `repo_path` requests are
   translated to the daemon's host path.

## Smoke expectations

The expected ce-ops#242 path is offline and fake-backed:

- deny paths never mint, push, or open a PR;
- dry-run verifies and audits but mints/pushes nothing;
- apply-path fakes run `verify → mint → push → open/update PR → revoke` in order;
- the credential is injected only into trusted host child transports, not the contained seat;
- audits are append-only and reject token/secret/PEM-shaped material.

## Safety invariants

- The contained seat supplies only `seat_id` and `branch`; it receives no forge credential and
  does not need `gh`. A compatibility `repo_path` field is ignored by the host daemon.
- The App or scoped-token mint authority never enters the contained seat.
- The host broker config (`~/.ce-egress/broker.json`), App PEMs under `/dev/shm/ce-devN`, host
  trust store, OpenBao/mint authority, SSH agent, Docker socket, and any GitHub/OpenBao tokens
  stay host-side and are not bind-mounted or passed as container environment.
- The installation token lives only in trusted host child push/PR env + the in-memory
  `ScopedToken` (redacted repr) — never the argv, a log, the audit, disk, durable records, or
  sandbox; it is revoked in a `finally`.
- The push is **never** a force-push (fast-forward only; the frozen `forge.change_push`).
- The audit is structurally secret-free and append-only.
- Defensive only — never offensive (no history rewrite, no detection evasion, no exfiltration).
