# Invalid: federated identity binding metadata inlined in Markdown

Federated identity binding records belong in `*.ce.yml` sidecars/examples, never
inline in Spec Kit Markdown bodies. The fenced block below is the violation this
fixture exists to catch (`VAL-FIB-NO-INLINE`).

```yaml
federated_identity_binding:
  record_id: fib-inline-bad
  record_kind: federated_identity_binding
```
