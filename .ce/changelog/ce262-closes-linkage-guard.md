---
slug: ce262-closes-linkage-guard
date: 2026-06-26
kind: added
scope: validator — PR closes-linkage guard
issue: ce-ops#262
---

Added `pr_closes_linkage` offline validator check: enforces that every PR
body/carrier contains exactly one `Closes creator-engine/ce-ops#<N>` linkage
line referencing a valid ce-ops issue number. This is the complementary
LINT-side guard to the autoclose bot introduced in the same ticket
(ce-ops#262). The check is registered in `checks/__init__.py` and covered by
`validators/tests/unit/test_pr_closes_linkage.py`.

Existing unit tests that construct synthetic carrier content are updated to
include a valid closes-linkage line so they pass the new guard without
triggering false positives.
