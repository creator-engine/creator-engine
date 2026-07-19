---
slug: ce-621-decisions-governance-class
date: 2026-07-19
kind: fixed
scope: automerge policy — governance predicate set
issue: ce-ops#621
---

**Close MC1 arming blocker: docs/decisions/**, docs/adr/**, docs/governance/** are now governance class.**

ADR-0016 §8 non-goal 8 declares: "ADR or ratification records: governance class; always two-key."
With MC1 (`docs_envelope`) armed, the `docs/**` path predicate previously caused
`docs/decisions/ADR-*.md` to classify as `docs` mutation class — qualifying for
zero-gesture auto-merge. A future ADR landing would then zero-gesture merge,
contradicting the governance requirement.

Changes to `validators/creator_engine_validator/forge/automerge_mutation_policy.yaml`:

- Added `docs/decisions/**` to the `governance` predicate set. This is the
  canonical ADR / ratification record directory (contains ADR-0016 and all
  current formal decision records).
- Added `docs/adr/**` to the `governance` predicate set. The `docs/adr/`
  directory exists in-tree and contains ADR-style records (ADR-0001 through
  ADR-0005); same §8 non-goal 8 basis.
- Added `docs/governance/**` to the `governance` predicate set. The
  `docs/governance/` directory contains canonical governance authority documents
  (`AUTHORITY_AND_RATIFICATION_MODEL.md`, `MUTATION_CLASS_MODEL.md`, etc.) that
  are referenced throughout ADR-0016 as governance authority sources; §8 non-goal
  4 covers "governance changes" and these documents are explicitly in-scope.

Precedence: `mutation_class_for_paths()` (mutation_classifier.py:136–170) is
rank-based; `governance` has rank 5 vs `docs` rank 1 in `class_order`. When a
path matches both `docs/**` and `docs/decisions/**` (governance), governance wins
unconditionally regardless of YAML ordering. No order-sensitivity in placement.

Defense engagement in `decide_automerge`:
- `mutation_class_for_paths(["docs/decisions/ADR-9999-x.md"])` returns `"governance"`.
- `governance` is in `GESTURE_CLASSES`.
- `automerge_policy.py:586`: `if mutation_class in GESTURE_CLASSES ... auto_blockers.append("gesture_class")`.
- `auto_blockers` non-empty → GESTURE returned, even when docs class flag and
  `docs_envelope` tier flag are both armed.

Updated `DOCS_ENVELOPE_PATHS` test fixture in `test_automerge_policy.py`:
the prior fixture used `docs/adr/ADR-0071-docs-envelope-automerge.md` as a
docs-class representative; that path now correctly escalates to governance. The
fixture is updated to `docs/guide/automerge-feature.md` (plain docs path, unaffected).

Updated `DOCS_ENVELOPE_PATHS` test fixture in `test_automerge_actuator.py`:
the same stale `docs/adr/ADR-0071-docs-envelope-automerge.md` entry was present
in the actuator unit test fixture, internally contradicting the PR's invariant.
Replaced with `docs/guide/automerge-feature.md` matching the policy-test companion
fixture exactly. Comment added mirroring `test_automerge_policy.py` style.
