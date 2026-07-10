---
slug: ce-n15a-skip-anomaly
date: 2026-07-10
kind: added
scope: merge queue daemon detection
---

Added detection-only alarms for repeated identical skip decisions and PRs that
remain approved without merging beyond their configured pass-age threshold.
Alarms are recorded beside the daemon liveness state and emitted loudly to
journald; they do not alter queue decisions or PR state.
