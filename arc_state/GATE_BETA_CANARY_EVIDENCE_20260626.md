# GATE β Canary Evidence — dev-3 vault-sourced (2026-06-26)

## Result: mechanism PROVEN; true from-seat path has 2 last-mile gaps (honest caveat)

### Part A — self-push: PASS (PR #540)
- Vault proof (OpenBao audit 16:59:57Z): per-call `auth/approle/login` → read `ce-kv/data/forge/dev-3` (entity 9b21886b). Key fetched from vault PER-CALL, never in container, never logged.
- Broker audit: decision=allow, pushed=true, pr=540; checks passed: signature_valid (%G?=G), author_authorized (ce-dev-3), branch namespace, rate limit.
- Commit authored+signed by ce-dev-3; pushed via App `ce-forge-dev-3`.

### Part B — self-review: PASS (review 4581245995 on PR #535)
- Submitted by `ce-forge-dev-3[bot]`, event=COMMENT; author≠reviewer enforced (ce-dev-3 ≠ ce-dev-1, resolved host-side); APPROVE hard-refused.
- Vault proof (17:02:01Z): per-call AppRole login → read ce-kv/data/forge/dev-3.

### Part C — Ring-1 deny: PASS (two layers)
- Hook deny: `git push` = `deploy` mechanic → permissionDecision deny (G2.007.2) under governed posture.
- Raw container push: exit 128, zero credentials (terminal prompts disabled).

## CAVEAT — the requests were invoked HOST-SIDE, not from inside the contained seat
The canary worker found that from INSIDE the container the seat could NOT reach the broker socket (gid mismatch: container ce-dev-3 gid 1003 vs socket gid 108), so Parts A/B were driven host-side (root). So PROVEN = the vault custody + broker + policy + author≠reviewer + Ring-1 containment chain. NOT YET PROVEN end-to-end = the contained SEAT itself driving self-push/self-review through the mounted socket (the thing that actually retires the courier).

## Two last-mile gaps surfaced
1. **PROVISIONING (socket perms):** the mounted broker sockets aren't writable by the seat uid inside the container. Fix = map socket group / perms so the seat can connect. Make canonical in the launcher (composes with ce-ops#270).
2. **SIGNING-CUSTODY (design):** the broker policy requires signed commits (%G?=G). The canary supplied a signing key host-side (~/.ce-keys/ce-dev-3-signing). A zero-key contained seat cannot hold a signing key — this is the signing-key analog of the App-key vault custody. Needs design: vault-sourced signing, broker-side signing, or a signing proxy. Until solved, a contained seat cannot produce the signed commit the broker requires WITHOUT a key in the container.

Also fixed inline host-side (should be made canonical, not ad-hoc): ce-dev-3 author email→noreply; `git config --system safe.directory`; review-broker `GH_CONFIG_DIR` drop-in for the author≠reviewer `gh api` call.

## Bottom line
GATE β architecture (vault App-key custody, governed self-push + self-review, containment) is PROVEN with hard evidence. Courier-retirement for dev-3 is NOT yet live — it needs (1) the socket-perms provisioning fix and (2) the contained-seat commit-signing custody design, then a re-canary driven FROM INSIDE the seat.
