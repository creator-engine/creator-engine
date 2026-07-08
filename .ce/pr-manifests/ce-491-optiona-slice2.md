# PR path manifest — ce-491-optiona-slice2

Per-PR carrier for branch `ce-491-optiona-slice2`.

Scope:
CE-491 Option A merge-time brain append intent materializer, slice 2. This slice keeps `ARMING_ENABLED = False`, adds only dry-run/importable materializer surfaces, and does not add live git write or GitHub API write paths.

- **Declared work class:** M

Changes:
- Wire `brain_append_intent_xor_direct_ledger` into `pr_preflight.run_preflight` as a hard gate.
- Add `HistoryScanner`, `CloseoutWindowPolicy`, and `MaterializerRunLoop` library APIs.
- Add focused unit coverage for HELD state guards, scanner ordering, closeout boundary behavior, and run-loop dispatch.
- Record the brief/design conflict resolution: malformed `BrainAppendRefusal` paths continue to enter HELD with quarantine per the hard invariant and existing slice-1 behavior.

Canonicalization:
`sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=8

AUTHORIZED_PATHS_SHA256=e6dd7fb1d9e4696975c2b3594006f8595a04d9805ec682de1069eca390a6b986

```text
.ce/changelog/ce-491-optiona-slice2.md
.ce/pr-manifests/ce-491-optiona-slice2.md
validators/creator_engine_validator/brain_intent_materializer.py
validators/creator_engine_validator/pr_preflight.py
validators/tests/unit/test_brain_intent_materializer_closeout.py
validators/tests/unit/test_brain_intent_materializer_hold.py
validators/tests/unit/test_brain_intent_materializer_runloop.py
validators/tests/unit/test_brain_intent_materializer_scan.py
```
