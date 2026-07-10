---
brief_id: BRIEF_dev3_controller_state_sync_20260709
ticket: ce-497-controller-state-sync-s1
seat: dev-3
seat_kind: contained-commit-only
branch: ce-497-controller-state-sync-s1
worktree: /var/tmp/ce-497-controller-state-sync-s1
size: S
units: 1
priority: TOP
mandate: main-controller-independence-20260709
grounded_on: origin/main@6ffd0fe19b8169d6b50a905e2de4ee4c92ea65d8
composed_at: 2026-07-09
---

# BRIEF: Controller state sync — snapshot script, slice 1

**Mandate (2026-07-09):** The DGX reboot halted the factory. The persistent
controller is a snowflake: its operational state (arc decisions, briefs, claims,
memory) lives only on the DGX and has no governed sync path. A replacement
controller cannot resume from SSOT. Fix the data-mobility gap as a program.
This slice (ce-497-controller-state-sync-s1) delivers the snapshot tool that
makes controller state committable — the first link in the fork-lift chain.

## Ticket content (ce-497, embedded)

**Parent:** ce-496 (controller-parity program).

**Gap:** The primary controller's operational state accretes in host-local paths
instead of the forge — live examples: `.ce/state/research/` (arc decisions,
resume states, ledgers), `.ce/briefs/` + `.ce/claims/` (dispatch state), and
`~/.claude/projects/-home-cedev2-creator-engine/memory/` (MEMORY.md + ~150 topic
files). None of it survives host loss. This is the exact snowflake pattern the
parity program exists to kill.

**Deliverable:** A governed snapshot tool (`tools/controller/state_sync.py`) that
collects data classes (b) arc state, (c) dispatch state, and optionally (a) memory
into a structured output directory with a manifest (what/when/from-where/sha256s)
and restore instructions. Dry-run is the default. No live push wiring in slice 1 —
the controller invokes the script; the commit/push lane is slice 2.

**Acceptance:** `--dry-run` (default) prints a manifest to stdout without writing
files. `--output-dir PATH` creates the snapshot tree. Denylist is test-pinned: no
`*.pat`, `*.pem`, `*.pass`, `*.key` file nor any path under `.ce-keys/` can appear
in the collected file set regardless of source_root contents.

---

## Standing obligations (copy verbatim into your PR body + checklist)

- [ ] Changelog fragment: `.ce/changelog/ce-497-controller-state-sync-s1.md`
- [ ] Carrier: `.ce/pr-manifests/ce-497-controller-state-sync-s1.md`
      slug field MUST be exactly `ce-497-controller-state-sync-s1`
- [ ] Work class line in PR body: `**Declared work class: story**`
      (LEGACY vocab: tiny|story|feature|epic; this is story = S)
