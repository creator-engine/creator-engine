# SEED BRIEF — dev-4 — extend public-repo confidentiality scanner beyond docs/ (P0)

Role: implementer. Branch: `ce-390-confidentiality-scanner-coverage` (off fresh
origin/main). Contained DGX seat — commit + signal READY-FOR-HARVEST with SHA;
controller harvests (self-push may be unavailable, that's fine).

## Problem (incident TODAY — highest-priority defensive fix)
A PR added a generated Python module under `validators/` that embedded real
internal infrastructure identifiers (internal IPs, hostnames, usernames,
secret-store paths, key-file paths) in plaintext. CI passed GREEN because the
confidentiality guard `validators/creator_engine_validator/public_docs_confidentiality.py`
scans ONLY README.md + docs/** (see `public_doc_files()` ~lines 214-229). This
repo is PUBLIC — every tracked text file is a publication surface, not just
docs. The guard meant to prevent exactly this leak class had a coverage hole.
(The leaking PR was caught in review, closed, and its branch deleted — your fix
prevents the NEXT one from passing CI.)

## Fix
1. Extend the confidentiality scan to ALL tracked text files in the repo —
   source (`validators/**`, `scripts/**`, `deploy/**`, `surfaces/**`),
   playbooks, workflows (`.github/**`), tracked `.ce/**` artifacts (changelogs,
   pr-manifests, reference docs) — not just README + docs/. Binary files and
   gitignored/untracked paths are out of scope. Reuse the existing pattern set
   and check plumbing; this is a COVERAGE change, keep detection logic intact
   unless a small refactor is genuinely required.
2. Fail-closed on scan errors: an unreadable file or pattern failure must FAIL
   the check, never skip silently.
3. Pre-existing hits: run the widened scan on current main. For each hit,
   either (a) it is genuinely public-safe → add a NARROW, per-file+per-token
   allowlist entry with a one-line justification comment, or (b) it is a real
   leak → do NOT fix it in this PR; list file+line+token-class (NOT the value)
   in your done-report so the controller can ticket a scrub. The gate must be
   GREEN on your branch with the allowlist, and any allowlist entry must be
   auditable (no blanket directory excludes, no regex-wildcards-everything).
4. Tests: fixture-driven — a synthetic tracked file containing a FAKE internal
   identifier (invent placeholder values like `100.99.99.99`, `host-test-xyz`;
   NEVER put real registry values in test fixtures or anywhere in this PR)
   must FAIL the check; the allowlist mechanism must be exercised; an
   unreadable-file scenario must FAIL closed. Prove fail-without/pass-with.

## Constraints
- Do NOT touch: `pr_preflight.py`, `ce_cli.py`, `carrier_gen.py`,
  `forge_triage.py`, `project_init.py`, `checks/fleet_manifest_guard.py`,
  `docs/adr/**`, `docs/downloads/**`, conveyor files. If wiring the check
  requires a registration line in a shared checks `__init__`, that single line
  is allowed — call it out in the done-report.
- FULL local preflight (`ce validate-pr`, TMPDIR=/var/tmp) GREEN in ONE pass
  before commit-for-harvest. If the brain-drift gate false-REDs on the
  persistent checkout, reconcile instance-local `.ce/state/brain` from the
  tracked canonical — do not weaken the gate.
- `.ce/changelog/ce-390-confidentiality-scanner-coverage.md` required.
  Carrier regen via `carrier_gen.write_carriers(base=<merge-base>)`; carrier
  stem == branch slug. PR body line (controller opens the PR):
  `- **Declared work class:** S` (bump to M only if the allowlist sweep forces
  a bigger diff — say so).

## STOP LINE
Commit on the branch + print `READY-FOR-HARVEST <sha>` + the done-report
(including the pre-existing-hits list, token CLASSES only). No push, no PR, no
merge, no scrubbing of pre-existing leaks.
