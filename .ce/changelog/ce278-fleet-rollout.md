---
slug: ce278-fleet-rollout
date: 2026-06-27
kind: feature
scope: [validators/creator_engine_validator/surfaces, validators/creator_engine_validator/ce_cli.py]
issue: ce-ops#278
---

- **Declared work class:** Feature

Added `ce surfaces fleet-rollout` subcommand that performs seat-by-seat fleet
rollout of updated rented-surface versions: stops each seat, applies
manifest-derived EnvironmentFile updates via render.py, relaunches via
canonical `ce launch`, and audits every stop/relaunch to the side_effect_ledger.
