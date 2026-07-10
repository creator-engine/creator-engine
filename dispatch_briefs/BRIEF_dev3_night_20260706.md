# BRIEF — dev-3 NIGHT additions — 2026-07-06 ~17:3xZ — 2 units (queue AFTER your current R2s)

Night-arc ratified (D1-D8). You are now BROKER SELF-PUSH for docs/code-class units (D7): push +
open PR yourself on completion, signal READY <branch> <sha> PR=<url>. Reviews/verdicts still
never self-push. Worktrees /var/tmp, base FRESH origin/main. Changelog fragment + carrier
slug==branch + honest work class per unit. Stop lines standard (no approve/merge, no signing).

## U6 — ce-ops#228 slice 1: JIT credential injection mechanism — branch `ce-228-jit-cred-injection`
COMMIT-ONLY EXCEPTION: this unit is gate-adjacent (credential path) — do NOT self-push; signal
BLOCKED-ENV/READY with sha and wait for controller harvest. Live wiring to a real seat is a
MORNING act — build + tests only tonight.
PRINCIPLE (Operator 2026-06-24, ticket embedded): a contained agent must NEVER hold its own
credential. Secrets via docker -e persist in `docker inspect` metadata — containment without
cred-isolation is incomplete. Motivating incident: PR #408 detached containers left
CLAUDE_CODE_OAUTH_TOKEN inspectable.
BUILD (the durable fix, transport-deputy pattern, extends YOUR broker — reuse the forge-read
lane's minting machinery from ce-475, incl. the flock rate-cap pattern from its R2):
- Broker verb `mint-seat-credential <seat-id> <credential-class>`: mints scoped short-TTL
  credential AT REQUEST TIME, delivers via the broker socket stream (NEVER via container env,
  argv, or any docker-inspectable metadata), audit line per mint incl. on refusal.
- Credential classes v1: `model-api` (harness model key) and `forge-scoped` (existing scoped-
  token path — unify, don't duplicate). Class allowlist per seat policy, fail-closed on unknown.
- Revocation on TTL + explicit revoke verb; single active credential per seat per class.
- Failure-direction tests: env-var delivery path IMPOSSIBLE by construction (grep-able assertion
  that no docker -e/exec env carries the secret); unknown class refused+audited; TTL expiry
  enforced; concurrent mint respects the flock serialization.
Work class: story.

## U7 — ce-ops#489: brain-init onboarding gap — branch `ce-489-brain-init-refusal-teaches`
Self-push OK (code-class, not gate-adjacent). Ticket embedded:
SYMPTOM: bare `ce launch` refuses G6-LAUNCH-BRAIN-BOOTSTRAP-REFUSED on a freshly onboarded
0.3.3 repo; the refusal does NOT name `ce brain init`; onboard --apply (own-App lane,
brownfield) emits posture.json + runtime-policy.yaml but NO brain assertion ledger under
<repo>/.ce/state/brain/assertions.yaml. Evidence: /var/tmp/ce-canary-c3/stage4_launch_smoke/
(controller host). First tenant hits this day one.
FIX (both halves):
1. `ce onboard --apply` emits the genesis brain ledger (same act as `ce brain init`) OR — if
   genuinely deferred by design — prints the exact next command as its final output line.
   Prefer emitting: one less tenant step.
2. The G6-LAUNCH-BRAIN-BOOTSTRAP-REFUSED refusal names `ce brain init` as the recovery command
   (refusal-that-teaches, same pattern as the takeover refusal shipped today — mirror its
   message structure).
Failure-direction tests: fresh-onboard → launch succeeds (or refusal teaches); refusal text
asserts the exact command string; onboard idempotency (re-apply doesn't clobber an existing
ledger). Work class: story.
