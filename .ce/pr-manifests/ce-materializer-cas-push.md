# PR path manifest - ce-materializer-cas-push

- **Declared work class:** M

Scope:
- Add deterministic materialization commit construction for the brain intent materializer.
- Add a guarded compare-and-swap push path that rescans after stale remote movement.
- Add focused unit coverage for construction determinism, disarmed push refusal, and CAS rescan behavior.

Out of scope:
- Enabling arming.
- Adding external distributed locking.
- Changing HELD or dry-run artifact formats.

Canonicalization:
`sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=5

AUTHORIZED_PATHS_SHA256=cc5e8aa9c394a90f3f4c97d0e3442d9c60c75bd631585f78fcb6c34f8d74c377

```text
.ce/changelog/ce-materializer-cas-push.md
.ce/pr-manifests/ce-materializer-cas-push.md
validators/creator_engine_validator/brain_intent_materializer.py
validators/tests/unit/test_brain_intent_materializer_commit_push.py
validators/tests/unit/test_brain_intent_materializer_dryrun.py
```
