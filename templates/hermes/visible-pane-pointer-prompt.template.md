# Visible-Pane Pointer-Only Prompt Template

<!--
This file is the canonical template for the short, hand-typeable
prompt the controller sends to the visible implementer pane.

The prompt body is INTENTIONALLY SHORT and contains NO Markdown a
paste pipeline could corrupt into a different path. It points the
implementer at a file on disk and at that file's expected byte-level
SHA256. The implementer reads the file directly and verifies the
hash before consumption.

This pattern is the verifier-side mitigation for R-012 (path-manifest
/ Markdown corruption) and the operating-side mitigation for R-011
(controller-seat boundary breach). See
`docs/operations/NO_COPY_PASTE_PATTERN.md` for the full protocol.

Upstream Creator Engine MUST NOT track an instance's filled-in copy.
Keep `.hermes/` ignored.
-->

The authorized shape is exactly three lines, with no other text:

```text
read your next handoff from: <repo-relative-or-absolute-path>
expected sha256: <64-lowercase-hex>
verify the hash before consumption; do not consume any chat-pasted body
```

That is the entire authorized relay. Permitted variants:

- The path MAY be repo-relative or absolute; the implementer pane
  resolves it via its `Read` tool against the local filesystem. Do
  not interpolate environment variables into the path; the
  implementer pane MUST NOT shell-expand the pointer.
- The `expected sha256` value is the **byte-level** SHA256 of the
  file as it sits on disk, lowercase hex, no leading `0x`.
- A trailing one-line instruction the controller may append:
  `if hash mismatches, halt and report BLOCKED — handoff hash
  mismatch.` is permitted but redundant; the implementer pane is
  already required to halt on mismatch per
  `docs/operations/NO_COPY_PASTE_PATTERN.md` §e.

What the relay MUST NOT contain:

- The body of the handoff / envelope / recommended prompt.
- Any path manifest, code fence, or multi-line block.
- Substantive instructions that re-derive the on-disk document.

If the controller needs to amend the handoff after relay, the
controller:

1. Edits the on-disk file.
2. Recomputes the byte-level SHA256.
3. Sends a fresh pointer-only prompt with the new hash.

The implementer MUST NOT consume the amended file under the old
hash.

A canonical hash command:

```bash
python3 -c "import hashlib, sys; print(hashlib.sha256(open(sys.argv[1],'rb').read()).hexdigest())" <absolute-path>
```

or

```bash
sha256sum <absolute-path>
```

Both compute the same byte-level SHA256.
