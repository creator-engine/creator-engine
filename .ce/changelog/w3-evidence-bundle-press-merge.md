# W3 Press-Merge Evidence Bundle

- Adds a CLI-agnostic `press_merge_bundle` aggregator and deterministic Markdown
  renderer for PR-keyed merge-read evidence bundles.
- Proposes `press-merge-bundle.schema.yaml` as a new no-authority schema rather
  than overloading the generic fan-in packet shape.
- Adds focused unit coverage for deterministic bytes, no-authority refusal,
  stale/missing evidence refs, renderer stability, and optional computer-use
  evidence.
