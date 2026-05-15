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
allowed_paths_count: 1
allowed_paths_sha256: 1a4f557a9a25285d61f908e02c2ad32f3a919ef7e36101d692275cd464ba9150
stop_line: EXAMPLE BATCH COMPLETE; AWAITING VERIFICATION.
---

# Handoff (malformed): init.py paste-pipeline corruption

This fixture exercises the
`path_manifest_init_py_corruption` regression class. The fenced
manifest below is what an envelope would look like AFTER a paste
pipeline collapsed `__init__.py` into `init.py`. The declared count
and SHA256 match the corrupted manifest exactly, so a naive
preflight that only checks count/hash would pass; the validator's
`path_manifest_init_py_corruption` error class catches the
regression anyway.

See `docs/operations/NO_COPY_PASTE_PATTERN.md` §i.

## Authorized path manifest

ALLOWED_PATHS_COUNT=1
ALLOWED_PATHS_SHA256=1a4f557a9a25285d61f908e02c2ad32f3a919ef7e36101d692275cd464ba9150

```text
validators/creator_engine_validator/checks/init.py
```

The implementer is expected to halt with
`path_manifest_init_py_corruption`.

## Stop line

```text
EXAMPLE BATCH COMPLETE; AWAITING VERIFICATION.
```
