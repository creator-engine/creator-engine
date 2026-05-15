# Pointer-Only Visible-Pane Pattern (No Copy-Paste)

**Status**: Workflow-hardening normative protocol. Part of the
**minimum repo-native delivery control plane** and **not a Jira
clone**. Layered onto, and subordinate to, the Feature 001 substrate
and the Feature 002 operating model. A fresh clone is sufficient to
apply this pattern; no external tracker credential or network state
is required.

## a. Purpose

When a controller hands an envelope, a handoff, or any other governed
prompt to an implementer pane by **pasting** the body of the prompt
into the implementer's input, two failure modes follow with high
probability:

1. **Markdown / path-boundary corruption.** Paste pipelines (chat
   panes, terminal multiplexers, clipboards) routinely collapse
   double-underscores, mangle code fences, drop or duplicate code
   blocks, normalize whitespace, lose blank lines, or rewrite
   filenames such that
   `validators/creator_engine_validator/checks/__init__.py` arrives
   in the implementer's pane as
   `validators/creator_engine_validator/checks/init.py`. <!-- path_manifest_fidelity: pedagogical -->
   The implementer then authors against the wrong manifest and the
   resulting batch corrupts the substrate.
2. **Evidence-chain corruption.** The pasted prompt is a transient
   transcript artifact: no two operators see exactly the same text;
   no verifier can recompute a hash; no archive of the prompt is
   guaranteed; and the implementer pane's source authorization is
   indistinguishable from chat noise.

The pointer-only pattern eliminates both failure modes. The
controller relays a **pointer to a file on disk** plus the file's
**expected SHA256**, and the implementer pane treats that file as the
source of truth for everything it does under the envelope.

This pattern makes one operational fact answerable from a fresh
clone:

> Which file on disk is the implementer pane authorized to consume,
> and what is the expected hash of that file at the moment the
> implementer consumes it?

## b. Source-of-truth relationship

| Upstream source of truth | Role |
|---|---|
| [`./CONTROLLER_BOUNDARY_POLICY.md`](./CONTROLLER_BOUNDARY_POLICY.md) | Role split between Source / controller / architect / implementer; bounds what the controller may do. |
| [`./PATH_MANIFEST_FIDELITY_PROTOCOL.md`](./PATH_MANIFEST_FIDELITY_PROTOCOL.md) | Count/hash protocol that the pointer file embeds and the implementer recomputes. |
| [`./TRANSCRIPT_ARCHIVE_PROTOCOL.md`](./TRANSCRIPT_ARCHIVE_PROTOCOL.md) | How the implementer-pane transcript is archived after the work is done. |
| [`../delivery/ASSIGNMENT_ENVELOPE_TEMPLATE.md`](../delivery/ASSIGNMENT_ENVELOPE_TEMPLATE.md) §c.1, §c.2 | Envelope header / ratification fields the pointer file points at. |
| `docs/delivery/RISK_REGISTER.md` R-012 | Path-manifest / Markdown corruption as a standing risk. |

## c. The pointer-only relay shape

A pointer-only visible-pane prompt has three parts and **only** three
parts:

1. A repo-relative or absolute path to a file on disk that contains
   the full envelope, handoff, or recommended-prompt body. That file
   MUST already exist on disk before the controller sends the
   prompt.
2. The **expected SHA256** of that file at the moment the prompt is
   sent.
3. A short instruction telling the implementer pane to read the file
   directly and to verify the hash before consumption. The
   instruction MUST NOT include the body of the file.

The canonical visible-pane prompt template is
[`../../templates/hermes/visible-pane-pointer-prompt.template.md`](../../templates/hermes/visible-pane-pointer-prompt.template.md).
A filled prompt is itself short, hand-typeable, and contains no
Markdown that a paste pipeline could corrupt into a different path.

## d. What MUST NOT appear in a pointer-only relay

- The full body of the handoff / envelope / recommended prompt.
- Long path manifests inside code fences (they belong inside the
  pointer file, where the implementer reads them under
  [`./PATH_MANIFEST_FIDELITY_PROTOCOL.md`](./PATH_MANIFEST_FIDELITY_PROTOCOL.md)).
- Copy-pasted shell commands containing the manifest as a heredoc.
- Multi-line code blocks of any kind whose corruption could change
  the meaning of a path or hash.
- Substantive instruction bodies that re-derive the envelope.

The implementer pane MUST refuse to consume a relay that smuggles
envelope substance back into the chat. Refusal text reads, in
substance: *"Pointer-only relay required; re-send a path-and-hash
pointer per `docs/operations/NO_COPY_PASTE_PATTERN.md`."*

## e. Implementer-pane verification on receipt

On receiving a pointer-only prompt, the implementer pane:

1. Reads the file at the pointer path using a tool that operates
   directly on the filesystem (e.g., `Read`). Pasting the file body
   back into the prompt MUST NOT be a step of any kind.