- [ ] NEVER commit a file named READY (gate signal, not a commit artifact)
- [ ] No ce-ops issue number references in PR body, commit messages, or code comments
      (use plain English descriptions of the ticket's intent)

---

## Files to produce — COMPLETE territory

All four files are new. No existing file is modified by this PR.

```
tools/controller/state_sync.py                              (new)
validators/tests/unit/test_controller_state_sync.py         (new)
.ce/changelog/ce-497-controller-state-sync-s1.md            (new)
.ce/pr-manifests/ce-497-controller-state-sync-s1.md         (new)
```

**Brain-pin precompute (byte-change rule):** All targets are new files.
Prior sha256: N/A for each. The PR diff must show only additions on these
four paths — no deletions from any existing file.

---

## Frozen / in-flight paths — DO NOT TOUCH

These paths are owned by concurrent open PRs. Your diff must not include any of them:

| Path | Owned by |
|---|---|
| `.ce/brain/assertions.yaml` | PR #918 (FROZEN — absolute stop) |
| `validators/creator_engine_validator/ce_cli.py` | PR #918 |
| `validators/creator_engine_validator/continuity_drill_runtime.py` | PR #920 |
| `validators/tests/unit/test_continuity_drill_cli.py` | PR #920 |
| `tools/mint-forge-token.py` | PR #920 |
| `validators/creator_engine_validator/schemas/identity-registry.schema.yaml` | PR #925 |
| `docs/governance/identity-registry.example.yaml` | PR #925 |
| `validators/creator_engine_validator/approver_ref_minting.py` | PR #924 |
| `docs/llms-install.md` | PR #924 |

No `surfaces/manifest.yaml` edit. No `assertions.yaml` edit. No new `AGENTS.md`
or `CLAUDE.md` changes.

---

## Tool specification: `tools/controller/state_sync.py`

### CLI surface

```
python3 tools/controller/state_sync.py [OPTIONS]

Options:
  --dry-run              Print manifest to stdout, write nothing. DEFAULT.
  --commit               Actually write the snapshot tree to --output-dir.
                         Requires explicit flag; dry-run is not overridden by
                         the presence of --output-dir alone.
  --output-dir PATH      Destination root for the snapshot tree.
                         Default: ./ce-controller-snapshot (relative to cwd).
  --source-root PATH     Repo working tree root to collect from.
                         Default: auto-detect (walk up from cwd to find .git).
  --memory-root PATH     Override path to controller memory directory.
                         Default: ~/.claude/projects/-home-cedev2-creator-engine/memory/
  --include-memory       Include (a) controller memory as a tar archive.
                         Off by default; operator opts in explicitly.
  --manifest-only        Compute and print manifest JSON without copying files.
  --target-branch BRANCH Label written into manifest.target_branch for the
                         caller's commit step. Default: ce-controller-state/<hostname>.
  --help                 Show this help and exit rc=0.
```

### Data classes collected

| Class | Source path (relative to source_root) | Flag |
|---|---|---|
| (a) Controller memory | `~/.claude/projects/-home-cedev2-creator-engine/memory/` | `--include-memory` only |
| (b) Arc state | `.ce/state/research/` | always |
| (c) Dispatch state — briefs | `.ce/briefs/` | always |
| (c) Dispatch state — claims | `.ce/claims/` | always |

### Secrets denylist (HARD — tested, cannot be overridden by flags)

A file is denied if ANY of the following match (case-insensitive suffix or
path segment):

```python
DENYLIST_SUFFIXES = {".pat", ".pem", ".pass", ".key", ".p8", ".pfx", ".pkcs12"}
DENYLIST_NAME_FRAGMENTS = {"_token", "secret", "password", "credentials"}
DENYLIST_PATH_SEGMENTS = {".ce-keys", "ce-keys"}
```

Denied files are recorded in `manifest["denied_paths"]` for audit. They are
NEVER included in `manifest["files"]` or copied to the output directory.

Test pins this: the test suite creates fixture files matching each denylist
pattern inside the source_root and asserts they are absent from `manifest["files"]`
and present in `manifest["denied_paths"]`.

### Manifest JSON schema

Written to `{output_dir}/manifest.json`:

```json
{
  "schema_version": "1",
  "snapshot_at": "<ISO-8601 UTC>",
  "source_host": "<socket.gethostname()>",
  "source_root": "<abs path>",
  "target_branch": "<from --target-branch>",
  "data_classes": ["arc_state", "dispatch_state"],
  "files": [
    {"path": "relative/to/source_root", "size": 1234, "sha256": "abc..."}
  ],
  "denied_paths": ["relative/path/that/hit/denylist"],
  "restore_instructions": "See RESTORE section below.",
  "restore_steps": [
    "1. Clone or fetch the target repo to the replacement host.",
    "2. Check out branch {target_branch}.",
    "3. Copy .ce/state/research/ → {replacement_repo_root}/.ce/state/research/",
    "4. Copy .ce/briefs/ → {replacement_repo_root}/.ce/briefs/",
    "5. Copy .ce/claims/ → {replacement_repo_root}/.ce/claims/",
    "6. If memory archive present: tar -xf memory.tar.gz -C ~/.claude/projects/..."
  ]
}
```

### Output directory layout (when `--commit`)

```
{output_dir}/
  manifest.json
  arc_state/           # mirror of .ce/state/research/
  dispatch_briefs/     # mirror of .ce/briefs/
  dispatch_claims/     # mirror of .ce/claims/
  memory.tar.gz        # only if --include-memory
```

### Error handling

- If `source_root` auto-detect fails (no `.git` found): exit rc=1, stderr message.
- If a data class source dir does not exist: log a warning (stderr), include
  `"missing_sources": ["arc_state"]` in manifest, continue (partial snapshot is
  valid; the controller may not have all classes populated).
- If `--commit` is not passed and `--output-dir` is not the default: still dry-run
  unless `--commit` is explicit. Print `[DRY-RUN] Would write to {output_dir}`.

---

## Unit tests: `validators/tests/unit/test_controller_state_sync.py`

All tests are `pytest.mark.fast`. Use `tmp_path` fixtures; no network, no disk
outside tmp_path (except reading the tool itself for import).

Import the tool as a module (use `importlib.util.spec_from_file_location` pattern
consistent with `test_gen_controller_bootstrap.py`).

Required test functions (minimum set — add more as the implementation warrants):

```python
def test_denylist_excludes_pat_files(tmp_path): ...
    # Create tmp_path/.ce/state/research/leaky.pat
    # Run collect() or equivalent internal function
    # Assert: result.denied_paths contains 'leaky.pat' substring
    # Assert: result.files has no entry with '.pat' suffix

def test_denylist_excludes_pem_files(tmp_path): ...
    # Same pattern for .pem

def test_denylist_excludes_pass_files(tmp_path): ...
    # Same pattern for .pass

def test_denylist_excludes_ce_keys_dir(tmp_path): ...
    # Create tmp_path/.ce-keys/auth.json
    # Assert excluded from files, present in denied_paths

def test_dry_run_default_writes_nothing(tmp_path, monkeypatch): ...
    # Seed tmp_path with .ce/state/research/foo.md
    # Run main(["--source-root", str(tmp_path), "--output-dir", str(tmp_path/"out")])
    # (no --commit flag)
    # Assert tmp_path/"out" does not exist OR is empty

def test_manifest_fields_present(tmp_path): ...
    # Run with --commit --output-dir
    # Load manifest.json
    # Assert all required keys present: schema_version, snapshot_at, source_host,
    #   source_root, files, denied_paths, restore_steps

def test_restore_steps_is_nonempty_list(tmp_path): ...
    # Assert manifest["restore_steps"] is list with len >= 3

def test_arc_state_collected(tmp_path): ...
    # Seed tmp_path/.ce/state/research/RESUME_STATE_foo.md
    # Run with --commit
    # Assert file path appears in manifest["files"]

def test_briefs_collected(tmp_path): ...
    # Seed tmp_path/.ce/briefs/BRIEF_foo.md
    # Assert appears in manifest["files"]

def test_claims_collected(tmp_path): ...
    # Seed tmp_path/.ce/claims/ce-123.md
    # Assert appears in manifest["files"]

def test_missing_source_dir_yields_warning_not_error(tmp_path, capsys): ...
    # Do NOT create .ce/state/research/ in tmp_path
    # Run with --commit
    # Assert rc == 0 (not a hard failure)
    # Assert "missing_sources" in manifest

def test_sha256_in_manifest_per_file(tmp_path): ...
    # Seed a known file, run, verify manifest["files"][0]["sha256"] is 64-char hex

def test_include_memory_flag_adds_memory_class(tmp_path): ...
    # Create fake memory_root in tmp_path
    # Run with --include-memory --memory-root ...
    # Assert "memory" appears in manifest["data_classes"]
```

---

## Changelog fragment (`.ce/changelog/ce-497-controller-state-sync-s1.md`)

```markdown
## ce-497-controller-state-sync-s1

- feat(controller-ops): add controller state snapshot tool — slice 1

  Adds tools/controller/state_sync.py: a governed snapshot script that
  collects controller data classes (b) arc state (.ce/state/research/),
  (c) dispatch state (.ce/briefs/ + .ce/claims/), and optionally (a)
  controller memory as a tar archive, into a structured output directory
  with a JSON manifest (what/when/from-where/sha256s) and restore
  instructions. Dry-run is the default; --commit is explicit opt-in.

  Denylist is hard and test-pinned: *.pat, *.pem, *.pass, *.key, and
  any path under .ce-keys/ are excluded from all snapshots regardless
  of source_root contents and the denied paths are recorded for audit.

  No live push wiring in slice 1 — the controller invokes the script
  and commits the output separately. Push automation is slice 2.

  - **Declared work class:** story
```

---

## PR carrier (`.ce/pr-manifests/ce-497-controller-state-sync-s1.md`)

```markdown
# PR path manifest — ce-497-controller-state-sync-s1

slug: ce-497-controller-state-sync-s1

- **Declared work class:** story

AUTHORIZED_PATHS_COUNT=4

AUTHORIZED_PATHS_SHA256=<compute via canonical sha256("\n".join(sorted(paths)) + "\n")>

\`\`\`text
.ce/changelog/ce-497-controller-state-sync-s1.md
.ce/pr-manifests/ce-497-controller-state-sync-s1.md
tools/controller/state_sync.py
validators/tests/unit/test_controller_state_sync.py
\`\`\`
```

Compute AUTHORIZED_PATHS_SHA256 by running:
```python
import hashlib
paths = sorted([
    ".ce/changelog/ce-497-controller-state-sync-s1.md",
    ".ce/pr-manifests/ce-497-controller-state-sync-s1.md",
    "tools/controller/state_sync.py",
    "validators/tests/unit/test_controller_state_sync.py",
])
print(hashlib.sha256(("\n".join(paths) + "\n").encode()).hexdigest())
```

---

## PR body template (use this verbatim, fill in validation output)

```markdown
## Summary

- Add tools/controller/state_sync.py: governed snapshot tool for controller
  state data classes (arc state, dispatch state, optional memory).
- Dry-run default; hard denylist for secrets (*.pat, *.pem, *.pass, *.key,
  .ce-keys/*) is test-pinned.
- Adds manifest with sha256s, source host, timestamp, and restore instructions.
- Slice 1: no live push wiring. Controller invokes script; commit/push is
  separate (slice 2).

**Declared work class: story**

## Validation

- `PYTHONPATH=validators .venv/bin/python -m pytest validators/tests/unit/test_controller_state_sync.py -v`
- `PYTHONPATH=validators .venv/bin/python -m creator_engine_validator.ce_cli validate-pr --repo-root . --declared-work-class S`

## Gate noise (pre-fill after running validate-pr)

<paste validate-pr output here>

## Closes

Controller state mobility gap — arc state, dispatch state, optional memory
are now snapshot-able into a committed tree with a denylist-pinned manifest.
Part of the main-controller independence program (2026-07-09 mandate).
```

---

## Preflight gate (run before pushing)

```bash
# From worktree root
PYTHONPATH=validators .venv/bin/python -m pytest \
  validators/tests/unit/test_controller_state_sync.py -v

PYTHONPATH=validators .venv/bin/python -m creator_engine_validator.ce_cli \
  validate-pr --repo-root . --declared-work-class S
```

Both must pass GREEN. If validate-pr reports path-manifest mismatch, recompute
AUTHORIZED_PATHS_SHA256 and update the carrier before pushing.

---

## Stop-lines (enforced)

1. No secrets in the snapshot — denylist is absolute and test-pinned.
2. No assertions.yaml modifications.
3. No gate surfaces (`validators/creator_engine_validator/ce_cli.py` is in-flight).
4. No live push wiring — the tool writes to a local output-dir only.
5. No READY file committed.
6. Slice 1 only: do not add `--push` or `--target-repo` live egress.
   Design the `--target-branch` parameter to exist (recorded in manifest
   for slice 2 consumption) but do not implement remote push in this unit.
