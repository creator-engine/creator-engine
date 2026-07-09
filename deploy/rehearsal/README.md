# Fresh-Tenant Rehearsal Harness

`deploy/rehearsal/run-rehearsal.sh` runs a fresh-tenant Creator Engine rehearsal
inside a clean Docker container with no repository checkout mounted into it. It
installs CE from the public installer, records the installed CLI version, runs
the first-hour CEO-mode stages, and writes a JSON evidence bundle.

Slice 1 intentionally stubs agent-mediated stages that require a live model,
GitHub, a live pull request, or a completed run. Each stub prints
`CE_REHEARSAL_STUB:` and records `status: "stub"` in the evidence bundle.
A slice-1 bundle with `stubbed > 0` does not constitute a passed rehearsal for
tenant-send gating; gating requires a later slice with live coverage and
Operator sign-off.

## Usage

Dry-run mode is safe and does not require Docker, network, or credentials:

```bash
./deploy/rehearsal/run-rehearsal.sh --dry-run
./deploy/rehearsal/run-rehearsal.sh --list-stages
./deploy/rehearsal/run-rehearsal.sh --help
```

Live mode is fail-closed unless `--live` is supplied:

```bash
CE_REHEARSAL_IMAGE=<your-docker-image> \
CE_REHEARSAL_SITE=<CE_SITE> \
CE_REHEARSAL_EVIDENCE_OUT=<output-path> \
./deploy/rehearsal/run-rehearsal.sh --live
```

The container is started without `--rm` so the cleanup trap can remove it with
`docker rm -f`. The harness mounts nothing from the host checkout.

## Environment

- `CE_REHEARSAL_IMAGE`: Docker image reference. Default tag: `ubuntu:24.04`.
  Use a digest-pinned image reference for reproducible live rehearsals.
- `CE_REHEARSAL_SITE`: installer base URL. Default:
  `https://creator-engine.dev`.
- `CE_REHEARSAL_EVIDENCE_OUT`: evidence JSON output path. Default:
  `/tmp/ce-rehearsal-evidence.json`.
- `CE_REHEARSAL_KEEP_CONTAINER`: set to `1` to keep the live container for
  debugging. Default: `0`.
- `CE_REHEARSAL_CONTAINER_NAME`: container name. Default:
  `ce-p3-rehearsal-$$`.

No secret, token, or credential value is accepted as a default.

## Stages

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

## Stub Inventory

- `ceo_launch`: stubs `ce launch --backend host`; reason:
  `requires_live_model`.
- `ceo_frame`: stubs the conversational Frame stage with simulated input
  `Add a README to the scratch repo.`; reason: `requires_live_model`.
- `ceo_scope`: stubs `ce ratify` because no live Scope exists; verifies
  `ce ratify --help` in live mode; reason: `requires_live_model`.
- `ceo_build`: stubs agent build, PR creation, and independent review; reason:
  `requires_live_model_and_github`.
- `ceo_merge`: stubs `ce merge <scope-id> --run <run-id> --apply`; verifies
  `ce merge --help` in live mode; reason: `requires_live_pr`.
- `ceo_report`: stubs `ce report <scope-id> --run-id <run-id>`; verifies
  `ce report --help` in live mode; reason: `requires_completed_run`.

## Evidence

The evidence bundle format is documented in
`deploy/rehearsal/evidence-format.md`. Slice 1 writes schema version `"1"` and
uses harness version `ce-p3-rehearsal-s1`.
