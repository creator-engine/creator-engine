# RESUME STATE — CE-DEV-2 — 2026-07-05 ~08:30Z (day-arc checkpoint #1)

> MEMORY.md first. Supersedes RESUME_STATE_CE_DEV2_NIGHTARC_20260705T0730Z.md. Arc SSOT =
> DAYARC_MANDATE_CE_DEV2_20260705.md (✅ RATIFIED ~07:05Z + execution log inside it — read it,
> it carries the full state). Night-arc residue: C5 retry = tonight, quiet window.

## ⏸️ AWAITING-OPERATOR (surface FIRST)
1. ghcr package visibility: ce-runtime is PRIVATE (anon pull 401), no API exists — needs Operator
   UI click (org packages → ce-runtime → settings → Change visibility → Public). Blocks tenant
   image pull; same click needed for ce-seat after first publish.
2. Disposable bootstrap token for the full-DoD follow-up canary (onboard --apply does real GitHub
   mutations): Operator picks sandbox ce-overwatch fine-grained PAT (recommended) vs disposable
   account.

## DAY-ARC (Operator directive ~06:55Z): contained CE to test users TODAY, one-liner + agent
## playbook paths, DoD-gated. Ratified: Linux+Docker only · Arad only · ghcr publish · full grants
## incl. 0.3.2 cut+sign. 0.3.2 REQUIRED & scope crisp (see mandate log).

## BOARD (foreman queues)
- dev-1 (tmux, self-push, DOUBLE-Enter): #414 installer-docs (ACTIVE, territory extended
  shrink-only for confidentiality ratchet after legit closed-set stop) → #417 → ce-onboarding-docs-
  accuracy (brief has ADDENDUM, sha re-verified) · PARALLEL: ce-s1b-seat-image + ce-npm-path-fix.
- dev-3 (ce-vps-codex via ssh dev1): ce-415 brownfield.enabled (ACTIVE, commit 7b7faba2 in
  preflight) → ce-s1a-docker-runner-backend (unit 4).
- dev-4 (ce-dgx-codex local): ce-434 (ACTIVE, long) → ce-445-c5prep-daemon-smoke (condition met:
  #799/#800 merged — squash-style, seat SHAs never on main, correction already sent) →
  ce-s1c-launch-default-policy (unit 5, gated on s1a merge, parallel-able) → ce-onboard-relaunch-ux
  (unit 6, after s1c, same launch_runtime.py).
- Merged this session: #795-#801 (7). Open PRs: none at checkpoint. Claims pruned through #801.

## EVENT → ACTION MAP
- Seat READY signals → harvest (contained seats: bundle-stream via docker exec cat; dev-3 worktree
  /var/tmp) → full host preflight → PR → fetch+worktree+diff-file → reviewer (Sonnet, "author=seat
  X, you are the independent reviewer") → approve as ce-dev-2 on green → chain merges (~15-25m).
- s1a merge → notify dev-4 s1c condition true. s1b PR → review incl. digest-pin discipline.
- All of {s1a,s1b,s1c,npm-fix,docs units} merged + ghcr-public click → cut 0.3.2 (release worker
  stages; ce-root-v1 signing INLINE by controller ONLY, incl. re-signed llms-install.md w/ line
  239 fix) → publish → RE-RUN both canaries vs live artifacts → DoD evidence → Arad handoff pack.
- ce-434 signal → harvest → also unlocks the "did-you-mean ce install" pool tiny (same ce_cli.py).

## CANARY FACTS (full reports in mandate log + task outputs)
- Path A: install+onboard PASS on live 0.3.1 (2 undocumented recoveries), containment FAIL
  (bare tmux, probe NOT CONTAINED), stopped at Anthropic login (legit). Env left: ce-canary-a on
  VPS, tmux ce-controller at login prompt.
- Path B: signed ceremony + bootstrap PASS; `ce install/session` missing on RELEASED wheel only
  (main already has ce-440-s1 forwarding) — 0.3.2 delivers. Env left: /var/tmp/ce-canary-b (DGX).
- ghcr ce-runtime@0.3.1 digest sha256:7618dbe8811d467c71ae2a8fec231e38fc837532a1dd09b7fe4e7f0dd575353c
  (manifest list; THE pin for s1b/s1c + C5 daemon).

## TICKETS this session: #447 S1 program · #448 npm PATH · #449 fantasy-CLI docs · #445 progress
## comment · #435 closed already-resolved · #384 role-gap evidence (verification role correctly
## REFUSED the ops canary → re-ran on general-purpose under controller creds).

## WATCHERS/TASKS: b7hq6ib7g PR-board (PRIOR session's, auto-resumed — do NOT duplicate) ·
## bw2w5n0yz seat-signals tightened (last-40-lines + full signal shape; dev-1 BLOCKED-echo noise
## lesson) · bmosax1vr daemon-log tail. Daemon healthy (logs to PRIOR session scratchpad
## rollback-launch.log — move at next restart). One triage worker (onboard-UX ticket) may still
## be running — check before re-filing.

## MECHANICS banked this session: squash-merge means seat SHAs never land on main — condition
## seats on PR-title-in-log, never raw SHA · herdr queue-adds may need a SECOND Enter (input box
## shows text = NOT submitted; empty placeholder = submitted) · ghcr package visibility has NO
## API · runtime-image build needs OCI_CPYTHON_BASE_IMAGE_* args from publish-runtime-image.yml
## lines 93-95 · reviewer worktrees: fetch branch + worktree + write diff-file to MY scratchpad.
