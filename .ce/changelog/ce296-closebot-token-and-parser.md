---
slug: ce296-closebot-token-and-parser
date: 2026-06-27
kind: changed
scope: ce-ops autoclose bot — token fallback + title parser
issue: ce-ops#296
---

**close-bot token fallback + ce-NNN title parsing.**

Adds a CE_OPS_TOKEN env fallback alongside CE_CROSS_REPO_TOKEN in the ce-ops-autoclose workflow (fail-open if absent), extends the issue-ref parser with a bare ce-NNN title pattern that deduplicates against existing ce-ops#N matches, and adds unit coverage for the title-scan path and token fallback behaviour.
