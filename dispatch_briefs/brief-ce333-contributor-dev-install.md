# WORK CLAIM — ce-ops#333 document the from-source editable dev-install path

**Seat:** dev-3 (VPS contained). **Role:** implementer-foreman. **You are a born foreman** — fan out; don't single-thread inline.

## Branch
```
git fetch origin && git checkout -b ce-333-contributor-dev-install origin/main
```

## Why (self-contained)
Onboarding our first collaborator surfaced that creator-engine has **no documented from-source editable dev-install path**, though it's the natural contributor setup. `validators/README.md` + `specs/001-.../quickstart.md` document only the deps-only + `PYTHONPATH=validators` clone mode. But `validators/pyproject.toml` defines console scripts (`ce`, `cev3`, `creator-engine-validator`), so an editable install is the obvious contributor path — it works but is undocumented.

## Task
Add a **"Developer install (from source, editable)"** section to `CONTRIBUTING.md` (cross-link from `validators/README.md` if appropriate) documenting this verified-working sequence (adapt to what you confirm actually works):
```
curl -LsSf https://astral.sh/uv/install.sh | sh
git clone <creator-engine> && cd creator-engine && git switch main && git pull
uv venv --python 3.14 validators/.venv
uv pip install --python validators/.venv/bin/python -e validators/   # editable; brings ce/cev3 console scripts
# verify: ce --version  /  ce validate-pr is available
```
Also document: (a) the **offline build-backend gap** — if the editable install needs network for the build backend, give the workaround; (b) fix/flag any **stale python-version** reference you find in the existing install docs.

## CRITICAL — confidentiality (public repo)
`CONTRIBUTING.md` is PRODUCT-FACING/public. Product-lens only: **ZERO `ce-ops#` references, no internal machinery (merge queue, wall, devs, fleet, Integrator)**. Document the contributor experience, not our internal ops.

## Allowed paths (nothing else; NO code changes)
`CONTRIBUTING.md`, `validators/README.md`, `docs/**` (only if a contributor-docs page is the right home), `.ce/changelog/**`, `.ce/pr-manifests/**`.

## Evidence (DoD)
Full `ce validate-pr` GREEN (docs still pass the gate — incl. the confidentiality/no-ce-ops-ref guard). Declare the G5-derived work-class.

## Stop-line
- Green + self-push works → push `ce-333-contributor-dev-install` + open PR referencing ce-ops#333. Do NOT approve/merge/enqueue.
- Green but push FAILS (self-push gap #337) → STOP + report exactly `READY-FOR-HARVEST: branch ce-333-contributor-dev-install, <N> commits, preflight GREEN`.
- Preflight RED → STOP + report the failing gate.
