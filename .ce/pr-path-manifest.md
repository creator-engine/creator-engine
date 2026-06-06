# PR path manifest — v3 G-3.7.2b runtime head-SHA assertion gate

This file is the **carrier** for this PR's ratified closed manifest (the
convention defined in `docs/operations/PATH_MANIFEST_FIDELITY_PROTOCOL.md`).
CI (`.github/workflows/validate.yml`) passes it to
`verify-path-manifest --base <PR base sha> --manifest .ce/pr-path-manifest.md`,
which enforces that this PR's `base..HEAD` diff equals exactly the authorized
path-set below (the diff-gate runs *active*, not neutral). The fidelity scan
(`scan-path-manifest`) additionally requires the declared count and SHA256 to
match the fenced block.

This is the enforcement half of the fourth G-3.7 slice (3.7.2b) — the runtime
head-SHA assertion. A NEW `RatificationBindingRefused(RunnerError)` PURE refusal
in `orchestrator.py` fires at the terminal change-open step (the point a live
drive promotes to `apply=True`) — BEFORE the change is opened: when the
ratification is SHA-pinned (`ApprovedPlan.ratified_head_sha` set) it REFUSES
unless the change's `head_sha` equals the ratified head AND the recomputed opaque
`binding_ref` over the in-force `{repo, installation_id, permissions,
ratified_head_sha}` tuple matches the ratified one. On pass it appends the
value-free `runtime_ratification_record` (the 3.7.2a model) to the chain.
`run_assembly.drive` forwards the value-free `binding_inputs`; a pure
`compute_binding_ref` lands in the spine. `ApprovedPlan` gains four OPTIONAL
fields (`ratified_head_sha`/`binding_ref`/`approver_ref`/`ratified_prompt_sha`,
default empty) so the gate is INERT and every existing unbound run/test is
byte-for-byte unchanged. The observed head + binding inputs cross the seam as
DATA; RED→GREEN, **CI-pure** (no live `gh`/network/`apply=True`). The orchestrator
stays forge-free (only `TYPE_CHECKING` forge import) and pure. It touches no
schema/check/example/contract/backend/CLI/wheel surface and adds no dependency
-> `--list-checks` is **unchanged at 43**, `available_backends()` is unchanged at
`('gvisor-proxy', 'local-noop')`, and `check-examples` stays 77/0. The spine diff
is purely additive (`compute_binding_ref`; `append`/`verify_chain` byte-identical).
Corrections-of-record + the verified ground truth are in
`.hermes/research/v3-g3-7-live-spike-planning-20260606T053007Z/REGROUNDING_LEDGER_G3_7_20260606T063941Z.md`.

- **base:** `e85642bf1b3c621eb85701fe5a9a085e18b1bc64`.
- **canonicalization:** `sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=6

AUTHORIZED_PATHS_SHA256=c9d69b1ec62b6083b33632763172e39e9b8a1c39a61917bb612d5f4d12273ca8

```text
.ce/pr-path-manifest.md
validators/creator_engine_validator/orchestrator.py
validators/creator_engine_validator/run_assembly.py
validators/creator_engine_validator/runtime_evidence_spine.py
validators/tests/unit/test_orchestrator.py
validators/tests/unit/test_run_assembly.py
```
