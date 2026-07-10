# BRIEF — dev-1 — 2026-07-07 ~23:xxZ — restock batch: 2 units (self-push lane)

Both units are fallout from tonight's dev-3 OOM incident (ce-ops#500) and the #888
harvest hygiene gap (ce-ops#499). Self-push per your lane: full preflight → push →
PR with carrier (slug==branch, self-inclusive, honest work class) + changelog
fragment + `- **Declared work class:**` line in the PR body. Base every branch on
FRESH origin/main (it is moving tonight — four approved PRs are merging). Host
resource rules remain in force: serialize full suites, TMPDIR=$HOME/tmp, -n 4 cap,
clean pytest dirs after each run.

## U1 — branch `ce-500-launcher-durability` (work class: story) — ce-ops#500 slices (b)+(c)
Substance (from tonight's incident, full detail in ce-ops#500): the runsc seat
containers keep their writable overlay in sentry MEMORY — a host OOM lost all of
dev-3's uncommitted work; and the launcher stages the codex config bind-source in
host /tmp, so tmpfiles cleanup made the stopped container unrestartable
("bind source path does not exist").
GOAL, in BOTH launchers (deploy/vps-runsc/run-vps-runsc.sh and
deploy/dgx-runsc/run-codex-runsc.sh, keeping them symmetric):
  (b) DURABLE WORKTREE ROOT: bind-mount the seat's unit-worktree root (the path
      the seat uses for /var/tmp worktrees) to a host-disk directory under the
      seat's durable state root, so seat work survives sentry/container death.
      Fresh directory per container launch is fine; surviving files must be
      inspectable from the host after a crash.
  (c) DURABLE STAGING: stage ALL launcher-generated bind-source files (config
      toml etc.) under the seat's durable state/log root (the existing
      ~/.ce/logs/seats/<seat>/ tree or equivalent XDG path), never host /tmp.
Also update any launcher docs/comments that reference the old /tmp path. If a
launcher test exists, extend it; if not, add a minimal shellcheck-clean assertion
or scripted smoke where the repo already has one for these scripts (do NOT invent
a new test framework). Note in the PR body that slice (a) memory caps is
deliberately out of scope (host-level, Operator).

## U2 — branch `ce-499-seat-preflight-design` (work class: S) — ce-ops#499 DESIGN-ONLY
Substance: contained seats repeatedly emit READY with (1) stale/missing autogen
reference docs (.ce/reference/cli.generated.md, schemas.generated.md) after CLI or
schema changes, and (2) malformed carriers (wrong work-class vocabulary, missing
G5 body line, missing AUTHORIZED_PATHS block) — forcing controller-side repairs
at harvest (the #888 harvest needed three).
GOAL: docs/design/seat-side-preflight.md — design a seat-side pre-READY check:
what it validates (carrier shape vs the real diff, autogen freshness, changelog
presence, work-class vocabulary), how it runs (a `ce` verb or a validate-pr
sub-profile — evaluate both, recommend one), fail-closed semantics (seat may not
signal READY while it fails), and acceptance = a harvest requiring zero
controller-side repairs. DESIGN ONLY — no implementation code (the CLI surface is
contested territory tonight: two in-flight PRs touch ce_cli/v3_cli). Public-docs
lens: generic placeholders, no internal topology.

STOP LINES: no gate acts, no signing, no scope beyond the named paths + carrier/
changelog per unit. U1 must not touch validators/ Python (launcher scripts + docs
+ their existing test surface only) — validators territory is claimed by two
in-flight PRs tonight. Signal per unit: self-pushed PR number + head sha.
