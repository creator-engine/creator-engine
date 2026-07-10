# BRIEF — ce-388-d2-pickup-openbao-deploy-tests — review-pickup OpenBao wiring, slice D2 (QUEUED UNIT 2)

Role: implementer (dev-3, contained, foreman mode). This is your SECOND unit — start it when your
D1 unit (ce-388-d1-pickup-openbao-supplier) reaches its READY-FOR-HARVEST signal. Do NOT wait for
D1 to merge:
- If origin/main already contains D1 when you start → branch `ce-388-d2-pickup-openbao-deploy-tests`
  off freshly-fetched origin/main as normal.
- Otherwise → branch it STACKED on your local D1 branch tip and SAY SO in your signal
  (`READY-FOR-HARVEST ce-388-d2-pickup-openbao-deploy-tests <sha> STACKED-ON ce-388-d1-...`); the
  controller rebases at harvest after D1 merges.
Worktree under /var/tmp. venv: `.venv/bin/python -m pytest`, PYTHONPATH=validators, TMPDIR=/var/tmp.

## Deliverables (D2 = deployment surface + tests for the D1 machinery; design embedded)
1. **Systemd/deployment surface**: the review-pickup service unit (find it: grep deploy/ for
   review-pickup; likely under deploy/systemd/ or deploy/gate-daemons/) gains the
   `--pickup-token-secret-*` vault flags (values via env/env-file, not hardcoded), and
   `install-gate-daemons-systemd.sh` (or the env-docs file it installs) documents the new
   gate-daemons.env variables: BAO_ADDR / BAO_TOKEN / BAO_CACERT and the CE_OPENBAO_ALLOWED_REFS
   entry. Document the exact allowed-refs entry (real values, they are non-secret):
   `path=forge/ce-dev-2/gh-token;field=token;purpose=review-pickup-token;owner_ref=controller:reviewer;policy_sha=ab4769424e205eb53ee31d61da0c386ae9a418682e9bc0a6636f82de708c8982`
   Also document that CE_PICKUP_TOKEN (static path) is removed from the unit only AFTER the vault
   path is verified live — keep the static fallback wiring intact in the unit for now (both paths
   present, vault flags commented-ready or env-gated; pick the cleaner form and say why).
2. **Unit tests for D1's machinery**:
   - test_v3_cli.py: `_review_pickup_token_supplier_from_args()` — unconfigured → None (static
     path preserved); configured → supplier built against a recording fake backend; `env:`
     target-ref rejected with clear error.
   - test_review_pickup.py: per-pass supplier invocation (fresh supplier() each pass + gh runner
     rebuilt); supplier failure → structured log + incomplete pass + retry (no daemon exit);
     PickupError with supplier configured → retry path; max-consecutive-failures → nonzero exit.
   Behavioral tests, no vacuous mocks; follow the file's existing fixture patterns.

## Constraints
- Files (closed set): the review-pickup systemd unit file · install-gate-daemons-systemd.sh (or
  its env-docs artifact) · validators/tests/unit/test_v3_cli.py ·
  validators/tests/unit/test_review_pickup.py · changelog · carrier. NOT: secret_identity.py,
  v3_cli.py, forge/review_pickup.py (your D1 owns those — D2 must not amend D1 code; if a D1
  defect blocks a test, signal BLOCKED with the specific defect instead of patching).
- Product lens in any docs text: no internal ticket refs.
- ⛔ Signed-artifact stop-line: SSHSIG/SHA256SUMS/content_sha256 gate failure → STOP and report;
  never sign.
- Preflight: FULL validate-pr; known env-gap gates (ssh-keygen, libsodium) may false-RED → if the
  ONLY failures are those AND your touched-module tests pass, signal with PREFLIGHT-NOTE.

## Evidence + signal
Commit `review-pickup: vault-flag deployment surface + supplier/loop unit tests`, emit
`READY-FOR-HARVEST ce-388-d2-pickup-openbao-deploy-tests <40-hex sha>` (+ STACKED-ON note if
applicable, + PREFLIGHT-NOTE if applicable). Work class: story.

## Stop line
No push, no PR, no review, no signing. Controller harvests on signal.
