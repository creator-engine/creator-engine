---
slug: ce-559-release-smoke-evidence-gate
date: 2026-07-14
kind: story
scope: validators
issue: ce-ops#559
---

**Fail-closed release smoke-evidence gate.**

Implement the fail-closed release smoke-evidence PR-diff gate.

- Detect release-class changes only when the signed install spec and release-finalize manifest both change.
- Require one canonical, detached-SSHSIG-verified evidence record and the complete typed finalize-manifest contract, both bound to the checked-out spec.
- Wire the gate into both CI merge-queue/PR validation and local preflight, with hermetic focused tests.
- Add the governed post-PR producer path: digest-pinned no-checkout smoke result,
  canonical offline-signing bytes, public-only SSHSIG finalization, exact
  finalized-tree verification, and atomic evidence/carrier output.
- Bind the clean-container result to its observed package, spec, finalize
  manifest, and artifact-set bytes; accept only the version-derived changed
  evidence record across successive releases; and require `ce-root-v1` exactly.
- Shell-quote the copyable OpenSSH signing operand; enumerate and validate every
  unchanged prior evidence record; and bind the installed `ce`/`cev3` version
  plus installer-persisted signed spec to identical pre/post finalized endpoint
  observations and explicit finalized-tree expectations.
- Require the complete installed `ce` and `cev3` build tokens to be identical,
  and transactionally publish staged evidence/carrier bytes only after an
  immediate finalized-tree revalidation, restoring both prior outputs on any
  replacement failure.
