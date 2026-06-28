# Brain Ingest Refresh

`scripts/brain-ingest-refresh.sh` is the advisory refresh loop for keeping the
local rebuildable brain recall store current with `MEMORY.md` and `docs/`.
It wraps the existing `ce brain ingest` command; it does not add a new gate,
schema, broker, validator, or CLI surface.

## Behavior

The script discovers Markdown sources from:

- `MEMORY.md`, when present.
- Every `*.md` file under `docs/`.

The default recall database is `<state-root>/brain/recall.sqlite`, matching the
`ce brain ingest` default. The default state root is `.ce/state`.

Before invoking ingest, the script reads the newest existing recall
`recall_entries.as_of` timestamp from the SQLite store. If no store exists, the
store is unreadable, or there is no usable timestamp, it reconciles the full
`MEMORY.md` plus `docs/` corpus. Otherwise, it compares each source file mtime
to that newest `as_of` value and passes only newer source files to
`ce brain ingest`.

If the store contains recall rows for `MEMORY.md` or `docs/**/*.md` files that no
longer exist, the script runs a full corpus reconciliation so the existing
ingest runtime can delete stale chunks for those sources. In the common case,
only changed files are passed to ingest.

Each ingest run supplies the current UTC `--as-of` snapshot timestamp. The
underlying ingest runtime remains content-hash idempotent, so a touched file
whose contents did not change can be selected by the mtime prefilter and still
produce an ingest no-op.

The script takes a non-blocking `flock` under `<state-root>/brain/` before doing
work. If a previous timer invocation is still running, the new invocation exits
0 after reporting that it skipped.

## Configuration

Common options:

```text
scripts/brain-ingest-refresh.sh
scripts/brain-ingest-refresh.sh --state-root .ce/state
scripts/brain-ingest-refresh.sh --db .ce/state/brain/recall.sqlite
scripts/brain-ingest-refresh.sh --embedder vllm-openai --endpoint http://localhost:PORT/v1/embeddings
scripts/brain-ingest-refresh.sh --force
scripts/brain-ingest-refresh.sh --dry-run
```

The same settings can be supplied through environment variables:

```text
CE_BRAIN_INGEST_STATE_ROOT=.ce/state
CE_BRAIN_INGEST_DB=.ce/state/brain/recall.sqlite
CE_BRAIN_INGEST_CE_BIN=ce
CE_BRAIN_INGEST_EMBEDDER=deterministic
CE_BRAIN_INGEST_MODEL_PATH=/path/to/model
CE_BRAIN_INGEST_ENDPOINT=http://localhost:PORT/v1/embeddings
CE_BRAIN_INGEST_ENDPOINT_MODEL_ID=<your-model-id>
CE_BRAIN_INGEST_ENDPOINT_DIM=<embedding-dimension>
```

`--force` bypasses the mtime prefilter and asks ingest to reconcile the full
`MEMORY.md` plus `docs/` corpus. This is useful after manual store surgery or
when validating a new embedder/store pairing.

## systemd User Timer

Example user unit:

```ini
[Unit]
Description=Refresh Creator Engine brain recall store

[Service]
Type=oneshot
WorkingDirectory=/path/to/creator-engine
ExecStart=/path/to/creator-engine/scripts/brain-ingest-refresh.sh
```

Example user timer:

```ini
[Unit]
Description=Run Creator Engine brain recall refresh periodically

[Timer]
OnBootSec=5m
OnUnitActiveSec=30m
Persistent=true

[Install]
WantedBy=timers.target
```

Install those as user units, then run:

```text
systemctl --user daemon-reload
systemctl --user enable --now ce-brain-ingest-refresh.timer
systemctl --user list-timers ce-brain-ingest-refresh.timer
```

## cron

Example cron entry:

```cron
*/30 * * * * cd /path/to/creator-engine && scripts/brain-ingest-refresh.sh >> .ce/state/brain/ingest-refresh.log 2>&1
```

For vLLM-backed refreshes, export the relevant `CE_BRAIN_INGEST_*` variables in
the crontab or source them from a local shell fragment before invoking the
script.

## Advisory Status

This refresh is intentionally advisory and non-gating. It keeps a derived recall
projection fresher for operators and agents, but Markdown remains the source of
truth. A failed timer run should be investigated like operational drift; it must
not block validation, review, merge, or release by itself.
