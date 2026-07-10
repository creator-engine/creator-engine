# N-D design SSOT — review-pickup OpenBao token wiring (architect brief, 2026-07-04 ~21:15Z)
> Controller-banked from the architect_research worker (task a785206e01ae761d3 transcript has the
> full version with all file:line anchors). A2 precondition 2; ratified night-arc lane N-D.

## Problem + current state
review-pickup needs the ce-dev-2 GH PAT (Search API Bearer + GH_TOKEN for gh runner). Today:
CE_PICKUP_TOKEN env → ~/.ce-keys/ce-dev-2.pat file → opt-in ambient gh (pickup_search.resolve_token,
pickup_search.py:243-284). Token is resolved ONCE at startup (v3_cli.py:5114) and static for the
daemon lifetime. Raw PAT at rest on host = the thing we're eliminating.

## Key finding: the wall's secret machinery is GENERIC
SecretRef/SecretRequest/SecretIdentityBackend + OpenBaoSecretIdentityBackend + get_backend registry
(secret_identity.py) and approval_wall_secret_supplier_from_secret_identity_backend
(forge/approval_capability.py:252-286 — issue→materialize(tmpfs)→read→revoke-in-finally) carry NO
approval-wall semantics. Reuse = new arg-parse helper + new flag family + new default constants.
Controller-key refusal (_ref_names_controller_key) is client-side enforced already.

## Design (condensed)
- New flag family on review-pickup: `--pickup-token-secret-{backend,mount,path,field,version,
  purpose,owner-ref,ref-policy-sha,target-ref,run-id,seat-id,ttl-seconds}`; defaults path
  forge/ce-dev-2/gh-token, field token, purpose review-pickup-token, owner_ref controller:reviewer,
  ttl 300; target-ref MUST be file: (env: rejected, fork-unsafe).
- New v3_cli helper `_review_pickup_token_supplier_from_args()` mirroring the wall's (~75 LOC);
  returns None when unconfigured → existing static-token path preserved byte-for-byte.
- `run_review_pickup_loop()` gains `token_supplier` + `gh_runner_factory` (defaults None): when
  set, EACH pass does supplier() (fresh grant→tmpfs→read→revoke) + rebuilds gh_runner. TTL only
  needs to cover one pass.
- Failure behavior: supplier failure or PickupError → structured log + incomplete pass + sleep +
  retry (BEHAVIOR CHANGE: today bare PickupError exits the daemon). Add
  `--pickup-token-max-consecutive-failures` (default from design follow-up #4) so a dead BAO_TOKEN
  eventually exits → systemd Restart takes over (avoids silent-stuck daemon).
- Systemd unit gains the vault flags; gate-daemons.env gains BAO_ADDR/TOKEN/CACERT; CE_PICKUP_TOKEN
  removed after verification. CE_OPENBAO_ALLOWED_REFS must include the new path entry (the
  wall-ref fallback predicate will NOT match it).

## Slices (dispatch as two units)
- **D1 (story, ~250 LOC)**: slices 1+2 — constants (secret_identity.py) + supplier helper + flags
  (v3_cli.py) + loop refresh + retry semantics (forge/review_pickup.py). Include the
  max-consecutive-failures flag.
- **D2 (story, ~280 LOC)**: slices 3+4 — systemd unit + install-gate-daemons-systemd.sh env docs +
  unit tests (test_v3_cli.py recording-backend fake + supplier tests; test_review_pickup.py
  per-pass supplier + skip-on-failure + retry-path tests).
D1 territory: secret_identity.py, v3_cli.py, forge/review_pickup.py — check vs #444 lease work
(also v3_cli.py!) before dispatch: SERIALIZE D1 after C3/#444 or route to same seat.

## ⏸️ OPERATOR prerequisites (deployment-time, NOT code-time — morning queue)
1. Store ce-dev-2 PAT at ce-kv/forge/ce-dev-2/gh-token field token (KV-v2).
2. Periodic-orphan BAO token w/ read on that path (+metadata) + sys/audit read (same recipe as the
   wall token — see ce-approval-wall-daemon-token-durable-recovery memory).
3. Author the governance policy doc whose sha256 = --pickup-token-secret-ref-policy-sha.
4. Set CE_OPENBAO_ALLOWED_REFS in gate-daemons.env with that policy_sha.
Code merges do NOT need these; the unconfigured path keeps current behavior.

## ✅ OPERATOR PREREQS EXECUTED 2026-07-05 ~04:0xZ (by CE-DEV-2, Operator-authorized in-session)
Full generate-root ceremony (proven script pattern; CEREMONY_OK; flag reverted; root revoked;
vault left unsealed/healthy; wall daemon rode through):
1. PAT stored: `ce-kv/forge/ce-dev-2/gh-token` field `token` (KV-v2; written via stdin; read-back
   length-verified). Host file ~/.ce-keys/ce-dev-2.pat retained until D1/D2 deployment verifies,
   then delete per design.
2. Daemon token minted: ORPHAN + PERIODIC (720h, renewable), policy `ce-pickup-token-read`;
   least-priv PROVEN (own-path read OK, wall-path DENIED). Custody: DGX `~/.ce-keys/ce-pickup-token`
   (0600). Stage to the deployment host with D2.
3. Policy doc authored + written to vault as `ce-pickup-token-read`. Canonical bytes:
   `.ce/state/research/ND_PICKUP_TOKEN_POLICY_20260705.hcl`;
   **POLICY_SHA=ab4769424e205eb53ee31d61da0c386ae9a418682e9bc0a6636f82de708c8982**
   (= --pickup-token-secret-ref-policy-sha value).
4. CE_OPENBAO_ALLOWED_REFS entry (staged here; lands in gate-daemons.env with D2):
   `path=forge/ce-dev-2/gh-token;field=token;purpose=review-pickup-token;owner_ref=controller:reviewer;policy_sha=ab4769424e205eb53ee31d61da0c386ae9a418682e9bc0a6636f82de708c8982`
D1/D2 are now fully unblocked code-AND-deployment-side (D1 still serialized behind #793 merge, v3_cli.py territory).
