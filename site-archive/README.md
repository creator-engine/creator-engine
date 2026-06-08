# Creator Engine — website version archive

Tracked, exact snapshots of every published version of the Creator Engine brand
site (`creator-engine.dev`). The live site is always `docs/index.html`; when it
is replaced, the outgoing bytes are snapshotted here so every version stays
versioned and tracked, independent of git archaeology.

These files are **not** served by GitHub Pages (Pages serves `docs/` only) — they
are durable history, browsable in the repo.

## Versions

| Version | Date | Snapshot file | Live commit | `docs/index.html` SHA256 | Notes |
|---|---|---|---|---|---|
| v1 | 2026-06-07 | `index-v1-launch-cyan.html` | `b33b01e` (#151) | `b4fcce246de074c591ed99b9d8ed3a021ea0088c09f8829e01db5ddfc2592a5e` | Initial GitHub Pages launch. Deep-ink + electric-cyan "trust" palette; alternating dark / white "paper" bands. |
| v2 | 2026-06-07 | `index-v2-control-room-violet.html` | `6da4079` (#155) | `bcac9fbf770aa8b261850c9b5af5c9749a3f1e8a40e428a10b3a01c9297e8ab3` | "Control-Room Violet" cyberpunk-neon redesign. Off-black + neon purple; crimson = privileged-gate semantic; inline-SVG "The Gate" artwork; `.hermes`→`.ce` naming. |
| v3 | 2026-06-07 | `index-v3-fomo.html` | `ed536e0` (#160) | `fac5fa4de6de2530b43de4640b67282aa73c21a0dae5005927c3b478b5226201` | FOMO + visual-augmentation pass on v2: era hero + anxiety couplet, "Propose · Ratify · Ship" refrain, governance scoreboard, governed-flow diagram (human gate on the critical path), audit-log panel, trust-debt curve, maturity ladder. Honest-metrics-only; implicit positioning. |
| **v4 (current — live)** | 2026-06-08 | `../docs/index.html` | this change | `58adf49f5db992386ad4c4f3fc749dccfc26c3528425b6b1ad5df5abbcf3ac2d` | Vocabulary-consistency tidy to the canon ([`docs/architecture/stage-vocabulary.md`](../docs/architecture/stage-vocabulary.md)): stage phases **Frame → Shape → Build → Review → Ship**; Scope-card labels **Goal / Done-when / Budget / Change-type / Ready**; Completion-Report labels **Outcome / Verdict / Next**; "mutation class"→**change type** (user-facing skin, `mutation_class` conserved underneath); hero terminal reframed to a representative `ce session`; corrected the stale "Visible Controller seat" → v3 product **"your agent, under CE"** (per [`docs/architecture/pilot-uiux-model.md`](../docs/architecture/pilot-uiux-model.md)). No redesign. |

## Policy

When `docs/index.html` is replaced, in the **same governed PR**:
1. Snapshot the outgoing bytes verbatim to `site-archive/index-vN-<slug>.html`.
2. Add a row above (version, date, file, live commit, content SHA256, notes).
3. Promote the incoming version's row to "current — live".

Snapshots are byte-exact copies of what was live; do not edit them after the fact.
