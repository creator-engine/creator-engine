---
kind: hermes-handoff
role: implementer
mode: tracked-file-implementation
controller: example-controller
ratifier: source
source_authorization_path: .hermes/recommended-prompts/example.md
source_authorization_sha256: 0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef
repo: creator-engine
base_branch: main
base_commit: 0123456789abcdef0123456789abcdef01234567
allowed_paths_count: 2
allowed_paths_sha256: 7f5184abd8376a52be9a346bd180157e65885f1154a0a682ec15e2bdcea2bb41
stop_line: EXAMPLE BATCH COMPLETE; AWAITING VERIFICATION.
---

# Handoff (malformed): manifest count mismatch

The declared `ALLOWED_PATHS_COUNT` below claims 2 paths but the
fenced manifest contains 3 unique lines. The validator's
`path_manifest_count_mismatch` error class catches this.

The declared SHA256 IS the correct SHA256 of the actual 3-line
normalized manifest, so this fixture isolates the count-mismatch
error class without also raising a hash mismatch.

## Authorized path manifest

ALLOWED_PATHS_COUNT=2
ALLOWED_PATHS_SHA256=7f5184abd8376a52be9a346bd180157e65885f1154a0a682ec15e2bdcea2bb41

```text
docs/example/file-a.md
docs/example/file-b.md
docs/example/file-c.md
```

The implementer is expected to halt with
`path_manifest_count_mismatch`.

## Stop line

```text
EXAMPLE BATCH COMPLETE; AWAITING VERIFICATION.
```
