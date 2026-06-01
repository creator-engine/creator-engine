# Invalid example — inline extension-hook-contract metadata in Markdown

Extension-hook-contract metadata belongs in `*.ce.yml` sidecars/examples, never inline
in a Markdown body. The fenced YAML below declares an `extension_contract` key in prose
and MUST be rejected (VAL-EXT-NO-INLINE).

```yaml
extension_contract:
  extension_id: ext-inline
  extension_kind: hook_pack
  ring: ring_1
```
