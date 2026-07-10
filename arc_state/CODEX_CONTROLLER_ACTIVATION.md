# CODEX CONTROLLER — ACTIVATION STEPS (Operator)
The DGX codex orchestrator is launched in tmux **`ce-controller:dev2-codex`** (YOLO/full-access, gpt-5.5) but its ChatGPT auth is EXPIRED (host `~/.codex/auth.json` last_refresh 2026-06-18, refresh token consumed). Activate it:

1. Switch to the window: `tmux select-window -t ce-controller:dev2-codex` (or `Ctrl-b 1`).
2. Exit the dead codex TUI: `Ctrl-C` twice (or `q`).
3. Re-authenticate (ACCT B = amitaicoco1@): `codex login` → complete the browser/device sign-in.
   - Verify: `codex login status` should show signed-in chatgpt auth.
4. Relaunch the controller from the repo root:
   `cd ~/creator-engine && codex --dangerously-bypass-approvals-and-sandbox -m gpt-5.5`
   (optional: bump reasoning effort to high via `/model` in the TUI — recommended for a controller.)
5. Orient it — paste this one line:
   `You are the new CE-DEV-2 Orchestrator. Read .ce/state/research/ORCHESTRATOR_HANDOFF_PACKAGE_20260628.md (sha256 532f97e7bef9f61f) IN FULL — your role, live fleet state, credentials map (~/.ce-keys/), and mechanics. Then read the newest RESUME_STATE_CE_DEV2_DAYARC_*.md + MEMORY.md. Confirm you can locate the credentials, then WAIT for me before driving the fleet.`

Durable directive already in place: `~/.codex/AGENTS.md` (orchestrator anti-inline directive) + repo `AGENTS.md` (worker-role policy) load automatically.

Alternative if you can't OAuth right now (NOT recommended — desyncs dev-4): copy dev-4's fresh token: `sudo cp ~cedev4/.codex/auth.json ~/.codex/auth.json && sudo chown cedev2:cedev2 ~/.codex/auth.json` — but the next refresh-token rotation will break whichever instance rotates second.
