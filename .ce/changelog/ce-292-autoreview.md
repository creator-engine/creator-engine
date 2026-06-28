---
slug: ce-292-autoreview
date: 2026-06-27
kind: added
scope: Claude reviewer self-fire wrapper
issue: ce-ops#292
work_class: tiny
---

Added the `/code-review` self-fire wrapper and AGENTS operating line that route
pre-PR and pre-merge reviewer evidence through a fresh-context reviewer worker.
The wrapper posts only `COMMENT` or `REQUEST_CHANGES` evidence and explicitly
keeps approval out of this self-fired path.

Added behavioral validator coverage for the self-fire review submission path so
an attempted `APPROVE` event is refused before any raw review POST is emitted.
