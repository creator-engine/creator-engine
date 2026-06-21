---
slug: ce164-work-sizing-floor
date: 2026-06-21
kind: added
scope: work-sizing floor classifier
issue: ce-ops#164/#170
---

Add the G5 Work-sizing F2 deterministic floor check as a separate validator
surface alongside the existing F1 sizing-record ceremony.

- Added a registered `work_sizing_floor` check for persisted
  `work-sizing-floor-record` YAML records.
- Added a pure `git diff --numstat` parser, local generated/lockfile/vendored
  exclusions, threshold classifier, and derived `sizing_floor` projection.
- Added deterministic PR-diff enforcement via `run_with_base` and the
  `verify-work-sizing-floor` CLI subcommand.
- Added schema and offline tests proving threshold boundaries, exclusions,
  projection drift detection, omitted/understated-record enforcement, excluded
  actual-diff paths, and under-floor declared work-class rejection.
