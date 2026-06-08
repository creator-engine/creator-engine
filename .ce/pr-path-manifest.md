# PR path manifest — feat(v3): G-7.4 two-mode installer + cost opt-out UX + `ce` exposure

This file is the carrier for this PR's closed path manifest under
`docs/operations/PATH_MANIFEST_FIDELITY_PROTOCOL.md`. CI passes it to
`verify-path-manifest --base <PR base sha> --manifest .ce/pr-path-manifest.md`
and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set
below. The fidelity scan (`scan-path-manifest`) additionally requires the
declared count and SHA256 to match the fenced block.

Scope: **G-7 slice 7E — the two-mode installer + the cost opt-out UX** (the fifth
ratified G-7 product-surface slice). Adds a NEW v3-classified PURE module
`v3_installer.py` + a `cev3 onboard` command + the served artifacts
(`docs/install/install.sh` one-liner, `docs/install/llms-install.md` agent-native
signed spec) + the contract `docs/contracts/installer.md`:

- **Verify-before-execute** — `require_verified` refuses (`InstallRefused`) an
  install spec unless it is signed by a **pinned CE key** (`PINNED_KEYS`) and
  verifies (in-tree content-address floor; the real asymmetric verify is an
  injectable seam). The grader-outside principle at install time.
- **Dependency resolution — detect-don't-assume** — `plan_dependencies` plans
  (never fail-on-missing): present→skip, missing→a permission-gated, **batched**
  sudo install (`runsc`/`proxy`/`git`/`python` system; `uv` user-space);
  idempotent. The read-only detection is live (`cev3 onboard` probes
  `shutil.which`); the privileged FIX is deferred.
- **Default-vs-Custom profile + the cost opt-out** — `build_profile`: Default →
  `spend_cap_enforcement: enforce`; Custom opt-out → `off` + a REQUIRED
  ratified-HUMAN-only `spend_cap_optout {ratified_prompt_sha, approver_ref}`
  binding (raises without it) + the **verbatim educate copy**. The emitted
  fragment is exactly what **`ce_spend_envelope`** accepts (CAP off ≠ DETECTION
  off — the global ceiling + anomaly→escalate stay on).
- **The `ce` exposure** — `ce_exposure_plan` exposes the v3 CLI as **`ce`** on the
  v3-only pilot (Operator-ratified directive; the internal `cev3` console_script
  is unchanged). **Human contract:** the operator approves only **sudo** + the
  **GitHub-App click**.

Implements `docs/architecture/pilot-deployment-transport.md` +
`docs/contracts/spend-envelope.md` (opt-out). Boundary (CI-pure): the verify /
dep-detect / profile / exposure logic + the `onboard` dry-run. **Deferred live
seams:** the `curl|bash` / privileged execution · the gVisor/proxy provisioning ·
the interactive GitHub-App click · the live transport probe.

Standing requirements honored: **v1↔v3 coexistence** (ADDITIVE; **v1 deleted = ∅**;
internal `cev3` entry unchanged); **G-4.1 naming hygiene** (`v3_installer`
v3-classified + residue-clean; pure — stdlib only; `v3_naming_hygiene` GREEN 0/0);
**version boundary** (`v3_installer` imports stdlib only; `v3_cli`→`v3_installer`
v3→v3; no `shared→v3` edge; `version_boundary` GREEN 0/0; `V3_RUNTIME` **25→26**);
**G-5** (the opt-out fragment feeds `ce_spend_envelope` unchanged — green). Check
surface unchanged (**47** — no registered check). `check-examples` stays **78/0**
(no example fixtures; the served artifacts are docs, not examples). Deferred
follow-ons (named): the live install drive + GitHub-App click; the pilot runbook +
roadmap flip (7F).

- **base:** `513797cf312e008e1fbad7c863b1e4eaa98873a2`.
- **canonicalization:** `sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=10

AUTHORIZED_PATHS_SHA256=70e999ce3dcafdac7e1c57e8365bd9895608b7cc5c141340f6247d6d4adffc69

```text
.ce/pr-path-manifest.md
docs/contracts/installer.md
docs/install/install.sh
docs/install/llms-install.md
validators/creator_engine_validator/_versions.py
validators/creator_engine_validator/v3_cli.py
validators/creator_engine_validator/v3_installer.py
validators/tests/unit/test_v3_cli.py
validators/tests/unit/test_v3_installer.py
validators/tests/unit/test_version_boundary.py
```
