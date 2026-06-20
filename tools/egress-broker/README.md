# ce-egress-broker (ADR-0007 publish gateway — deterministic v0)

A **non-agent, deterministic** host-side broker that couriers a contained CE seat's *signed*
commit to the forge under fail-closed policy, attributed to the seat's **own** GitHub App. It
replaces the manual uncontained-controller courier and is the incremental path to the full
[ADR-0007](../../docs/decisions/ADR-0007-egress-gateway-publish-broker.md) egress gateway. See
the architecture map: [`docs/architecture/egress-broker.md`](../../docs/architecture/egress-broker.md).

> **Forge-egress TCB. Fail-closed: deny on any verification doubt.**

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

Exit codes: `0` allow, `2` fail-closed refusal, `3` config error. Add `--json` for machine output.

## Before a live `--apply`

1. **Host trust store** — the CE dev signing public keys must be in the broker host's gpg
   keyring / ssh `allowed_signers`. Without it every commit verifies `E`/`U` → denied (correctly).
   *This is the root of trust.*
2. **PEM custody** — each seat's App PEM RAM-only (`/dev/shm/ce-devN/…`), readable by the broker
   host user, invisible to the agent container. The broker process never reads the PEM — only
   `openssl` does, at sign time.
3. **Config** — copy `apps.example.json` to a host-local path; set the real App ids, the
   `authorized_logins` allow-list, and confirm `installation_id` (recorded for dev-2; `null` →
   discovered for dev-4) and the branch namespaces.

## Safety invariants

- The App **PEM never enters the broker process** (only `openssl dgst -sha256 -sign` reads it).
- The installation token lives only in the child push/PR env + the in-memory `ScopedToken`
  (redacted repr) — never the argv, a log, the audit, or disk; it is revoked in a `finally`.
- The push is **never** a force-push (fast-forward only; the frozen `forge.change_push`).
- The audit is structurally secret-free and append-only.
- Defensive only — never offensive (no history rewrite, no detection evasion, no exfiltration).
