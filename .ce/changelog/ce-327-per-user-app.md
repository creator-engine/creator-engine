---
slug: ce-327-per-user-app
date: 2026-06-28
kind: fix
scope: onboarding github app identity
issue: ce-ops#327
---

Refuse contained-seat onboarding when `github.app.kind: own` points at a known
foreign CE App id, and surface per-user GitHub App creation guidance in the
onboarding manifest.
