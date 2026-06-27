---
slug: ce-arad-pilot-runbook
date: 2026-06-27
kind: added
scope: pilot co-drive runbook
issue: ce-ops#319
---

**Pilot co-drive runbook (internal).**

- Added `playbooks/controller/runbooks/arad-pilot.md`: the durable, reusable procedure for taking a new pilot user from a cold machine to their first governed, Operator-ratified PR.
- Homed in `playbooks/**` (outside the public-docs confidentiality scan surface) so it can name internal mechanics (pilot repo, reviewer login, App cred path) without leaking into the served `docs/**` tree and without an allowlist edit.
- No secret values embedded; credentials referenced by path/name only; the approver-ref is documented as a value-free 64-hex digest.
- Closes ce-ops#319.
