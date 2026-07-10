---
brief_id: BRIEF_dev1_queue2_20260709
seat: dev-1
seat_kind: host-self-push
units: 2
priority: TOP
grounded_on: origin/main@e3ab6e6aa2d9878a67df517f80aca9536e171165
composed_at: 2026-07-09
---

# BRIEF: Dev-1 queue stock — 2026-07-09 round 2

Two units. Complete U1 first; U2 has explicit preconditions. Validate-pr must pass
GREEN before pushing either PR (FULL validate-pr — not targeted-tests-only; dev-1 is
a host seat with the full test suite).

**G5 size cap (both units are S):** each PR body must contain exactly one bolded
work-class line: `**Declared work class: story**`

---

## UNIT 1 — ce-500 slices a + d — memory caps + preflight TMPDIR staging

```
branch: ce-500-launcher-caps-s2
ticket: contained-seat OOM mitigation — cgroup memory caps + preflight TMPDIR/worker-cap staging
```

### Mandate (2026-07-09)

Dev-4's gVisor sentry held 77 GB of shmem overlay during a full validate-pr run inside
the container; the host had no swap; the OOM-killer fired; the sentry died; the entire
writable worktree was atomically lost. Slices (b) durable bind-mount worktree and (c)
durable config staging landed via PR #891 (MERGED). Two mitigation lanes remain open:

- **(a) No per-seat cgroup memory limit** — containers launch with `HostConfig.Memory = 0`
  (unbounded). Adding an 8 GB default ceiling ensures pytest-triggered sentry balloon is
  contained to the seat, not the host.
- **(d) Preflight TMPDIR on tmpfs** — concurrent full preflights on the host write
  pytest tmpdirs to host /tmp (16 GB tmpfs), which compete with the sentry for RAM. A
  durable wrapper must set TMPDIR to a disk-backed path, cap -n parallelism, and clean up
  after each run.

### Ticket content (ce-ops#500, embedded)

**Incident:** 2026-07-07, dev-3 (ce-vps-codex, VPS host, runsc-gvproxy-ptrace). Host
RAM 30 GB, swap 0. Full validate-pr suite (`-n auto`) running inside container. Sentry
total-vm 51 GB; anon-rss 3.0 GB; shmem-rss 5.6 GB at kill time. OOM-killer terminated
sentry. Writable layer (shmem overlay) evaporated — all in-progress work lost.

**Root-cause addendum (2026-07-07 ~21:4xZ):** host /tmp is a 16 GB tmpfs. Three
concurrent full-suite preflights from dev-1 worker shells (bypassing the ~/.bashrc TMPDIR
redirect from 2026-06-22) held 13 GB of /tmp/pytest-of-ce-dev-1 tmpdirs. tmpfs pages are
RAM; those dirs competed directly with the dev-3 sentry. Related: ce-ops#184.

**Slice (a):** Add a configurable per-seat memory ceiling to the DGX and VPS launcher
scripts (`HostConfig.Memory` / docker `--memory` flag). Default: 8 GB for runsc seats.
Configurable via env var so the operator can increase it for large-suite runs. Seat-level
OOM (pytest dies inside the container) is preferred to host OOM (sentry dies, all work lost).

**Slice (d):** Add a governed preflight wrapper script (`tools/preflight-caps.sh`) that:
1. Creates `$HOME/tmp` if absent.
2. Exports `TMPDIR=$HOME/tmp` (disk-backed; survives /tmp eviction).
3. Caps pytest parallelism at `-n 4` maximum (never `-n auto`).
4. Accepts the same argv as `validate-pr` / pytest and forwards them.
5. After each run, removes `$TMPDIR/pytest-of-*` dirs (bounded cleanup).

---

### Standing obligations — copy verbatim into PR body + checklist

- [ ] Changelog fragment: `.ce/changelog/ce-500-launcher-caps-s2.md`
- [ ] Carrier: `.ce/pr-manifests/ce-500-launcher-caps-s2.md`
      slug field MUST be exactly `ce-500-launcher-caps-s2`
- [ ] Work class line in PR body: `**Declared work class: story**`
      (LEGACY vocab: tiny|story|feature|epic; this is story = S)
