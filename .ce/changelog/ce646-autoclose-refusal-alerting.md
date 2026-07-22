---
slug: ce646-autoclose-refusal-alerting
date: 2026-07-22
kind: fixed
scope: ce-ops autoclose governance refusal visibility
issue: ce-ops#646
---

**Surface autoclose parser-shim refusals through governance alerting.**

Route module-level parser-shim refusals through the existing non-blocking governance alert path before retaining a constant, fail-closed RuntimeError. Missing or unloadable shims retain the unavailable refusal, while execution or binding failures use a distinct load-failed refusal; both are covered by hermetic synthetic-alert tests. The autoclose workflow remains untouched; post-merge observation is whether its alert token/environment is available on the next PR-close run.
