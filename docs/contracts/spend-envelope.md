# Contract: Spend Envelope — the tokenomics gate (G-5)

**Status:** Canonical. Enforced by the `ce_spend_envelope` check; the pure decision
substrate is `creator_engine_validator/runner/spend_gate.py`.

## Purpose

Spend as a **deny-by-default blast-radius axis** — the cost-runaway protection that
is the #1 pilot blocker. G-5 is a **stateful** spend gate, distinct from the G-4
stateless per-action gate: the action gate asks *"is this allowed?"* (pure
`classify`); the spend gate asks *"is there budget left?"* (a ledger + a
threshold). It **reuses the G-4 action-gate's escalation + evidence machinery** —
the same hash-chained evidence spine and the same escalation discipline — with
`spend` as the new axis.

This is the CI-pure decision substrate. The live `usage` / `/usage` taps, the live
cockpit escalation channel, the cross-process concurrency semaphore, the live
vendor-rate fetch, and the empirical harness-overhead benchmark are named deferred
follow-ons (exactly as G-4 deferred its live hook tap).

## The two kinds of enforcement (Fork A)

- **Admission gate** — refuse a run whose envelope is *already* exhausted, **before
  provision**. No per-action pre-estimation (an LLM call's cost is unknown until it
  returns).
- **Post-action circuit-breaker** — meter spend as reported; trip when cumulative
  spend crosses the cap. Two-tier: a **soft** alert tripwire (~80%, continue) and a
  **hard** breaker (100%, **pause + escalate**, preserving state). Hard-deny is the
  fallback, not the default.

## Budget hierarchy (Fork B)

Nested **deny-by-default** envelopes `global -> fleet -> run`,
**most-restrictive-wins** (a run admits only if *every* enclosing envelope has
headroom). A **global ceiling is mandatory** whenever any `$` envelope is declared
— the anti-catastrophe backstop. `max_concurrent_runs` is a second, **concurrency**
envelope dimension (a semaphore ceiling).

The envelope shape is `{scope, amount, unit, window}` (+ optional `reset_anchor`,
`fleet_id`), stackable.

## Billing-tier-aware metric — two disjoint regimes (Fork C)

- **Fleet -> API-USD (`$`).** Computed from the transport/API `usage` object
  (`input_tokens` / `output_tokens` / `cache_creation_input_tokens` /
  `cache_read_input_tokens`) × the per-model rate table. The only fleet-legitimate,
  precisely-meterable path. The cost signal is **faithful-by-construction**
  (transport-reported, never agent-asserted) — it inherits the Fork-1 fidelity (the
  agent cannot spoof its own spend).
- **Subscription / OAuth seat -> single-seat `%`-meter.** `%` of the rolling 5-hour
  and rolling-weekly windows. **Never a fleet scope** — a subscription seat is
  ToS-non-poolable and mechanically single-seat. So a `%` envelope is `run`-scoped
  only; `fleet` / `global` scopes are `$`; and a `%`-metered policy declares no
  `fleet` scope.

**Strategic clarification:** CE's fleet/cockpit tokenomics is inherently an API-$
story; subscription value is the solo single-seat developer (the cost-sensitive
north-star market is single-seat).

## Read live, never hardcode

Vendor rates and caps drift (e.g. a +50% weekly bump expiring 2026-07-13). So
per-model rates live in the runtime-policy `model_rates` table and are **re-read
each run** — never baked into code. `compute_cost` consumes the injected rates;
cache-read defaults to the documented **0.1× ratio** (a ratio, not an expiring
absolute price) and cache-creation to the input rate when a row omits them. The
live vendor-rate fetch is a deferred follow-on.

## Two-signal refusal protocol

Distinct refusal codes, never conflated (the retry-storm hazard):

- **`budget_exhausted`** — out of budget; **do NOT retry** (cf. 412).
- **`throttle`** — concurrency/rate limit; **retry with backoff** + honor any
  `Retry-After` (cf. 429).

