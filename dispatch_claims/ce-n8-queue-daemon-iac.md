# WORK CLAIM — ce-n8-queue-daemon-iac
claimed: 2026-07-10T15:1xZ
controller: ce-dev-2 (Claude face)
seat: dev-1 (peer controller, self-push lane)
ticket: STRANGELOOP-2 N-8 (deployment parity — queue-daemon topology as declared IaC)
branch: ce-n8-queue-daemon-iac
role: implementer (peer self-push)
work_class: S
scope: declare the live queue-daemon systemd topology as IaC in deploy/queue-daemon/ with the
  corrected env drop-in (add CE_DAEMON_LIVENESS_STATE_PATH, drop CE_DAEMON_LOG_DIR,
  parameterized paths) + redeploy-procedure README. Declaration only; no live systemd mutation.
  Sequences BEFORE the queued controller-lane gate redeploy (singleton+IaC rule).
territory: deploy/queue-daemon/** only, changelog+carrier.
  Collision scan 2026-07-10T15:1x: NO COLLISIONS — n15a is in forge/integrator_belt.py;
  materializer-deploy-unit touches deploy/materializer/ + deploy/singleton-redeploy/ (dev-1
  instructed read-only on redeploy-singleton.sh). No in-flight branch touches deploy/queue-daemon/.
evidence_expected: SELF-PUSHED ce-n8-queue-daemon-iac PR#<n> after FULL local validate-pr GREEN.
