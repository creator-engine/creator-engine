# PR path manifest — feat(site): ship v5 consumer redesign (NVIDIA OpenShell safety) + archive v4

This file is the carrier for this PR's closed path manifest under
`docs/operations/PATH_MANIFEST_FIDELITY_PROTOCOL.md`. CI passes it to
`verify-path-manifest --base <PR base sha> --manifest .ce/pr-path-manifest.md`
and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set
below. The fidelity scan (`scan-path-manifest`) requires the declared count and
SHA256 to match the fenced block.

Scope: **SITE — ship the Operator-approved v5 consumer-facing redesign.** Replace
the live `docs/index.html` (v4 vocab-tidy) with the approved v5 redesign: a
"two-altitude descent" consumer reframe (idea→app promise descending to the
mechanism proof), a neon-lime create/safe/go accent layered over Control-Room
Violet, a dedicated **Built for security with NVIDIA OpenShell** section (OpenShell
isolates the runtime, CE governs the work — complementary infrastructure, not an
NVIDIA product), and a consumer-worry→CE-mechanism safety-mapping table. The canon
vocabulary is retained (Frame → Shape → Build → Review → Ship; Scope card; ◆
Completion Report; grader-outside-the-agent). Per the website-archive policy, the
outgoing v4 bytes are snapshotted verbatim to
`site-archive/index-v4-vocab-canon.html` and the `site-archive/README.md` ledger is
updated (v4 promoted to an archived row; v5 = current — live). **No
code/schema/test/example change**; `docs/` is the only Pages-served path touched.

- **base:** `e0cfbef6d2172a2edf963ba078873e0cb76eeb37`.
- **canonicalization:** `sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=4

AUTHORIZED_PATHS_SHA256=a296917ab22b7e7b586d5dca54c5adc5434596c7decee2f1a82e23c07da14485

```text
.ce/pr-path-manifest.md
docs/index.html
site-archive/README.md
site-archive/index-v4-vocab-canon.html
```
