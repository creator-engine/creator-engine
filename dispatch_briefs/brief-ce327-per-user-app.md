# WORK CLAIM — ce-ops#327 onboarding must provision a per-user GitHub App (per-seat identity)

**Seat:** dev-4 (DGX build seat). **Role:** implementer-foreman. **Born foreman** — fan out.

## Branch
```
git fetch origin && git checkout -b ce-327-per-user-app origin/main
```

## Why (self-contained)
Onboarding does not require a PER-USER GitHub App, so contained seats end up committing/acting under a generic shared identity (observed tonight: harvested contained-seat commits authored as `CE Worker`/`Codex`, not the real dev account). `validators/creator_engine_validator/ce_onboard.py` + `onboard_apply.py` have no `app_id` cross-check and no rejection of a foreign/shared `app_id` for a `kind: own` seat.

## Task
1. **Validator guard:** reject onboarding where the seat declares `kind: own` (its own identity) but the `app_id` is a known-shared/foreign App — force a genuine per-user App. Fail-closed with a clear message.
2. **Onboarding flow:** prompt/guide the operator to create + supply a per-user GitHub App (manifest/answers flow), so a per-seat identity is provisioned rather than falling back to a shared one.
3. Tests proving: `kind: own` + foreign/shared `app_id` → rejected; a valid per-user `app_id` → accepted.

## Allowed paths (nothing else)
`validators/creator_engine_validator/ce_onboard.py`, `validators/creator_engine_validator/onboard_apply.py`, a schema constraint file if required, `validators/tests/**`, `.ce/changelog/**`, `.ce/pr-manifests/**`.

## Evidence (DoD)
Full `ce validate-pr` GREEN (CI-parity, full suite). 
⚠️ **G5 BODY FORMAT (mandatory):** the PR body MUST contain exactly ONE line formatted precisely as `- **Declared work class:** <tiny|story|feature|epic>` (a `**Work class:**` header or a `[PASS]` log line does NOT match — this papercut failed 4 PRs tonight). Pick the tier the gate derives.

## Stop-line
- Green + self-push works → push + PR ref ce-ops#327. Do NOT approve/merge.
- Green but push FAILS (contained-seat self-push gap #337; also note your container's libsodium gap fails `check-examples` on an unrelated fixture — if that's your ONLY failure it's pre-existing) → STOP + report `READY-FOR-HARVEST: branch ce-327-per-user-app, <N> commits, preflight green-except-libsodium`.
- Preflight RED on a NEW gate from your change → STOP + report it.
