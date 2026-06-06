# PR path manifest — v3 G-3.7.3a live-mode `apply` conditional + observed-base-head assertion seam

This file is the **carrier** for this PR's ratified closed manifest (the
convention defined in `docs/operations/PATH_MANIFEST_FIDELITY_PROTOCOL.md`).
CI (`.github/workflows/validate.yml`) passes it to
`verify-path-manifest --base <PR base sha> --manifest .ce/pr-path-manifest.md`,
which enforces that this PR's `base..HEAD` diff equals exactly the authorized
path-set below (the diff-gate runs *active*, not neutral). The fidelity scan
(`scan-path-manifest`) additionally requires the declared count and SHA256 to
match the fenced block.

This is the CI-PURE code half of the live spike (3.7.3a), split out from the live
drive so the crown-jewel live wiring is reviewed BEFORE any real secret touches it
(see the execution prompt's split axis). It adds, entirely offline (fakes), the
three seams the live drive (3.7.3b) needs: (1) `make_run_driver(..., live: bool =
False, head_observer=None)` so `change_opener` opens the change `apply=live`
(default OFF → the current path is byte-for-byte unchanged); (2) in live mode, a
SHA-pinned ratification REQUIRES an injected `head_observer` (the real host-side
authenticated read of the LIVE repo head is supplied by the 3.7.3b runbook) and
`drive` passes the observed head to the gate as value-free DATA, refusing a live
`apply=True` of a bound plan with no observer; (3) the orchestrator gate (step
4.6b) asserts the INDEPENDENTLY-observed head equals the ratified head BEFORE the
change-open — closing the agent-trust/TOCTOU gap (the agent merely CLAIMING the
ratified head cannot drive a live apply against a different real head). The
refusal stays a PURE assertion in `orchestrator.py` (the observed head crosses the
seam as DATA; `run_assembly` supplies it). Absent `observed_head_sha` the gate is
byte-for-byte the 3.7.2b behavior. **CI-pure:** every path is driven by fakes; NO
real `gh`/network/`apply=True`/PR/signer/PEM; RED→GREEN with an adversarial RED
proof that the observed-head assertion is load-bearing. It touches no
schema/spine/check/example/contract/forge/backend/CLI/wheel surface and adds no
dependency → `--list-checks` is **unchanged at 43**, `available_backends()` is
unchanged at `('gvisor-proxy', 'local-noop')`, and `check-examples` stays 77/0.
`runtime_evidence_spine.py` is byte-unchanged (the observed-head check is an
equality assertion, not a new digest). Corrections-of-record + the verified ground
truth are in
`.hermes/research/v3-g3-7-live-spike-planning-20260606T053007Z/REGROUNDING_LEDGER_G3_7_20260606T063941Z.md`.

- **base:** `2890b51e0fe1d27a65f9029e15591c72e4f1c90f`.
- **canonicalization:** `sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=5

AUTHORIZED_PATHS_SHA256=2124d90c0461850246d4990ec3fa39cfa2edb12416bd5f685df5ae5832982022

```text
.ce/pr-path-manifest.md
validators/creator_engine_validator/orchestrator.py
validators/creator_engine_validator/run_assembly.py
validators/tests/unit/test_orchestrator.py
validators/tests/unit/test_run_assembly.py
```
