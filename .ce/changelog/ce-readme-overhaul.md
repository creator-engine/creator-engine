---
slug: ce-readme-overhaul
date: 2026-07-08
kind: changed
scope: public README, CLI reference, and README version-drift gate
issue: readme-overhaul
---

**Overhaul the public README, add the public CLI reference, and extend README version drift coverage.**

- Replace the stale README status narrative with a public-facing product overview, stage model, quickstart, modes table, status pointers, and documentation fan-out.
- Move the public `ce` command inventory to `docs/reference/cli.md` and keep README linked to that reference.
- Keep release freshness structural by pointing readers to the release badge, changelog, and GitHub Releases instead of hand-maintained dated status prose.
- Extend the current-version drift validator so README CE-version text claims are checked against the canonical package version.
- Add unit coverage for matching README version text, stale README version text, version-free README content, CLI-reference parity, and the README reference link.