## State-as-projection (the differentiator)

There is **no mutable ledger file**. The cumulative tally is `project_spend` — a
PURE fold over the `runtime_spend_ledger` leaves on the existing hash-chained
evidence spine (`runtime_evidence_spine`), per scope + window. The breaker reads the
projection synchronously after each metered leaf (async budgets lag = post-mortem,
not a gate). Both the metered leaves and the breach trips ride the **same**
tamper-evident chain (content-addressed + chain-linked + policy-bound), so the spend
ledger is itself spoof-resistant grader input. **CE's per-run envelope** — refusing
*and aborting a specific run* on its own envelope — is the gap no surveyed tool
fills (they stop at key/team/window).

## Cost-enforcement opt-out — the cap / detection split

The opt-out is an **explicit, ratified, HUMAN-only** choice — an agent can never set
it (the gate is external to the agent; the policy is operator-authored + ratified).

- **Operator-facing field:** `spend_cap_enforcement: enforce | off` (default
  `enforce`).
- **The split:** `off` disables the sub-allocated **fleet / run budget CAPS** (the
  friction). It NEVER disables the always-on **runaway-DETECTION net** — the
  mandatory **global `$` ceiling** + anomaly → escalate stay on. *Caps off ≠ blind.*
- **Ratification binding required:** `off` REQUIRES a `spend_cap_optout`
  `{ratified_prompt_sha, approver_ref}` (64-hex opaque digests). An unratified
  opt-out fails the check (`VAL-SPEND-OPTOUT-UNRATIFIED`).
- **Educate-at-opt-out (copy for the G-7 installer):** *"Turning this off won't
  speed up your runs; it only removes per-run / per-fleet budget friction. The
  runaway-detection net (global ceiling + anomaly → escalate) stays on."* The
  installer Default-vs-Custom profile that surfaces this is **G-7** (this contract
  fixes the mechanism + the copy).

## The guard — `ce_spend_envelope`

A check over Runtime Policy records. It fires only on records that DECLARE spend
governance (green-on-day-one otherwise). Predicates:

- `VAL-SPEND-NO-GLOBAL-CEILING` — a `$` envelope set without a `global` `$` ceiling.
- `VAL-SPEND-ENVELOPE-INCONSISTENT` — an inner cap exceeding an outer cap (per
  window).
- `VAL-SPEND-REGIME-UNIT` — a `%` envelope off `run` scope, a non-`$` `fleet`/
  `global` scope, or a `%`-policy declaring a `fleet` scope.
- `VAL-SPEND-OPTOUT-UNRATIFIED` — `spend_cap_enforcement: off` without a valid
  ratification binding.

The field *shapes* are owned by `schemas/runtime-policy.schema.yaml` +
`ce_runtime_policy`; this check owns the cross-envelope *semantics*.

## Standing requirements honored (G-4.1)

Per `docs/contracts/v3-naming-hygiene.md`, this gate (1) keeps the v3 surface free
of bootstrapping-harness residue (`v3_naming_hygiene` stays green — `runner.spend_gate`
and the spend schemas are residue-clean), and (2) wires any v3 instance-local state
under the neutral `_versions.V3_LOCAL_STATE_ROOT` = `.ce/state` (never `.hermes/`,
never `.claude/`) — though G-5's ledger is state-as-projection (no new state file).

## Deferred follow-ons (named)

Live `usage` / `/usage` taps · live cockpit escalation channel · cross-process
concurrency semaphore / queue / sticky-lease · live vendor-rate fetch · the
CE-harness overhead micro-benchmark · an incremental derived global/fleet ledger
cache.

See also: `docs/contracts/runtime-policy.md` (the spend-envelope policy fields),
`docs/contracts/runtime-evidence.md` (the spend-ledger / breach records),
`runner/audit_overlay.py` (the G-4 `decide()` machinery this composes with).
