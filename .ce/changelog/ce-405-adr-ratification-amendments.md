---
slug: ce-405-adr-ratification-amendments
date: 2026-07-06
kind: changed
scope: governance / brain ledger append ADR
issue: ce-ops#405
---

**Ratify ADR-0005 with three ratification-time amendments.**

Marks ADR-0005 as Ratified (Operator, 2026-07-06, day-arc D3 batch). Adds
same-day evidence of the full 2026-07-05 five-fold ledger-serialization pileup
(#838/#835/#836 three-way chain-position collision plus #843 branch recompute).
Strengthens §6 merge-gate evidence requirement from "may require" to "must
require". Adds §8 enforcement note that out-of-band appends bypassing the daemon
are refused at the merge gate once it ships.

Docs/governance only: no implementation, no ledger schema change, no
`.ce/brain/**` mutation.
