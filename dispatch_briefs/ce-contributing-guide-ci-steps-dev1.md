# SEED BRIEF — Contributing guide: add missing first-PR CI steps — SEAT: dev-1

**Context:** Our first external contributor (Nitzan) onboards TODAY via the
`contribute-to-CE` path. `docs/guide/contributing-to-ce.md` currently omits three
requirements that the live CI gates enforce, so her first PR would fail CI even if
the change is correct. Close that gap so the guide matches reality.

**Branch:** `ce-contributing-guide-ci-steps` (off `origin/main`).
**Role:** implementer. **Work class:** declare by diff floor (likely XS/S).
**Repo:** creator-engine/creator-engine. You are non-contained → self-push + open the PR.

## Allowed paths (exactly these)
- `docs/guide/contributing-to-ce.md`
- `docs/guide/contributing-to-ce.html`   (keep the committed HTML sibling in sync)
- `.ce/pr-manifests/ce-contributing-guide-ci-steps.md`  (carrier)
- `.ce/changelog/ce-contributing-guide-ci-steps.md`     (changelog fragment)

## The gap — add these THREE, accurately, where they fit the existing flow
The guide already covers the path-manifest **carrier** (§5) and validator pytest
commands (§3). It is MISSING:

1. **Declared work class line.** CI's work-sizing gate requires the PR **body** to
   contain exactly one line: `- **Declared work class:** <XS|S|M|L>` at/above the
   diff-LOC floor. (Classes are now **XS/S/M/L** — legacy tiny/story/feature/epic are
   aliased but do not teach them.) Add this to the §5 first-PR checklist and explain
   it reads the PR event body (a body edit alone won't re-trigger; close+reopen does).
2. **Per-PR changelog fragment.** Every PR needs `.ce/changelog/<branch-slug>.md`;
   CI has a changelog gate. Add it to the checklist next to the carrier step.
3. **Single-pass local preflight.** Teach `ce validate-pr` as the one command that
   runs the full gate set GREEN locally before push (superset of the individual
   pytest commands already listed). Recommend running it in ONE pass until green.

Keep it boring, accurate, and cross-referenced in the guide's existing citation
style. Do NOT touch install.sh, downloads/, signed-release artifacts, or governance
canon. Do NOT invent new gates — only document ones that already exist.

## HTML sync
`contributing-to-ce.html` is a committed static render (there is no auto-renderer;
#696 hand-rendered it). Mirror your .md edits into the .html using the SAME styling
as the current file so the two stay consistent. `test_site_index_docs_nav.py` guards
the site nav — don't break its expectations (it expects the .html to exist).

## Evidence / DoD (report back with these)
- `ce validate-pr` GREEN locally in one pass (TMPDIR=/var/tmp if host /tmp/.git trap).
- Carrier stem == branch slug == `ce-contributing-guide-ci-steps`; regen via
  `carrier_gen.write_carriers(base=<merge-base>)` after final commit; `rm -rf
  validators/build` before `git add`.
- `git commit && echo <SHA>` — report the SHA.
- Push branch, open PR with the declared-work-class line in the BODY. Do NOT
  approve/merge — controller holds the gate.
