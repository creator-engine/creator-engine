# Computer-Use Ticket

## What It Does

Runs a bounded authenticated-browser ticket loop for UI actions that cannot be
completed through ordinary repository edits.

## When To Use

Use this playbook when a ratified ticket requires a live browser session and the
work can be performed by an authenticated Chrome instance through
`chrome-devtools-mcp --autoConnect`.

Do not use it for sudo prompts, 2FA/MFA, password re-entry, recovery codes, or
fresh login establishment. Those are human halt points.

## Preconditions (DoR)

- A ticket names the exact UI target and desired state.
- A filled authority envelope constrains the browser action.
- The seat can attach to a live authenticated Chrome through
  `chrome-devtools-mcp --autoConnect`.
- The controller accepts the dead ends listed in `harness.md` and will halt
  instead of trying them.

## Outputs (DoD)

- Screenshot evidence of the resulting UI state.
- Machine recheck evidence where the surface exposes a readable state.
- Closed-set report: done, blocked-human, blocked-substrate, or no-op.
- Historical alias note when an identity rename preserves old logins as aliases.
