# WORK CLAIM — ce-f1s2-preflight-env-propagation
claimed: 2026-07-10T13:2xZ
controller: ce-dev-2 (Claude face)
seat: dev-4 (ce-dgx-codex)
ticket: F-1 slice 2 (VPS_STORAGE_GATE_INCIDENT_DESIGN_20260710.md; ratified N-13 scope)
branch: ce-f1s2-preflight-env-propagation
role: implementer
work_class: S
scope: product fix for the fourth storage mechanism — pr_preflight env helpers must
  propagate caller TMPDIR/PYTEST_ADDOPTS (caller-as-default, intentional overrides still
  win); unit tests for propagation/override/absence/token-drop behavior.
territory: validators/creator_engine_validator/pr_preflight.py,
  validators/tests/unit/test_pr_preflight_env.py (or existing test file),
  changelog+carrier (NEW).
  Collision scan 2026-07-10T13:2x: COLLISION with in-flight ce-f1-storage-admission
  (PR #947, held queue) on pr_preflight.py — RESOLVED BY SERIALIZATION: brief carries a
  hard START-GATE (no edits until origin/main contains checks/disk_headroom.py, i.e.
  #947 merged). No other in-flight branch touches these files (hotfix worker is in
  checks/signed_artifact_pins.py + checks/path_manifest_fidelity.py only).
evidence_expected: READY-FOR-HARVEST ce-f1s2-preflight-env-propagation <40-hex-sha>
  after focused preflight-k tests + confidentiality check green.
