---
slug: ce-release-0-3-4
date: 2026-07-08
kind: chore
scope: release
issue: creator-engine/ce-ops#501
---

**bump 0.3.3 -> 0.3.4 + CHANGELOG + release staging.**

Rolls up 35 candidate PRs merged since v0.3.3 (plus one post-ledger hygiene patch, PR #894) covering JIT seat credential minting, egress broker read lane, work-claims lifecycle, controller takeover and continuity drill, brain memory-layer slice 1, SSHSIG signing deputy design, host-ops broker design, ephemeral controller seam design, and a sheaf of fixes and infra hardening. Bumps version 0.3.3 -> 0.3.4, assembles the 0.3.4 CHANGELOG section, stages signed 0.3.4 release artifacts under .ce/release-staging/0.3.4/, and publishes the placeholder-signed 0.3.4 install spec to docs/llms-install.md (controller completes the ce-root-v1 signature).
