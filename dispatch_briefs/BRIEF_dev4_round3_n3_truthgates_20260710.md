# DISPATCH — dev-4 ROUND 3 — 2026-07-10 — N-3 truthfulness gates (2 units)
Role: implementer foreman. One signal per unit:
`READY-FOR-HARVEST <branch> <full-40-hex-sha>` / `BLOCKED <branch> <one-line-reason>`
Preconditions: `git fetch origin main`; branch each unit off fetched origin/main; worktrees
under /var/tmp/wt-<branch>. aarch64 known-failure carve-out applies to full suites.

Context (embedded): reviewers keep hand-catching two documentation defect classes that must
become mechanical validate-pr gates (ratified arc item): docs teaching `ce` verbs that do not
exist in the shipped CLI (a prior review found ~7 unshipped verbs taught on main), and
.md/.html sibling files drifting apart (dual-format emission doctrine: .md is source, .html
is the sibling render).

## UNIT A — branch `ce-n3-documented-verbs-gate` — class S
New check module `validators/creator_engine_validator/checks/documented_verbs.py`:
- Enumerate SHIPPED verbs programmatically from the CLI parser registry (import the ce_cli
  module and walk its subparsers in-process — no subprocess `--help` scraping; also include
  the documented v3/cev3 forwarding shims if the registry exposes them).
- Scan tracked docs (docs/**/*.md at minimum) for taught invocations — the ` ce <verb>`
  pattern in code fences and inline code spans. Be conservative: only flag tokens that
  lexically look like verbs (lowercase, hyphenated words directly following `ce `), skip
  placeholders like `ce <verb>` themselves.
- RED when a doc teaches a verb the registry does not ship, listing file:line and the verb.
  Include an explicit allowlist seam (data in the module, initially empty) for deliberate
  forward-teaching, so exceptions are visible diffs.
- Register in validate-pr following the sibling-check idiom (mirror the newest check's
  registration in cli.py / pr_preflight.py). NOTE: another in-flight branch also appends to
  those registration points — expect a trivial rebase at harvest; keep your registration
  delta minimal.
- Tests: fixture docs with a shipped verb (green), unshipped verb (red, names it),
  placeholder skip, allowlist pass. Baseline honesty: if the CURRENT tree has offenders,
  the check must support a recorded-baseline/ratchet mechanism like existing debt-ratchet
  checks — new offenses RED, existing debt enumerated not silently passed; list the found
  offenders in your completion report.

## UNIT B — branch `ce-n3-dualformat-sync-gate` — class S
New check module `validators/creator_engine_validator/checks/dual_format_sync.py`:
- Discover the repo's md↔html sibling convention empirically FIRST (find existing .md files
  with an .html sibling; inspect whether the html carries a generation marker/hash comment).
  Gate rule, smallest-good: when a PR diff modifies one sibling of a pair without touching
  the other, RED naming the stale sibling (content-hash comparison only if the repo already
  embeds a source-hash marker — do not invent a rendering pipeline).
- Same registration idiom + rebase note as Unit A.
- Tests: pair-modified-together green; md-only modified red; html-only modified red;
  non-paired file untouched by the gate.
Files per unit: the new check module + registration lines + test module + changelog +
carrier (slug=branch). Carrier line: `- **Declared work class:** S`. Product lens: zero
internal ticket refs in prose.

## Stop lines (both units)
ce_cli.py MODIFICATIONS (importing/reading it is required for Unit A — but zero edits),
v3_cli.py, install.sh, docs/llms-install.md, docs/** content edits (the gates READ docs,
never fix them in this unit), conveyor*.py, daemon_lease.py, validation_sandbox_*, forge/**,
deploy/**, .github/**, launch_runtime.py, secret_identity.py, seat-watch modules,
.ce/brain/assertions.yaml, any file in the other unit's carrier.
