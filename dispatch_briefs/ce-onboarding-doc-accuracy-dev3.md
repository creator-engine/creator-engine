# BRIEF — dev-3 — onboarding doc accuracy fix (smoke-test findings)

Born-foreman, contained/no-egress (DO NOT push — controller harvests). Fresh branch `ce-onboarding-doc-accuracy` off CURRENT origin/main (`git fetch origin main` first). Drive to READY-FOR-HARVEST GREEN, then `git rev-parse HEAD` and report the SHA.

## Why
A real-installer smoke test (CE installed via the public one-liner inside a fresh Linux container) found the just-merged macOS-via-container runbook is missing a required step, plus minor version drift in dev docs. You wrote the original guide (#650) — fix it.

## Edits — do EXACTLY these, nothing else

### 1. BLOCKING — `docs/guide/onboarding-macos-container.md`, "Verify and Launch" section
Between the `command -v ce` verification block and the `ce launch` block, ADD a `ce brain init` step:
```bash
ce brain init
```
With prose: "Initialize CE's local knowledge ledger. This is required once per working directory before your first `ce launch`."
RATIONALE: without it, `ce launch` refuses with `G6-LAUNCH-BRAIN-BOOTSTRAP-REFUSED` (verified in the smoke test — `ce brain init` then `ce launch` → spawned).

### 2. `docs/guide/onboarding-macos-container.md`, "Caveats" section
ADD a caveat: `ce launch` spawns a Claude Code (`claude`) session — that harness must be installed and authenticated inside the container before the session is productive.

### 3. Cosmetic version drift (live installer serves 0.3.0)
- `README.md:65`: `version `0.2.0`` → `version `0.3.0``
- `README.md:207`: `creator-engine-validator==0.2.0` → `creator-engine-validator==0.3.0`
- `docs/contracts/installer.md:60`: `downloads/0.2.0/SHA256SUMS` → `downloads/0.3.0/SHA256SUMS`
- `docs/contracts/installer.md:80`: `docs/downloads/0.2.0/` → `docs/downloads/0.3.0/`
Confirm these are the actual current strings before editing (line numbers may shift); fix the version, not surrounding text.

## DO NOT TOUCH
- Do NOT edit the uv "manifest-pinned / hash-checked" claims (installer.md:63, zero-to-governed-seat-quickstart.md:22) or the "save the verified paths" instructions (quickstart:30-36). Those docs describe the INTENDED behavior; the installer is being fixed separately to match. Leave them.
- Do NOT edit `welcome.md`'s `ce onboard` section (a separate verification is pending).

## Gates
- `README.md` edits trip `test_v1_docs_reconciliation` — your path-manifest MUST name `README.md` and that test; reconcile if validate-pr flags it.
- Carriers: `.ce/pr-manifests/<slug>.md` (regen via carrier_gen API; rm build/egg-info first) + `.ce/changelog/<slug>.md`. Product-lens (zero ce-ops# refs in shipped docs). One work-class line (`- **Declared work class:** tiny` or `story` per diff).
- FULL `ce validate-pr` GREEN in one pass (TMPDIR=/var/tmp). STOP at green; report SHA. Do NOT push.
