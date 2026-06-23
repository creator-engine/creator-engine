# ce-ops#163 — Worker Spawn Primitive

- Added `ce worker spawn` as a harness-agnostic worker-seat primitive with typed
  roles, depth bounds, explicit worker worktree validation, prompt/brief digests,
  and value-free worker records under `.ce/state/workers/<worker_id>/worker.yaml`.
- Added a v1 `worker_spawn` runtime with a pure planning path, credential-scrubbed
  child environment, and an injectable launcher seam over `launch_runtime.launch`.
- Added unit and CLI coverage for role validation, dry-run no side effects,
  no controller token inheritance, injected launcher use, and version-boundary
  classification.
