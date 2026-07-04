# Tenant embedding endpoint UX

- Added explicit launch-time brain recall configuration via `CE_BRAIN_RECALL_EMBEDDER`, `CE_BRAIN_RECALL_ENDPOINT`, `CE_BRAIN_RECALL_ENDPOINT_MODEL_ID`, and `CE_BRAIN_RECALL_ENDPOINT_DIM`.
- Added `recall_status` to Controller brain-bootstrap payloads and launch result JSON so unconfigured/unavailable recall is visible while SSOT bootstrap remains fail-closed.
- Added a non-fatal `ce doctor` recall endpoint advisory check.
- Updated launch runtime tests for hydrated, unavailable, and unconfigured recall states.
