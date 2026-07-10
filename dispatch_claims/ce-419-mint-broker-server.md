# WORK CLAIM — ce-419-mint-broker-server
claimed: 2026-07-10T08:1xZ
controller: ce-dev-2 (Claude face)
seat: dev-3 (ce-vps-codex)
ticket: ce-ops#419
branch: ce-419-mint-broker-server
role: implementer
work_class: S
scope: thin HTTP server entrypoint wrapping existing pure handle_token_request +
  systemd unit template + config template + injected-transport tests. PEM injection,
  network exposure decision, TLS/DNS, deploy activation = controller-lane, OUT of scope.
territory: tools/mint-broker/ce_mint_broker_server.py (NEW),
  deploy/systemd/ce-mint-broker.service (NEW), tools/mint-broker/config.example.yaml (NEW),
  validators/tests/unit/test_mint_broker_server.py (NEW), changelog+carrier (NEW).
  Collision scan 2026-07-10: NO COLLISIONS (all NEW paths; no in-flight branch touches them).
evidence_expected: READY-FOR-HARVEST ce-419-mint-broker-server <40-hex-sha> after focused
  tests + confidentiality check green; contained-seat profile preflight if runnable.
