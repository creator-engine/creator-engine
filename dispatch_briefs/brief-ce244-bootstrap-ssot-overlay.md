# WORK CLAIM — ce-ops#344 / ce-ops#244 · controller-bootstrap knowledge-load · Slice 1 · SSOT overlay + generator validation + test

**Tracking:** ce-ops#344 (controller knowledge-load), builds on ce-ops#244. **Role:** implementer. **Single-seat, bounded.**

## Branch
```
git fetch origin && git checkout -b ce244-bootstrap-ssot-overlay origin/main
```

## Lane / Ticket
- **Parent lane:** controller-bootstrap knowledge-load (ce-ops#344), builds on ce-ops#244.
- **This slice:** Enrich `docs/design/controller-bootstrap-ssot.json` with a `controller_knowledge_overlay` section; extend the generator to validate and render it; add a deterministic test.
- **Explicitly OUT OF SCOPE:** live harness injection into `CLAUDE.md` / `AGENTS.md` / `.claude/agents/`; any new `ce` CLI group; any change to `ce_cli.py`, `README.md`, `test_v1_docs_reconciliation.py`, `.ce/reference/cli.generated.md`, or any validator schema.

## Why (self-contained — you cannot read private ce-ops issues)

CE controllers do not deterministically load high-frequency-action knowledge on startup or after `/clear`. The committed `CLAUDE.md`/`AGENTS.md` are tiny PUBLIC product stubs — internal ops must NOT go there (product-lens doctrine). Controller ops knowledge needs a private channel.

`docs/design/controller-bootstrap-injection.md` (committed, readable) defines a three-prong design: one tracked JSON SSOT (`docs/design/controller-bootstrap-ssot.json`) feeds a preview generator (`scripts/gen-controller-bootstrap.py`) that emits preview-only bootstrap artifacts. The generator MUST NOT touch live `CLAUDE.md`, `AGENTS.md`, or `.claude/agents/`.

The current SSOT exists but covers only canonical roles, foreman directive, safety floor, vocabulary mapping, worker selection, harness output templates. It has NO section for the ops-knowledge content controllers must load: startup sequence, pre-dispatch checklist (territory-map/worktrees + pointer+SHA mechanic), harvest sequence, subagent model-routing, preflight discipline, G5 body-line rule, new-`ce`-group 3-file coupling. This slice adds that section and makes it machine-verifiable.

**Design constraints you MUST honor (from `docs/design/controller-bootstrap-injection.md`):** generator emits to stdout or a preview dir ONLY (never live `CLAUDE.md`/`AGENTS.md`/`.claude/agents/`); generated artifacts carry visible preview-only warnings; deterministic for identical SSOT input; fail closed on missing/malformed required sections; no secret values anywhere.

### Read before writing
1. `scripts/gen-controller-bootstrap.py` — fully. Extension points: `REQUIRED_SECTIONS` tuple, `validate_ssot()`, `render_foreman_core()`.
2. `docs/design/controller-bootstrap-ssot.json` — fully; match the existing section shapes.
3. `docs/design/controller-bootstrap-injection.md` §h (Generator Behavior) + §j (Acceptance) — non-negotiable constraints.
4. `validators/tests/unit/test_v1_docs_reconciliation.py` — DO NOT TOUCH; read only to confirm this slice adds NO new `ce` group (it does not).
5. `.ce/pr-manifests/ce244-worker-tier.md` — canonical carrier format.

## Task

### 1. Enrich `docs/design/controller-bootstrap-ssot.json`
Add a top-level `"controller_knowledge_overlay"` mapping with these required sub-keys:
- `"startup_sequence"` (array): (1) read SSOT-grounded bootstrap before accepting any task; (2) load newest `.ce/state/research/RESUME_STATE_*` by mtime; (3) surface any `AWAITING-OPERATOR` items; (4) probe-don't-remember — verify seat states, branch states, in-flight territory before dispatch.
- `"pre_dispatch_checklist"` (array): (a) check live in-flight territory map (consult `.ce/pr-manifests/` + `.ce/briefs/` + active worktrees under `.claude/worktrees/` and `.ce/wt-*/`); (b) intersect every candidate path against in-flight files; (c) check context % — >40% compact/clear before an unrelated dispatch; (d) save seed brief to a file, send seat the pointer + `sha256sum` (never a long inline prompt); (e) verify work claim before seat starts.
- `"harvest_sequence"` (array): (a) check seat output for `READY-FOR-HARVEST`; (b) verify `ce validate-pr`/preflight GREEN on the branch; (c) harvest to a staging worktree under `.ce/wt-<slug>-harvest/`; (d) controller holds merge gate — enqueue only after independent review + green required checks.
- `"subagent_model_routing"` (mapping): `"controller"`→`"claude-code effort:high"`, `"codex_work_seat"`→`"codex gpt-5.5 effort:high (default)"`, `"codex_hardest"`→`"codex gpt-5.5 effort:xhigh (hardest only)"`, `"architect_research_worker"`→`"claude-sonnet"`, `"implementer_worker"`→`"codex (preferred) or claude-code implementer role"`, `"verification_worker"`→`"codex or claude-code verification role"`. Embed the policy: codex→all work seats; xhigh reserved for hardest codex only; Claude controllers effort:high not xhigh. Do NOT embed drift-prone version strings — tier + effort label only.
- `"preflight_discipline"` (array): (a) run `scripts/ce-preflight.sh --base origin/main --head-ref <branch> --declared-work-class <class>` (or `ce validate-pr`) on a CLEAN committed tree before any push; (b) two-strikes rule; (c) never raw `pytest` only; (d) preflight runs the same gates as CI; (e) `ce validate-pr` is canonical.
- `"g5_body_line_rule"` (array): every PR body has exactly one line `- **Declared work class:** <tiny|story|feature|epic>`; case-insensitive; a `**Work class:**` header or `[PASS]` log line does NOT satisfy it; pick the smallest honest class the floor accepts.
- `"new_ce_group_coupling"` (array): any new `ce` CLI group in `ce_cli.py` requires (a) `README.md` mention (public groups); (b) update `test_v1_docs_reconciliation.py` expected set; (c) regenerate `.ce/reference/cli.generated.md` via `python scripts/gen_cli_reference.py --write`; (d) internal-only groups → add to the internal-groups set, README check exempt.

Keep values factual and terse. No secrets/credentials/PII.

### 2. Extend `scripts/gen-controller-bootstrap.py` (three changes only)
a. Add `"controller_knowledge_overlay"` to `REQUIRED_SECTIONS`.
b. In `validate_ssot()`, after the `worker_selection_policy` validation, add:
```python
overlay = require_mapping(root["controller_knowledge_overlay"], "$.controller_knowledge_overlay")
for key in ("startup_sequence", "pre_dispatch_checklist", "harvest_sequence",
            "preflight_discipline", "g5_body_line_rule", "new_ce_group_coupling"):
    require_list(overlay.get(key), f"$.controller_knowledge_overlay.{key}")
require_mapping(overlay.get("subagent_model_routing"), "$.controller_knowledge_overlay.subagent_model_routing")
```
c. In `render_foreman_core()`, after `render_worker_selection(ssot)`, add a `render_knowledge_overlay(ssot)` helper that renders the overlay keys as titled bullet sections; include the preview-only warning; keep rendering deterministic (no timestamps/dynamic data).
Do NOT change other generator behavior (`--harness`/`--out-dir`/`--list-files`/`--ssot` args, `build_files()`, `write_preview_files()`, `ensure_safe_out_dir()`).

### 3. New test `validators/tests/unit/test_gen_controller_bootstrap.py`
Module-level `pytestmark = pytest.mark.fast` (test-tier-split convention, ce-ops#11 merged). Cover: `test_ssot_validates`, `test_overlay_section_present`, `test_required_overlay_keys`, `test_build_files_produces_expected_keys` (expects `codex/AGENTS.md` + `claude/CLAUDE.md`), `test_overlay_content_in_rendered_output` (startup_sequence appears in both rendered harness outputs), `test_generator_refuses_live_paths` (`ensure_safe_out_dir` on `CLAUDE.md` / `.claude/agents` / repo-root each raises `SystemExit`), `test_deterministic_output` (two `build_files()` calls identical), `test_missing_overlay_section_fails_closed` (minimal SSOT without overlay → `validate_ssot()` raises `SystemExit`). Import the module functions directly (guard is `if __name__ == "__main__"`); use `importlib`/`runpy` if the hyphenated filename blocks direct import.

### 4. Carrier files
- `.ce/changelog/ce244-bootstrap-ssot-overlay.md` — changelog fragment (match an existing fragment's frontmatter).
- `.ce/pr-manifests/ce244-bootstrap-ssot-overlay.md` — path-manifest carrier; list every touched file; compute `AUTHORIZED_PATHS_COUNT` + `AUTHORIZED_PATHS_SHA256` = `sha256("\n".join(sorted(unique_paths)) + "\n")` (regenerate via `carrier_gen.write_carriers` API if available; rm build/egg-info first). The `- **Declared work class:** story` line belongs here + in the PR body.

## Allowed Paths (CLOSED — nothing else)
```
docs/design/controller-bootstrap-ssot.json
scripts/gen-controller-bootstrap.py
validators/tests/unit/test_gen_controller_bootstrap.py
.ce/changelog/ce244-bootstrap-ssot-overlay.md
.ce/pr-manifests/ce244-bootstrap-ssot-overlay.md
```
**EXCLUDE (never touch):** `CLAUDE.md`, `AGENTS.md`, `.claude/agents/`, `.claude/skills/`, `ce_cli.py`, `v3_cli.py`, `README.md`, `test_v1_docs_reconciliation.py`, `.ce/reference/cli.generated.md`, any `schemas/*.yaml`, any `.github/workflows/`, anything not listed above.

## Evidence (DoD)
1. Full `ce validate-pr` (`scripts/ce-preflight.sh --base origin/main --head-ref ce244-bootstrap-ssot-overlay --declared-work-class story`) GREEN in ONE pass on a clean committed tree (all gates; not raw pytest).
2. `python -m pytest validators/tests/unit/test_gen_controller_bootstrap.py -v` all GREEN.
3. `python scripts/gen-controller-bootstrap.py --harness all` prints preview output incl overlay content for both harnesses, no `SystemExit`, no live file overwritten (`git status` shows only the 5 allowed files).
4. `git diff --name-only HEAD` does NOT include any excluded file.
5. PR body carries exactly one `- **Declared work class:** story` line.
6. Carrier integrity: `AUTHORIZED_PATHS_SHA256` matches the path-set hash.
7. PR body states: "This PR generates preview-only controller bootstrap artifacts. Applying generated bootstrap to live `CLAUDE.md`, `AGENTS.md`, or `.claude/agents/` is separate ratified work."

## HARD RULES
- Full `scripts/ce-preflight.sh` (≡ `ce validate-pr`) GREEN on a clean committed tree BEFORE any push. Not raw pytest, not a subset.
- Two-strikes: same gate fails twice → STOP + report the gate name; do not broaden the PR.
- PR body MUST carry exactly `- **Declared work class:** story`.
- Allowed-paths is CLOSED; any out-of-scope required file → STOP + report (do not expand scope).
- Do NOT add a new `ce` CLI group. Do NOT overwrite `CLAUDE.md`/`AGENTS.md`/`.claude/agents/`. No secrets anywhere.
- HOLD: do NOT self-approve/merge/enqueue. Report `READY-FOR-HARVEST` when green.

## Stop Line
- Green + self-push works → push `ce244-bootstrap-ssot-overlay`, open PR referencing ce-ops#344+#244. Report `READY-FOR-HARVEST: branch ce244-bootstrap-ssot-overlay, <N> commits, preflight GREEN, test count <N>`. Do NOT approve/merge/enqueue.
- Green but push fails (contained self-push gap) → STOP, report `READY-FOR-HARVEST: branch ce244-bootstrap-ssot-overlay, <N> commits, preflight GREEN`. Retry push at most once.
- Preflight RED on your gate → fix once; same gate again → STOP + report.
- Out-of-scope file flagged → STOP + report; do not touch it.
