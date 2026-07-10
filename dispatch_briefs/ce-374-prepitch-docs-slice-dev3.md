# SEED BRIEF — ce-ops#374: pre-pitch docs slice (rendered "What is CE" + architecture) — SEAT: dev-3

**Ticket:** ce-ops#374 (L9 docs surface). **Branch:** `ce-374-prepitch-docs-slice` (off origin/main). **Role:** implementer. **Work class:** declare by floor (XS/S, or legacy tiny/story — alias accepted).

## Goal (self-contained — embed, do not rely on reading the private ticket)
Today `creator-engine.dev/#docs` is a flat list of links to RAW markdown files served as plain text (GitHub Pages from `docs/`). Ship the **pre-pitch slice** of the docs portal: ONE real, **rendered + styled** page — "What is CE" + an architecture-at-a-glance diagram — reachable from the site. This is what a pilot user / the NVIDIA pitch audience lands on. NOT the full portal (that's ce-ops#37, post-pitch).

## Scope (bounded — one page, real rendering)
1. A single rendered HTML page (or a minimal static-site-generated page) titled ~"What is Creator Engine" served from the site (GitHub Pages serves `docs/`). It must render as a styled page with nav back to the site — NOT raw markdown.
2. Content: a tight "What is CE" (the product in plain language — governed agent-native SDLC; grader-outside-the-agent) + an **architecture-at-a-glance** diagram (controller→seats→forge→containment; or reuse an existing diagram in `docs/architecture/` if one fits). Keep it product-lens (public-docs doctrine: NO internal ce-ops# refs, NO Skynet, ecosystem-labeled-or-omit).
3. Reachable: linked from the site's `#docs` section (and/or top nav). Pick the LIGHTEST rendering approach that produces a real page (a single styled HTML, or a minimal generator) — do NOT stand up a heavy portal framework; that's #37.
4. If a docs-build step is added, keep it minimal + documented.

## Constraints
- Public-docs PRODUCT lens: zero ce-ops# references, no internal codenames; run/clear the confidentiality scan.
- Don't break the existing `#docs` markdown links.

## Evidence / DoD
- The rendered page exists, is styled (not raw md), reachable from the site, and passes the public-docs confidentiality scan.
- Per-PR `.ce/changelog/<slug>.md` + carrier + work-class line.

## Stop line
FULL `ce validate-pr` GREEN locally (one pass) BEFORE self-push. Then commit + push + open PR as your own seat identity, report branch/SHA/PR#/preflight line. Controller holds the gate. Foreman mode.
