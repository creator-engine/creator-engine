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
allowed_paths_sha256: fa46444f51f9a07abe40ac52ca7ebb98c43f21cfce7c278a624390710a8247e7
stop_line: EXAMPLE BATCH COMPLETE; AWAITING VERIFICATION.
---

# Handoff: Example well-formed handoff

This fixture exercises the well-formed shape of a Hermes handoff
under `docs/operations/CONTROLLER_BOUNDARY_POLICY.md`,
`docs/operations/NO_COPY_PASTE_PATTERN.md`,
`docs/operations/PATH_MANIFEST_FIDELITY_PROTOCOL.md`, and
`docs/operations/TRANSCRIPT_ARCHIVE_PROTOCOL.md`. It is intentionally
short.

## Authorized path manifest

ALLOWED_PATHS_COUNT=2
ALLOWED_PATHS_SHA256=fa46444f51f9a07abe40ac52ca7ebb98c43f21cfce7c278a624390710a8247e7

```text
docs/example/file-a.md
docs/example/file-b.md
```

The implementer recomputes `count` and `sha256` from the fenced block
on receipt and halts on any mismatch.

## Stop line

```text
EXAMPLE BATCH COMPLETE; AWAITING VERIFICATION.
```
