---
slug: ce185-broker-slice1
date: 2026-06-22
kind: added
scope: devops privileged-action broker validator/runtime
issue: ce-ops#185
work_class: feature
---

Adds Slice-1 of the DevOps privileged-action broker runtime substrate.

- Adds a fail-closed broker skeleton that ingests
  `privileged_action_envelope` wrappers, runs schema, capability-coherence,
  semantic no-secret, and execution-policy validation, then dispatches only to
  local stub executors for `broker-proxies` and `capability-handoff`.
- Adds a YAML-backed append-only broker ledger that reuses the existing
  `runtime_evidence_spine.append` / `verify_chain` hash-chain semantics for
  value-free decision and action evidence.
- Adds a registered validator check that discovers top-level broker envelope
  YAML outside `schemas/`, `templates/`, and `.tmp.` artifacts.
- Adds focused unit coverage for the worked SSH-sign pilot, structural denials,
  coherence denials, semantic secret denials, execution-policy denials, refusal
  ledger behavior, handoff dispatch, chain verification, and check discovery.

No live OpenBao, SSH, network, shell, subprocess, or privileged execution is
introduced in this slice.
