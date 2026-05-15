# Transcript Archive Protocol

**Status**: Workflow-hardening normative protocol. Part of the
**minimum repo-native delivery control plane** and **not a Jira
clone**. Layered onto, and subordinate to, the Feature 001 substrate
and the Feature 002 operating model. A fresh clone is sufficient to
apply this protocol; no external tracker credential or network state
is required.

## a. Purpose

A governed batch's implementer-pane transcript records the literal
sequence of tool calls and authored content under the envelope. The
transcript is the only artifact that lets a Source review reconstruct
**how** the implementer arrived at the diff, and the only artifact
that can prove the controller did not silently edit tracked files
from the controller seat (see
[`./CONTROLLER_BOUNDARY_POLICY.md`](./CONTROLLER_BOUNDARY_POLICY.md)
§d).

Without a hashed, archived transcript, the controller's verification
collapses into trust. With one, a fresh-clone reviewer can confirm:

1. The implementer pane consumed the same handoff bytes the controller
   relayed (via the pointer-only protocol in
   [`./NO_COPY_PASTE_PATTERN.md`](./NO_COPY_PASTE_PATTERN.md)).
2. The implementer pane's tool calls produced exactly the diff the
   controller staged.
3. No editing happened from a non-implementer seat under the envelope.

This protocol makes one operational fact answerable from a fresh
clone:

> Where is the implementer-pane transcript for batch `<id>` archived,
> what is its byte-level SHA256, and which on-disk handoff and
> recommended-prompt documents was that transcript authored against?

## b. Source-of-truth relationship

| Upstream source of truth | Role |
|---|---|
| [`./CONTROLLER_BOUNDARY_POLICY.md`](./CONTROLLER_BOUNDARY_POLICY.md) | Role-split rules; the transcript is the controller's evidence that the implementer (and only the implementer) authored under the envelope. |
| [`./NO_COPY_PASTE_PATTERN.md`](./NO_COPY_PASTE_PATTERN.md) | Pointer-only relay; the transcript shows the implementer consumed a path-and-hash relay, not a pasted body. |
| [`./PATH_MANIFEST_FIDELITY_PROTOCOL.md`](./PATH_MANIFEST_FIDELITY_PROTOCOL.md) | The transcript records the implementer's manifest preflight count/hash output. |
| [`../delivery/SCOPE_AUDIT_CHECKLIST.md`](../delivery/SCOPE_AUDIT_CHECKLIST.md) | Scope audit consumes the transcript as one of its evidence inputs. |
| [`./session-continuity-protocol.md`](./session-continuity-protocol.md) | Instance-local-vs-upstream split. Transcripts live in instance-local archive paths, NOT in upstream `docs/` or `specs/`. |

## c. Archive location

Transcripts MUST be archived in an **instance-local** directory that
is gitignored from the upstream tree. The conventional path shape is

```text
.hermes/transcripts/<UTC-timestamp>-<batch-slug>-<role>-pane-%<pane-id>.txt
```

where:

- `<UTC-timestamp>` follows the compact `YYYYMMDDThhmmssZ` shape used
  by the rest of the Hermes ecosystem.
- `<batch-slug>` is a short kebab-case slug identifying the envelope.
- `<role>` is `architect`, `implementer`, `controller`, or
  `source` — the role the pane is playing under the envelope.
- `<pane-id>` is an instance-local pane identifier; this field MUST
  NOT propagate into upstream tracked artifacts beyond appearing in
  the transcript filename itself.

The archive path is recorded in the **handoff** document on disk so
that any verifier can locate it deterministically. The handoff
records the **expected** SHA256 of the archive at the moment the
batch is closed; verifiers recompute that SHA256 to confirm
non-tampering.

`.hermes/` is gitignored. The transcript filename and its hash MAY be
cited in tracked completion reports as governance evidence; the
transcript **body** MUST NOT be committed because the body routinely
contains instance-local paths, pane identifiers, and other facts
prohibited from the upstream tree per
[`../delivery/NEXT_TASK_PROTOCOL.md`](../delivery/NEXT_TASK_PROTOCOL.md)
§e.

