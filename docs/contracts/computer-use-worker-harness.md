# Contract: Computer-Use Worker Harness

Gate: ce-ops#142, Phase 1 only
Related schema: `schemas/computer-use-authority-envelope.schema.yaml`

## Purpose

This contract captures the computer-use worker substrate validated for today's
UI side-effect work. It defines the allowed browser harness, explicit dead
ends, human-in-loop halt points, evidence requirements, and completion report
vocabulary. It does not authorize live Ring-2 hook honoring; that remains a
Phase 2 follow-up for ce-ops#142.

## Supported Browser Harness

The supported harness is:

- authenticated browser control through `chrome-devtools-mcp --autoConnect`;
- attached to the live user Chrome session;
- enabled by the user's Chrome remote-debugging exposure visible through
  `chrome://inspect`.

This path uses the already-authenticated human browser context. It is the only
validated worker harness path for this phase.

## Forbidden Dead Ends

The following harness routes are forbidden for this contract because they were
not the validated substrate and caused unsafe or unusable behavior:

- fresh-profile MCP browser sessions;
- launching the default Chrome profile with `--remote-debugging-port`;
- Playwright automation against the real Chrome profile, due to the
  gnome-keyring hang failure mode.

Workers must not retry these routes as fallback strategies.

## Human-In-Loop Halt Points

Sudo mode, password prompts, 2FA/MFA/OTP, recovery-code handling, or any
credential re-entry prompt is a hard HALT.

The worker must not bypass, infer, scrape, store, or request these values from
the envelope. The correct action is to stop and return control to the human.
After the human completes the protected step, the worker may continue only if
the target and mechanic remain within the active authority envelope.

## Evidence Requirements

Each completed UI side effect needs two evidence classes:

- screenshot evidence showing the resulting UI state;
- machine recheck evidence confirming the resulting state through an
  independent non-visual read when available.

If machine recheck is unavailable, the completion report must mark the item
`DEFERRED` or `HALTED` with the reason. Screenshot-only evidence is not enough
to claim fully verified completion.

## Completion Report Vocabulary

Completion reports use a closed status set:

| Status | Meaning |
| --- | --- |
| `DONE` | The UI action completed and both screenshot and machine recheck evidence are present. |
| `SKIPPED` | The target was intentionally not acted on because it was out of scope or already satisfied before action. |
| `DEFERRED` | The target remains in scope, but completion requires a later phase, unavailable evidence, or external state. |
| `HALTED` | Work stopped at a human-in-loop boundary such as sudo mode, 2FA/MFA/OTP, password re-entry, recovery code, or unclear authority. |

No other completion status is valid for this harness.

## Phase Boundary

Phase 1 delivers the contract and validator envelope substrate only. Live
Ring-2 hook honoring for computer-use mechanics is deferred to a Phase 2
ce-ops#142 follow-up issue.
