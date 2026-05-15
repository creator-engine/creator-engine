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
allowed_paths_sha256: deadbeefdeadbeefdeadbeefdeadbeefdeadbeefdeadbeefdeadbeefdeadbeef
stop_line: EXAMPLE BATCH COMPLETE; AWAITING VERIFICATION.
---

# Handoff (malformed): manifest hash mismatch

The declared `ALLOWED_PATHS_SHA256` below does NOT equal the
recomputed SHA256 of the normalized fenced manifest. The validator's
`path_manifest_hash_mismatch` error class catches this.

The declared count IS correct, so this fixture isolates the
hash-mismatch error class.

## Authorized path manifest

ALLOWED_PATHS_COUNT=2
ALLOWED_PATHS_SHA256=deadbeefdeadbeefdeadbeefdeadbeefdeadbeefdeadbeefdeadbeefdeadbeef

```text
docs/example/file-a.md
docs/example/file-b.md
```

The implementer is expected to halt with
`path_manifest_hash_mismatch`.

## Stop line

```text
EXAMPLE BATCH COMPLETE; AWAITING VERIFICATION.
```
