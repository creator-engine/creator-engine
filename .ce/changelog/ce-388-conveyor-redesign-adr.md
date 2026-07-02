---
slug: ce-388-conveyor-redesign-adr
date: 2026-07-02
kind: added
scope: conveyor daemon security-redesign ADR
issue: ce-ops#388
---

Added ADR-0004 proposing the conveyor daemon arm-safety-by-construction model.
The ADR makes discovery payloads data-only, moves checkout and git/gh authority
to daemon-owned working directories and pinned daemon config, treats imported
bundle contents as untrusted validation input, and blocks G-N3 arming until an
independent security review ratifies explicit arming criteria.
