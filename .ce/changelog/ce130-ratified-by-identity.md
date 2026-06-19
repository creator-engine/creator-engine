---
slug: ce130-ratified-by-identity
date: 2026-06-19
kind: changed
scope: decision-record validation
issue: ce-ops#130
---

Decision records now require accepted `ratification.ratified_by` values to name
the concrete ratifier handle rather than a generic role placeholder such as
`the Operator`.

Updated ADR-0005 to record the actual ratifier handle, refreshed the
decision-record contract/schema wording, and rebuilt the validator app wheel so
the packaged check matches source.
