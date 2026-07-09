# PR path manifest — ce-conveyor-intake-s1 · conveyor intake queue dry-run planning

Per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`, the path manifest convention). CI runs:

```bash
verify-path-manifest --base <PR base sha> --manifest-dir .ce/pr-manifests --head-ref ce-conveyor-intake-s1
```

and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below.

Base:
`4fae126d179f1c9cf7d618c268ca334036cdc8d7` (`origin/main`, fix review followups batch two).

Summary:
- **Declared work class:** S
- Adds a YAML-backed conveyor intake queue with pending, claimed, and done directories.
- Adds flag-gated daemon runner dry-run planning for idle seats when an intake queue root is configured.
- Adds focused unit coverage and a short design note.

Pre-edit probes:
- `git show origin/main:validators/creator_engine_validator/conveyor_intake_queue.py 2>&1 | head -5` -> `fatal: path 'validators/creator_engine_validator/conveyor_intake_queue.py' does not exist in 'origin/main'`
- `git show origin/main:validators/creator_engine_validator/conveyor_daemon_runner.py | grep -n 'intake\|INTAKE'` -> zero hits

Per-file purpose (the closed path-set — 6 paths):
- **`.ce/changelog/ce-conveyor-intake-s1.md`** *(A)* — changelog fragment.
- **`.ce/pr-manifests/ce-conveyor-intake-s1.md`** *(A)* — this carrier.
- **`docs/design/conveyor-intake-queue.md`** *(A)* — queue layout and scope note.
- **`validators/creator_engine_validator/conveyor_daemon_runner.py`** *(M)* — optional env config and dry-run intake logging.
- **`validators/creator_engine_validator/conveyor_intake_queue.py`** *(A)* — queue primitives and planning reader.
- **`validators/tests/unit/test_conveyor_intake_queue.py`** *(A)* — focused queue and config tests.

Canonicalization:
`sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=6

AUTHORIZED_PATHS_SHA256=59a01a0542bffacf92c133c34c54b4e7f2b42be21f39966ea7367de87165abec

```text
.ce/changelog/ce-conveyor-intake-s1.md
.ce/pr-manifests/ce-conveyor-intake-s1.md
docs/design/conveyor-intake-queue.md
validators/creator_engine_validator/conveyor_daemon_runner.py
validators/creator_engine_validator/conveyor_intake_queue.py
validators/tests/unit/test_conveyor_intake_queue.py
```
