# CE End-to-End User Journey — Working Mental Model

**Status:** shared model agreed by Operator + Controller 2026-06-22, to **revisit after the dev-4 M1 canary**. Companion to [[ce-fleet-retirement-clean-install-program]] + `RUNBOOK_DEV4_RETIREMENT_M1.md`. Strategic anchor for the self-driving-onboarding agent (ce-ops#197).

## Why this matters
The dev-4 retirement canary is not just fleet maintenance — done faithfully (agent drives the install, Operator ratifies/supervises) it is **the first real end-to-end test of the new-user onboarding journey**. Cataloguing exactly what the driving agent has to do = the requirements spec for #197.

## The journey (5 stages) — "inception" framing made mechanical
- **Stage 0 — Pre-CE (ungoverned).** User has a machine, their own coding agent (Claude Code/codex), their own creds (GitHub, model sub). Agent is UNGOVERNED.
- **Stage 1 — Install (ungoverned agent; trust = the signed playbook).** User tells their agent "install CE from creator-engine.dev." Agent fetches `install.sh`, verifies the signed trust anchor (DNS `_ce-root-v1` TXT + SSHSIG), runs the playbook → signed wheels → venv → `ce` on PATH. **Necessarily ungoverned** (CE isn't running yet); the signature is its governance.
- **Stage 2 — Initialize workspace (still the installer agent).** `ce brain init` (genesis ledger; ce-ops#206, MERGED #350), identity/mode/secrets config.
- **Stage 3 — Inception switch (handoff to governed).** Installer agent's FINAL act: launch the first CE-governed agent via canonical `ce launch`/`ce start`, then exit. The new process has CE's Ring-1 hook (`hook_check.py`) wired — that IS "governed." = "close the ungoverned agent, open a governed one," made mechanical. The human does NOT type this; the installer agent performs it as handoff.
- **Stage 4 — Governed steady state (the face).** User works through cockpit / CEO-mode (Frame→Shape→Build→Review→Ship), expressing intent + ratifying, never typing `ce`. Governed controller spawns governed worker seats.
- **Stage 5 — Updates (dream-within-a-dream).** New signed release → `ce update`. dev-4 loop: develops CE → release built+published → `ce update`s → governs its NEXT CE work with the new release. CE eating its own tail.

## Sharper-edge points (with Operator's 2026-06-22 answers)
1. **Handoff trigger is a CONFIRMED product gap.** There is NO single high-level `ce onboard`/`ce start` that does init→brain→first-governed-launch→cockpit. Confirmed by Arad's pilot: her Claude Code **hand-stitched several `ce` commands** — a documented pain point. **This gap IS ce-ops#197.** The dev-4 canary must record the exact stitched command sequence the driving agent uses → that becomes #197's requirements spec.
2. **Canary scope = dev-mode seat only.** The cockpit/CEO face does not exist yet, so dev-4 validates Stages 1–3 + 5 (install / governance / update spine), NOT the novice cockpit face (Stage 4 for a non-dev). A later "ceo-mode" canary tests the cockpit once it exists.
3. **Install trust boundary is real and correct as-is.** Stage 1 is ungoverned by necessity; the signed trust anchor is its governance; everything after is governed/(M2)contained. Deliberate, documented seam — and the load-bearing attack surface (signature verification must hold).
4. **M1 vs M2 = same journey, different substrate.** M1 = host install + tmux + governed controller (canaried now). M2 = governed agent launches into a CONTAINER, install also provisions the container substrate, tmux retired. **Operator emphasis: follow a successful M1 with an M2 install very soon after.**

## To revisit after dev-4 M1
- The exact stitched command sequence the driving agent ran (→ #197 spec).
- Every point where the agent had to improvise / hit a missing affordance (onboarding gaps).
- Whether `ce update` (Stage 5) is smooth or stitched.
- What an `ce onboard` one-shot should encapsulate.
- Then: schedule the M2 (containerized) canary.
