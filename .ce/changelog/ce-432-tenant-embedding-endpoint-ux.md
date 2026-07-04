# Tenant embedding endpoint UX

- Added explicit launch-time brain recall configuration via `CE_BRAIN_RECALL_EMBEDDER`, `CE_BRAIN_RECALL_ENDPOINT`, `CE_BRAIN_RECALL_ENDPOINT_MODEL_ID`, and `CE_BRAIN_RECALL_ENDPOINT_DIM`.
- Added `recall_status` to Controller brain-bootstrap payloads and launch result JSON so unconfigured/unavailable recall is visible while SSOT bootstrap remains fail-closed.
- Added a non-fatal `ce doctor` recall endpoint advisory check.
- Updated launch runtime tests for hydrated, unavailable, and unconfigured recall states.
- Rework: added real unit tests for `probe_controller_recall_endpoint` (no-endpoint shortcut, http/https default-port selection, malformed endpoint, real reachable/unreachable sockets) and for `CE_BRAIN_RECALL_ENDPOINT_DIM` invalid-value graceful degradation.
- Rework: launch path now fails fast on a configured-but-unresponsive recall endpoint via a cheap bounded pre-probe before `open_surface(...).hydrate_session(...)`, and passes a short explicit timeout (`LAUNCH_RECALL_ENDPOINT_TIMEOUT_SECONDS`) to the embedding adapter instead of its 60s default.
- Rework: non-blocking folds — corrected doctor docstring, added a `[WARN]` marker for the non-fatal advisory check, and downgraded UNCONFIGURED launch logging from WARNING to info-level.
