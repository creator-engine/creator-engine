---
kind: decision-record
record_type: adr
schema_version: "1"
id: ADR-0010
title: "Take the first-party app wheel out of authored PRs (implementation of ADR-0006)"
status: accepted
date: "2026-06-21"
decision_makers: ["ce-arch-merge-throughput"]
consulted: []
informed: []
review_by: "2026-12-21"
mutation_class: governance
ratification:
  ratified_by: ce-dev-2
  ratified_at: "2026-06-21"
  ratification_prompt_sha: "87727ac82943652c2d18530487c49e809669f9ab3420b96f5bfa0dcff8a9c652"
  quorum: n1_solo
  # N=1 native mode: ratified by the sole resolved human (the Operator, login
  # ce-dev-2 per .ce/coordination.yml identity_map -> human_id peer-operator),
  # decision authored by a distinct agent label (ce-arch-merge-throughput).
evidence_refs:
  - kind: issue
    ref: "ce-ops#164 — small-PR / merge-unit policy; the ~61%-of-substantive-PRs wheel-serialization grounding lives here."
    tag: merge-unit-164
  - kind: issue
    ref: "ce-ops#133 — ADR-0006 implementation umbrella (derived artifacts out of the trust path)."
    tag: adr0006-impl-133
  - kind: issue
    ref: "ce-ops#80 — CE release process gap: versioned build + signed publish (the Gate-4 dependency)."
    tag: release-gap-80
  - kind: issue
    ref: "ce-ops#39 — merge-throughput prior art (merge queues); the eventual queue lane."
    tag: merge-queue-39
  - kind: doc
    ref: "docs/architecture/ADR-0006-derived-artifacts-out-of-trust-path.md — the ratified architecture this ADR implements (Gates 2-3)."
    tag: adr0006-arch
  - kind: doc
    ref: "validators/tests/unit/test_wheelhouse_built_surface.py — the author-side drift guard that is the serialization point."
    tag: drift-guard
crosswalk:
  informs:
    - ce-ops#164
    - ce-ops#133
    - ce-ops#80
---

# Take the first-party app wheel out of authored PRs (implementation of ADR-0006)

## Context and Problem Statement

CE commits a derived first-party binary, the application wheel
`validators/wheelhouse/creator_engine_validator-*.whl` (plus its line in
`validators/wheelhouse/SHA256SUMS`), into git. Measured over CE's own history,
**17 of the last 28 first-parent merges (61%) touched the wheelhouse**; every
substantive `feat`/`fix` code PR rebuilds the wheel because
`test_wheelhouse_built_surface.py` asserts the committed wheel's bundled command
surface equals current source. Because the wheel is binary, any two in-flight
code PRs cannot auto-merge — the second to land is forced into a rebuild +
rebase. This is CE's dominant merge-throughput tax (the "rebase-hell" named by
ce-ops#165 / ADR-0009).

The target architecture is already ratified: **ADR-0006 (accepted, ratified by
the Operator 2026-06-19) chose to un-commit the first-party app wheel, build it
in CI, and publish it via a signed release**, keeping vendored dependency wheels
in git. ADR-0006 is design-only; its Gates 2-5 are unbuilt. This ADR decides the
**implementation strategy and sequencing** for Gates 2-3 — the part that removes
the merge tax — without overturning ADR-0006.

The committed first-party wheel guards a **drift / reproducibility attestation**
("the shippable wheel is provably built from this exact source, offline"). It
does **not** guard the offline install path: end-user offline install
(`docs/install.sh`) runs from a published, signed `/downloads/<version>/`
artifact, and CI/no-egress contexts consume the **dependency** wheelhouse (which
stays committed). Removing the first-party wheel therefore does not weaken
hermetic install — provided an automated step rebuilds-and-verifies it in place.

## Decision Outcome

Chosen option: **hybrid — bake now, un-commit later.**

- **Phase A.** The author-side wheel-drift gate (`test_wheelhouse_built_surface`'s
  first-party-wheel parity assertions, currently a required author-blocking check)
  is relaxed so source PRs do not rebuild or commit the first-party wheel. A
  **lightweight push-to-main CI job** (NOT blocked on the full merge-queue
  #39/#164) rebuilds the wheel from merged source, re-pins the `SHA256SUMS`
  app-wheel line, verifies wheel⇄source parity, and commits the regenerated wheel.
  The committed wheel, the dependency wheelhouse, `install.sh`, and every offline
  consumer are otherwise **unchanged** — no trust-path or install-path change in
  Phase A. Between gate-relaxation and the bake job, the committed wheel may be
  transiently stale; this is acceptable because it is a drift-attestation, not the
  install authority.
- **Phase B (ADR-0006 Gate 3/4, separate ratification).** Once a CI
  build-and-verify lane is proven and signed-release publication exists, the
  committed first-party wheel is removed, packaging tests build into a tempdir,
  and the bake job degrades into Gate-2 verify-only.

The push-to-main bake job may author the regenerated-wheel commit (it writes a
purely derived artifact from already-merged, already-reviewed source), under two
constraints: (a) the bake is deterministic and verifiable — the committed wheel
must provably equal a fresh build of the merged source; (b) it runs only on
already-merged source, never as a pre-review injection path.

## Consequences

- Good — eliminates the ~61% author-side wheel conflict (the highest-leverage
  single merge-throughput fix); decoupled from the merge-queue via a push-to-main job.
- Good — Phase A carries zero trust-path/install risk; offline/hermetic install untouched.
- Good — attestation strengthens: the wheel is only ever built by an automated
  step from merged source, never hand-built by an author.
- Good — stays on the ratified ADR-0006 trajectory; the bake step becomes Gate-2's verifier.
- Bad — between gate-relaxation and the bake job, a transiently-stale committed
  wheel lives on main; mitigated because it is a drift-attestation, not install authority.
- Bad — Phase B still depends on the signed-release pipeline (ce-ops#80, Sept-gated)
  and is correctly gated behind its own ratification.

## Gate Boundary Statement

This ADR decides implementation strategy/sequencing for ADR-0006 Gates 2-3. Phase A
binds only the author-side drift-gate relaxation + (later) a push-to-main bake job —
no install/trust-root/release change. Phase B (remove the committed wheel; re-point
install) remains a separate Operator-ratified gate under ADR-0006.
