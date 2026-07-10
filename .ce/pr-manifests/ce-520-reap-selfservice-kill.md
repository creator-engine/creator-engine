# PR path manifest - ce-520-reap-selfservice-kill

Per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`, ce-ops#21 convention).
This is the closed path set for the `ce reap once` stale tmux self-service kill
guidance slice.

- **Declared work class:** S

Per-file purpose:

- **`.ce/changelog/ce-520-reap-selfservice-kill.md`** *(A)* - changelog fragment.
- **`.ce/pr-manifests/ce-520-reap-selfservice-kill.md`** *(A)* - this closed path-set carrier.
- **`validators/creator_engine_validator/seat_reaper.py`** *(M)* - threads stale-live tmux operator guidance into status/once payloads and escalation records.
- **`validators/tests/unit/test_seat_reaper.py`** *(M)* - pins the exact-session `tmux kill-session` guidance for stale live tmux launch surfaces.

Canonicalization:
`sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=4

AUTHORIZED_PATHS_SHA256=e98502c3538034313718adfc632f6dcbeef18fd57c04b0cbf47f62ae0f97f071

```text
.ce/changelog/ce-520-reap-selfservice-kill.md
.ce/pr-manifests/ce-520-reap-selfservice-kill.md
validators/creator_engine_validator/seat_reaper.py
validators/tests/unit/test_seat_reaper.py
```
