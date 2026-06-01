# Invalid: connector metadata inlined in Markdown

Connector descriptors belong in `*.ce.yml` sidecars/examples, never inline in
Spec Kit Markdown bodies. The fenced block below is the violation this fixture
exists to catch (`VAL-CONN-NO-INLINE`).

```yaml
connector:
  connector_id: conn-inline-bad
  connector_kind: tracker
```
