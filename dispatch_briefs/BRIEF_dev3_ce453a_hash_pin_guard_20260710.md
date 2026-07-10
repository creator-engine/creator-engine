# DISPATCH — ce-453a-hash-pin-guard — role: implementer — work class: S
Ticket: ce-ops#453 Part A ONLY (Part B already landed as PR #831 — do not touch skip-transparency code).
Claim: ce-453a-hash-pin-guard. Branch: `ce-453a-hash-pin-guard` off freshly fetched origin/main.
BASE SHA pinned in the dispatch pointer message; STOP and signal BLOCKED if `git rev-parse origin/main`
after `git fetch origin main` does not match it.
Worktree if needed: /var/tmp/wt-ce-453a-hash-pin-guard (NOT under /workspace).

## Context (embedded — no egress needed)
Incident 2026-07-05: a seat brief allowed edits to
`validators/creator_engine_validator/schemas/install-answers.schema.yaml`, whose sha256 is pinned as
`answers_schema_sha256` inside the SIGNED `docs/llms-install.md`. Host preflight failed RED
(INSTALL_REFUSED artifact_hash_mismatch) while nothing at brief-composition or validate-pr level had
flagged that touching a hash-pinned file is release-class work. Part A closes that gap mechanically.

## Unit
Add a validate-pr gate that flags any diff touching a file whose sha256 is pinned inside a signed
artifact, when the corresponding pin is not updated in the same diff.
1. NEW check module `validators/creator_engine_validator/checks/signed_artifact_pins.py`:
   - Enumerate pin lines in `docs/llms-install.md` (pattern `*_sha256:`). Resolve each pin to the
     repo file it pins (at minimum: `answers_schema_sha256` →
     `validators/creator_engine_validator/schemas/install-answers.schema.yaml`; enumerate the others
     from the doc's own structure/comments — resolve conservatively and keep the mapping data-driven
     in one place so new pins extend it without code change where feasible).
   - Gate logic: if the PR diff modifies a pinned file AND does not modify the pin line for it in the
     signed artifact → RED with a message naming the file, the pin key, and stating this is
     release-class work requiring the release-op/spec-signing procedure. If both change together →
     still emit a NOTICE that a signed-artifact re-sign is required (fail-closed messaging, not
     silent green).
   - Self-changes to `docs/llms-install.md` alone (pin update without pinned-file change) → NOTICE,
     not RED.
2. Register the check in the validate-pr composition following the existing idiom used by sibling
   checks (find how e.g. portability_plane is wired via cli.py; tests must stay count-agnostic per
   the ce-288 convention).
3. Tests: NEW `validators/tests/unit/test_signed_artifact_pins.py` — fixture-driven: (a) pinned file
   touched without pin update → RED; (b) both together → green+notice; (c) unrelated diff → green;
   (d) pin-only change → notice. Use synthetic fixture docs/files inside the test module; do NOT
   modify the real `docs/llms-install.md`.

## Files (allowed writes)
- validators/creator_engine_validator/checks/signed_artifact_pins.py (NEW)
- the one registration point for validate-pr checks (match sibling-check idiom; smallest diff)
- validators/tests/unit/test_signed_artifact_pins.py (NEW)
- .ce/changelog/ce-453a-hash-pin-guard.md (NEW)
- path-manifest carrier via carrier_gen API — carrier slug MUST equal branch slug
  `ce-453a-hash-pin-guard`.
PR body must contain the exact line:
- **Declared work class:** S

## Stop lines — do NOT touch
docs/llms-install.md (SIGNED artifact — modifying it is a release op, and your unit must not do it),
install.sh, ce_cli.py / v3_cli.py, conveyor*.py, daemon_lease.py, validation_sandbox_*, forge/**,
deploy/**, .github/**, checks touched by Part B (#831). Extend-don't-weaken: all existing tests stay.

## Preflight + signal (standing, ce-ops#303)
FULL `ce validate-pr` GREEN one pass. Seat venv is known-broken (ce-ops#521): if validate-pr cannot
run for that environmental reason ONLY, run the focused test set green and signal BLOCKED with the
exact failure class (host preflight is then the authoritative attestation). NEVER weaken/skip tests.
COMMIT before signalling. Then emit exactly one line:
`READY-FOR-HARVEST ce-453a-hash-pin-guard <full-40-hex-sha>`
or
`BLOCKED ce-453a-hash-pin-guard <reason>`
