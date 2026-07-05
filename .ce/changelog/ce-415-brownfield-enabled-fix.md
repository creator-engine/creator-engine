---
slug: ce-415-brownfield-enabled-fix
date: 2026-07-05
kind: fixed
scope: installer brownfield inventory
issue: ce-415
---

Derive `brownfield.enabled` from real brownfield probe signals instead of
defaulting empty probes to true. Empty non-git directories now report disabled
brownfield adoption, while detected Git history, workflows, or test commands
enable the brownfield inventory.
