# DISPATCH — dev-4 — 2026-07-10 — unit: N-1 slice 2 review-pickup acting chain — class M

**Not a duplicate (verified):** main has zero hits for `review_acting`/`--acting`; the
review_dry_run_DESIGN.md "Slice 2 hook" refers only to a CLI subcommand out of this scope.
Clean new work.

Role: implementer foreman.
Signal: `READY-FOR-HARVEST ce-n1s2-review-pickup-acting <full-40-hex-sha>` or
`BLOCKED ce-n1s2-review-pickup-acting <reason>`.
Branch: `ce-n1s2-review-pickup-acting` off freshly fetched `origin/main` OR LATER.
Worktree: `/var/tmp/wt-ce-n1s2-review-pickup-acting`.
QUEUE NOTE: this is your ACTIVE unit now — the gated ce-f1s2 unit stays queued; when its
START-GATE opens (origin/main contains checks/disk_headroom.py), checkpoint-commit this unit,
execute f1s2 (small), then resume this one.

Standing preflight: `ce validate-pr --profile contained-seat` if env supports it, otherwise
focused tests + BLOCKED(env).

**PRE-SIGNAL CHECKLIST**
- [ ] `python -m pytest validators/tests/unit/test_public_docs_confidentiality.py::test_tracked_text_files_contain_no_new_confidential_or_internal_references -q`
- [ ] All listed tests GREEN, no pre-existing test regressions
- [ ] `deploy/systemd/ce-review-pickup-daemon.service` acting flag is commented out (default OFF)

## Context

### Slice 1 state on origin/main
- PR #917 shipped `validators/creator_engine_validator/forge/review_dry_run.py`:
  `run_dry_run_pass` wraps `poll_review_pickup(dry_run=True, apply=False)` and emits a
  WOULD_ASSIGN / WOULD_SKIP JSONL feed. No acting path exists.
- PR #915 shipped `seat_watch_daemon.py` + `seat_watch_runner.py` + `deploy/seat-watch/*` —
  observe-only, no acting authority.

### Seams left by slice 1
- `poll_review_pickup` (`review_pickup.py` ~line 206): the `dry_run=False, apply=True` path
  assigns reviewers; each `result.items` entry carries `repo`, `number`, `head_sha`, `url`,
  `title`, `assigned_reviewer`, `reason`. The acting pass consumes these items.
- NDJSON ledger pattern from `pickup.py` (S2 leg, ~lines 247–333): `load_ledger(path)`,
  `append_ledger(path, record)`, `ledger_key(...) -> tuple[str,str,str]`,
  `ledger_keys(records) -> set`. The acting ledger must follow this exact pattern.
- `deploy/systemd/ce-review-pickup-daemon.service` line ~13: ExecStart uses
  `ce review-pickup --loop --apply`; env from `%h/.config/creator-engine/gate-daemons.env`.
- `v3_cli.py` ~line 4493: `p_review_pickup` parser; ~line 5794: `_cmd_review_pickup`;
  `--apply`/`--dry-run` exist; `--acting` is absent.

### Comment vs review endpoint (structural authority boundary)
Post verdicts via `POST /repos/{repo}/issues/{pr_number}/comments` (Issues API, issues:write).
This is structurally distinct from `POST /repos/{repo}/pulls/{pr_number}/reviews` (approval).
The acting module must NEVER call the reviews endpoint.

## Unit

### 1. New module `validators/creator_engine_validator/forge/review_acting.py`
Module docstring must state: posts PR comments only via `issues/{number}/comments`; never calls
`pulls/{number}/reviews`; no approval or merge authority; token scope required = issues:write only.

Exports (all I/O injectable):

a. Config flag:
```python
ACTING_ENABLED_ENV = "CE_REVIEW_ACTING_ENABLED"
def is_acting_enabled(env: Mapping[str, str] | None = None) -> bool:
    """Return True only when CE_REVIEW_ACTING_ENABLED=1. Default OFF."""
```

b. Acting ledger — follow the pickup.py S2 NDJSON pattern exactly:
```python
def load_acting_ledger(path: Path | str) -> list[dict[str, Any]]: ...
def append_acting_ledger(path: Path | str, record: Mapping[str, Any]) -> None: ...
def acting_ledger_key(repo: str, pr_number: int) -> tuple[str, str, str]:
    return (f"review-acting:{repo}:{pr_number}", f"{repo}:{pr_number}", "comment_posted")
def acting_ledger_keys(records: Iterable[Mapping[str, Any]]) -> set[tuple[str, str, str]]: ...
```

c. PR comment helper (issues endpoint, NOT reviews):
```python
def post_pr_comment(repo: str, pr_number: int, body: str, *, gh_runner: GhRunner) -> str | None:
    """POST to issues/{pr_number}/comments. Returns comment html_url or None on failure."""
```

d. Context and spawner seam:
```python
@dataclass(frozen=True)
class ActingContext:
    repo: str; pr_number: int; head_sha: str; url: str; title: str; assigned_reviewer: str

Spawner = Callable[[ActingContext, GhRunner], str]  # returns verdict text; raises on failure

def default_spawner(ctx: ActingContext, gh_runner: GhRunner) -> str:
    """Spawn ce lane launch --role reviewer with an embedded seed. Returns verdict text."""
    # subprocess.run with timeout=180; reads stdout for verdict.
```

