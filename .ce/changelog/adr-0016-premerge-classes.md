---
slug: adr-0016-premerge-classes
date: 2026-07-19
kind: added
scope: governance / decision records
issue: ce-ops#616
---

**ADR-0016 — Pre-delegated merge classes (MC0, MC1, MC2): land the ratified decision record for zero-gesture merge tiers.**

- Added `docs/decisions/ADR-0016-pre-delegated-merge-classes.md` — the Operator-ratified (2026-07-19) decision record codifying the three pre-delegated merge policy tiers.
- **MC0 (`carrier_changelog_mechanical`)** — already active since 2026-07-17 ratification; this ADR formalizes the predicate set and replaces the session record as canonical policy text.
- **MC1 (`docs_envelope`)** — defines predicates for docs-only PRs (Key-2 reviewer still required; post-approval merge trigger removed); not yet armed.
- **MC2 (`xs_s_within_territory`)** — defines predicate target for XS/S seat-territory PRs; implementation gaps (territory registry, policy-fired reviewer-dispatch) documented; not yet armed.
- Governance record only; no code or behavior change.
