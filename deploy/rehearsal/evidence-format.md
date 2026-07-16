# Fresh-Tenant Rehearsal Evidence Format

The Fresh-Tenant Rehearsal harness writes one machine-readable JSON evidence
bundle. The default output path is:

```bash
${CE_REHEARSAL_EVIDENCE_OUT:-/tmp/ce-rehearsal-evidence.json}
```

The schema version for slice 1 is `"1"`. Any incompatible field rename, field
removal, status change, or required-field semantic change must bump
`schema_version` in a later slice.

A slice-1 bundle with `stubbed > 0` does not constitute a passed rehearsal for
tenant-send gating; gating requires a later slice with live coverage and
Operator sign-off.

## Schema

```json
{
  "schema_version": "1",
  "rehearsal_id": "<uuid-v4>",
  "run_timestamp_utc": "<ISO-8601>",
  "harness_version": "ce-p3-rehearsal-s1",
  "container_image": "<image used>",
  "ce_package_version": "<from cev3 --version or null>",
  "ce_site": "<CE_SITE value used>",
  "stages": [
    {
      "stage": "<name>",
      "status": "pass | fail | stub | skip",
      "started_at": "<ISO-8601>",
      "completed_at": "<ISO-8601>",
      "duration_ms": 0,
      "stub_reason": "<string or null>",
      "exit_code": 0,
      "notes": "<string or null>"
    }
  ],
  "summary": {
    "total_stages": 0,
    "passed": 0,
    "failed": 0,
    "stubbed": 0,
    "skipped": 0
  },
  "failures": [
    {
      "stage": "<name>",
      "message": "<string>"
    }
  ]
}
```

## Top-Level Fields

- `schema_version`: evidence schema version. Slice 1 always writes `"1"`.
- `rehearsal_id`: UUID v4 generated for this harness invocation.
- `run_timestamp_utc`: UTC timestamp for the evidence bundle write.
- `harness_version`: harness identity. Slice 1 writes `ce-p3-rehearsal-s1`.
- `container_image`: Docker image tag used for the clean container.
- `ce_package_version`: captured `cev3 --version` output when available, else
  `ce --version` output when available, else `null`.
- `ce_site`: installer base URL supplied through `CE_REHEARSAL_SITE`.
- `stages`: ordered list of stage records.
- `summary`: counts derived from `stages`.
- `failures`: one entry per failed stage, preserving the stage name and failure
  message.

## Stage Fields

- `stage`: exact stage name emitted by `run-rehearsal.sh --list-stages`.
- `status`: one of:
  - `pass`: the stage executed successfully.
  - `fail`: the stage failed and added an entry to `failures`.
  - `stub`: the stage was intentionally simulated because it requires a live
    model, live pull request, completed run, or GitHub surface.
  - `skip`: the stage was intentionally skipped.
- `started_at`: UTC timestamp captured before the stage action.
- `completed_at`: UTC timestamp captured after the stage action.
- `duration_ms`: elapsed stage wall time in milliseconds.
- `stub_reason`: reason for a stubbed stage, otherwise `null`.
- `exit_code`: command exit code when the stage records a command probe,
  otherwise `null`.
- `notes`: short implementation-specific details, or `null`.

## Stage Names

Slice 1 uses these stage names in order:

```text
provision
install
install_verify
onboard
scratch_repo
ceo_launch
ceo_frame
ceo_scope
ceo_build
ceo_merge
ceo_report
teardown
```

## Release-smoke result

The governed `--release-smoke` mode does not emit the timestamped slice-1
rehearsal bundle. It writes this value-free canonical JSON contract instead:

```json
{"container_image":"registry.example/ce-smoke@sha256:<64 lowercase hex>","containment":{"host_checkout_mount":false},"schema_version":"1","stages":{"install":"passed","install_verify":"passed"},"summary":{"failed":0,"stubbed":0}}
```

The producer accepts exactly these fields and values. Tags, checkout mounts,
failed/stubbed counts, missing stages, non-passing stages, additional fields,
or non-canonical JSON are refused before unsigned evidence bytes are emitted.
The result contains no timestamps, IDs, logs, host paths, credentials, or
secret-shaped values.