e. Pass function:
```python
@dataclass(frozen=True)
class ActingPassResult:
    commented: tuple[dict[str, Any], ...] = ()
    skipped_dedup: tuple[dict[str, Any], ...] = ()
    failed: tuple[dict[str, Any], ...] = ()

def run_acting_pass(*, items, gh_runner, acting_ledger_path, log_sink=None, spawner=None,
                    clock=None) -> ActingPassResult: ...
```
Algorithm: load ledger; per item: (a) dedup — key seen → skip; (b) spawn via
`(spawner or default_spawner)(ctx, gh_runner)` in try/except — on exception log incident event
via log_sink, append `{action: "spawn_failed", ...}` ledger entry, add to failed, continue
(never crash-loop); (c) on success `post_pr_comment`; (d) append
`{kind: "ce-review-acting", action: "comment_posted", ...}` ledger entry; (e) add to commented.

### 2. Extend `v3_cli.py`
Add to the `ce review-pickup` parser (after `--dry-run`, ~line 4524):
`--acting` (store_true; help: arm acting mode — spawn reviewer, post verdict as PR comment;
Operator/face must set; default OFF) and `--acting-ledger-path` (default None; required when
--acting). In `_cmd_review_pickup` (~5794): when `args.acting and not dry_run and applied and
args.acting_ledger_path`, call `review_acting.run_acting_pass(items=result.items, ...)`.

### 3. Extend `deploy/systemd/ce-review-pickup-daemon.service`
Add COMMENTED-OUT acting env vars + a COMMENTED armed ExecStart variant. The active ExecStart
must NOT include `--acting`. Operator arms by manually uncommenting after audit:
```ini
# Acting mode: Operator arms by uncommenting the vars + armed ExecStart below. Default OFF.
# CE_REVIEW_ACTING_ENABLED=1
# CE_REVIEW_ACTING_LEDGER_PATH=<state-root>/review-pickup-acting/ledger.ndjson
# ExecStart=... --acting --acting-ledger-path "${CE_REVIEW_ACTING_LEDGER_PATH}" --json
```

### 4. New tests `validators/tests/unit/test_review_acting.py`
All offline — zero live network/subprocess. Fake GhRunner + injectable Spawner per the slice-1
idiom (test_p8_review_daemon_s1.py). Required cases: (1) is_acting_enabled False on empty env;
(2) True for =1; (3) load ledger [] on missing file; (4) NDJSON round-trip; (5) key shape;
(6) dedup skip of ledgered PR; (7) new PR → spawner called + comment posted; (8) spawner raises
→ incident logged, failed, loop continues; (9) cross-restart dedup; (10) post_pr_comment hits
issues/{n}/comments and NEVER pulls/{n}/reviews; (11) failed spawn appends spawn_failed entry.

## Files (allowed writes)
- validators/creator_engine_validator/forge/review_acting.py (new)
- validators/tests/unit/test_review_acting.py (new)
- validators/creator_engine_validator/v3_cli.py (acting flags wiring only)
- deploy/systemd/ce-review-pickup-daemon.service (commented acting vars + commented armed ExecStart)
- CHANGELOG.md (entry under Unreleased)
- .ce/changelog/ce-n1s2-review-pickup-acting.md (new)
- .ce/pr-manifests/ce-n1s2-review-pickup-acting.md (new; exactly `- **Declared work class:** M`)
Do NOT create new systemd units, new launcher scripts, or new deploy/ subdirectories.

## Stop lines
- No call to `pulls/{pr_number}/reviews` anywhere — structural approval prohibition.
- `--acting` defaults OFF; manual uncomment in the service file is the only arming path.
- No push, no sign, no git write operations. `.github/**` read-only.
- Do not touch pr_preflight.py or checks/**.
- Do not modify review_pickup.py, review_dry_run.py, pickup.py, pickup_search.py, or any
  existing test file (test_v3_cli.py included — another in-flight branch touches it).
- Do not broaden token scope: no pull_requests:write, no merge/approve capability anywhere.
- Do not modify deploy/seat-watch/, deploy/queue-daemon/, deploy/conveyor-daemon/, deploy/daemons/.

## Signal
When all unit tests pass, confidentiality test passes, preflight per directive, and the service
file's acting flag is confirmed commented (default OFF):
`READY-FOR-HARVEST ce-n1s2-review-pickup-acting <full-40-hex-sha>`
Commit early and often.

**PATH note:** use the absolute `/workspace/creator-engine/.venv/bin/ce` and
`/workspace/creator-engine/.venv/bin/python`; do not rely on $PATH resolution.

---

## AMENDMENT 1 (controller, 2026-07-10 ~15:4xZ) — resolves BLOCKED structural-production-path-unreachable

Both blockers are valid findings. Scope amended:

1. **Loop seam — review_pickup.py is now an ALLOWED write, for exactly one additive change:**
   add an optional injectable callback parameter to poll_review_pickup (e.g.
   `on_pass_items: Callable[[Sequence[Mapping[str, Any]]], None] | None = None`), invoked once
   per pass after apply with that pass's result items. Default None = byte-for-byte identical
   behavior. Existing tests must remain untouched and green; add loop-seam coverage in YOUR new
   test file only. `_cmd_review_pickup` then passes the acting pass as this callback when
   --acting is armed (loop mode reachable; single-pass mode unchanged).

2. **Spawner — config-driven command template, not lane-launch knowledge in the module:**
   drop the lane-launch default_spawner. New contract: env var CE_REVIEW_ACTING_SPAWN_CMD holds
   an Operator-configured command template; the module substitutes {repo} {number} {head_sha}
   {url} placeholders (shlex-safe, no shell=True), runs it with timeout=180, stdout = verdict
   text. If acting is enabled but the template is unset: per-item ledger incident
   `spawner_unconfigured`, item added to failed, no crash. The governed lane-launch command
   VALUE is deployment config (documented as a commented example in the service file, like the
   flag) — arming and governance stay Operator-side, mechanism stays in the module. Test cases
   10/11 adapt accordingly; add: template substitution correctness, shlex safety (no shell
   injection via title), and spawner_unconfigured path.

All other constraints unchanged, including the structural no-approve prohibition. Resume.
