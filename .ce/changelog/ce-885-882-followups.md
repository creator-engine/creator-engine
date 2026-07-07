---
slug: ce-885-882-followups
date: 2026-07-07
kind: fix
scope: onboard workflow refresh + brain ledger preflight coverage
issue: CE-885, CE-882
---

**Close the #885 and #882 follow-up batch with explicit refusals and test pins.**

- Refuse `ce install --refresh-workflow --spec ...` instead of silently ignoring
  the supplied spec path.
- Surface trimmed workflow-refresh write stderr in the human-readable failure
  detail.
- Pin refresh data protection for non-CE workflow files.
- Pin PR preflight fail-closed behavior when the comparison base is unprovable,
  and pin the unchanged-ledger fast path so it avoids ledger tail hashing.
