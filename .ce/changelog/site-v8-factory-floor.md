---
slug: site-v8-factory-floor
date: 2026-06-19
kind: changed
scope: brand site (creator-engine.dev / docs/index.html) + cockpit theme pin
issue: ce-ops#51
---

**Website v8 "The Factory Floor" redesign — replaces v7 "The Choice"; the
cockpit theme is re-pinned to the new palette to keep the site↔cockpit
single-source-of-truth invariant.**

- **New live `docs/index.html` (v8).** Dark warm-factory palette (steel /
  near-black + violet, a rationed moss/oxide accent); retires the v7 serif and
  the Control-Room Violet palette, and retires the "Choice" / red-pill
  cinematic landing. Page flow: hero → Agent-Native Install → animated
  production-line → How it works. → Five governed phases → NVIDIA OpenShell →
  fear map → Technical credibility → CTA.
- **Hero animation.** A five-station inline-SVG conveyor (Frame → Shape →
  Build → Review → Ship): idea-blobs ride the belt and each weld-arm fires
  only as the workpiece reaches its station (the station effect delays are
  phase-aligned to belt travel time, not a fixed independent beat). Caption:
  "An idea comes in → a working App comes out." Reduced-motion-safe (static
  posed frame under `prefers-reduced-motion`).
- **Agent-Native Install** sits directly under the hero, left-aligned
  openclaw-style, with two `#`-commented copy boxes (agent-paste / human
  one-liner); the `#` comment lives outside the copy target so Copy grabs only
  the command.
- **Ported v7 content sections** restyled into v8: the Scope card + ◆
  Completion Report ("How it works."), the five-phase strip, the OpenShell
  complementarity plates, the worry→mechanism fear map, the Technical-
  credibility caps, and the "Be a Creator. Safely." CTA. The cockpit board
  section was removed pending a real `ce cockpit` capture.
- **Brand assets.** Nav carries the plate-less transparent weld-arm mark
  (`docs/assets/ce-logo-v2-weldarm-transparent.svg`, derived from the shipped
  `ce-logo-v2-weldarm.svg`); `ce-favicon-v2.svg` stays the favicon.
- **Cockpit theme re-pin.** `v3_cockpit.THEME` and the serve-test `SITE_HEX`
  are re-pinned from Control-Room Violet to the v8 palette
  (`ink-900 #0C0B0A · ink-850 #16140F · ink-800 #191712 · fg #FAF8F1 ·
  violet #A06BFF · spark #7FB069 · gate #E0605C · amber #E08B4C`), and the
  matching `--token:#hex` aliases are added to the site `:root`, so the
  `ce cockpit` palette stays pinned verbatim to the live site.

Per the site-versioning policy, the same PR snapshots the outgoing v7 page
byte-identically to `site-archive/index-v7-the-choice.html` (sha256
`38f89de4…`) and promotes v8 to "current — live" in the archive ledger. No
validator wheel rebuild: the `v3_cockpit.py` edit is theme constants only and
ships from source under `PYTHONPATH=validators`; the wheelhouse is untouched.
