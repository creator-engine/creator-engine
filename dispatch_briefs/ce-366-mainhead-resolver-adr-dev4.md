# SEED BRIEF — ce-ops#366: ADR/design — ratified main-HEAD artifact resolver/builder/verifier surface — SEAT: dev-4

**Context (self-contained — do not fetch any ticket):** CE's install/update surface is
signed-release/mirror-based only (`ce update` follows the signed mirror path; releases are
ce-root-v1-signed with SHA256SUMS + DNS anchor). Contributor lanes L1.a (clean-main-install) and
L1.b (auto-track-main) are BLOCKED on a missing governed mechanism: nothing can take current
`origin/main` HEAD → first-party wheel → fail-closed hash verification → install/promote. This is a
NEW TRUST SURFACE (main-HEAD artifacts have no release signature) and is RATIFICATION-GATED: the
Operator must ratify the trust contract before any implementation. Your deliverable is the DESIGN
ONLY — an ADR that gives the Operator a concrete contract to ratify. NO implementation code.

**Required 4-step contract to design:**
1. **Fetch/resolve** — resolve `origin/main` to a specific commit SHA; fail on ambiguity/network error.
2. **Build** — reproducible first-party wheel from that exact commit, commit SHA embedded.
3. **Verify** — source + wheel hashes checked FAIL-CLOSED; no placeholder-signing, no trust-on-first-use;
   define the verification record.
4. **Install/promote** — atomic in-place swap with rollback record.

**ADR must decide/propose (with options + recommended default):** the trust anchor for unsigned
main-HEAD artifacts (commit-SHA pinning vs CI artifact attestation vs Operator-signed interim certs);
how this chain differs from and composes with the signed-release chain; how `ce update --track main`
(L1.b) layers on top; failure/rollback semantics; and the explicit list of what remains
Operator-ratified vs automatic. Study the existing release/install surfaces in the repo first
(release staging, `ce update`, install.sh flow under docs/downloads + validators release modules) and
cite the real modules/paths in the ADR. Mark the ADR status: **Proposed — awaiting Operator ratification**.

**Branch:** `ce-366-mainhead-resolver-adr` (off `origin/main`, worktree under /var/tmp — NOT /workspace).
**Role:** implementer (docs-only diff). **Work class:** by floor (likely S — docs).
**Obligations:** ADR file under docs/adr/ following the existing numbering/format there;
`.ce/changelog/ce-366-mainhead-resolver-adr.md` + `.ce/pr-manifests/ce-366-mainhead-resolver-adr.md`
(carrier slug == branch, covers all changed paths). Venv has no activate — use `.venv/bin/python -m pytest`.
Run the FULL local validator preflight (`ce validate-pr`, CI-parity) before commit-for-harvest; note
stale-env discrepancies rather than chasing them. Commit (do NOT push — controller harvests) and echo
the commit SHA. Done-report = branch, SHA, files, preflight evidence.
