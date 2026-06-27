# ce-ops#293 observe-only belt daemon evidence

Date: 2026-06-27
Checkout: `/tmp/wt-ce293`
Mode: successful observe-only work-pickup poll

The target command shape for the daemon is observe-only. The command below
intentionally omits `--claim`, `--enable-launch`, and `--allow-ambient-gh`.
`CE_PICKUP_TOKEN` was supplied from the remote token and is redacted here; the
token was never printed.

## Command

```sh
PYTHONPATH=/tmp/ce298-test-pkgs:/tmp/wt-ce293/validators \
  CE_PICKUP_TOKEN=<redacted> \
  TMPDIR=/var/tmp \
  python3 -m creator_engine_validator.ce_cli pickup poll \
    --identity ce-dev-4 \
    --repo creator-engine/creator-engine \
    --label enhancement \
    --json
```

## Observed JSON snippet

```json
{
  "ok": true,
  "count": 5,
  "items": [
    {
      "repo": "creator-engine/creator-engine",
      "number": 9,
      "title": "Sprint 0: enforce controller/architect role boundaries"
    },
    {
      "repo": "creator-engine/creator-engine",
      "number": 89,
      "title": "CE runtime: refuse duplicate live Controller launches for same profile/controller_id"
    },
    {
      "repo": "creator-engine/creator-engine",
      "number": 104,
      "title": "CE Review Gate: enforce distinct reviewer venue for independent PR review"
    },
    {
      "repo": "creator-engine/creator-engine",
      "number": 83,
      "title": "Add a bounded CE role/sub-agent for GitHub Issue intake and creation"
    },
    {
      "repo": "creator-engine/creator-engine",
      "number": 157,
      "title": "CE UX: Controller context-window observability..."
    }
  ]
}
```

## Result

The live observe-only source CLI poll succeeded with five labeled pickup items.
No claim or launch flags were present in the command.
