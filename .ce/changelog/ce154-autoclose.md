---
slug: ce154-autoclose
date: 2026-06-20
kind: added
scope: github-actions
issue: ce-ops#154
base: 03d3796dd16429358884658a29bdcda8e3f986b4
---

Adds cross-repo ce-ops autoclose automation for merged pull requests.

- Adds a fail-soft GitHub Action that runs on PRs merged to `main` and uses the
  dedicated `CE_OPS_TOKEN` secret, not `GITHUB_TOKEN`, to close
  creator-engine/ce-ops issues.
- Parses only explicit closing refs (`Closes ce-ops#N`, `Fixes ce-ops#N`, or
  `Resolves ce-ops#N`) and ignores bare mentions, adjacent keyword text, and
  negated prose.
- Documents the authoring convention tracked toward ce-ops#65 and adds parser
  unit coverage for the closing-ref grammar.
