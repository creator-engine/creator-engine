---
slug: ce-468-cli-exposure-verify-fix
date: 2026-07-06
kind: fix
scope: validators
issue: ce-ops#468
---

**fix: verify_cli predicate tolerates onboard->install verb rename.**

verify_cli() grepped for the legacy onboard verb string which was renamed to install in 0.3.2. Changed invocation to top-level --help and predicate to check usage: <command> in stdout.
