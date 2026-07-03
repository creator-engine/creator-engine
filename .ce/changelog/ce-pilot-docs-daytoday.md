---
slug: ce-pilot-docs-daytoday
date: 2026-07-03
kind: docs
scope: pilot-facing guides (docs/guide/solo-ceo-onboarding.md, docs/guide/solo-dev-onboarding.md, docs/index.html)
issue: pilot-docs-audit-20260703
---

**Pilot-facing command-surface corrections + collaborator section.**

- Corrected every documented command in `solo-ceo-onboarding.md` and
`solo-dev-onboarding.md` whose verb belongs to `cev3` (scope, shape, ratify,
drive, artifacts, show, merge, report, status, inbox) but was shown as a
bare `ce` command, matching `pilot-runbook.md`'s existing naming convention.
`ce launch` was left untouched — it is a real `ce` command.
- Fixed `docs/index.html`: `ce fanin show` (not a real subcommand) corrected
to `ce fanin inspect`; the Solo + Dev doc-card's "with `ce` commands"
wording corrected to `cev3` to match the corrected guide.
- Added a new "Working with a collaborator on your repo" section to
`solo-ceo-onboarding.md` covering how governance, review, ratification, and
the merge gate behave once a second person has write access to the repo.
