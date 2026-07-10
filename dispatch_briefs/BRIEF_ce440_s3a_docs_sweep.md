# BRIEF — ce-ops#440 Slice 3a: docs blast-radius sweep (cev3 → unified `ce` surface)

Role: implementer. Ticket: ce-ops#440 slice S3a (design excerpt embedded below — do NOT go
looking for host-side design files or private tickets; everything you need is in this brief).
Branch: `ce-440-s3a-docs-sweep` off CURRENT `origin/main` (fetch first; verify your base
includes BOTH the #776 CLI-unification merge b71d032f AND the #772 walkthrough merge — check
`git log --oneline origin/main | head -15` for "Complete Walkthrough"; if #772 is absent,
signal `BLOCKED ce-440-s3a-docs-sweep base-missing-772` and stop).
Worktree: create under `/var/tmp/ce-440-s3a` (NOT /workspace). Repo venv has no activate —
use `.venv/bin/python -m pytest`.

## Design excerpt (S3 of the ratified ce-ops#440 CLI-unification design)
ONE user-facing `ce` command; cev3 retired as a user-facing name; binaries never encode
versions. S1 merged (#776: 32 v3 verbs forwarded natively under `ce`; onboard→install).
S2 (cev3 deprecation notice) is building separately. S3 = docs blast-radius sweep + systemd
ExecStart migration. THIS SLICE IS S3a = the DOCS SWEEP ONLY; the systemd/deploy migration
(S3b) is precondition-gated and explicitly NOT yours.

## Scope
Sweep user-facing documentation so no reader is told to run `cev3`:
1. Inventory: `git grep -n 'cev3' -- 'docs/' ':!docs/downloads' ':!docs/install.sh'` plus
   `README.md` and `playbooks/` (playbooks are internal-facing: sweep only where they
   instruct running a command that now has a native `ce` equivalent; leave internal-plumbing
   references like module paths, service args, or code identifiers alone).
2. For each USER-FACING instructional occurrence (guides, contracts, architecture docs,
   README, site html): replace the `cev3 <verb>` invocation with its `ce <verb>` equivalent.
   Verify each replacement resolves: the 32 forwarded verbs live in `V3_FORWARDING_SHIMS`
   (validators/creator_engine_validator/ce_cli.py:207) — check the verb is in that dict (or
   is a native `ce` group) before writing it into a doc. If a documented cev3 invocation has
   NO ce equivalent, do not invent one — list it in the done-report as residual.
3. EXCLUDE and leave byte-identical: `docs/adr/**` and `docs/decisions/**` (historical
   records — never rewrite; if one describes cev3 as the CURRENT user surface in a way that
   now misleads, list it in the done-report, change nothing), `docs/install.sh`,
   `docs/downloads/**` (signed-release-coupled), `deploy/**` (S3b).
4. Keep paired .md/.html files consistent — if a swept .md has a rendered .html sibling,
   update both the same way.

## Allowed paths
docs/** (minus the exclusions above) · README.md · playbooks/** (instructional occurrences
only) · .ce/changelog/ce-440-s3a-docs-sweep.md (new; required) ·
.ce/pr-manifests/ce-440-s3a-docs-sweep.md via carrier_gen API
(`write_carriers(base="origin/main")` — never hand-list; rm any build/ + *.egg-info first)

## Do NOT touch
validators/creator_engine_validator/** (S2/dev-4 territory: ce_cli.py, v3_cli.py) ·
validators/tests/unit/test_ce_cli_v3_shim.py · validators/tests/unit/test_v1_docs_reconciliation.py
and test_support_agent_p0.py (conditionally claimed by S2 — if your sweep makes either test
RED and fixing requires editing them, STOP and signal BLOCKED with the failing assertion
verbatim rather than editing) · conveyor_daemon.py + test_conveyor_daemon.py (8c/dev-1) ·
deploy/** · docs/install.sh · docs/downloads/** · docs/adr/** · docs/decisions/** ·
test_portability_plane.py (your own prior branch, in harvest — keep disjoint).

## Novelty check (FIRST — semantic, not bare grep)
Confirm user-facing instructional `cev3` occurrences still exist in the included doc set on
your base (the inventory command above must return hits OUTSIDE the excluded dirs). Controller
pre-verified ~10+ files match on post-#781 main. If the sweep has already landed (zero
instructional hits remain), signal `BLOCKED ce-440-s3a-docs-sweep already-landed <evidence>`.

## Public-docs lens (standing)
Public docs are product-lens: the sweep must not introduce internal vocabulary, internal
ticket references (no ce-ops#N), or internal-only command groups (herdr/ask/support/triage/
automerge-kill-switch) into any public doc.

## Preflight + signal (standing directive, ce-ops#303)
Run the FULL local preflight (`ce validate-pr`, CI-parity, TMPDIR=/var/tmp) GREEN in ONE pass
before commit-for-harvest. KNOWN CONTAINER LIMITATION: full validate-pr may fail on this
container's environment (Python 3.11 out of contract, missing textual, missing ssh-keygen) —
if and ONLY if the failures are that environment class, run the focused set green instead
(test_v1_docs_reconciliation.py + test_site_index_docs_nav.py + any test asserting on docs
content + carrier/changelog checks), commit, and still signal READY with the env caveat; the
controller re-runs the authoritative preflight host-side at harvest.
Commit message: `ce-ops#440 slice 3a: docs sweep cev3 -> unified ce surface`.
Then `git rev-parse HEAD` and signal EXACTLY:
`READY-FOR-HARVEST ce-440-s3a-docs-sweep <full-40-hex-sha>` (+ env caveat if applicable)
or `BLOCKED ce-440-s3a-docs-sweep <reason>`.

## Stop line
No S3b (deploy/systemd). No source-code edits. No test edits beyond what Allowed paths
permits (none). No pushing (controller harvests). No issue filing, review, approve, or merge
actions. Done-report must include: files swept (count + list), residual cev3 occurrences
left in place with one-line reasons (ADRs, no-equivalent verbs, internal plumbing), and the
verb-resolution evidence for any non-obvious replacement.
