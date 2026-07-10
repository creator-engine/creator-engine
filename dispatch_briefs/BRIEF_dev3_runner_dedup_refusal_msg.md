# BRIEF — dev-3 batch: runner-dedup + brownfield-refusal-message (2 file-disjoint units)

Role: implementer (dev-3, contained, foreman mode — parallel workers OK, units are disjoint).
Per unit: branch off FRESH origin/main (fetch first; main ≥ cc7d152c today), worktree /var/tmp,
`.venv/bin/python -m pytest`, PYTHONPATH=validators, TMPDIR=/var/tmp.

## U1 — branch `ce-runner-helper-dedup` — work class: story
From #809's independent review (pooled follow-up, embedded here since you can't read the PR):
the new plain-Docker runner backend (validators/creator_engine_validator/runner/docker_backend.py,
merged as ce-ops#447 unit A) duplicated ~8 argv/mount/env translation helpers that the gvisor
backend already had, and it reaches into another module's PRIVATE (underscore) symbol via a
cross-module import.
Deliverable: (a) hoist the shared translation helpers into a common module within the runner
package (e.g. runner/_translate.py or the package __init__ — follow the package's existing
conventions) with BOTH backends consuming them — behavior-identical refactor, no semantic
changes (the containment-security review verified exact argv properties: --cap-drop=ALL,
no-new-privileges, --user, digest-only image_ref, no --privileged/--runtime/docker-socket —
NONE of that may change; the existing tests pin these and must pass UNMODIFIED except for
import-path updates); (b) replace the private cross-module import with a public seam (promote
the symbol or route through the shared module).
Allowed paths: validators/creator_engine_validator/runner/** + its unit tests
(test_docker_backend.py, test_openshell_backend.py, and any new shared-helper test file) +
changelog/carrier. ⛔ Do NOT touch launch_runtime.py, onboard_apply.py, ce_cli.py (open PR #819
owns those), and do NOT change any test ASSERTION about argv/mount properties.

## U2 — branch `ce-brownfield-refusal-message` — work class: tiny
Live-canary evidence (2026-07-05, embedded): in v3_cli.py around lines 3436-3454, the refusal
for "brownfield apply escalation env vars SET but App PEM/broker credentials UNRESOLVED" emits
the byte-identical message as "escalation env vars NEVER SET" (e2_brownfield_seam_unavailable:
"set CE_FORGE_LIVE_FORGE + CE_FORGE_ADOPTION_WRITE") — a tenant who already exported both vars
is told to do the thing they already did, with no hint that credential resolution (app.kind=own
PEM path / shared mint-broker) is the actual blocker.
Deliverable: distinguish the two states in the refusal — when both escalation vars are set but
the credential layer can't resolve, the message must say so and name the actual remediation
(configure the App credential per the brownfield adoption contract: local PEM for kind:own or
broker for kind:shared). Keep the never-set message unchanged. Tests: put the new tests in a NEW
dedicated test file (e.g. validators/tests/unit/test_v3_brownfield_refusals.py) — ⛔ do NOT edit
test_v3_cli.py or test_v3_installer.py (an in-flight parked branch owns edits there); cover:
vars-never-set → existing message; vars-set-but-unresolvable-creds → new distinct message.
Allowed paths: v3_cli.py (that refusal seam only), the NEW test file, changelog/carrier.

## STOP lines (both units)
⛔ install-answers.schema.yaml and ANY file named by a `_sha256:` pin in docs/llms-install.md =
signed-release-coupled, never touch. Never sign. No review/approve/merge/enqueue.
⚠️ Your container lacks ssh-keygen → @requires_ssh_keygen integration tests SKIP locally; your
green is not final (host harvest arbitrates). Say in your READY note if tests skipped.

## Evidence bar
Full `ce validate-pr --profile contained-seat` GREEN one pass per unit before commit-for-harvest.
Changelog + carrier per branch (stem == slug). Declared work class line per PR body (U1=story,
U2=tiny).
Signal per unit: `READY-FOR-HARVEST <branch> <40-hex sha>`.
