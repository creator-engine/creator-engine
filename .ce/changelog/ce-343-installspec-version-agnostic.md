---
slug: ce-343-installspec-version-agnostic
date: 2026-06-28
kind: fix
scope: installer tests
issue: ce-ops#343
---

**version-agnostic install-spec tests.**

- **Declared work class:** story
- Install-spec tests derive current package version, wheel names, and versioned mirror paths from canonical SEMVER.
