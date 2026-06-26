---
slug: ce235-dequeue-settle
date: 2026-06-26
kind: added
scope: feature -- merge-queue dequeue primitive + integrator settle window
issue: ce-ops#235
---

**dequeue primitive + settle window.**

- Dequeue now checks `repository.mergeQueue.entries` for the target PR and calls GitHub's `dequeuePullRequest` mutation only when queued.
- Unqueued PRs are treated as an idempotent no-op; missing PRs fail clearly.
- Added top-level v1 `ce dequeue <pr>` wiring through a subprocess bridge to preserve the v1/v3 import boundary.
- Made the integrator approval settle delay configurable and testable with injected clock/sleep.
