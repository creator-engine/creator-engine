# Rented-Surface Dependency-Update Governance — Arc Design (2026-06-26)

Operator directive: "no band-aids — proper mechanism to update every external surface CE rents (codex, herdr, …) under CE." Trigger: dev-3 codex seat surfaced an `npm install -g @openai/codex` self-update prompt during the GATE β canary.

## Inventory + pinning state (today)
| Surface | Pinned? | Where |
|---|---|---|
| herdr (fork) | ✅ commit SHA `ff924966` | 3 Dockerfiles (duplicated, no cross-check) |
| Zig toolchain | ✅ version + per-arch sha256 | 3 Dockerfiles (duplicated) |
| Python deps (PyYAML/jsonschema/textual) | ✅ `==` pins + wheelhouse | requirements*.txt, pyproject.toml |
| codex agent binary | ❌ bind-mounted, unconstrained | run-*-runsc.sh (version only in a tag string) |
| container images | ❌ tag-only (VPS `:x86_64` fully floating, no digest) | run-*-runsc.sh |
| Rust toolchain | ❌ `rust:1-bookworm` floating | Dockerfiles |
| base OS (debian/python slim) + apt pkgs (nodejs/gh/git) | ❌ unpinned | Dockerfiles |
| OpenBao, gVisor/runsc, gvproxy | ❌ NOT in repo at all (host out-of-band) | — |

## The live hole (immediate)
`hook_check.py` `_MECHANIC_RULES` blocks `npm publish`, `git push`, `gh pr merge/review`, etc. — but NOT `npm install -g` / `pip install` / `apt-get install` / `curl|sh`. A contained seat with egress can self-update its own toolchain. VPS codex package mount is also `rw` (DGX correctly mounts the binary `readonly`).

## Design (reuse CE machinery; no parallel infra)
1. **SSOT manifest** `surfaces/manifest.yaml` — every surface: version + commit/digest + source + custody + update_policy + last_evaluated. Builds/launches read from it (render.py → build-args + launch-env.sh).
2. **Pinning discipline** — digest/commit-pinned everywhere; new validator check `surfaces_manifest_consistent` (hard-fail): Dockerfile ARGs + run-script image defaults + requirements.txt all match manifest; any `digest: null` for a pinnable type fails.
3. **Update detection** — `ce surfaces check-updates` (read-only; npm/GitHub/ziglang APIs) → JSON report; controller-only, never auto-applies.
4. **Evaluation gate** — changelog + CVE + vendor-capability grounding ([[verify-vendor-capability-vs-our-wiring]]) → ratification carrier `carriers/surface-bump-<surface>-<version>.md`.
5. **Staged canary** — manifest-bump branch → isolated build → one canary seat → full gate + ring-1 smoke before fleet.
6. **Canonical fleet rollout** — single lever = manifest bump PR; `ce surfaces fleet-rollout` does stop → EnvironmentFile update → canonical relaunch → herdr readiness, seat-by-seat, side_effect_ledger audit. NEVER per-seat npm/pip.
7. **Rollback** — revert the manifest commit + re-rollout; the image IS the surface state.
8. **Refusal-spine rule** — ring-1 blocks toolchain self-update (`npm i -g`, `pip install` [exempt `--no-index`], `apt install`, `curl|sh`, `dpkg -i`); VPS codex binary mount → `readonly`.
9. **Audit** — manifest git history + carrier + side_effect_ledger + `CE_IMAGE_REVISION` label answer "what version ran on seat X on date Y".

## Ticket breakdown (phased)
- **Phase 2 / IMMEDIATE FIX (urgent, ~35 lines):** #E ring-1 toolchain-self-update block (+tests, exempt `pip --no-index`); #F VPS codex binary mount `readonly`.
- **Phase 1 / FOUNDATION:** #A `surfaces/manifest.yaml` SSOT + `surfaces_manifest_complete` check; #B `surfaces_manifest_consistent` CI guard.
- **Phase 1 cont.:** #C digest-pin base images; #D fix VPS floating `:x86_64` tag.
- **Phase 3:** #G `ce surfaces check-updates`; #H carrier schema + runbook.
- **Phase 4:** #I `ce surfaces fleet-rollout`; #J `surfaces/render.py`; #K wire CI image build from manifest.

## Composition
Fleet-retirement/clean-install (#207/#208 — #I IS the rollout mechanism they need); Ring-1 (#219 — #E is a closure increment); `ce update` (#190 — same trust philosophy, non-overlapping scope: that's CE's own pkg, this is external surfaces); `ce validate-pr` (#252 — #B joins the gate).

## Open items needing Operator/host input
OpenBao + gVisor/runsc current versions must be inventoried on each host (not in repo) before the manifest can be populated for those surfaces.
