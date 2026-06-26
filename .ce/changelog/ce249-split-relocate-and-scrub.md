---
slug: ce249-split-relocate-and-scrub
date: 2026-06-26
kind: changed
scope: public docs surface (docs/operations, docs/delivery, docs/architecture, docs/governance) / confidentiality guard
issue: ce-ops#249
---

**Public-repo confidentiality split (ce-ops#249): relocate internal fleet/ops/
strategy docs to the private tracker and scrub the product docs that stay.**

- **Removed 23 internal-only documents from the public surface.** Internal
  fleet/daemon/rehearsal operations runbooks, live delivery-tracking instances
  (backlog / kanban / dependencies / risk register / public-readiness gate),
  internal strategy/research design notes, and the OpenAI-account-switch
  script/report are deleted from the public repo. They are preserved verbatim
  in the private internal tracker (byte-identical backup), which is now their
  single home.
- **Scrubbed 8 product docs that remain public.** Confidential internal-tracker
  ticket references were reworded to generic phrasing; account logins in the
  GitHub-native coordination protocol were generalized to "the reviewer
  identity" / "the author identity"; and the controller runtime contract's one
  host-specific mention was generalized to "GPU host." The docs keep their
  product value with zero internal leakage.
- **De-linked the surviving docs from the relocated set.** Every relative
  Markdown link that pointed at a now-removed internal doc was converted to a
  plain inline filename reference, so the public docs carry no dangling links
  (the `#476` dangling-internal-doc-link guard stays green).
- **Shrank the confidentiality debt-ratchet allowlist.** The deleted and the
  now-clean files were removed from `_KNOWN_PENDING` in the public-docs
  confidentiality guard, keeping the allowlist honest (it may only shrink).
