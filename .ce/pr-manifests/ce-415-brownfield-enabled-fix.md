# PR path manifest - ce-415-brownfield-enabled-fix

Per-PR carrier (`.ce/pr-manifests/<branch-slug>.md` convention).
This is the closed path set for deriving `brownfield.enabled` from real probe
signals.

Per-file purpose:
- **`.ce/changelog/ce-415-brownfield-enabled-fix.md`** *(A)* - changelog fragment.
- **`.ce/pr-manifests/ce-415-brownfield-enabled-fix.md`** *(A)* - this closed path-set carrier.
- **`validators/creator_engine_validator/v3_cli.py`** *(M)* - derive CLI probe `enabled` from history/workflow/test signals.
- **`validators/creator_engine_validator/v3_installer.py`** *(M)* - project `brownfield.enabled` from probe signals instead of a default-true field.
- **`validators/tests/unit/test_v3_cli.py`** *(M)* - cover empty non-git and signal-bearing probe behavior.
- **`validators/tests/unit/test_v3_installer.py`** *(M)* - cover stale/default-true probe suppression when no real signals exist.

Canonicalization:
`sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=6

AUTHORIZED_PATHS_SHA256=12858648e537fca2bae89d264de2083ead0a34c788b1179344fe11f534e0fa29

```text
.ce/changelog/ce-415-brownfield-enabled-fix.md
.ce/pr-manifests/ce-415-brownfield-enabled-fix.md
validators/creator_engine_validator/v3_cli.py
validators/creator_engine_validator/v3_installer.py
validators/tests/unit/test_v3_cli.py
validators/tests/unit/test_v3_installer.py
```
