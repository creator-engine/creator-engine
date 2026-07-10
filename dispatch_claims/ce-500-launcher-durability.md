# WORK CLAIM — ce-500-launcher-durability (+ sibling ce-499-seat-preflight-design)
- seat: dev-1 (self-push lane, VPS)
- dispatched: 2026-07-07 ~23:xxZ by CE-DEV-2 controller
- brief: .ce/briefs/BRIEF_dev1_restock_20260707T23.md (sha256 b2665e1f…9bc1), mirrored /home/ce-dev-1/briefs/
- U1 ce-500-launcher-durability: deploy/vps-runsc/run-vps-runsc.sh + deploy/dgx-runsc/run-codex-runsc.sh (+launcher docs/test surface) — #500 slices (b) durable worktree bind-mount + (c) durable staging. Explicitly forbidden: validators/ Python (claimed by #888/#889/dev-3 in-flight).
- U2 ce-499-seat-preflight-design: docs/design/seat-side-preflight.md DESIGN-ONLY (CLI surface contested tonight).
- mode: self-push → PRs; controller reviews+gates on open
