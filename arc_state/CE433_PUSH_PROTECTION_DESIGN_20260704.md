# ce-ops#433 item 2 — Push-Protection Design Note (architect worker, 2026-07-04 ~01:0xZ)
> CONTROLLER ANNOTATIONS (read first):
> 1. Worker's "gap 1" (scanner-widening unverified) is RESOLVED: controller verified on
>    origin/main directly — commit cf42857d = PR #738 "widen public-repo confidentiality scan
>    to all tracked text files" + #741 hardening ARE on main. The worker read the 0.3.1-rc2
>    release-branch checkout (docs-scoped scanner) — branch skew, not a real gap.
> 2. Worker CORRECTED the controller's framing: identity-denylist runtime artifact is
>    PLAINTEXT (gitignored, never committed), NOT digest tokens — schema actively REJECTS
>    64-hex digests. Non-recoverability = committed-representation property only. Also
>    fleet_manifest_guard consumer is narrow (fleet manifests only) + FAIL-OPEN when the
>    artifact is absent (normal state in CI). Any A/C consumer needs its own generation step
>    with registry access.
> 3. RECOMMENDATION (for Operator morning decision): first slice = Option C (broker
>    precondition hook, S-class, pure code, closes the automated no-human push lane) +
>    Option A (GitHub secret-scanning push protection w/ custom patterns) as a SEPARATE
>    org-admin governance action — A is the only control reaching dev-1/controller direct
>    pushes; its bypass-list lockdown is org-config, not code. B (pre-push hook) = optional
>    feedback layer only, never the enforcement story.
> 4. Residuals to carry into the ticket if ratified: pattern-list staleness vs registry
>    rotation (needs a sync trigger), Hyperscan dry-run of existing 8 patterns, A's
>    bypass-by-write-access lockdown.

(worker note appended below annotations)

---
# Design Note — ce-ops#433 Item 2: Push-Protection for Internal Identifiers (worker text, verbatim)

## 0. What exists today (evidence)
- Scanner (release-branch view): public_docs_confidentiality.py FORBIDDEN_PATTERNS = 8 regexes
  (ce-ops#N, ce-ops URL, ce-dev-N, tailnet suffix, VPS IP, Hetzner, skynet, ce-ops-N); scan scope
  docs-only IN THAT CHECKOUT (see controller annotation 1 — widened on main via #738/#741).
- Identity denylist (#751): generated artifact data/identity_denylist.generated.yaml is
  INTENTIONALLY GITIGNORED runtime data; entries are plaintext casefolded identifier strings
  (schema REJECTS 64-hex digests, identity_denylist.py:41,117-118); matching = substring
  containment (find_identity_matches, :138-147); generated from private ce-ops
  infra/identity-registry.yaml by scripts/gen_identity_denylist.py:140-153. ONLY consumer =
  checks/fleet_manifest_guard.py:68-111 (fleet manifests only) and FAIL-OPEN when artifact
  absent (CODE_IDENTITY_DENYLIST_UNAVAILABLE, :130-142,157-166).
- Egress/push broker: orchestrator.py:287-484 courier() = verify→mint→push→PR→revoke,
  fail-closed; policy.py:235-331 evaluate() checks signature/author/branch/rate + pluggable
  preconditions (:320-328) — NO diff-content inspection today. PreconditionHook seam
  (orchestrator.py:53-60) = natural extension point; courier() folds Precondition results into
  the fail-closed AND. Broker pushes host-side (push_change, orchestrator.py:487-492) —
  seat-local git hooks never fire on that lane. dev-1/controller self-push DIRECTLY (no broker,
  no hook infra exists in-repo — grep for pre-push/hooksPath = none).
- GitHub platform: secret-scanning custom patterns = Hyperscan (PCRE subset, no backrefs);
  create → dry-run → publish → enable push protection per pattern; org-level pattern enforces
  only on repos with push protection enabled; blocks CLI/UI/API/MCP pushes transport-agnostic
  (favorable for broker App-token pushes — non-interactive failure, no bypass TTY). BYPASS: any
  write-access actor can bypass with a reason; org can configure delegated bypass — lockdown is
  org-config. Pattern count/complexity limits UNDOCUMENTED — verify live in org settings.
  Sources: GitHub docs (custom patterns; push protection concepts; supported patterns) +
  GitHub changelogs 2025-08-19 (patterns-in-push-protection GA), 2025-09-16 (delegated bypass).

## 1. Option matrix
| Option | Coverage | Bypass | Cost | Doctrine fit |
|---|---|---|---|---|
| A. GitHub push protection + custom patterns | ALL push paths incl. broker App-token + direct human/controller pushes | write-access interactive bypass (org lockdown required); pattern staleness vs registry; Hyperscan subset; undocumented pattern ceiling | low ongoing; org-admin to configure; periodic pattern re-sync job | STRONG (rent-not-reinvent; only true pre-acceptance gate) |
| B. ce-installed pre-push hook | only checkouts with hook; moot for broker lane (host-side push); nothing installs hooks today (net-new); 100+ live worktrees retrofit | --no-verify, raw API, hook edit, fresh clone | moderate (installer + retrofit + sync) | WEAK standalone (convention not enforcement); OK as local feedback |
| C. Broker precondition content-scan | exactly the broker lane (dev-3/dev-4) — their ONLY push route; fail-closed via existing evaluate() AND | uncovered: dev-1/controller direct pushes | low-moderate: new preconditions_hook impl + CLI wiring + synthetic-fixture tests; policy.py core untouched | STRONG for its lane; label partial |
| D. A+C (+B optional) | best achievable | residual: A bypass rights; denylist staleness; novel identifiers not yet in registry (inherent to denylists) | A(org action)+C(S code) | BEST — defense-in-depth |

## 2. Recommended first slice
C first (S-class, pure code, closes the automated no-human lane):
tools/egress-broker/egress_broker/orchestrator.py new default preconditions_hook + wiring in
ce_egress_broker.py / ce_egress_self_push_broker.py, reusing public_docs_confidentiality scan
fns + identity_denylist.find_identity_matches (when artifact present); unit tests w/ synthetic
leak fixtures ONLY. Then A as a SEPARATE org-admin governance action (custom patterns seeded
from registry-derived denylist, dry-run, publish, bypass-list lockdown) + XS script rendering
pattern payloads for the admin. NOT bundled in one PR.

## 3. Residual gaps
(1) ~~scanner-widening unverified~~ RESOLVED by controller (on main). (2) identity denylist
fail-open + narrow; A/C consumers need their own artifact-generation with registry access
(scheduled freshness workflow referenced but not verified live). (3) A bypass = org-config
risk, not code. (4) C never reaches direct pushes. (5) pattern staleness vs registry rotation
(no auto-trigger exists). (6) Hyperscan compat of the 8 patterns needs GitHub dry-run.

## 4. Dispatchable follow-ups
- Implementer (S): Option C broker precondition hook + tests.
- Targeted research: verify #751 freshness-workflow existence on main.
- Governance/ops (Operator/org-admin): Option A enablement + bypass lockdown.
- Sync design: registry-change → pattern-list refresh trigger.
