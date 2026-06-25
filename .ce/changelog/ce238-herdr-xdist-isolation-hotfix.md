---
slug: ce238-herdr-xdist-isolation-hotfix
date: 2026-06-25
kind: fixed
scope: herdr steer-lock test isolation
issue: ce-ops#238
---

**isolate herdr steer locks under xdist.**

- Extract `_default_steer_lock_dir()` and add an autouse fixture pinning it to a per-test tmp_path so xdist tests no longer leak steer leases (fixes main-red after #443).
