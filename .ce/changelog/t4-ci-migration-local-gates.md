---
slug: t4-ci-migration-local-gates
date: 2026-07-21
kind: changed
scope: ci/validate
---

**Run formerly local-only repository invariants in CI.**

- Add explicit Validate workflow steps for brain append safety, documentation
  confidentiality and portability, support corpus, fleet manifests, aggregate
  examples, signed artifacts, and dual-format sync.
- Expose the two preflight-only invariants through thin CLI adapters that retain
  the existing preflight implementations.
- Cover the `preflight-gate` parser, dispatch, failure, and unsupported-command
  behavior at the CLI layer.
- Regenerate the checked CLI reference so the new `preflight-gate` command
  surface remains byte-synchronized with the argparse tree.
