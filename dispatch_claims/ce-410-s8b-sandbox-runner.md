# WORK CLAIM: ce-410-s8b-sandbox-runner
- Lane: CE-410 hardening chain slice 8b (production validation-sandbox runner, receipt-emitting)
- Seat: dev-1 (non-contained, self-push) — batch-dispatched alongside #775 test rework (file-disjoint)
- Branch: ce-410-s8b-sandbox-runner
- Paths: NEW governance/policies/worker-container/podman-verification-v1.yaml + NEW validation_sandbox_runner.py + NEW receipt module + tests + changelog. Frozen: validation_sandbox.py. Additive-only escape hatch: container_launcher.py.
- Territory: verified disjoint (dev-3 #440 S1 = CLI files; dev-4 S3 = deploy/daemons+daemon_lease+conveyor_daemon; #775 rework = test_conveyor_discovery.py; #774 rework = checks/portability_plane)
- Precondition: #773 (8a) merged to main — encoded in brief as verify-before-start
- Claimed: 2026-07-04 by CE-DEV-2 controller
- Brief: BRIEF_ce410_s8b_sandbox_runner.md sha256=a0352065df48163edd712a4128342d9ac577b96b1d437bc1497ce3f07f11f829 (design SSOT co-transferred)
