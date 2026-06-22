---
slug: ce89-controller-seat-exclusivity-doc
date: 2026-06-22
kind: documented
scope: controller launch/runtime identity
issue: creator-engine/creator-engine#89
---

Document duplicate live mutation-capable Controller-seat refusal semantics.

This docs-only slice defines `controller_id` as the durable live-exclusive
mutation authority identity within a repo/project/profile scope, separates that
identity from concrete process/session/pane/sentinel evidence, and records the
future `ce launch` / `ce hud` contract: refuse duplicate same-identity
mutation-capable Controller seats before side effects unless attaching/resuming
the live seat, completing ratified transfer/terminalization, or entering
explicit read-only observer mode with mutation disabled.

This does not add runtime behavior, schemas, validators, tests, GitHub
authority, credential handling, or provider/account changes.
