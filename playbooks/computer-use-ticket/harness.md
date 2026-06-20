# Harness

## Runtime Contract

- Use a live authenticated Chrome instance through
  `chrome-devtools-mcp --autoConnect`.
- Keep browser work within the filled authority envelope.
- Use screenshot capture plus any available machine-readable recheck before
  reporting success.
- When pasting into Codex or a similar prompt surface, send the second Enter
  required to submit and use `C-u` eight times to clear stale text before a new
  paste.

## Dead Ends

- Fresh-profile MCP is a dead end for authenticated-browser work.
- `--remote-debugging-port` on the default Chrome profile is a dead end.
- Playwright against a real browser profile is a dead end because the keyring
  hang prevents a reliable authenticated loop.

## Halt Conditions

- Sudo prompts.
- 2FA, MFA, OTP, password re-entry, or recovery-code handling.
- A target surface outside the authority envelope.
- A browser substrate that cannot attach through `chrome-devtools-mcp --autoConnect`.

## Sunset

Sunset this playbook when the authenticated-browser substrate has a narrower
machine-authored API path for the same ticket class and that replacement is
ratified.
