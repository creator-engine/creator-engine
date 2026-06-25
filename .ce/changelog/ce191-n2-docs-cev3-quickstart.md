---
slug: ce191-n2-docs-cev3-quickstart
date: 2026-06-25
kind: documented
scope: governed-flow guides / quickstart
issue: ce-ops#191
base: 574a843d
---

Points the user-facing governed-flow docs at the `cev3` command (the v3
governed flow) instead of the bare `ce` invocation, matching the installer's
own next-step hint and the shims it exposes.

- Rewrites governed-flow command invocations from `ce <subcommand>` to
  `cev3 <subcommand>` (onboard, session, scope, ratify, drive, report, pr,
  review, collect, merge, show, artifacts, guide) in
  `docs/guide/zero-to-governed-seat-quickstart.md`,
  `docs/guide/pilot-runbook.md`, and
  `docs/operations/GREENFIELD_FIRST_PROJECT_PROTOCOL.md`.
- Adds a prereq note near the install one-liner in the quickstart stating the
  host needs `curl` and `git` available (`git` is required for the first-value
  author→commit→push→PR→merge flow).
- Leaves product-name prose ("Creator Engine"/"CE") and the signed
  `docs/llms-install.md` install spec untouched.
