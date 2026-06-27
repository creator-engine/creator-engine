---
slug: deterministic-citations-brain-gotcha
date: 2026-06-27
kind: added
scope: knowledge-ssot / design learning (internal)
issue: ce-ops#310
---

**Persisted a durable design gotcha in the Knowledge-SSOT: deterministic
citations for doc-grounded agents.**

- **Added Knowledge-SSOT assertion** (`.ce/brain/assertions.yaml`, type
  `gotcha`, scope `global`, verification `static`): any outward-facing
  doc-grounded / customer-support agent must ground via **docs-as-skills**
  (load specific allowlisted doc files on demand) rather than RAG/embeddings or
  context-stuffing, so it cites the EXACT source file+section it loaded. This is
  the load-bearing mechanism that makes cite-or-refuse enforceable, gives a
  verifiable user trail, enforces confidentiality at bundle-build time, and
  makes freshness checkable. The assertion is content-addressed to its evidence
  note (`source_sha256`).
- **Added `.ce/brain/notes/deterministic-citations.md`** — the tracked design
  note the assertion cites (resolvable in a fresh clone), capturing the
  principle, why it is load-bearing, and why it is a non-obvious gotcha.
- **Updated `validators/tests/unit/test_ce_brain_drift.py`** — the
  authoritative-ledger test now expects the new active assertion (count 9 → 10)
  and asserts the gotcha record is present and artifact-backed.

Internal knowledge layer only; no public `docs/**` surface and no
behaviour/code change. Chosen over a public ADR/design doc to keep the unshipped
support-agent feature out of the published surface while making the general
design principle durable and recallable via `ce brain recall`.