## d. Closing a transcript: the archive/hash/close protocol

At the moment the implementer reaches the envelope's stop line, the
controller (or, where applicable, the implementer pane itself before
relinquishing the seat) performs the following steps **in order**:

1. **Flush the transcript.** Save the pane's full transcript to the
   archive path named in §c. The flush includes the pointer-only
   prompt the implementer consumed; the implementer's preflight
   manifest recomputation output; every tool call (with arguments)
   and tool result; every message authored under the envelope; and
   the implementer's report-back ending at the stop line.
2. **Hash the archive.** Compute the byte-level SHA256 of the archive
   file with a reproducible command (see §e). Both
   `python3 -c "import hashlib, sys; print(hashlib.sha256(open(sys.argv[1],'rb').read()).hexdigest())" <path>`
   and `sha256sum <path>` are acceptable; both compute the same hash.
3. **Record in the handoff.** Write or update the handoff document on
   disk so that the document records the transcript's archive path
   and its SHA256. If the handoff is the on-disk pointer file from
   [`./NO_COPY_PASTE_PATTERN.md`](./NO_COPY_PASTE_PATTERN.md), the
   record lives in the handoff's transcript section. The handoff
   itself MAY be re-hashed and re-relayed under a fresh pointer if
   downstream verifiers need the updated hash.
4. **Close the pane.** Mark the implementer pane closed for the
   batch. Any subsequent text in the pane after the stop line is
   **not** part of the batch's transcript and MUST NOT be folded into
   the archive after step 2 has produced its hash.

This four-step **archive / hash / close** sequence is the protocol
the workflow-hardening initiative names; downstream policies refer to
it by that name.

## e. Hash command shapes

The byte-level SHA256 of the archive:

```bash
python3 -c "import hashlib, sys; print(hashlib.sha256(open(sys.argv[1],'rb').read()).hexdigest())" .hermes/transcripts/<file>.txt
```

or

```bash
sha256sum .hermes/transcripts/<file>.txt
```

The SHA256 of the archive is a **byte-level** hash, not a normalized
hash. This is intentional: any byte-level change to the archive after
closure is detectable as a mismatch against the recorded hash.

(The transcript's content MAY contain unsorted, non-normalized text —
that is fine. The hash is over raw bytes; normalization belongs to
the path-manifest hash, not to the transcript hash.)

## f. Verifier-side reproducibility

A Source review consuming the closed batch reads:

1. The handoff on disk, including its recorded transcript archive
   path and expected SHA256.
2. The archive at that path.
3. The recomputed SHA256 of the archive on the reviewer's
   filesystem.

If the recomputed hash matches the handoff's recorded hash, the
transcript is the one the implementer pane closed and the
controller's report-back is reproducible. If it does not match, the
batch's evidence chain is broken regardless of how clean the diff
looks; the reviewer halts and escalates to Source.

## g. What the transcript MUST NOT contain

The transcript reflects the implementer pane's session. To preserve
the audit value of the archive, the transcript MUST NOT contain:

- Secrets, credentials, tokens, account identifiers, or environment
  variables holding such values.
- Source ratification approvals dictated through chat rather than
  through a ratified envelope.
- Any text intended to substitute for the on-disk handoff (paste-back
  of the envelope body, etc.) — the pointer-only relay rule in
  [`./NO_COPY_PASTE_PATTERN.md`](./NO_COPY_PASTE_PATTERN.md) applies
  to the transcript itself.

The transcript MAY legitimately contain absolute filesystem paths
specific to the operator's workstation; that is one of the reasons
the archive lives under the gitignored `.hermes/` tree rather than in
upstream `docs/`.

## h. Acceptance posture

This document satisfies the workflow-hardening requirement to add a
transcript archive / hash / close protocol:

- Names the archive location convention in §c, including
  instance-local-vs-upstream segregation.
- Names the archive / hash / close sequence in §d, ordered so that
  the hash is computed before any post-stop-line text can taint it.
- Names the hash command shapes in §e.
- Names the verifier-side reproducibility protocol in §f.
- Names content the transcript MUST NOT contain in §g.
