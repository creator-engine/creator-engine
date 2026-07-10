# Materializer CAS Push Pre-Arming

- Added deterministic materialization commit construction for merge-time brain append intents.
- Added compare-and-swap push handling that abandons stale commits and rescans before rebuilding.
- Preserved disabled arming by keeping push refusal behind the arming guard while allowing disarmed commit inspection.
- Added focused unit coverage for deterministic construction, CAS push refusal, and rescan behavior.
