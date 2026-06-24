### ce-ops#227 — Wave-A: register Ring-1 PreToolUse hook in contained seat config + canary test-hardening

- Register `[[hooks.PreToolUse]]` in the generated contained-codex `config.toml` (both DGX and VPS runsc launchers), invoking `.codex/hooks/ce-pretooluse-codex.py` with `PYTHONPATH` set so the validator imports inside the image. Closes the live gap where contained seats ran with the Ring-1 per-call deny hook unregistered. gVisor remains the Ring-0 sandbox (`sandbox_mode=danger-full-access`); the hook is the separate Ring-1 layer.
- Retarget the live herdr integration test off the host-staged `/tmp/herdr-share` binary to the in-image `/usr/local/bin/herdr` (glibc-mismatch guard).
- Add DGX-side socket-env-leak test (socket var never reaches the seat env; scrubbed by `env -i`).
- Add same-pane render test (dispatcher pane id == attached root pane id).
