---
slug: ce-427-approver-ref-provenance
date: 2026-07-09
kind: changed
scope: install answers ratification provenance
---

Install answers ratification bindings can now carry client App provenance for
the approver reference. A focused minting helper derives and verifies the
client-bound digest, while the schema keeps legacy bindings valid and requires
complete provenance when the provenance object is present.
