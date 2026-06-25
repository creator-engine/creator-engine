---
slug: ce242-contained-seat-self-push-pr
date: 2026-06-25
kind: changed
scope: egress broker / contained-seat SELF-PUSH
issue: ce-ops#242
---

**contained-seat self-push via injected credential (transport-deputy).**

Route a contained seat outbound git push through the transport-deputy injection seam: host-side JIT credential injection outside the sandbox; fail-closed without a valid injected cred; token-leak verified (never in seat env/argv/fs/logs). Tests included. (ce-ops#242)
