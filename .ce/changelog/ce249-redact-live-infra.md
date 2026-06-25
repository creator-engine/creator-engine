---
slug: ce249-redact-live-infra
date: 2026-06-25
kind: fix
scope: docs
issue: ce-ops#249
---

**redact live-infra identifiers from public repo.**

Redact live tailnet host/VPS IP, Hetzner, operator handle (->chmod735+n1_solo), and pitch-arc framing from public docs; confidentiality CI guard ratchet. (Non-own .ce carriers not touched per one-carrier-per-PR.)
