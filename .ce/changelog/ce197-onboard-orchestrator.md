---
slug: ce197-onboard-orchestrator
date: 2026-06-23
kind: added
scope: v1 ce kernel (ce onboard orchestrator + doctor onboard-probes + brain_init library entry)
issue: ce-ops#197
---

**`ce onboard` — the first-run one-shot orchestrator (ce-ops#197 PR-4 + PR-5).**

The design-heavy heart of onboarding: one guided, idempotent, resumable,
gracefully-degrading command that wraps the brittle hand-typed trust-verify →
install → `ce brain init` → first governed launch sequence. Built faithful to the
revised 3-mode governed-install design
(`.ce/state/research/DESIGN_197_CE_ONBOARD.md` §A install modes, §B governed
rail, §1.1 six phases).

- **NEW `ce_onboard.py` + `ce onboard` subparser (PR-5).** Sequences the six
  phases (`doctor` → `install` → `verify_install` → `fix_path` → `bootstrap` →
  `launch`) as a thin composition layer over existing surfaces. A data-table of
  `PhaseSpec`s is the SINGLE SOURCE of the §B.2 consequence-class / reversibility
  classification — both the runner and `--emit-manifest` read it. The
  orchestrator is built around injectable legs (`OnboardLegs`) so the happy path
  and every degradation branch run offline with mocked legs. Flags: `--json`,
  `--install-mode {agent,guided,hybrid,print,skip}` (auto-selected per §A.5 —
  **hybrid when an agent is present, else guided; NEVER print**, the manual
  fallback), `--install-root`, `--no-launch`, `--no-fix-path`, `--offline`,
  `--yes`, `--harness`, `--emit-manifest`. First launch drives exactly ONE
  `ce launch` and asserts a single live controller via `seat_lifecycle`
  (the #212 single-controller post-condition). Each `--json` phase record carries
  the §B.3 audit fields (`consequence_class`, `reversibility`, `decision`,
  `verify`).
- **`--emit-manifest` (PR-5, the §A.1 agent-installability surface).** Emits a
  machine-readable description (`ce.onboard.manifest/v1`) of every phase — id,
  action, blast-radius, consequence-class, reversibility, default decision — so a
  user's own agent can plan + gate the install under the governed-install rail
  before any step runs.
- **doctor onboard phase-1 probes (PR-4).** `doctor_runtime.probe_low_tmpdir`
  (friction #3 — tmpfs exhaustion floor) and `probe_path_gap` (friction #2/#212 —
  `~/.local/bin` off PATH), surfaced advisory-only under
  `payload["onboard_probes"]`. They never refuse on their own; onboard reads them.
- **`ce_cli.brain_init(state_root)` library entry (PR-4).** The genesis-ledger
  bootstrap is now a library-callable function (returns `BrainInitOutcome`,
  raises `BrainInitError` on a corrupt ledger) so the orchestrator drives it in
  process rather than shelling out to its own CLI. `_brain_init` (the `ce brain
  init` handler) is refactored onto it — behavior unchanged.

`_versions.py` classifies `ce_onboard` as `v1` (a thin composition over the v1
kernel surfaces; imports only v1 + shared modules, no v3 — the HARD invariant
stays untouched). The new `ce onboard` command group is documented in
`README.md` and guarded by `test_v1_docs_reconciliation`. This unit MODELS the
hybrid hand-off + emits the manifest; it does NOT implement the install.sh bash
hand-off (PR-7, a separate later unit).