2. Computes the SHA256 of the file on disk. The exact command shape
   is recorded in [§g](#g-suggested-commands) below.
3. Compares the computed hash to the controller-relayed expected
   hash. Mismatch is a halt.
4. Parses the pointer file's path manifest per
   [`./PATH_MANIFEST_FIDELITY_PROTOCOL.md`](./PATH_MANIFEST_FIDELITY_PROTOCOL.md)
   §c and recomputes the manifest count/hash. Mismatch is a halt.
5. Treats the pointer file as the **only** source of truth for
   allowed paths, prohibited surfaces, validation commands, scope
   audit commands, stop condition, and report-back format. Anything
   the controller said in chat that is not also present in the
   pointer file is non-authoritative.

If the controller sends additional chat after the pointer-only prompt,
the implementer pane treats those messages as informal context only.
Substantive corrections require the controller to update the pointer
file on disk and relay a new path-and-hash pointer.

## f. Controller obligations

The controller MUST:

1. Write the envelope / handoff / recommended-prompt body to a file
   on disk **before** sending the relay.
2. Compute the file's SHA256 with a reproducible command.
3. Send the pointer-only prompt containing exactly: the path, the
   expected hash, and the short consume-and-verify instruction. The
   relay MUST follow
   [`../../templates/hermes/visible-pane-pointer-prompt.template.md`](../../templates/hermes/visible-pane-pointer-prompt.template.md).
4. If the controller subsequently amends the pointer file, the
   controller MUST relay a fresh pointer with the new hash. The
   implementer pane MUST NOT consume the amended file under the old
   hash.
5. Archive the implementer pane's transcript at end-of-batch per
   [`./TRANSCRIPT_ARCHIVE_PROTOCOL.md`](./TRANSCRIPT_ARCHIVE_PROTOCOL.md).

The controller MUST NOT paste the envelope body, even "for
convenience" or "so the chat record is complete." The chat record is
not the source of truth; the file on disk is.

## g. Suggested commands

Compute a file SHA256 with the platform-portable shape:

```bash
python3 -c "import hashlib, sys; print(hashlib.sha256(open(sys.argv[1],'rb').read()).hexdigest())" <path>
```

or

```bash
sha256sum <path>
```

Both compute the byte-level SHA256 over the file as it sits on disk.
The pointer-only prompt MUST use the byte-level SHA256, not a
normalized-line-ending hash, because a hash mismatch under any
representation correctly halts the implementer.

(Note that the **path manifest** hash inside the pointer file is a
*normalized* hash per
[`./PATH_MANIFEST_FIDELITY_PROTOCOL.md`](./PATH_MANIFEST_FIDELITY_PROTOCOL.md)
§c; the two hashes serve different purposes and MUST NOT be
conflated.)

## h. Worked example shape

A pointer-only relay reads, in substance:

```text
read your next handoff from: <repo-relative-or-absolute-path>
expected sha256: <64-hex-chars>
verify the hash before consumption; do not consume any chat-pasted
body
```

That is the entire authorized shape. The visible-pane pointer prompt
template
[`../../templates/hermes/visible-pane-pointer-prompt.template.md`](../../templates/hermes/visible-pane-pointer-prompt.template.md)
records the exact wording.

## i. Why this matters: the `__init__.py` regression class

A specific, observed failure mode motivates this pattern. Pasted
relays have, more than once, transformed the literal path
`validators/creator_engine_validator/checks/__init__.py` into the
corrupted path `validators/creator_engine_validator/checks/init.py` <!-- path_manifest_fidelity: pedagogical -->
because the paste pipeline interpreted the surrounding Markdown as
bold-underscore formatting and stripped the leading and trailing
double underscores. The corrupted path does not exist in the Python
package; tracked-file authoring against it silently creates a new,
non-registry-running module while leaving the real registry-running
`__init__.py` untouched. The substrate quietly diverges from the
envelope.

The pointer-only pattern eliminates this failure mode because the
manifest never appears in chat: it lives in the pointer file on disk
where Markdown is preserved byte-exact and where a hash check makes
any corruption visible.

The `path_manifest_fidelity` validator's
`path_manifest_init_py_corruption` error class
([`./PATH_MANIFEST_FIDELITY_PROTOCOL.md`](./PATH_MANIFEST_FIDELITY_PROTOCOL.md)
§e) is the verifier-side backstop for this specific regression.

## j. Acceptance posture

This document satisfies the workflow-hardening requirement to codify
the no-copy-paste / pointer-only visible-pane pattern:

- Names the pointer-only relay shape (path + expected SHA256 +
  consume-and-verify instruction) in §c.
- Names what MUST NOT appear in a relay in §d.
- Names the implementer-pane verification protocol in §e.
- Names the controller's relay obligations in §f.
- Names the canonical hash command shapes in §g and the worked
  pointer-only relay shape in §h.
- Names the `__init__.py` regression class motivating the pattern in
  §i.
