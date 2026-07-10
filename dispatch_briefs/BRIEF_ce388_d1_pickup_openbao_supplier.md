# BRIEF — ce-388-d1-pickup-openbao-supplier — review-pickup OpenBao token wiring, slice D1

Role: implementer (dev-3, contained). Branch: `ce-388-d1-pickup-openbao-supplier` off
freshly-fetched origin/main. Worktree under /var/tmp. venv: `.venv/bin/python -m pytest`,
PYTHONPATH=validators, TMPDIR=/var/tmp.

## PRECONDITION (hard gate — this unit is serialized behind the queue-daemon lease merge)
`git fetch origin main` FIRST and verify v3_cli.py at your branch tip contains the queue-daemon
startup-lease code (e.g. `grep -n "_defer_to_supervisor_lease\|_acquire_queue_daemon_lease"
validators/creator_engine_validator/v3_cli.py` — both must hit). If absent, your fetch is stale or
the gate PR has not merged: signal `BLOCKED ce-388-d1-pickup-openbao-supplier precondition-unmet`
and STOP.

## Why (embedded — you cannot read tickets)
review-pickup needs the ce-dev-2 GH PAT. Today: CE_PICKUP_TOKEN env → PAT file → ambient gh
(pickup_search.resolve_token), resolved ONCE at startup and static for the daemon lifetime; raw
PAT at rest is what we're eliminating. The approval-wall's secret machinery is fully GENERIC
(SecretRef/SecretRequest/OpenBaoSecretIdentityBackend in secret_identity.py + the
issue→materialize(tmpfs)→read→revoke supplier pattern in forge/approval_capability.py
`approval_wall_secret_supplier_from_secret_identity_backend`) — reuse it, don't reinvent.

## Deliverables (D1, story)
1. Constants in secret_identity.py for review-pickup token ref defaults: path
   `forge/ce-dev-2/gh-token`, field `token`, purpose `review-pickup-token`, owner_ref
   `controller:reviewer`, ttl 300.
2. New flag family on the review-pickup CLI in v3_cli.py:
   `--pickup-token-secret-{backend,mount,path,field,version,purpose,owner-ref,ref-policy-sha,target-ref,run-id,seat-id,ttl-seconds}`
   mirroring the existing `--approval-wall-secret-*` parse helper pattern. target-ref MUST be
   `file:` — reject `env:` with a clear error (fork-unsafe). Plus
   `--pickup-token-max-consecutive-failures` (default 10).
3. New v3_cli helper `_review_pickup_token_supplier_from_args()` mirroring the wall's supplier
   construction (~75 LOC). Returns None when the flag family is unconfigured → the existing
   static-token path is preserved BYTE-FOR-BYTE (this is the compat bar).
4. `run_review_pickup_loop()` (forge/review_pickup.py) gains `token_supplier` and
   `gh_runner_factory` params (default None): when set, EACH pass calls supplier() (fresh
   grant→tmpfs→read→revoke) and rebuilds the gh runner; supplier failure or PickupError →
   structured log + incomplete pass + sleep + retry (today a bare PickupError exits the daemon —
   that changes ONLY when a supplier is configured); after N consecutive failures exit nonzero so
   systemd Restart takes over (no silent-stuck daemon).

Deployment facts (context only; do NOT hardcode secrets): the vault path/policy already exist;
policy sha `ab4769424e205eb53ee31d61da0c386ae9a418682e9bc0a6636f82de708c8982` will be supplied via
flag at deployment. Unit/env docs + full test suite are slice D2 (separate unit) — if the
test-coupling gate demands test changes for the touched modules, add minimal behavioral smoke
tests (supplier-unconfigured → None; env: target-ref rejected) and note D2 owns the full suite.

## Constraints
- Files (closed set): validators/creator_engine_validator/secret_identity.py · v3_cli.py ·
  validators/creator_engine_validator/forge/review_pickup.py · (minimal smoke-test file if the
  coupling gate requires, named in carrier) · .ce/changelog/ce-388-d1-pickup-openbao-supplier.md ·
  .ce/pr-manifests/ce-388-d1-pickup-openbao-supplier.md. Anything else → BLOCKED, don't widen.
- Do NOT touch the queue-daemon lease code, approval-wall flags/behavior, pickup_search.resolve_token
  semantics for the unconfigured path, or any deploy/ file.
- ⛔ Signed-artifact stop-line: any signed-artifact gate failure → STOP and report; never sign.

## Preflight + known container env gaps (standing)
FULL `ce validate-pr`; if the ONLY failures are the known env-gap gates (install-spec ssh-keygen,
PCO-024 libsodium/examples) AND all touched-module tests pass, commit and signal with the
preflight note. Any other failure → fix or BLOCKED.

## Evidence + signal (no push auth — controller harvests)
Commit `review-pickup: per-pass OpenBao token supplier (flags, loop refresh, bounded retry)`, emit
`READY-FOR-HARVEST ce-388-d1-pickup-openbao-supplier <40-hex sha>` (+ ` PREFLIGHT-NOTE envgap:<gates>`
if applicable). Work class: story.

## Stop line
No push, no PR, no review, no signing. Controller harvests on signal.
