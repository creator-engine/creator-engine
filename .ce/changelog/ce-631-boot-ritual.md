---
slug: ce-631-boot-ritual
date: 2026-07-19
kind: added
scope: controller resume ritual — boot-time pin re-derivation
issue: ce-ops#631
---

**Add the boot-time pin re-derivation checklist as a mandatory controller resume ritual.**

- Adds `docs/operations/BOOT_TIME_PIN_REDERIVATION_PROTOCOL.md`, requiring
  every resume-state claim (git head/remote, worktree porcelain per
  claimed-staged branch, open-PR set and approval states, armed-policy
  state incl. kill-switch, daemon/wall/queue health, fleet seat liveness,
  and newest resume-state file mtime) to be re-derived live before any
  binding act after a boot, `/clear`, relaunch, or handoff; a mismatch
  between a claim and its live derivation is a STOP.
- Adds a "Resume side" section to the `ce-checkpoint` skill pointing at the
  new protocol, so writing a checkpoint and resuming from one carry
  symmetric obligations.
- Registers the new doc in the public-docs confidentiality guard's
  `docs/operations/**` debt-ratchet allowlist.