- [ ] NEVER commit a file named READY (gate signal, not a commit artifact)
- [ ] No ce-ops issue number references in PR body, commit messages, or code comments
      (use plain English descriptions of the ticket's intent)

---

### Files to produce — COMPLETE territory

All paths below are the ENTIRE diff. No other file may appear in the PR diff.

```
deploy/dgx-runsc/run-codex-runsc.sh            (modify — add CE_DGX_MEMORY_LIMIT)
deploy/vps-runsc/run-vps-runsc.sh              (modify — add CE_VPS_MEMORY_LIMIT)
tools/preflight-caps.sh                        (new)
validators/tests/unit/test_launcher_memory_caps.py  (new)
.ce/changelog/ce-500-launcher-caps-s2.md       (new)
.ce/pr-manifests/ce-500-launcher-caps-s2.md    (new)
```

**Brain-pin precompute (byte-change rule — verify BOTH before first edit):**

```
deploy/dgx-runsc/run-codex-runsc.sh  sha256: ebaffa437dc113a6bc5a731fdda56a3986df5fbed8db8948f794316a8f1bf8a9
deploy/vps-runsc/run-vps-runsc.sh    sha256: 301ab7f7139489aead95cf821c3953b43cbcd814bf0cf3bfc77e3f55ef6bbbc9
```

If your local file does not match, fetch origin/main and reset before editing.
`pyproject.toml` and `validators/workflows/` are frozen — do not touch.

---

### Frozen / in-flight paths — DO NOT TOUCH (U1)

| Path | Owned by |
|---|---|
| `.ce/brain/assertions.yaml` | PR #929 (ABSOLUTE STOP) |
| `validators/creator_engine_validator/ce_cli.py` | PR #929 (open) |
| `docs/reference/cli.md` | PR #929 (open) |
| `validators/creator_engine_validator/launch_runtime.py` | dev-4 in-flight (ce-490) |
| `validators/tests/unit/test_contained_launch_preflight.py` | dev-4 in-flight (ce-490) |
| `tools/controller/state_sync.py` | dev-3 in-flight (ce-497) |
| `docs/operations/CONTROLLER_BOOTSTRAP.md` | dev-1 prior unit (ce-496) |
| `validators/creator_engine_validator/schemas/identity-registry.schema.yaml` | PR #925 (open) |
| `docs/governance/identity-registry.example.yaml` | PR #925 (open) |

No `surfaces/manifest.yaml` edit. No new `AGENTS.md` or `CLAUDE.md` changes.

---

### Launcher memory cap specification

**DGX launcher (`deploy/dgx-runsc/run-codex-runsc.sh`):**

Add to Environment section of usage():
```
  CE_DGX_MEMORY_LIMIT       Docker --memory cgroup cap for this seat. Use docker units
                            (e.g. 8g, 12g, 16g). Set to empty string to disable.
                            Default: 8g  (runsc seats; prevents host OOM from unbounded sentry).
```

In the docker run argv construction, after the existing `--runtime` flag:
```bash
CE_DGX_MEMORY_LIMIT="${CE_DGX_MEMORY_LIMIT:-8g}"
if [[ -n "$CE_DGX_MEMORY_LIMIT" ]]; then
  DOCKER_ARGS+=(--memory "$CE_DGX_MEMORY_LIMIT")
fi
```

Add `CE_DGX_MEMORY_LIMIT` to the dry-run print block and the detach-mode argv echo.

**VPS launcher (`deploy/vps-runsc/run-vps-runsc.sh`):**

Same pattern, env var name `CE_VPS_MEMORY_LIMIT`, default `8g`.

```
  CE_VPS_MEMORY_LIMIT       Docker --memory cgroup cap for this seat. Default: 8g.
                            Set to empty string to disable.
```

---

### Preflight caps wrapper specification (`tools/preflight-caps.sh`)

```bash
#!/usr/bin/env bash
# tools/preflight-caps.sh — Governed CE preflight wrapper
# Enforces: disk-backed TMPDIR, -n parallelism cap, post-run tmpdir cleanup.
# Usage: tools/preflight-caps.sh [validate-pr args...] | tools/preflight-caps.sh pytest [pytest args...]
set -euo pipefail

CE_PREFLIGHT_TMPDIR="${CE_PREFLIGHT_TMPDIR:-$HOME/tmp}"
CE_PREFLIGHT_MAX_WORKERS="${CE_PREFLIGHT_MAX_WORKERS:-4}"

mkdir -p "$CE_PREFLIGHT_TMPDIR"
export TMPDIR="$CE_PREFLIGHT_TMPDIR"

# Warn if TMPDIR is on tmpfs
if mount | grep -q "on $(df --output=target "$TMPDIR" | tail -1) type tmpfs"; then
  echo "[preflight-caps] WARNING: TMPDIR=$TMPDIR is on tmpfs — disk-backed path preferred." >&2
fi

# Forward args; replace -n auto with -n $CE_PREFLIGHT_MAX_WORKERS if present
args=("$@")
for i in "${!args[@]}"; do
  if [[ "${args[$i]}" == "-n" && "${args[$((i+1))]:-}" == "auto" ]]; then
    args[$((i+1))]="$CE_PREFLIGHT_MAX_WORKERS"
    echo "[preflight-caps] Capped -n auto → -n $CE_PREFLIGHT_MAX_WORKERS" >&2
    break
  fi
done

"${args[@]}"
rc=$?

# Post-run cleanup
find "$CE_PREFLIGHT_TMPDIR" -maxdepth 1 -name 'pytest-of-*' -exec rm -rf {} + 2>/dev/null || true

exit $rc
```

---

### Tests: `validators/tests/unit/test_launcher_memory_caps.py`

Use `pytest.mark.fast`. Import pattern from `test_dgx_runsc.py` (bash dry-run via
`CE_DGX_DRY_RUN=1` / `CE_VPS_DRY_RUN=1` with subprocess, or argv inspection via
the existing `run-codex-runsc.sh --dry-run` facility).

Required test functions:

```python
def test_dgx_memory_limit_default_in_argv(tmp_path):
    # Run run-codex-runsc.sh with CE_DGX_DRY_RUN=1
    # Assert "--memory" and "8g" appear in captured stdout

def test_dgx_memory_limit_custom_in_argv(tmp_path):
    # Run with CE_DGX_MEMORY_LIMIT=16g CE_DGX_DRY_RUN=1
    # Assert "--memory" "16g" appears in argv

def test_dgx_memory_limit_disabled_when_empty(tmp_path):
    # Run with CE_DGX_MEMORY_LIMIT="" CE_DGX_DRY_RUN=1
    # Assert "--memory" does NOT appear in argv

def test_vps_memory_limit_default_in_argv(tmp_path):
    # Run run-vps-runsc.sh with CE_VPS_DRY_RUN=1
    # Assert "--memory" and "8g" appear in captured stdout

def test_vps_memory_limit_custom_in_argv(tmp_path):
    # Run with CE_VPS_MEMORY_LIMIT=12g CE_VPS_DRY_RUN=1
    # Assert "--memory" "12g" appears in argv

def test_preflight_caps_script_exists_and_executable():
    # REPO_ROOT / "tools" / "preflight-caps.sh" exists and os.access(X_OK)

def test_preflight_caps_env_defaults_to_home_tmp(tmp_path, monkeypatch):
    # Run tools/preflight-caps.sh echo TMPDIR=$TMPDIR
    # (no CE_PREFLIGHT_TMPDIR set; HOME=tmp_path)
    # Assert output contains str(tmp_path / "tmp")
```

---

### Changelog fragment (`.ce/changelog/ce-500-launcher-caps-s2.md`)

```markdown
## ce-500-launcher-caps-s2

- fix(contained-seat): add cgroup memory cap to DGX and VPS runsc launchers

  Adds `CE_DGX_MEMORY_LIMIT` (default `8g`) and `CE_VPS_MEMORY_LIMIT` (default `8g`)
  env-configurable docker `--memory` flags to the runsc seat launchers. Seats now OOM
  inside the container (pytest dies, work survives in the durable bind-mount worktree)
  rather than triggering a host OOM-kill that evaporates the gVisor sentry and all in-
  progress work. Disable by setting the env var to empty string.

- fix(preflight): add governed TMPDIR + parallelism cap wrapper for host preflight runs

  Adds `tools/preflight-caps.sh`: a thin bash wrapper that exports TMPDIR to a disk-backed
  path (default `$HOME/tmp`), warns if the resolved TMPDIR is on tmpfs, caps `-n auto` to
  `-n 4` (configurable via CE_PREFLIGHT_MAX_WORKERS), forwards all argv to the wrapped
  command, and cleans up `pytest-of-*` tmpdirs post-run. Prevents host-tmpfs RAM
  competition with contained-seat sentry processes during concurrent preflight runs.

  - **Declared work class:** story
```

---

### PR carrier (`.ce/pr-manifests/ce-500-launcher-caps-s2.md`)

```markdown
# PR path manifest — ce-500-launcher-caps-s2

slug: ce-500-launcher-caps-s2

- **Declared work class: story**

AUTHORIZED_PATHS_COUNT=6

AUTHORIZED_PATHS_SHA256=e2d2fd47b54cc731b9237fb263f6219411bdae16afd525f7fcc745971e61bc86

\`\`\`text
.ce/changelog/ce-500-launcher-caps-s2.md
.ce/pr-manifests/ce-500-launcher-caps-s2.md
deploy/dgx-runsc/run-codex-runsc.sh
deploy/vps-runsc/run-vps-runsc.sh
tools/preflight-caps.sh
validators/tests/unit/test_launcher_memory_caps.py
\`\`\`
```

Compute verification:
```python
import hashlib
paths = sorted([
    ".ce/changelog/ce-500-launcher-caps-s2.md",
    ".ce/pr-manifests/ce-500-launcher-caps-s2.md",
    "deploy/dgx-runsc/run-codex-runsc.sh",
    "deploy/vps-runsc/run-vps-runsc.sh",
    "tools/preflight-caps.sh",
    "validators/tests/unit/test_launcher_memory_caps.py",
])
print(hashlib.sha256(("\n".join(paths) + "\n").encode()).hexdigest())
# → e2d2fd47b54cc731b9237fb263f6219411bdae16afd525f7fcc745971e61bc86
```

---

### PR body template (U1)

```markdown
## Summary

- Add CE_DGX_MEMORY_LIMIT (default 8g) and CE_VPS_MEMORY_LIMIT (default 8g) to DGX
  and VPS runsc seat launchers via docker --memory cgroup flag.
- Seat-level OOM (pytest dies, durable worktree survives) replaces host OOM-kill
  (sentry dies, shmem overlay evaporates, all in-progress work lost).
- Add tools/preflight-caps.sh: disk-backed TMPDIR enforcement, -n cap (max 4), and
  post-run pytest tmpdir cleanup for host preflight runs.

**Declared work class: story**

## Validation

- `PYTHONPATH=validators .venv/bin/python -m pytest validators/tests/unit/test_launcher_memory_caps.py -v`
- `TMPDIR=$HOME/tmp PYTHONPATH=validators .venv/bin/python -m creator_engine_validator.ce_cli validate-pr --repo-root . --declared-work-class S`

## Gate noise (pre-fill after running validate-pr)

<paste validate-pr output here>

## Closes

Adds cgroup memory ceiling to contained-seat launchers and a governed preflight
wrapper to prevent host-tmpfs RAM competition — mitigations for the slice (a) and
slice (d) gaps identified in the 2026-07-07 OOM incident debrief.
Slices (b) durable worktree and (c) durable config staging already landed.
```

---

### Preflight gate (U1 — run before pushing)

```bash
# From repo root on dev-1 (host seat — FULL validate-pr required)
PYTHONPATH=validators .venv/bin/python -m pytest \
  validators/tests/unit/test_launcher_memory_caps.py -v

TMPDIR=$HOME/tmp PYTHONPATH=validators .venv/bin/python -m \
  creator_engine_validator.ce_cli validate-pr \
  --repo-root . --declared-work-class S
```

Both must pass GREEN. Path-manifest mismatch → recompute AUTHORIZED_PATHS_SHA256.

---

### Stop-lines (U1)

1. No `launch_runtime.py` edits (dev-4 in-flight).
2. No `ce_cli.py` edits (PR #929 open).
3. No `assertions.yaml` edits.
4. No `surfaces/manifest.yaml` edit.
5. Memory limit is disable-able (CE_DGX_MEMORY_LIMIT="" / CE_VPS_MEMORY_LIMIT="") — do NOT hard-code.
6. No READY file committed.

---
---

## UNIT 2 — ce-470 slice 2 — `ce identity lookup` CLI verb

```
branch: ce-470-identity-lookup-s2
ticket: infra-identity SSOT auto-recall — ce identity lookup <name> CLI verb
```

### PRECONDITIONS (verify before starting U2)

**STOP.** Do not begin U2 until BOTH conditions are confirmed:

1. **PR #925 MERGED** — extends identity-registry schema with `app_name`, `client_id`,
   `tenant_scope` fields. The lookup command reads these fields. Without the schema merge,
   the test fixture registry would use a stale schema.

2. **PR #929 MERGED** — open PR that also modifies
   `validators/creator_engine_validator/ce_cli.py`. Merging #929 first prevents a
   rebase conflict on the same file. After #929 merges, fetch origin/main, verify the
   ce_cli.py SHA below has changed, recompute if needed.

Confirm with:
```bash
gh pr view 925 --repo creator-engine/creator-engine --json state -q '.state'
gh pr view 929 --repo creator-engine/creator-engine --json state -q '.state'
# Both must return "MERGED"
```

**ce_cli.py brain-pin (will shift when #929 merges — recompute after verifying):**

```
validators/creator_engine_validator/ce_cli.py
  sha256 on origin/main NOW: d5e4ad9810296b85949dacedada5d2902cd8e7b1343a797c1711a2c551b3768e
  → after #929 merges this SHA changes; compute fresh sha256sum before editing.
```

---

### Mandate (2026-07-09)

During canary C2 work, the installation ID for the mythos-ce GitHub App had to be
re-derived via an App JWT round-trip because neither the identity registry nor a
programmatic CE-native query path existed to resolve the pointer. The registry
(`infra/identity-registry.yaml`) is the ratified SSOT. Controllers must be able to
resolve identity pointers without env-file spelunking or live API calls.

This slice (ce-470-identity-lookup-s2) delivers the CLI verb:
  `ce identity lookup <name-or-app-id>`

The schema extension (PR #925) is a precondition. This slice is implementation-only:
add the command group and verb, read the registry, print non-secret fields.

---

### Ticket content (ce-ops#470, embedded — slice 2 scope)

**Full ticket scope recap:**
- (a) Registry schema extension: handled by PR #925.
- (b) Recall path — `ce identity lookup`: THIS SLICE.
- (c) Precedence rule in registry header: deferred to follow-on doc sweep.

**Deliverable (slice 2):**

`ce identity lookup <name>` — resolves an app entry from the identity registry.

Behavior:
- Positional arg `<name>` matches `app_name` (exact, case-insensitive) OR numeric `app_id`.
- Registry path: `--registry-path PATH` flag OR `CE_IDENTITY_REGISTRY_PATH` env var.
  **No bundled real registry path.** If neither is set, print an error and exit rc=2.
- Prints non-secret fields to stdout (YAML or key: value pairs):
  `app_name`, `app_id`, `client_id`, `installation_id`, `tenant_scope`,
  `pem_custody` (the POINTER — file:// or openbao-ref: value — NEVER the PEM contents).
- For each `token_storage` pointer: prints the pointer only, never the token value.
- Exit codes: 0 = found and printed, 1 = not found in registry, 2 = registry file
  not found or unreadable.
- Includes a precedence-rule comment in the command handler:
  `# Registry WINS: when a field is present here, it is authoritative over env files and MEMORY.md`

---

### Standing obligations — copy verbatim into PR body + checklist

- [ ] Changelog fragment: `.ce/changelog/ce-470-identity-lookup-s2.md`
- [ ] Carrier: `.ce/pr-manifests/ce-470-identity-lookup-s2.md`
      slug field MUST be exactly `ce-470-identity-lookup-s2`
- [ ] Work class line in PR body: `**Declared work class: story**`
      (LEGACY vocab: tiny|story|feature|epic; this is story = S)
- [ ] NEVER commit a file named READY (gate signal, not a commit artifact)
- [ ] No ce-ops issue number references in PR body, commit messages, or code comments
      (use plain English descriptions of the ticket's intent)

---

### Files to produce — COMPLETE territory

```
validators/creator_engine_validator/ce_cli.py           (modify — add identity group + lookup cmd)
validators/tests/unit/test_identity_lookup_cmd.py       (new)
.ce/changelog/ce-470-identity-lookup-s2.md              (new)
.ce/pr-manifests/ce-470-identity-lookup-s2.md           (new)
```

**Explicitly excluded (all handled by other PRs):**

- `docs/reference/cli.md` — PR #929's territory; do not touch. CLI doc update is a follow-on.
- `infra/identity-registry.yaml` — not in ce_cli.py; do not modify the registry itself.
- `validators/creator_engine_validator/schemas/identity-registry.schema.yaml` — PR #925.
- `docs/governance/identity-registry.example.yaml` — PR #925.

---

### Frozen / in-flight paths — DO NOT TOUCH (U2)

| Path | Owned by |
|---|---|
| `.ce/brain/assertions.yaml` | PR #929 (ABSOLUTE STOP) |
| `docs/reference/cli.md` | PR #929 |
| `validators/creator_engine_validator/schemas/identity-registry.schema.yaml` | PR #925 |
| `docs/governance/identity-registry.example.yaml` | PR #925 |
| `validators/tests/unit/test_identity_registry_schema.py` | PR #925 |
| `validators/creator_engine_validator/launch_runtime.py` | dev-4 in-flight (ce-490) |
| `tools/controller/state_sync.py` | dev-3 in-flight (ce-497) |
| `deploy/dgx-runsc/run-codex-runsc.sh` | U1 of this queue (must be pushed before U2 starts, or treat as frozen) |
| `deploy/vps-runsc/run-vps-runsc.sh` | U1 of this queue |

---

### `ce identity lookup` implementation specification

#### Command group addition in `ce_cli.py`

Add to the main argument parser (near the end of `_build_argparser` or equivalent):

```python
# identity group
identity_group = groups.add_parser("identity", help="identity registry recall")
identity_sub = identity_group.add_subparsers(dest="identity_cmd")

lookup_cmd = identity_sub.add_parser(
    "lookup",
    help="resolve an App entry from the identity registry by name or app_id"
)
lookup_cmd.add_argument(
    "name",
    help="app_name (case-insensitive) or numeric app_id to look up"
)
lookup_cmd.add_argument(
    "--registry-path",
    default=None,
    help=(
        "path to identity-registry YAML "
        "(default: CE_IDENTITY_REGISTRY_PATH env var; error if neither set)"
    )
)
lookup_cmd.add_argument(
    "--output",
    choices=["text", "json"],
    default="text",
    help="output format (default: text key: value pairs)"
)
```

#### Handler function

```python
def _cmd_identity_lookup(args) -> int:
    # Registry WINS: when a field is present here, it is authoritative over env files and MEMORY.md.
    import yaml, json, os, sys
    from pathlib import Path

    registry_path = args.registry_path or os.environ.get("CE_IDENTITY_REGISTRY_PATH")
    if not registry_path:
        print(
            "error: no registry path supplied. "
            "Use --registry-path or set CE_IDENTITY_REGISTRY_PATH.",
            file=sys.stderr,
        )
        return 2

    p = Path(registry_path)
    if not p.exists():
        print(f"error: registry file not found: {p}", file=sys.stderr)
        return 2

    try:
        registry = yaml.safe_load(p.read_text())
    except Exception as e:
        print(f"error: failed to parse registry: {e}", file=sys.stderr)
        return 2

    apps = registry.get("apps", [])
    needle = args.name.lower()
    match = None
    for app in apps:
        if str(app.get("app_id", "")).lower() == needle:
            match = app
            break
        if (app.get("app_name") or "").lower() == needle:
            match = app
            break

    if match is None:
        print(f"not found: no app entry matching '{args.name}'", file=sys.stderr)
        return 1

    # Non-secret fields only.
    # pem_custody is a POINTER (file:// or openbao-ref:), never secret content.
    SAFE_FIELDS = [
        "app_name", "app_id", "client_id", "installation_id",
        "tenant_scope", "pem_custody", "description",
    ]
    output = {k: match[k] for k in SAFE_FIELDS if k in match}

    if args.output == "json":
        print(json.dumps(output, indent=2))
    else:
        for k, v in output.items():
            print(f"{k}: {v}")

    return 0
```

Wire into the main dispatch block alongside other `group == "identity"` handling.

---

### Tests: `validators/tests/unit/test_identity_lookup_cmd.py`

All tests `pytest.mark.fast`. Use `tmp_path` and `monkeypatch`. Do not call live registry.
Use a fixture YAML with synthetic (non-real) values.

```python
FIXTURE_REGISTRY = {
    "repos": [...],       # minimal valid entries; copy schema defaults
    "accounts": [...],
    "apps": [
        {
            "app_name": "mythos-ce",
            "app_id": 4103119,
            "client_id": "Iv23liuJpTEST",
            "installation_id": 141552951,
            "tenant_scope": "account-wide",
            "pem_custody": "file://~/.ce-keys/mythos-ce.test.pem",
        },
        {
            "app_name": "dev-seat-1",
            "app_id": 4027068,
        },
    ],
    "tokens": [...],
    "signing_keys": [...],
    "host_topology": [...],
    "authoring_review_matrix": {...},
}
```

Required test functions:

```python
def test_lookup_by_app_name_returns_zero(tmp_path, monkeypatch): ...
    # Write fixture registry to tmp_path/registry.yaml
    # Run: ce identity lookup mythos-ce --registry-path <path>
    # Assert rc == 0

def test_lookup_by_app_id_returns_zero(tmp_path, monkeypatch): ...
    # Run: ce identity lookup 4103119 --registry-path <path>
    # Assert rc == 0

def test_lookup_not_found_returns_one(tmp_path, monkeypatch): ...
    # Run: ce identity lookup nonexistent-app --registry-path <path>
    # Assert rc == 1

def test_lookup_missing_registry_returns_two(tmp_path, monkeypatch): ...
    # Run with --registry-path pointing to nonexistent file
    # Assert rc == 2

def test_lookup_no_registry_path_returns_two(tmp_path, monkeypatch): ...
    # Ensure CE_IDENTITY_REGISTRY_PATH not set; no --registry-path
    # Assert rc == 2

def test_lookup_prints_non_secret_fields(tmp_path, capsys, monkeypatch): ...
    # Run lookup for mythos-ce
    # Assert stdout contains "app_id", "client_id", "installation_id", "pem_custody"
    # Assert stdout does NOT contain actual PEM content (no "BEGIN RSA", "BEGIN EC")

def test_lookup_pem_custody_is_pointer_not_content(tmp_path, capsys, monkeypatch): ...
    # pem_custody value starts with "file://" or "openbao-ref:"
    # Assert printed pem_custody is the pointer string, not file contents

def test_lookup_json_output_format(tmp_path, capsys, monkeypatch): ...
    # Run with --output json
    # Assert json.loads(stdout) is a dict with "app_name" key

def test_lookup_env_var_registry_path(tmp_path, monkeypatch): ...
    # Set CE_IDENTITY_REGISTRY_PATH env var to fixture path, no --registry-path flag
    # Assert rc == 0
```

---

### Changelog fragment (`.ce/changelog/ce-470-identity-lookup-s2.md`)

```markdown
## ce-470-identity-lookup-s2

- feat(identity): add `ce identity lookup <name>` registry recall CLI verb

  Adds the `identity lookup` subcommand to the CE CLI. Resolves an App entry from
  the identity registry YAML (path via --registry-path flag or CE_IDENTITY_REGISTRY_PATH
  env var) by app_name (case-insensitive) or numeric app_id. Prints non-secret fields
  only: app_name, app_id, client_id, installation_id, tenant_scope, pem_custody pointer.
  pem_custody is a file:// or openbao-ref: pointer — never secret content.

  Exit codes: 0 = found, 1 = not found, 2 = registry unavailable.
  Implements the registry-wins precedence rule: registry values are authoritative over
  env files and prose memory. CLI doc update deferred (follows PR #929 cli.md owner).

  Precondition: identity-registry schema extension (app_name/client_id/tenant_scope
  fields) must be merged before this unit ships.

  - **Declared work class:** story
```

---

### PR carrier (`.ce/pr-manifests/ce-470-identity-lookup-s2.md`)

```markdown
# PR path manifest — ce-470-identity-lookup-s2

slug: ce-470-identity-lookup-s2

- **Declared work class: story**

AUTHORIZED_PATHS_COUNT=4

AUTHORIZED_PATHS_SHA256=49c96343ec5a748458ed2f28c0a6d3b7fb301070c948b5c63d2bc4b4a1e2f71f

\`\`\`text
.ce/changelog/ce-470-identity-lookup-s2.md
.ce/pr-manifests/ce-470-identity-lookup-s2.md
validators/creator_engine_validator/ce_cli.py
validators/tests/unit/test_identity_lookup_cmd.py
\`\`\`
```

Compute verification:
```python
import hashlib
paths = sorted([
    ".ce/changelog/ce-470-identity-lookup-s2.md",
    ".ce/pr-manifests/ce-470-identity-lookup-s2.md",
    "validators/creator_engine_validator/ce_cli.py",
    "validators/tests/unit/test_identity_lookup_cmd.py",
])
print(hashlib.sha256(("\n".join(paths) + "\n").encode()).hexdigest())
# → 49c96343ec5a748458ed2f28c0a6d3b7fb301070c948b5c63d2bc4b4a1e2f71f
```

---

### PR body template (U2)

```markdown
## Summary

- Add `ce identity lookup <name>` subcommand: reads the identity registry YAML
  (path via --registry-path or CE_IDENTITY_REGISTRY_PATH) and prints non-secret
  fields for an App entry matched by app_name or app_id.
- Implements registry-wins precedence rule: registry values are authoritative over
  env files and prose memory.
- pem_custody output is a file:// or openbao-ref: pointer only — no secret content.
- Precondition: identity-registry schema extension (PR that added app_name/client_id/
  tenant_scope) must be merged before this PR lands.

**Declared work class: story**

## Validation

- `PYTHONPATH=validators .venv/bin/python -m pytest validators/tests/unit/test_identity_lookup_cmd.py -v`
- `TMPDIR=$HOME/tmp PYTHONPATH=validators .venv/bin/python -m creator_engine_validator.ce_cli validate-pr --repo-root . --declared-work-class S`

## Gate noise (pre-fill after running validate-pr)

<paste validate-pr output here>

## Closes

Delivers the CE-native registry recall path — controllers and seats can resolve
App identity pointers without env-file spelunking or live API calls. Schema
extension and example entry landed in the preceding PR as a precondition.
```

---

### Preflight gate (U2 — run before pushing)

```bash
# From repo root on dev-1 (host seat — FULL validate-pr required)
PYTHONPATH=validators .venv/bin/python -m pytest \
  validators/tests/unit/test_identity_lookup_cmd.py -v

TMPDIR=$HOME/tmp PYTHONPATH=validators .venv/bin/python -m \
  creator_engine_validator.ce_cli validate-pr \
  --repo-root . --declared-work-class S
```

Both must pass GREEN.

---

### Stop-lines (U2)

1. No `docs/reference/cli.md` edit (PR #929 territory).
2. No `infra/identity-registry.yaml` modification — lookup reads it, does not write it.
3. No `assertions.yaml` edit.
4. No `surfaces/manifest.yaml` edit.
5. pem_custody field MUST print only the pointer string, never file contents.
6. No READY file committed.
7. Do not begin before PR #925 AND PR #929 are both MERGED.
