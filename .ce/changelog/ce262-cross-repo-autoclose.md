---
slug: ce262-cross-repo-autoclose
date: 2026-06-26
kind: added
scope: github-actions
issue: ce-ops#262
base: d5cf03d12e3fe307d178ac4820159ee014a4d7db
---

Enhance cross-repo ce-ops autoclose bot to close issues referenced in PR titles.

- Adds title-scan path: every ``ce-ops#N`` token in a PR title is auto-closed
  on merge (no closing keyword required; CE PR titles embed the issue, e.g.
  ``feat(ce-ops#262): ...``).  Body ``Closes/Fixes/Resolves ce-ops#N`` refs
  continue to work (ce-ops#154 behavior preserved).
- Extracts parsing logic into ``tools/ce-ops-autoclose/parse_issue_refs.py``
  (stdlib-only, no install required) so the three functions —
  ``parse_title_refs``, ``parse_body_closing_refs``, and ``parse_all_refs`` —
  can be unit-tested independently of the workflow driver.
- Updates ``.github/scripts/ceops_autoclose.py`` to import from the shared
  parser module and to accept ``CE_CROSS_REPO_TOKEN`` as the primary secret
  name (``CE_OPS_TOKEN`` kept as legacy fallback for existing configurations).
- Updates ``.github/workflows/ce-ops-autoclose.yml`` to pass
  ``CE_CROSS_REPO_TOKEN`` to the driver step.
- Adds 27 unit tests in ``validators/tests/unit/test_ce262_parse_issue_refs.py``
  covering title-only, body-keyword, combined, dedup, cross-repo form,
  case-insensitivity, and none-found cases.
- Maintains full backward compatibility with existing
  ``test_ceops_autoclose.py`` (all 11 tests continue to pass).
