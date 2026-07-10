# DISPATCH — Conveyor slice-S: bundle-landing — dev-4 (foreman)

LANE: continue the conveyor (slice-1 `conveyor.py` + design merged to main). Build **slice-S = bundle-landing**: the host-side step that takes a git BUNDLE (already extracted from a contained seat by the controller) + lands it into a review/harvest worktree on a fresh base, ready for the slice-1 prep. This eliminates the manual "fetch bundle → create branch → worktree" toil. Read the design at **`.ce/design/conveyor-harvest-push.md` (on origin/main)** for the slice boundaries — build ONLY slice-S; do NOT build slice-M (docker/container transport = Operator-gated arming).

WORKTREE under /var/tmp off CURRENT origin/main. Branch **ce-conveyor-bundle-landing**. validate-pr via `TMPDIR=/var/tmp PYTHONPATH=$PWD/validators /workspace/creator-engine/.venv/bin/python -m creator_engine_validator.ce_cli validate-pr`. STOP before push.

## Scope (pure, safe — no docker, no push, no forge)
Extend `validators/creator_engine_validator/conveyor.py` (or a sibling) with a bundle-landing helper that, given (bundle_path, branch_name, base_ref):
1. `git bundle verify` the bundle (reject malformed/incompatible-base bundles with a structured error).
2. Fetch the branch ref FROM the bundle into a local branch (`git fetch <bundle> <branch>:<branch>`), naming the local branch == the intended carrier stem (footgun #4).
3. Verify/rebase onto CURRENT `base_ref` (footgun #5) — fetch base fresh first.
4. Return a structured landing result (branch, head sha, ahead/behind, ready/reasons) — then the caller runs the existing slice-1 `prepare_harvest`.
It MUST NOT: invoke docker/ssh, push, open/approve PRs, or run a daemon loop. The bundle is provided by the controller (out of scope how it was extracted). Inject any subprocess runner (git seam) for testability.

## Evidence
- Unit tests (injected fake git + a real tiny bundle fixture in tmp): happy path lands the branch; malformed-bundle and wrong-base cases return not-ready.
- `ce validate-pr` GREEN. Carrier+changelog (head_ref=ce-conveyor-bundle-landing, kind=feat, scope=conveyor) + `- **Declared work class:** story` (OLD names). rm validators/build before git add. Branch name == carrier stem.
- Verify vs origin/main, NOT rc2. Do NOT touch docs/install.sh or docs/downloads.
Report: branch, SHA, validate-pr PASS line, the slice-S API.
