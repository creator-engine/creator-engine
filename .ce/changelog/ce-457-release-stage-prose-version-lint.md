---
slug: ce-457-release-stage-prose-version-lint
date: 2026-07-05
kind: fixed
scope: release staging / install-spec signing seam
issue: ce-ops#457
---

**release-stage prose version lint.**

- Added a fail-closed release-stage lint over canonical install-spec prose before signing bytes are hashed or emitted.
- The lint refuses semver-looking prose strings that do not match the target release version and reports the offending line/string.
- Added release-publish regressions for stale prose refusal and clean matching prose emission.
