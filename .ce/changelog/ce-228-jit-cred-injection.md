---
slug: ce-228-jit-cred-injection
date: 2026-07-06
kind: story
scope: Add mint-seat-credential / revoke-seat-credential to egress host broker; model-api + forge-scoped classes; flock-serialized single-active store; failure-direction tests.
issue: 228
---

**feat(broker): add JIT seat credential lane (ce-ops#228 slice 1).**

Add JIT seat credential lane to the egress host broker (ce-ops#228 slice 1).

Contained seats can now request short-TTL credentials at run time via the broker
socket (`mint-seat-credential` / `revoke-seat-credential` verbs). The host
validates the per-seat class allowlist, mints at request time, and returns the
secret only in the authenticated Unix socket response. No Docker/env/argv/exec
delivery surface is created.

Credential classes v1: `model-api` and `forge-scoped`. The `forge-scoped` class
reuses the existing `ScopedToken`/`TokenRequest` machinery from the ce-475
read-lane (not duplicated). The host flock serialization pattern from ce-475 is
carried forward for single-active-per-(seat, class) enforcement.

Revocation: TTL expiry via `_expire_locked` + explicit `revoke-seat-credential`
verb; single active credential per seat per class enforced by the store.

Failure-direction coverage: no-env-delivery impossible-by-construction assertion,
unknown class refused and audited, TTL expiry enforced, concurrent mint serialized
through flock.

Harvested from contained seat dev-3 (self-push gap, ce-ops#337).
