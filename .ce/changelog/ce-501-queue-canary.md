## ce-501-queue-canary

- feat(queue-daemon): add CE_QUEUE_DAEMON_CANARY=1 mode to launch-queue-daemon.sh

  When CE_QUEUE_DAEMON_CANARY=1 is set: implies --dry-run, omits all
  --approval-wall-secret-* flags (wall resolves DORMANT legitimately), relaxes
  required-env to GH_TOKEN + CE_GATE_REPO + CE_GATE_AUTHORIZED_REVIEWERS,
  refuses if CE_DAEMON_STATE_ROOT conflicts with the live daemon default,
  and emits a visible CANARY MODE banner. Closes the queue canary launcher gap.

  - **Declared work class:** S
