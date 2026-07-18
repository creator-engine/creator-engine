---
slug: ce-606-runtime-policy-hardening
date: 2026-07-18
kind: security
scope: runtime-policy dispatch materialization and pair-commit recovery
issue: ce-ops#606
work_class: S
---

**security(launcher): dirfd-walk dispatch materialization + recovery hardening**

Closes the five hardening findings from the two-key review of the runtime-policy
slice. Dispatch-policy materialization now resolves every directory component
with a dir_fd-relative no-follow walk from the filesystem root, so no
intermediate symlink swap can relocate the per-dispatch policy copy; mkdir
failures beyond collisions surface as typed launch refusals, and hosts without
dir_fd support refuse fail-closed. The onboarded policy/receipt pair commit
restores both names best-effort on recovery, preserves any last-known-good
recovery link whose restore fails, chains the original error under a typed
recovery failure, and checks the existing pair's mode with lstat semantics.
The onboarding destination-directory walk is made consistent with the same
dirfd no-follow resolution and refuses unnormalized traversal components.
