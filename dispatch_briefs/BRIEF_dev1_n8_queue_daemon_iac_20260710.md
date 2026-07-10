# DISPATCH — dev-1 — 2026-07-10 — unit: queue-daemon topology as IaC (N-8) — class S
Role: peer controller, self-push lane. Signal for the fleet ledger:
`READY-FOR-HARVEST ce-n8-queue-daemon-iac <full-40-hex-sha>` (or, since you self-push:
`SELF-PUSHED ce-n8-queue-daemon-iac PR#<n>`), or `BLOCKED ce-n8-queue-daemon-iac <one-line-reason>`.
Branch `ce-n8-queue-daemon-iac` off freshly fetched origin/main OR LATER. Worktree of your
choosing (your standing conventions apply). You may push your own branch and open your own PR
after FULL local `ce validate-pr` GREEN one-pass (CI-parity) per your standing lane; review and
merge stay at the gate as usual.

## Context (embedded)

STRANGELOOP-2 mandate N-8 (deployment parity): the merge-gate queue-daemon runs from a systemd
unit whose host-network topology and env drop-in exist ONLY as local knowledge on this
deployment host — merged≠deployed audits keep finding drift, and the singleton+IaC redeploy rule
requires the IaC to exist BEFORE the next redeploy. One such redeploy is already queued behind
the current arc, and its drop-in correction is known: the env set must GAIN
CE_DAEMON_LIVENESS_STATE_PATH and DROP CE_DAEMON_LOG_DIR. Encode the corrected state.

## Unit

1. Inventory deploy/queue-daemon/ in the repo vs the LIVE unit on this host (discover the actual
   unit name via systemctl list-units | grep -i queue or systemctl cat <unit>; read
   /etc/systemd/system including drop-ins; the daemon runs as its own uid with an env-file).
2. Declare the full topology as IaC in deploy/queue-daemon/: unit file, drop-in template with the
   CORRECTED env set (add CE_DAEMON_LIVENESS_STATE_PATH, remove CE_DAEMON_LOG_DIR; parameterize
   host-specific paths), host-network requirement, restart/hardening directives — matching what
   actually runs TODAY except the two corrected env vars.
3. README or runbook section in deploy/queue-daemon/ stating the redeploy procedure is
   deploy/singleton-redeploy/redeploy-singleton.sh --daemon queue-daemon (never nohup).
4. A validator or test only if a sibling deploy/ dir has one to mirror — otherwise none.

## Files (allowed writes)

- deploy/queue-daemon/** (note: deploy/singleton-redeploy/redeploy-singleton.sh is in another
  in-flight branch's territory — read it, do not edit it)
- .ce/changelog/ce-n8-queue-daemon-iac.md — changelog fragment
- .ce/pr-manifests/ce-n8-queue-daemon-iac.md — carrier (slug=branch) with exactly
  `- **Declared work class:** S`

## Stop lines

Do NOT restart, reload, or edit the LIVE systemd state (declaration only — the redeploy is a
separate controller-lane act). No secrets or tokens in any file. Env-file VALUES parameterized;
never copy values embedding usernames or host-specific identity — use placeholders. Public-doc
confidentiality applies: zero internal ticket refs, zero seat/host identifiers in tracked files.
Run the confidentiality check before push:
python -m pytest validators/tests/unit/test_public_docs_confidentiality.py::test_tracked_text_files_contain_no_new_confidential_or_internal_references -q
