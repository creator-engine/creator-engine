# ARAD-SEND READINESS NOTE — 2026-07-07 (assemble-only; NO send — Operator holds all external comms)

## What is on main and ready for the tenant journey
- **Canonical journey doc pair (#877, merged)**: `docs/guide/quickstart.md` (copy-pasteable —
  every command verified paste-safe after two blocking fixes: slugged `ce shape`, full
  `ce ratify --approver-ref` form) + `docs/guide/how-ce-builds-software.md`. Both passed the
  full vocabulary bars (no bet/appetite, Goal/Done-when/Change-type, Budget as opt-in % aside,
  CLI-anchored, honest loop, zero internal refs). The quickstart teaches the PROVEN tenant path:
  `ce brain init` (once) → `ce launch --backend host`, contained lane honestly marked
  hardening-in-progress.
- **Next-step hints (#876, merged)**: the terminal now teaches the journey after each verb, with
  hints correctly suppressed when a scope isn't ready.
- **shape --from <prd> (#878)**: approved, in final rebase — Arad's actual arrival situation
  (existing PRD) becomes first-class. Expected on main today.
- **Brain-init refusal-that-teaches + genesis ledger (#881, from the launch smoke findings)**:
  in final round — `ce onboard` will leave a valid genesis ledger, and the G6 refusal now names
  `ce brain init`. Expected on main today.

## ⚠️ Caveat that MUST inform the send (new since yesterday)
**ce-ops#494**: every repo onboarded since 2026-06-19 carries an adoption workflow with a broken
spec-canonicalization (a `\1` regex backref collapsed to a control byte) → its CI spec-verify
fails closed when it runs. **Arad's repo (onboarded 2026-07-03) is affected.** The template fix
is merged (#859), but already-onboarded repos need the regenerated workflow. RECOMMENDATION:
either (a) hold the send until the #494 remediation lane (workflow regen for existing tenants)
ships, or (b) include a one-line honest note + the regen step in the welcome message. Decision
is the Operator's.
**⏫ DECIDED 2026-07-07 ~15:4xZ: Operator chose (a) — HOLD the send for #494 remediation. dev-3's
refresh-workflow unit is the send-critical path; see DECISIONS_20260707.md item 4.**

## Still owned by the Operator (unchanged)
- T4 welcome-pack rewrite (your codex session's territory — no pack edits made by controller).
- The one open decision: whether .md sources ship inside the HTML-first bundle.
- The send itself (hard stop: zero external comms from controllers).

## Suggested send shape when ready
Welcome pack (HTML-first, links canon docs, never duplicates) + pointer to quickstart.md as the
first hour + the #494 regen step if (b) above. All governed-journey docs are now product-lens
clean (no internal issue refs, ecosystem-labeled).

## ⏫ UPDATE ~18:xxZ — remediation tool APPROVED (PR #885)
`ce onboard --refresh-workflow` + signer-parity guard approved and queuing. ON MERGE the hold
condition is met tool-side. REMAINING BEFORE SEND: run the refresh against Arad's onboarded repo
(tenant-side act — Operator session or governed App lane; single-file atomic write, idempotent,
refuses non-CE files). Then the send is unblocked per the hold decision.

## UPDATE 2026-07-07 ~20:0xZ (controller)
- PR #885 MERGED (main bd5b1f83). Tool-side hold condition MET.
- Remaining before send: APPLY `ce onboard --refresh-workflow` to Arad repo (tenant-side act, Operator/App lane) + Operator T4 pack + md-sources decision.
