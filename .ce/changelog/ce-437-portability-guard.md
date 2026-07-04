---
slug: ce-437-portability-guard
date: 2026-07-04
kind: feature
scope: validators
---

Added a control-plane portability guard that blocks undeclared Linux runtime-plane
assumptions in validator modules while preserving current debt through explicit
runtime-plane declarations and dated baseline exemptions.

Reworked command detection to catch wrapped or absolute-path runtime commands and
added fail-closed manifest coverage for missing, malformed, and stale baseline
entries.
