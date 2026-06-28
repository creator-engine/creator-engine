---
slug: ce-preflight-before-push-ssot
date: 2026-06-28
kind: changed
scope: PR/merge SSOT + release runbook (docs/playbooks)
issue: ce-ops#343
---

**Mandate the full offline CI-parity suite (`ce validate-pr`) before pushing
ANY PR — feature, release/publish, and controller-authored alike.**

- **`docs/operations/AUTHOR_A_CE_VALID_PR.md`** — adds a load-bearing
  "MANDATORY before EVERY push — no exemptions" directive: `ce validate-pr`
  (full CI-parity offline suite, whole tree, CLEAN working tree) must go green
  locally before any push, with no "it's just a release/signature ceremony"
  exemption. Notes the offline suite mirrors `validate.yml` (local green ≈ CI
  green) and cites the #603 release-publish incident plus the durable fix
  (ce-ops#343).
- **`playbooks/controller/briefs/merge-gate.md`** — adds a "Preflight
  precondition (before EVERY push, no exemptions)" section restating the same
  rule in the playbook's voice, cross-linked to the author SSOT.
- **`docs/delivery/VERSIONING_AND_RELEASE_POLICY.md`** — adds a
  "Release-publish preflight" section: a release-publish PR is a code change,
  not a signature ceremony; publishing `X.Y.Z` updates `docs/llms-install.md` +
  adds `docs/downloads/X.Y.Z/`, which breaks the version-pinned install-spec
  tests (`test_v3_installer.py`, `test_install_bootstrap.py`,
  `test_onboard_apply_live.py`). The publish PR must run `ce validate-pr`
  locally and update those tests in the same PR before pushing. References the
  #603 incident and the durable version-agnostic-tests fix (ce-ops#343, under
  ce-ops#291 / W2 release-bump).

Docs/playbooks only — no source, test, or release-artifact changes.
