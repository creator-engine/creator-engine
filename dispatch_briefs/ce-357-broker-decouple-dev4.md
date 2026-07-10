# BRIEF — dev-4 — ce-ops#357: decouple Surface-B review broker from seat working tree

Born-foreman, contained/no-egress (DO NOT push — controller harvests). Fresh branch `ce-357-broker-decouple` off CURRENT origin/main (`git fetch origin main` first). Drive to READY-FOR-HARVEST GREEN; report `git rev-parse HEAD` + the SHA.

## Context (EMBEDDED — you cannot read the ticket; this IS the scope)
CE's Surface-B autonomous-APPROVE review broker runs as a per-seat systemd unit whose `WorkingDirectory` points at a DEV SEAT's own git working tree (e.g. `/home/ce-dev-3/creator-engine`), and it imports `creator_engine_validator.forge` + `egress_broker` directly from that tree. **Problem:** the broker's code version is COUPLED to whatever branch/commit the seat happens to have checked out — any seat changing branches or going stale can break or silently alter the live broker on its next restart (this actually happened during #356 Surface-B pre-stage: a stale import crashed the broker until the seat checkout was advanced).

## Goal — decouple the broker from any seat working tree
The broker must run from a DEDICATED, controller-managed STABLE checkout/pinned location, NOT a seat's tree. This (1) breaks the seat-branch coupling, (2) enables deterministic governance updates via one mechanism, (3) aligns with the clean-install direction (installed/pinned package, not run-from-source).

## Deliverables — code + unit template + governed update script + tests ONLY (host provisioning is controller-side; do NOT attempt to deploy/restart systemd)
1. **Parameterize the broker's runtime location.** Update the systemd unit at `deploy/systemd/ce-egress-self-review.service` (and any `@`-template variant) so `WorkingDirectory` + the import path resolve to a DURABLE, configurable stable path (e.g. `${CE_BROKER_HOME:-/opt/ce-broker/creator-engine}`) — NOT a hard-coded seat home. Keep the existing `CE_EGRESS_RUN_MODE` + `--run-mode` ExecStart wiring intact (that arming knob must survive).
2. **Governed init/update mechanism.** Add a small, idempotent controller-run script (e.g. under `tools/egress-broker/` or `deploy/`) that initializes/updates the stable broker checkout to a pinned origin/main commit (fetch + checkout pinned SHA, verify clean, no seat coupling). Fail-closed: if the target path is missing/dirty or the pin can't be verified, refuse and exit non-zero with a clear reason — never silently run a wrong version.
3. **Broker import robustness.** Ensure `tools/egress-broker/ce_egress_self_review_broker.py` resolves its `creator_engine_validator` import from the stable checkout location (driven by the same env/path), not implicitly from CWD.
4. **Tests:** cover (a) the unit/template renders the configurable path (no hard-coded seat home remains), (b) the init/update script's fail-closed paths (missing dir, dirty tree, bad pin), (c) the broker resolves imports from the configured stable path. Use stubs/temp dirs — no live systemd, no network.

## Do NOT
- Do NOT deploy, install, or restart any systemd unit on any host (controller does host provisioning + the per-seat run-mode drop-ins).
- Do NOT change the broker's review/approval logic or the author≠approver wall.
- Do NOT touch `os_native_backend.py`, `install.sh`, or `support_runtime.py` (other lanes in flight).

## Gates
- FULL `ce validate-pr` GREEN in ONE pass (`TMPDIR=/var/tmp`). Carriers: manifest via `carrier_gen.write_carriers(base=<merge-base>)` API (rm build/egg-info first), + `.ce/changelog/<slug>.md`. PR body work-class line (likely `story`). Product-lens. STOP at green; report SHA. Do NOT push.
