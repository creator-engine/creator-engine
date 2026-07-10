# CE-410 Slice-8 SPIKE — Operator Ratification Package (assembled 2026-07-04 ~07:0xZ)
> Night-arc G0 deliverable per NIGHTARC_MANDATE_CE_DEV2_20260704.md. Design SSOT:
> CE410_ARMING_FIX_DESIGN_20260703.md (SHA d36916652fde…c0147f), slicing SSOT:
> CE410_SLICING_20260703.md.

## 1. What is being asked
Authorize the **slice-8 SPIKE**: an architect task to design the PRODUCTION validation sandbox —
running conveyor validation on the worker-container-policy substrate (role verification, empty
secret/egress allowlists) instead of the dev/test in-process seam shipped in slice 7. Slice 8 is
the explicit Operator checkpoint in the ratified slicing; its output gates slices 9-10 and,
ultimately, any conveyor re-arming decision (which remains a SEPARATE ratification with the full
Re-Arming Evidence Bundle).

## 2. Foundation evidence — slices 1-7 ALL LANDED
| # | Slug | PR | Merged (UTC) | What it removed |
|---|---|---|---|---|
| 1 | ce410-alloc-core | #758 | 2026-07-03 ~10:35 | (new allocator module, no wiring) |
| 2 | ce410-conveyor-alloc-wire | #761 | 2026-07-03 15:37 | daemon_owned_paths_allocated default-True bool → unforgeable DaemonPathAllocation/Receipt |
| 3 | ce410-integrator-alloc-wire | #760 | 2026-07-03 12:00 | ad-hoc workspace dirs → allocator-issued dirs |
| 4 | ce410-authority-contexts-core | #762 | 2026-07-03 16:30 | os.environ mutation; introduced TransportCredentialContext / LocalGitContext / ValidationSandboxContext (typed, frozen, credential-scrubbed) |
| 5 | ce410-integrator-git-phase-split | #764 | 2026-07-03 ~17:2x | one credentialed env across all git ops → transport env ONLY for push/fetch/ls-remote; credentialless hardened local git (all 14 call sites through one phase-selected seam; strict interception test) |
| 6 | ce410-conveyor-phase-authority | #763 | 2026-07-04 03:28 | conveyor validate/git ambient env inheritance → phase-typed GitRunner env + scrubbed validate env (sys.executable + minimal PATH after fix loop; real-resolution test) |
| 7 | ce410-validation-env-scrub | #768 | 05:42 UTC (68a1473e7) | inline scrub → typed ValidationSandboxSpec/Result seam: construction-time credential refusal, pre-exec re-validation, real-subprocess allowlist proof, audit-trail result |

Independent non-author review on every gate-adjacent slice (2,4,5,6,7); two blocking defects
caught and fixed in-lane (slice 6 PATH/interpreter regression; slice 7 first-attempt base
collision reworked). Design's arming defect classes (a) payload self-marking and (b)+(c)
credential inheritance are now closed at the code level for the DEV seam.

## 3. What slice 8 must decide (the SPIKE questions)
1. Substrate: run validation inside the worker-container policy runtime (which container class,
   which policy profile: role verification + empty secret/egress allowlists per design) — and how
   the ValidationSandboxSpec from slice 7 maps onto container config (the seam was built to be
   the stable contract; the SPIKE decides its production implementation).
2. Filesystem shape: what the validation container may mount (allocator-issued workspace only?),
   TMPDIR strategy, wheel/venv provisioning inside the sandbox.
3. Evidence: what a "production sandbox ran this validation" receipt looks like for slice 9's
   armed-refusal gate (armed construction refuses WITHOUT production sandbox evidence) and
   slice 10's publish-reverify audit.
4. Cost/latency budget: validate-pr is ~6-7 min in-process; containerized budget + caching
   strategy.
5. NEW CONTEXT since the design was written (2026-07-04): ce-ops#437 RATIFIED the two-plane OS
   strategy + amendments (canonical Linux runtime image; NO fleet/solo differentiation; containerized single-privileged-launcher w/ socket-scoping requirements) — the SPIKE MUST design the validation sandbox ON
   that runtime image so slice 8 and #437 land as one substrate, not two.

## 4. Remaining lineage after slice 8
- Slice 9 (S): armed-construction refusal without production-sandbox evidence.
- Slice 10 (S): publish-reverify (tree/base/manifest re-check before push/PR) + per-phase audit.
- Then: Re-Arming Evidence Bundle → SEPARATE Operator ratification to arm the conveyor.

## 5. Recommended dispatch (on your GO)
architect_research worker (read-only) producing the slice-8 design for ratification; inputs:
this package, CE410_ARMING_FIX_DESIGN_20260703.md, slice-7 validation_sandbox.py as the frozen
contract, worker-container policy substrate code, ce-ops#437. Output: design doc + the slice-9
receipt schema proposal. No implementation until you ratify the SPIKE output.

## 6. Open items attached to this lineage (not blockers for the SPIKE)
- ce-ops#434 (validate-pr contained-seat profile) — tooling QoL, twice-proven need.
- ce-ops#435 (check-examples aggregate false-RED on bare main) — gate hygiene; slices 6/7
  preflights had to reason around it.
